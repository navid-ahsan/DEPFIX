#!/usr/bin/env python3
"""
Improved Documentation Scraper — GitHub API edition
====================================================

Strategy vs the legacy scrape.py:
  1. Uses the GitHub REST API (file tree + raw content download) instead of HTML
     scraping.  This produces clean Markdown/RST with no nav/sidebar noise.
  2. Targets ONLY error-relevant file types per library:
       install*, troubleshoot*, faq*, error*, exception*, migration*, quickstart*,
       getting_started*, common_issues*, configuration*, compatibility*
     These are the files that contain traceback text and fix instructions that the
     CI/CD RAG actually needs to match against.
  3. Excludes junk: C++ docs, changelogs, generated API reference stubs, static
     assets, examples that are just Python files.
  4. Chunks content by headings (not by file), keeping chunks ≤800 chars with
     100-char overlap, so small errors are retrieved precisely.
  5. Strips RST/Sphinx markup (directives, role markers, toctree entries) before
     embedding — raw :class:`Foo` tokens pollute vector space.
  6. Writes {library, source, content, section, filetype, chunk_idx} per line to
     data/documents/{library}.jsonl, overwriting the old file.

Rate limits:
  • Unauthenticated: 60 req/hr — sufficient only for tiny runs.
  • Set GITHUB_TOKEN env var for 5 000 req/hr (free with any GitHub account).

Usage:
    # Single library:
    python scripts/scrape_docs.py --library torch

    # All libraries:
    python scripts/scrape_docs.py

    # Limit pages per library (useful for quick testing):
    python scripts/scrape_docs.py --max-files 20
"""

import os
import re
import sys
import json
import time
import base64
import argparse
import textwrap
from pathlib import Path
from typing import Iterator

import requests

# ── CONFIG ───────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("data/documents")

# fmt: off
#  repo         — GitHub "owner/repo"
#  docs_path    — directory inside the repo that contains documentation files
#  include_ext  — file extensions to consider
#  priority_re  — regex matched against filename (case-insensitive);
#                 if it matches the file gets processed FIRST
#  skip_path_re — regex matched against the full file path;
#                 files whose path matches are skipped entirely
LIBRARY_SOURCES = {
    "torch": {
        "repo":         "pytorch/pytorch",
        "docs_path":    "docs/source",
        "include_ext":  {".rst"},
        "priority_re":  r"install|error|exception|troubleshoot|faq|note|warning|migration|cuda|device",
        "skip_path_re": r"cpp/|c_api/|jit_language|onnx_diagnostic|CHANGELOG|autograd.*md|_static",
    },
    "monai": {
        "repo":         "Project-MONAI/MONAI",
        "docs_path":    "docs/source",
        "include_ext":  {".rst", ".md"},
        "priority_re":  r"install|error|exception|troubleshoot|faq|getting_start|quickstart|losses|metrics|transforms",
        "skip_path_re": r"apidocs/|CHANGELOG|_static",
    },
    "flower": {
        "repo":         "adap/flower",
        "docs_path":    "doc/source",
        "include_ext":  {".rst", ".md"},
        "priority_re":  r"install|error|exception|troubleshoot|faq|quickstart|tutorial|strategy|simulation",
        "skip_path_re": r"ref-api/|CHANGELOG",
    },
    "torchvision": {
        "repo":         "pytorch/vision",
        "docs_path":    "docs/source",
        "include_ext":  {".rst"},
        "priority_re":  r"install|error|exception|troubleshoot|faq|getting_start|transform|dataset",
        "skip_path_re": r"CHANGELOG|_static|generated/",
    },
    "torchaudio": {
        "repo":         "pytorch/audio",
        "docs_path":    "docs/source",
        "include_ext":  {".rst"},
        "priority_re":  r"install|error|exception|troubleshoot|faq|getting_start|backend|io",
        "skip_path_re": r"CHANGELOG|_static|generated/",
    },
    "scikit-learn": {
        "repo":         "scikit-learn/scikit-learn",
        "docs_path":    "doc/modules",
        "include_ext":  {".rst"},
        "priority_re":  r"install|error|exception|troubleshoot|faq|common_pitfall|preprocessing|pipeline",
        "skip_path_re": r"CHANGELOG|generated/|_static",
    },
    "requests": {
        "repo":         "psf/requests",
        "docs_path":    "docs",
        "include_ext":  {".rst"},
        "priority_re":  r"install|error|exception|troubleshoot|faq|quickstart|advanced|authentication",
        "skip_path_re": r"CHANGELOG|_static",
    },
    "waitress": {
        "repo":         "Pylons/waitress",
        "docs_path":    "docs",
        "include_ext":  {".rst"},
        "priority_re":  r"install|error|exception|troubleshoot|faq|quickstart|runner|logging",
        "skip_path_re": r"CHANGELOG|_static",
    },
    "pyramid": {
        "repo":         "Pylons/pyramid",
        "docs_path":    "docs/narr",
        "include_ext":  {".rst"},
        "priority_re":  r"install|error|exception|troubleshoot|faq|quickstart|config|view|route",
        "skip_path_re": r"CHANGELOG|_static",
    },
    "tenseal": {
        "repo":         "OpenMined/TenSEAL",
        "docs_path":    "tutorials",
        "include_ext":  {".md", ".rst"},
        "priority_re":  r"install|error|exception|troubleshoot|faq|getting_start|quickstart|context",
        "skip_path_re": r"CHANGELOG|_static",
    },
}
# fmt: on

