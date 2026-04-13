"""
GitHub documentation fetcher for dependency setup.

Three-tier documentation pipeline:
  1. Primary GitHub repo  — README / docs / tutorials
  2. Secondary GitHub repos — e.g. pytorch/tutorials, MONAI/tutorials
  3. Official docs website  — Sphinx / ReadTheDocs HTML scraping

Results are merged, deduplicated by content hash, and written to
data/documents/{dep_name}.jsonl for later embedding.
"""

import asyncio
import base64
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx

DOCS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "documents"

# Patterns for files we want — ordered by usefulness for debugging errors.
# CHANGELOG and CONTRIBUTING are intentionally excluded.
_INCLUDE_PATTERNS = [
    r"^README(\.(md|rst|txt))?$",
    r"^(docs?|documentation)/.*\.(md|rst|txt)$",
    r"^(tutorials?)/.*\.(md|rst|txt)$",
    r"^(examples?)/.*\.(md|rst|txt)$",
    r"^(guide|howto|how-to|cookbook)/.*\.(md|rst|txt)$",
    # Non-standard source dirs (e.g. pytorch/tutorials repo layout)
    r"^[a-z]+_source/.*\.(md|rst|txt)$",
    r"^(beginner|intermediate|advanced|recipes)/.*\.(md|rst|txt)$",
]

_EXCLUDE_PATTERNS = [
    r"/api[_-]?reference/",
    r"/_autosummary/",
    r"/generated/",
    r"(^|/)CHANGELOG(\.(md|rst|txt))?$",
    r"(^|/)CONTRIBUTING(\.(md|rst|txt))?$",
    r"(^|/)GOVERNANCE(\.(md|rst|txt))?$",
    r"(^|/)HISTORY(\.(md|rst|txt))?$",
    r"(^|/)CHANGES(\.(md|rst|txt))?$",
    r"/(release|migration|upgrade)[_-]?(guide|notes)?(\.(md|rst|txt))?$",
]

_MAX_FILE_BYTES = 150_000
_MAX_FILES = 80
_CHUNK_TARGET = 800

_WEB_RATE_DELAY = 0.3   # seconds between page requests
_WEB_MAX_PAGES  = 15    # max pages scraped per library
_WEB_SKIP_EXTS  = re.compile(
    r'\.(zip|tar\.gz|gz|png|jpg|gif|svg|pdf|css|js|ico|woff|woff2|ttf|eot)$',
    re.IGNORECASE,
)

# Fetch-depth presets exposed to callers
DEPTH_PRESETS: dict[str, int] = {
    "quick":    15,
    "balanced": 40,
    "full":     80,
}


# ---------------------------------------------------------------------------
# Rate-limit helper
# ---------------------------------------------------------------------------

async def check_rate_limit(github_token: Optional[str] = None) -> dict:
    """Return current GitHub API rate limit (remaining, limit, reset_at, reset_in_sec)."""
    import time as _time
    headers: dict = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "DEPFIX/1.0",
    }
    token = github_token or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get("https://api.github.com/rate_limit", headers=headers)
        if resp.status_code == 200:
            data = resp.json().get("rate", {})
            remaining = data.get("remaining", 0)
            reset_at = data.get("reset", 0)
            return {
                "remaining": remaining,
                "limit": data.get("limit", 60),
                "reset_at": reset_at,
                "reset_in_sec": max(0, int(reset_at - _time.time())),
            }
    except Exception:
        pass
    return {"remaining": 0, "limit": 60, "reset_at": 0, "reset_in_sec": 3600}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_dep_name(name: str) -> str:
    """Prevent path-traversal in JSONL filenames."""
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', name) or ".." in name:
        raise ValueError(f"Invalid dependency name: {name!r}")
    return name


