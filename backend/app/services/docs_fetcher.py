"""
GitHub documentation fetcher for dependency setup.

Pulls README, tutorials, examples, and docs/ from GitHub repos, chunks the
content, and writes to data/documents/{dep_name}.jsonl for later embedding.
"""

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

DOCS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "documents"

# Patterns for files we want — ordered by usefulness for debugging errors.
# CHANGELOG and CONTRIBUTING are intentionally excluded (version history /
# developer onboarding are not helpful when diagnosing CI failures).
_INCLUDE_PATTERNS = [
    r"^README(\.(md|rst|txt))?$",
    r"^(docs?|documentation)/.*\.(md|rst|txt)$",
    r"^(tutorials?)/.*\.(md|rst|txt)$",
    r"^(examples?)/.*\.(md|rst|txt)$",
    r"^(guide|howto|how-to|cookbook)/.*\.(md|rst|txt)$",
]

# Skip auto-generated / maintenance content that is not useful for debugging
_EXCLUDE_PATTERNS = [
    r"/api[_-]?reference/",
    r"/_autosummary/",
    r"/generated/",
    # Developer / maintenance files — kept out even when nested inside docs/
    r"(^|/)CHANGELOG(\.(md|rst|txt))?$",
    r"(^|/)CONTRIBUTING(\.(md|rst|txt))?$",
    r"(^|/)GOVERNANCE(\.(md|rst|txt))?$",
    r"(^|/)HISTORY(\.(md|rst|txt))?$",
    r"(^|/)CHANGES(\.(md|rst|txt))?$",
    r"/(release|migration|upgrade)[_-]?(guide|notes)?(\.(md|rst|txt))?$",
]

_MAX_FILE_BYTES = 150_000  # skip files larger than this
_MAX_FILES = 80            # global default; overridden by max_files parameter
_CHUNK_TARGET = 800        # target chars per chunk

# Fetch-depth presets exposed to callers
DEPTH_PRESETS: dict[str, int] = {
    "quick":    15,   # ~16 API requests/dep  — safe for unauthenticated (60 req/hr)
    "balanced": 40,   # ~41 API requests/dep  — fits ~120 deps/hr authenticated
    "full":     80,   # ~81 API requests/dep  — maximum quality; requires token for >1 dep/hr
}


async def check_rate_limit(github_token: Optional[str] = None) -> dict:
    """Return current GitHub API rate limit (remaining, limit, reset_at, reset_in_sec).

    Uses the stored/env token when provided.  Falls back to anonymous if none.
    """
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


def _candidate_priority(path: str) -> int:
    """
    Return sort key for candidate file paths (lower = fetched first).
    When the repo has more matching files than _MAX_FILES, we fetch the most
    useful content first: user-facing docs before raw README.
    """
    lp = path.lower()
    if re.match(r'^docs?/', lp) or re.match(r'^documentation/', lp):
        return 0
    if re.match(r'^tutorials?/', lp):
        return 1
    if re.match(r'^examples?/', lp):
        return 2
    if re.match(r'^(guide|howto|how-to|cookbook)/', lp):
        return 3
    if re.match(r'^readme', lp):
        return 10
    return 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_dep_name(name: str) -> str:
    """Prevent path-traversal in JSONL filenames."""
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', name) or ".." in name:
        raise ValueError(f"Invalid dependency name: {name!r}")
    return name


def _parse_github_url(url: str) -> tuple[str, str]:
    """
    Extract (owner, repo) from a github.com URL.
    Raises ValueError for non-GitHub or malformed URLs.
    """
    from urllib.parse import urlparse
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