# ── CONSTANTS ────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 800   # chars
CHUNK_OVERLAP = 100   # chars
GITHUB_API    = "https://api.github.com"
REQUEST_DELAY = 0.15  # seconds between API calls (be polite)


# ── GITHUB API HELPERS ───────────────────────────────────────────────────────
def _github_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(url: str, params: dict | None = None) -> dict | list | None:
    """GET a GitHub API URL, handling rate-limit back-off automatically."""
    headers = _github_headers()
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
        except requests.RequestException as exc:
            print(f"    network error: {exc}", file=sys.stderr)
            time.sleep(5)
            continue

        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait  = max(1, reset - int(time.time())) + 5
            print(f"    rate limited — sleeping {wait}s …")
            time.sleep(wait)
            continue

        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            print(f"    HTTP {resp.status_code} for {url}")
            return None

        return resp.json()

    return None


def list_repo_tree(repo: str, docs_path: str) -> list[dict]:
    """Return all blobs under docs_path using the git-tree API (one request)."""
    # Resolve the default branch first
    repo_meta = _get(f"{GITHUB_API}/repos/{repo}")
    if not repo_meta:
        print(f"  Could not read repo metadata for {repo}", file=sys.stderr)
        return []
    default_branch = repo_meta.get("default_branch", "main")

    time.sleep(REQUEST_DELAY)
    tree_data = _get(
        f"{GITHUB_API}/repos/{repo}/git/trees/{default_branch}",
        params={"recursive": "1"},
    )
    if not tree_data or "tree" not in tree_data:
        print(f"  Could not fetch file tree for {repo}:{docs_path}", file=sys.stderr)
        return []

    blobs = [
        entry for entry in tree_data["tree"]
        if entry["type"] == "blob" and entry["path"].startswith(docs_path)
    ]
    return blobs


def fetch_file_content(repo: str, file_path: str) -> str | None:
    """Download a single file's text content via the contents API."""
    time.sleep(REQUEST_DELAY)
    data = _get(f"{GITHUB_API}/repos/{repo}/contents/{file_path}")
    if not data or "content" not in data:
        return None
    try:
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        return None


# ── CONTENT CLEANING ─────────────────────────────────────────────────────────
_RST_DIRECTIVE = re.compile(r"^\s*\.\. [\w-]+::.*$", re.MULTILINE)
_RST_ROLE      = re.compile(r":[a-z]+:`[^`]*`")
_RST_SUBST     = re.compile(r"\|[^|]+\|")
_RST_TOCTREE   = re.compile(r"^\s{0,3}:(?:maxdepth|numbered|hidden|caption|glob):.*$", re.MULTILINE)
_MD_BADGE      = re.compile(r"!\[.*?\]\(.*?\)")
_MULTI_BLANK   = re.compile(r"\n{3,}")
_TRAILING_WS   = re.compile(r"[ \t]+$", re.MULTILINE)


def clean_doc_text(text: str, filetype: str) -> str:
    if filetype == ".rst":
        text = _RST_DIRECTIVE.sub("", text)
        text = _RST_TOCTREE.sub("", text)
        text = _RST_ROLE.sub(lambda m: m.group(0).split("`")[1], text)
        text = _RST_SUBST.sub("", text)
    elif filetype in {".md", ".markdown"}:
        text = _MD_BADGE.sub("", text)

    text = _TRAILING_WS.sub("", text)
    text = _MULTI_BLANK.sub("\n\n", text)
    return text.strip()


# ── CHUNKING ─────────────────────────────────────────────────────────────────
_HEADING_RST = re.compile(r"^[^\n]+\n[=\-~^\"#*+]{3,}\s*$", re.MULTILINE)
_HEADING_MD  = re.compile(r"^#{1,4} .+$", re.MULTILINE)


def _split_by_headings(text: str, filetype: str) -> list[tuple[str, str]]:
    """Return list of (section_title, section_body) pairs."""
    pattern = _HEADING_MD if filetype in {".md", ".markdown"} else _HEADING_RST
    splits  = list(pattern.finditer(text))
    if not splits:
        return [("", text)]

    sections = []
    for i, match in enumerate(splits):
        title = match.group(0).strip().lstrip("#").strip()
        start = match.end()
        end   = splits[i + 1].start() if i + 1 < len(splits) else len(text)
        body  = text[start:end].strip()
        if body:
            sections.append((title, body))
    return sections if sections else [("", text)]