def _parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a github.com URL."""
    parsed = urlparse(url)
    if parsed.netloc.lower().replace("www.", "") != "github.com":
        raise ValueError(f"Only github.com URLs are supported, got: {url!r}")
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from: {url!r}")
    owner, repo = parts[0], parts[1].replace(".git", "")
    if not re.match(r'^[a-zA-Z0-9._-]+$', owner) or not re.match(r'^[a-zA-Z0-9._-]+$', repo):
        raise ValueError(f"Invalid owner/repo in URL: {url!r}")
    return owner, repo


def _matches_include(path: str) -> bool:
    for p in _INCLUDE_PATTERNS:
        if re.search(p, path, re.IGNORECASE):
            return True
    return False


def _matches_exclude(path: str) -> bool:
    for p in _EXCLUDE_PATTERNS:
        if re.search(p, path, re.IGNORECASE):
            return True
    return False


def _candidate_priority(path: str) -> int:
    """Lower = fetched first."""
    lp = path.lower()
    if re.match(r'^docs?/', lp) or re.match(r'^documentation/', lp):
        return 0
    if re.match(r'^tutorials?/', lp) or re.search(r'_source/', lp):
        return 1
    if re.match(r'^examples?/', lp):
        return 2
    if re.match(r'^(guide|howto|how-to|cookbook|beginner|intermediate|advanced|recipes)/', lp):
        return 3
    if re.match(r'^readme', lp):
        return 10
    return 5


def _chunk_text(text: str) -> list[str]:
    """
    Split markdown/RST text into paragraph-based chunks targeting ~800 chars.
    Fenced code blocks are kept intact. Strips YAML front matter first.
    """
    text = re.sub(r'^---[\s\S]*?---\s*\n', '', text, count=1)
    text = re.sub(r'^[=\-~#+*^]{4,}\s*$', '', text, flags=re.MULTILINE)

    code_blocks: list[str] = []

    def _save_block(m: re.Match) -> str:
        code_blocks.append(m.group(0))
        return f"\n\n__CODE_BLOCK_{len(code_blocks) - 1}__\n\n"

    text = re.sub(r'(?s)```.*?```|~~~.*?~~~', _save_block, text)

    paragraphs = re.split(r'\n{2,}', text)
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para or len(para) < 10:
            continue
        cb_match = re.fullmatch(r'__CODE_BLOCK_(\d+)__', para)
        if cb_match:
            para = code_blocks[int(cb_match.group(1))]

        if current_len + len(para) > _CHUNK_TARGET and current_parts:
            chunk = "\n\n".join(current_parts)
            if len(chunk) >= 50:
                chunks.append(chunk)
            current_parts = [para]
            current_len = len(para)
        else:
            current_parts.append(para)
            current_len += len(para)

    if current_parts:
        chunk = "\n\n".join(current_parts)
        if len(chunk) >= 50:
            chunks.append(chunk)

    return chunks


def _content_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()


# ---------------------------------------------------------------------------
# Private: fetch one GitHub repo (no file I/O)
# ---------------------------------------------------------------------------

async def _fetch_repo_chunks(
    dep_name: str,
    repo_url: str,
    headers: dict,
    client: httpx.AsyncClient,
    file_cap: int,
    chunk_idx_start: int = 0,
) -> Tuple[List[dict], int, bool]:
    """
    Walk one GitHub repo tree, fetch matching doc files, return chunks.

    Returns:
        (chunks_data, requests_used, rate_limited_mid_fetch)
    """
    try:
        owner, repo = _parse_github_url(repo_url)
    except ValueError:
        return [], 0, False

    tree: Optional[list] = None
    branch_used: Optional[str] = None
    requests_used = 0

    for branch in ("main", "master", "develop"):
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
            headers=headers,
        )
        requests_used += 1
        if resp.status_code == 200:
            tree = resp.json().get("tree", [])
            branch_used = branch
            break
        if resp.status_code == 403:
            remaining = resp.headers.get("x-ratelimit-remaining", "")
            if remaining == "0" or "rate limit" in resp.text.lower():
                return [], requests_used, True

    if tree is None:
        return [], requests_used, False

    all_candidates = [
        item["path"]
        for item in tree
        if item.get("type") == "blob"
        and _matches_include(item["path"])
        and not _matches_exclude(item["path"])
        and item.get("size", 0) <= _MAX_FILE_BYTES
    ]
    candidates = sorted(all_candidates, key=_candidate_priority)[:file_cap]

    if not candidates:
        return [], requests_used, False

    chunks_data: list[dict] = []
    chunk_idx = chunk_idx_start
    rate_limited_mid = False

    for path in candidates:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            params={"ref": branch_used},
            headers=headers,
        )
        if resp.status_code == 403:
            remaining = resp.headers.get("x-ratelimit-remaining", "")
            if remaining == "0" or "rate limit" in resp.text.lower():
                rate_limited_mid = True
                break
        if resp.status_code != 200:
            continue

        requests_used += 1
        content_b64 = resp.json().get("content", "")
        try:
            raw = base64.b64decode(content_b64.replace("\n", "")).decode("utf-8", errors="ignore")
        except Exception:
            continue

        ext = Path(path).suffix.lstrip(".")
        section = Path(path).stem
        source_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch_used}/{path}"

        for chunk_text in _chunk_text(raw):
            chunks_data.append({
                "library": dep_name,
                "source": source_url,
                "content": chunk_text,
                "section": section,
                "filetype": ext,
                "chunk_idx": chunk_idx,
            })
            chunk_idx += 1

    return chunks_data, requests_used, rate_limited_mid


# ---------------------------------------------------------------------------
# Private: scrape official docs website
# ---------------------------------------------------------------------------

def _extract_page_text(html: str) -> str:
    """Extract main readable content from a Sphinx/ReadTheDocs HTML page."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content elements
    for tag in soup.select(
        "nav, aside, header, footer, script, style, "
        "[role=navigation], [role=banner], [role=contentinfo], "
        ".sidebar, .sphinxsidebar, .toctree-wrapper, "
        ".wy-nav-side, .wy-side-nav-search, "
        "#searchbox, .related, .headerlink, "
        "[aria-label=breadcrumb]"
    ):
        tag.decompose()

    # Try progressively broader content containers
    for selector in (
        "div[role=main]",
        ".rst-content",
        "article",
        "main",
        ".body",
        ".document",
        "#content",
    ):
        node = soup.select_one(selector)
        if node:
            text = node.get_text(separator="\n", strip=True)
            if len(text) > 100:
                return text

    return soup.get_text(separator="\n", strip=True)


