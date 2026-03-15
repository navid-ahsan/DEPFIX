#!/usr/bin/env python3
"""
Re-chunk existing github_raw JSONL files without touching the GitHub API.

Reads each JSONL, groups entries by source URL, re-fetches each source URL
from raw.githubusercontent.com (no API rate limit), re-chunks with the updated
chunker (code-block-preserving), and excludes files that match CONTRIBUTING /
CHANGELOG / GOVERNANCE / etc. exclude patterns.

This fixes the CONTRIBUTING chunk pollution in n8n, torch, requests, pyramid,
waitress, and flower without needing a GitHub token.

For old_local deps (scikit-learn, monai, tenseal, torchaudio, torchvision) use
scripts/refetch_stale_docs.py instead (requires GitHub API + token or rate limit reset).

Usage:
    python scripts/rechunk_raw_docs.py
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import httpx

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND.parent))

# Import only the low-level helpers — avoids triggering the full FastAPI app init
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("docs_fetcher", _BACKEND / "app" / "services" / "docs_fetcher.py")
_mod  = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_chunk_text    = _mod._chunk_text
_matches_exclude = _mod._matches_exclude

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "documents"


def _source_path(source_url: str) -> str:
    """Extract repo-relative path from a raw.githubusercontent.com URL."""
    # https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}
    m = re.match(r"https://raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+/(.+)", source_url)
    return m.group(1) if m else ""


async def rechunk_file(jsonl_path: Path, client: httpx.AsyncClient) -> dict:
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(l) for l in lines if l.strip()]
    if not records:
        return {"name": jsonl_path.stem, "status": "empty", "before": 0, "after": 0}

    # Only process github_raw files — skip old_local
    if any("/app/data/" in r.get("source", "") for r in records):
        return {"name": jsonl_path.stem, "status": "skipped_old_local",
                "before": len(records), "after": len(records)}

    before_count = len(records)

    # Collect unique source URLs, excluding maintenance files
    seen_sources: set[str] = set()
    for r in records:
        src = r.get("source", "")
        if src and src not in seen_sources:
            seen_sources.add(src)

    dep_name   = records[0].get("library", jsonl_path.stem)
    new_chunks: list[dict] = []
    chunk_idx  = 0
    fetched    = 0
    skipped    = 0

    for source_url in sorted(seen_sources):
        repo_path = _source_path(source_url)
        if not repo_path:
            continue

        # Apply updated exclude patterns — this removes CONTRIBUTING, CHANGELOG, etc.
        if _matches_exclude(repo_path):
            skipped += 1
            continue

        try:
            resp = await client.get(source_url, timeout=20)
            if resp.status_code != 200:
                continue
        except Exception:
            continue

        raw = resp.text
        ext = Path(repo_path).suffix.lstrip(".")
        section = Path(repo_path).stem

        for text in _chunk_text(raw):
            new_chunks.append({
                "library":   dep_name,
                "source":    source_url,
                "content":   text,
                "section":   section,
                "filetype":  ext,
                "chunk_idx": chunk_idx,
            })
            chunk_idx += 1
        fetched += 1

    if not new_chunks:
        return {"name": jsonl_path.stem, "status": "empty_after_filter",
                "before": before_count, "after": 0, "skipped": skipped}

    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for entry in new_chunks:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {
        "name":    jsonl_path.stem,
        "status":  "done",
        "before":  before_count,
        "after":   len(new_chunks),
        "fetched": fetched,
        "skipped": skipped,
    }


async def main() -> None:
    jsonl_files = sorted(DOCS_DIR.glob("*.jsonl"))
    print(f"Re-chunking {len(jsonl_files)} JSONL file(s) from {DOCS_DIR}\n")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        results = []
        for f in jsonl_files:
            r = await rechunk_file(f, client)
            results.append(r)
            status = r["status"]
            if status == "done":
                delta = r["after"] - r["before"]
                sign = "+" if delta >= 0 else ""
                print(f"  ✓  {r['name']:20s}  {r['before']:5d} → {r['after']:5d} chunks "
                      f"({sign}{delta:+d})  skipped_files={r.get('skipped', 0)}")
            elif status == "skipped_old_local":
                print(f"  ~  {r['name']:20s}  {r['before']:5d} chunks  [old_local, use refetch_stale_docs.py]")
            else:
                print(f"  ⚠  {r['name']:20s}  {status}")

    print(f"\nDone. Run 'python scripts/audit_docs_quality.py' to verify results.")


if __name__ == "__main__":
    asyncio.run(main())