def chunk_text(text: str, filetype: str) -> list[tuple[str, str]]:
    """Return (section_title, chunk) pairs, each chunk ≤ CHUNK_SIZE chars."""
    chunks: list[tuple[str, str]] = []
    for title, body in _split_by_headings(text, filetype):
        if len(body) <= CHUNK_SIZE:
            chunks.append((title, body))
        else:
            # Hard-wrap on sentence / paragraph boundaries
            start = 0
            while start < len(body):
                end = start + CHUNK_SIZE
                if end < len(body):
                    # Walk back to the last whitespace
                    boundary = body.rfind("\n", start, end)
                    if boundary <= start:
                        boundary = body.rfind(" ", start, end)
                    if boundary > start:
                        end = boundary
                chunk = body[start:end].strip()
                if chunk:
                    chunks.append((title, chunk))
                start = end - CHUNK_OVERLAP
    return chunks


# ── RELEVANCE FILTER ─────────────────────────────────────────────────────────
_ERROR_KEYWORDS = re.compile(
    r"\b(error|exception|traceback|raise|import|install|fail|crash|timeout|"
    r"TypeError|ValueError|RuntimeError|ImportError|AttributeError|"
    r"CUDA|cuda|device|driver|pip|package|dependency|version|incompatible|"
    r"fix|workaround|solution)\b",
    re.IGNORECASE,
)


def relevance_score(text: str) -> float:
    """0–1 keyword density of error-relevant terms in a 500-char window."""
    sample = text[:500]
    hits   = len(_ERROR_KEYWORDS.findall(sample))
    words  = max(len(sample.split()), 1)
    return min(hits / words, 1.0)


# ── MAIN SCRAPER ─────────────────────────────────────────────────────────────
def scrape_library(name: str, cfg: dict, max_files: int) -> list[dict]:
    repo       = cfg["repo"]
    docs_path  = cfg["docs_path"]
    incl_ext   = cfg["include_ext"]
    prio_pat   = re.compile(cfg.get("priority_re", r""), re.IGNORECASE)
    skip_pat   = re.compile(cfg.get("skip_path_re", r"^$"), re.IGNORECASE)

    print(f"\n[{name}] Listing {repo}:{docs_path} …")
    blobs = list_repo_tree(repo, docs_path)
    if not blobs:
        print(f"  No files found — skipping {name}.")
        return []

    # Filter by extension and skip pattern
    candidates = [
        b for b in blobs
        if Path(b["path"]).suffix in incl_ext
        and not skip_pat.search(b["path"])
    ]

    # Sort: priority files first, then alphabetical
    def sort_key(b: dict) -> tuple:
        fname = Path(b["path"]).name
        return (0 if prio_pat.search(fname) else 1, b["path"])

    candidates.sort(key=sort_key)
    candidates = candidates[:max_files]
    print(f"  {len(candidates)} files after filters (max_files={max_files})")

    documents: list[dict] = []
    for blob in candidates:
        file_path = blob["path"]
        filetype  = Path(file_path).suffix
        section   = Path(file_path).stem

        raw = fetch_file_content(repo, file_path)
        if not raw:
            print(f"  SKIP (empty): {file_path}")
            continue

        cleaned = clean_doc_text(raw, filetype)
        if not cleaned:
            continue

        raw_url = (
            f"https://raw.githubusercontent.com/{repo}/HEAD/{file_path}"
        )

        for chunk_idx, (section_title, chunk) in enumerate(chunk_text(cleaned, filetype)):
            # Drop low-relevance chunks that are pure navigation/API stubs
            if len(chunk) < 80:
                continue
            score = relevance_score(chunk)
            if score < 0.02 and chunk_idx > 0:
                # allow the first chunk of every file regardless (intro text)
                continue

            documents.append({
                "library":   name,
                "source":    raw_url,
                "content":   chunk,
                "section":   section_title or section,
                "filetype":  filetype,
                "chunk_idx": chunk_idx,
            })

        print(f"  ✓ {file_path} → {chunk_idx + 1} chunks")

    return documents


def write_jsonl(documents: list[dict], library: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{library}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for doc in documents:
            json.dump(doc, f, ensure_ascii=False)
            f.write("\n")
    print(f"  → wrote {len(documents)} chunks to {out_path}")


# ── ENTRY POINT ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Scrape library docs via GitHub API")
    ap.add_argument("--library",   default=None,
                    help="Scrape only this library (default: all)")
    ap.add_argument("--max-files", type=int, default=60,
                    help="Max files to download per library (default: 60)")
    args = ap.parse_args()

    if not os.getenv("GITHUB_TOKEN"):
        print(
            "WARNING: GITHUB_TOKEN not set. "
            "Rate limit is 60 req/hr (unauthenticated). "
            "For full runs, set: export GITHUB_TOKEN=ghp_…\n"
        )

    targets = (
        {args.library: LIBRARY_SOURCES[args.library]}
        if args.library and args.library in LIBRARY_SOURCES
        else LIBRARY_SOURCES
    )

    for lib_name, lib_cfg in targets.items():
        docs = scrape_library(lib_name, lib_cfg, args.max_files)
        if docs:
            write_jsonl(docs, lib_name)
        else:
            print(f"  [{lib_name}] No documents produced.")

    print("\nDone. Re-run the embedding pipeline to index the new documents.")
