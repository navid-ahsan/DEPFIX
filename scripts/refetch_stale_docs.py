#!/usr/bin/env python3
"""
Re-fetch docs for dependencies that still have stale local data
(identified by /app/data/doc_sources/ paths in their JSONL files).

Usage:
    GITHUB_TOKEN=ghp_xxx python scripts/refetch_stale_docs.py

If GITHUB_TOKEN is set it uses authenticated GitHub API (5000 req/hr).
Without it, unauthenticated requests are used (60 req/hr — may fail if
the limit was recently exhausted).
"""

import asyncio
import importlib.util as _ilu
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
_spec = _ilu.spec_from_file_location("docs_fetcher", _BACKEND / "app" / "services" / "docs_fetcher.py")
_mod  = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
fetch_and_save_docs = _mod.fetch_and_save_docs

# Deps whose JSONL files still have old /app/data/doc_sources/ paths
STALE_DEPS = {
    "scikit-learn": "https://github.com/scikit-learn/scikit-learn",
    "monai":        "https://github.com/Project-MONAI/MONAI",
    "tenseal":      "https://github.com/OpenMined/TenSEAL",
    "torchaudio":   "https://github.com/pytorch/audio",
    "torchvision":  "https://github.com/pytorch/vision",
}

# Deps that are github_raw but need a full re-fetch to benefit from
# the new _MAX_FILES=80 and tutorials/examples patterns:
#   - n8n:    was 82% CONTRIBUTING; now only 6 README chunks — too thin.
#             Use n8n-docs repo (actual user docs, not the monorepo) for better results.
#   - torch:  still only has files from the old 40-file cap; will gain more
#   - pyramid: only 27 chunks; wider patterns may surface more docs
REFRESH_DEPS = {
    "n8n":     "https://github.com/n8n-io/n8n-docs",   # separate docs repo, much richer
    "torch":   "https://github.com/pytorch/pytorch",
    "pyramid": "https://github.com/Pylons/pyramid",
}


async def main() -> None:
    token = os.getenv("GITHUB_TOKEN")
    if token:
        print(f"[auth] Using GITHUB_TOKEN from environment (authenticated, 5000 req/hr)")
    else:
        print("[warn] No GITHUB_TOKEN — unauthenticated (60 req/hr). May fail if rate-limited.")
        print("       Set GITHUB_TOKEN=ghp_xxx to use authenticated mode.\n")

    all_deps = {**STALE_DEPS, **REFRESH_DEPS}
    results: dict[str, dict] = {}

    for dep, url in all_deps.items():
        print(f"\n[fetch] {dep}  ({url})")
        try:
            result = await fetch_and_save_docs(dep, url, github_token=token)
        except Exception as exc:
            result = {"status": "error", "message": str(exc), "chunks": 0, "files": 0}

        results[dep] = result
        status = result["status"]
        chunks = result.get("chunks", 0)
        files  = result.get("files", 0)
        msg    = result.get("message", "")

        if status == "done":
            print(f"  ✓  {chunks} chunks from {files} files")
        elif status == "warning":
            print(f"  ⚠  {chunks} chunks from {files} files — {msg}")
        else:
            print(f"  ✗  ERROR — {msg}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_chunks = sum(r.get("chunks", 0) for r in results.values())
    for dep, r in results.items():
        s = r["status"]
        icon = "✓" if s == "done" else ("⚠" if s == "warning" else "✗")
        print(f"  {icon}  {dep:20s}  {r.get('chunks', 0):5d} chunks  {r.get('files', 0):3d} files")
    print(f"\n  Total new chunks: {total_chunks}")

    errors = [d for d, r in results.items() if r["status"] == "error"]
    if errors:
        print(f"\n  Failed deps: {', '.join(errors)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