def _chunk_text(text: str) -> list[str]:
    """
    Split markdown/RST text into paragraph-based chunks targeting ~800 chars each.

    Fenced code blocks (``` or ~~~) are kept intact — they are never split
    across chunk boundaries, which preserves executable examples in the output.
    Strips YAML front matter and RST underline decorators first.
    """
    # Strip YAML front matter
    text = re.sub(r'^---[\s\S]*?---\s*\n', '', text, count=1)
    # Strip RST header decorators (lines of ===, ----, ~~~~)
    text = re.sub(r'^[=\-~#+*^]{4,}\s*$', '', text, flags=re.MULTILINE)

    # Protect fenced code blocks so blank lines inside them don't become splits
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
        # Restore code block placeholder
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
        # Non-GitHub custom URL — nothing we can do
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
) -> Dict[str, Any]:
    """
    Fetch documentation from a GitHub repository and save to
    data/documents/{dep_name}.jsonl.

    max_files overrides the global _MAX_FILES cap — use DEPTH_PRESETS values
    (15/40/80) to control request budget vs. documentation completeness.

    Returns a dict with:
      status: "done" | "warning" | "error"
      chunks: int
      files:  int
      requests_used: int   — actual GitHub API requests consumed
      message: str (only on warning/error)
    """
    dep_name = _validate_dep_name(dep_name)
    owner, repo = _parse_github_url(repo_url)
    file_cap = max_files if max_files is not None else _MAX_FILES

    # Prefer caller-supplied token, then environment variable
    token = github_token or os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "DEPFIX/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:

        # Discover the default branch (main / master / develop)
        tree: Optional[list] = None
        branch_used: Optional[str] = None
        for branch in ("main", "master", "develop"):
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
                headers=headers,
            )
            if resp.status_code == 200:
                tree = resp.json().get("tree", [])
                branch_used = branch
                break
            if resp.status_code == 403:
                remaining = resp.headers.get("x-ratelimit-remaining", "")
                if remaining == "0" or "rate limit" in resp.text.lower():
                    return {
                        "status": "error",
                        "message": (
                            "GitHub API rate limit exceeded. "
                            "Add a GitHub personal access token in Setup → Config to increase the limit."
                        ),
                        "chunks": 0,
                        "files": 0,
                    }

        if tree is None:
            return {"status": "error", "message": f"Cannot access {owner}/{repo} tree", "chunks": 0, "files": 0}

        # Select files matching include patterns, then sort by usefulness
        all_candidates = [
            item["path"]
            for item in tree
            if item.get("type") == "blob"
            and _matches_include(item["path"])
            and not _matches_exclude(item["path"])
            and item.get("size", 0) <= _MAX_FILE_BYTES
        ]
        # docs/ first, tutorials/ second, README last — ensures best content
        # is fetched whenever the repo exceeds the file cap
        candidates = sorted(all_candidates, key=_candidate_priority)[:file_cap]

        if not candidates:
            return {"status": "warning", "message": "No documentation files found", "chunks": 0, "files": 0}

        chunks_data: list[dict] = []
        chunk_idx = 0
        rate_limited_mid_fetch = False
        requests_used = 1  # already used 1 for the tree

        for path in candidates:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                params={"ref": branch_used},
                headers=headers,
            )
            if resp.status_code == 403:
                remaining = resp.headers.get("x-ratelimit-remaining", "")
                if remaining == "0" or "rate limit" in resp.text.lower():
                    # Save whatever we gathered before the limit hit
                    rate_limited_mid_fetch = True
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
            source_url = (
                f"https://raw.githubusercontent.com/{owner}/{repo}/{branch_used}/{path}"
            )

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

    if not chunks_data:
        return {
            "status": "warning",
            "message": "Files found but no content could be extracted",
            "chunks": 0,
            "files": len(candidates),
            "requests_used": requests_used,
        }

    # Write JSONL
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DOCS_DIR / f"{dep_name}.jsonl"
    with open(out_path, "w", encoding="utf-8") as fh:
        for entry in chunks_data:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if rate_limited_mid_fetch:
        return {
            "status": "warning",
            "message": (
                f"GitHub rate limit hit after {chunk_idx} chunks — partial docs saved. "
                "Add a GitHub token in Setup → Config for full coverage."
            ),
            "chunks": chunk_idx,
            "files": len(candidates),
            "requests_used": requests_used,
        }

    return {"status": "done", "chunks": chunk_idx, "files": len(candidates), "requests_used": requests_used}