def _extract_doc_links(html: str, current_url: str, base_path_prefix: str) -> list[str]:
    """Extract same-domain doc links from an HTML page."""
    from bs4 import BeautifulSoup

    base_domain = urlparse(current_url).netloc
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith(("#", "mailto:", "javascript:")):
            continue
        full = urljoin(current_url, href)
        p = urlparse(full)
        if p.netloc != base_domain:
            continue
        # Stay within the docs path prefix (avoid crawling to root site)
        if not p.path.startswith(base_path_prefix):
            continue
        # Skip binary/media files
        if _WEB_SKIP_EXTS.search(p.path):
            continue
        # Normalise: strip fragment, normalise trailing slash
        clean = p._replace(fragment="", query="").geturl()
        links.append(clean)

    return links


async def _fetch_web_chunks(
    dep_name: str,
    root_url: str,
    client: httpx.AsyncClient,
    chunk_idx_start: int = 0,
) -> List[dict]:
    """
    Scrape an official documentation website (Sphinx/ReadTheDocs).
    Discovers linked pages on the same domain + path prefix, extracts main
    content, chunks it. Politely rate-limits at 0.3s per page.
    """
    parsed_root = urlparse(root_url)
    # Path prefix: /en/stable/ or /en/latest/ or /projects/foo/en/latest/
    # We stay within this prefix to avoid crawling the whole site.
    base_path_prefix = parsed_root.path.rstrip("/") + "/"
    if base_path_prefix == "/":
        base_path_prefix = "/"

    def _page_priority(url: str) -> int:
        path = urlparse(url).path.lower()
        for i, kw in enumerate([
            "install", "quick", "getting-start", "user", "guide",
            "tutorial", "error", "trouble", "faq", "api",
        ]):
            if kw in path:
                return i
        return 99

    headers = {"User-Agent": "DEPFIX/1.0 (documentation indexer; non-commercial)"}
    chunks: list[dict] = []
    visited: set[str] = set()
    queue: list[str] = [root_url]
    chunk_idx = chunk_idx_start
    first_page = True

    while queue and len(visited) < _WEB_MAX_PAGES:
        queue.sort(key=_page_priority)
        url = queue.pop(0)

        # Normalise trailing slash for dedup
        url_norm = url.rstrip("/") + "/"
        if url_norm in visited:
            continue
        visited.add(url_norm)

        if not first_page:
            await asyncio.sleep(_WEB_RATE_DELAY)
        first_page = False

        try:
            resp = await client.get(url, headers=headers, timeout=20)
            if resp.status_code != 200:
                continue
            if "html" not in resp.headers.get("content-type", ""):
                continue

            html = resp.text

            # Discover more pages from every visited page (sidebar is on all pages)
            new_links = _extract_doc_links(html, resp.url.__str__(), base_path_prefix)
            for link in new_links:
                link_norm = link.rstrip("/") + "/"
                if link_norm not in visited and link not in queue:
                    if len(queue) < _WEB_MAX_PAGES * 3:
                        queue.append(link)

            text = _extract_page_text(html)
            # Clean up excessive blank lines
            text = re.sub(r'\n{3,}', '\n\n', text)
            if len(text) < 150:
                continue

            # Page title for section field
            from bs4 import BeautifulSoup
            soup_title = BeautifulSoup(html, "html.parser")
            h1 = soup_title.find("h1")
            section = h1.get_text(strip=True) if h1 else (
                urlparse(url).path.rstrip("/").rsplit("/", 1)[-1] or "index"
            )

            for chunk in _chunk_text(text):
                chunks.append({
                    "library": dep_name,
                    "source": url,
                    "content": chunk,
                    "section": section,
                    "filetype": "html",
                    "chunk_idx": chunk_idx,
                })
                chunk_idx += 1

        except (httpx.TimeoutException, httpx.HTTPError):
            continue
        except Exception:
            continue

    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def resolve_github_url(
    dep_name: str,
    custom_repo_url: Optional[str] = None,
    known_urls: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Return a GitHub repo URL for a dependency.

    Priority:
      1. custom_repo_url (if provided and is github.com)
      2. known_urls dict (from AVAILABLE_DEPENDENCIES)
      3. PyPI JSON API project_urls lookup
    """
    if custom_repo_url:
        if "github.com" in custom_repo_url:
            return custom_repo_url.rstrip("/")
        return None

    if known_urls and dep_name in known_urls:
        url = known_urls[dep_name]
        if url and "github.com" in url:
            return url.rstrip("/")

    # Fall back to PyPI
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                f"https://pypi.org/pypi/{dep_name}/json",
                headers={"User-Agent": "DEPFIX/1.0"},
            )
            if resp.status_code == 200:
                info = resp.json().get("info", {})
                project_urls = info.get("project_urls") or {}
                for key in ["Source", "Repository", "Code", "GitHub"]:
                    url = project_urls.get(key, "")
                    if url and "github.com" in url:
                        return url.rstrip("/")
                home = info.get("home_page", "")
                if home and "github.com" in home:
                    return home.rstrip("/")
    except Exception:
        pass

    return None


async def fetch_and_save_docs(
    dep_name: str,
    repo_url: str,
    github_token: Optional[str] = None,
    max_files: Optional[int] = None,
    secondary_repos: Optional[List[str]] = None,
    scrape_docs_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch documentation from GitHub repo(s) and optionally an official docs
    website, then save to data/documents/{dep_name}.jsonl.

    Sources fetched:
      1. Primary repo (repo_url)
      2. Secondary repos (secondary_repos) — each gets max_files//2 file budget
      3. Official docs site (scrape_docs_url) — HTML scraping via BeautifulSoup

    Returns a dict with:
      status: "done" | "warning" | "error"
      chunks: int  — total chunks across all sources
      files:  int  — files fetched from primary repo
      requests_used: int
      sources: dict — per-source chunk counts
      message: str (only on warning/error)
    """
    dep_name = _validate_dep_name(dep_name)
    file_cap = max_files if max_files is not None else _MAX_FILES
    secondary_cap = max(5, file_cap // 2)

    token = github_token or os.getenv("GITHUB_TOKEN")
    gh_headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "DEPFIX/1.0",
    }
    if token:
        gh_headers["Authorization"] = f"Bearer {token}"

    all_chunks: list[dict] = []
    total_requests = 0
    primary_files = 0
    rate_limited = False
    source_counts: dict[str, int] = {}

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:

        # ── Tier 1: Primary GitHub repo ────────────────────────────────────
        primary_chunks, req_used, rl = await _fetch_repo_chunks(
            dep_name, repo_url, gh_headers, client, file_cap, chunk_idx_start=0
        )
        total_requests += req_used
        rate_limited = rl

        # Estimate primary file count from unique sources
        primary_files = len({c["source"] for c in primary_chunks})
        all_chunks.extend(primary_chunks)
        source_counts["primary"] = len(primary_chunks)

        # ── Tier 2: Secondary GitHub repos ─────────────────────────────────
        secondary_chunk_count = 0
        if not rate_limited and secondary_repos:
            for sec_url in secondary_repos:
                sec_chunks, req_used, rl = await _fetch_repo_chunks(
                    dep_name, sec_url, gh_headers, client,
                    file_cap=secondary_cap,
                    chunk_idx_start=len(all_chunks),
                )
                total_requests += req_used
                all_chunks.extend(sec_chunks)
                secondary_chunk_count += len(sec_chunks)
                if rl:
                    rate_limited = True
                    break
        source_counts["secondary_repos"] = secondary_chunk_count

        # ── Tier 3: Official docs website ──────────────────────────────────
        web_chunk_count = 0
        if scrape_docs_url:
            try:
                web_chunks = await _fetch_web_chunks(
                    dep_name, scrape_docs_url, client,
                    chunk_idx_start=len(all_chunks),
                )
                all_chunks.extend(web_chunks)
                web_chunk_count = len(web_chunks)
            except Exception:
                pass  # web scraping failure never blocks the pipeline
        source_counts["web_scrape"] = web_chunk_count

    # ── Deduplicate by content hash ─────────────────────────────────────────
    seen_hashes: set[str] = set()
    unique_chunks: list[dict] = []
    for chunk in all_chunks:
        h = _content_hash(chunk["content"])
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_chunks.append(chunk)

    # Re-index chunk_idx after dedup
    for i, chunk in enumerate(unique_chunks):
        chunk["chunk_idx"] = i

    # ── Handle empty result ─────────────────────────────────────────────────
    if not unique_chunks:
        if rate_limited:
            return {
                "status": "error",
                "message": (
                    "GitHub API rate limit exceeded. "
                    "Add a GitHub personal access token in Setup → Config."
                ),
                "chunks": 0, "files": 0, "requests_used": total_requests,
                "sources": source_counts,
            }
        return {
            "status": "warning",
            "message": "No documentation content found across all sources",
            "chunks": 0, "files": 0, "requests_used": total_requests,
            "sources": source_counts,
        }

    # ── Write JSONL ─────────────────────────────────────────────────────────
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DOCS_DIR / f"{dep_name}.jsonl"
    with open(out_path, "w", encoding="utf-8") as fh:
        for entry in unique_chunks:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    status = "warning" if rate_limited else "done"
    result: Dict[str, Any] = {
        "status": status,
        "chunks": len(unique_chunks),
        "files": primary_files,
        "requests_used": total_requests,
        "sources": source_counts,
    }
    if rate_limited:
        result["message"] = (
            f"GitHub rate limit hit — partial docs saved ({len(unique_chunks)} chunks). "
            "Add a GitHub token in Setup → Config for full coverage."
        )
    return result
