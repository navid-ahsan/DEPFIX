#!/usr/bin/env python3
"""
Audit the quality of docs JSONL files.

Shows chunk counts, source origin (github_raw vs old_local), section
diversity, and a sample of section names per dependency.

Usage:
    python scripts/audit_docs_quality.py
"""

import json
import re
from collections import Counter
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "documents"


def classify_source(source: str) -> str:
    if "/app/data/" in source or source.startswith("/"):
        return "old_local"
    if "raw.githubusercontent.com" in source:
        return "github_raw"
    return "other"


def audit_file(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(l) for l in lines if l.strip()]
    total = len(records)
    if total == 0:
        print(f"  {path.name:30s}  EMPTY")
        return

    source_types = Counter(classify_source(r.get("source", "")) for r in records)
    sections = Counter(r.get("section", "") for r in records)
    top_sections = sections.most_common(6)
    avg_len = sum(len(r.get("content", "")) for r in records) // total

    origin = "✓ github_raw" if source_types.get("github_raw", 0) == total else (
        "✗ old_local " if source_types.get("old_local", 0) > 0 else "? mixed     "
    )

    print(f"\n  {path.stem:20s}  {total:5d} chunks  {origin}  avg_len={avg_len}")
    print(f"    Top sections: " + ", ".join(f"{s!r}({n})" for s, n in top_sections))

    # Flag maintenance crud
    bad = [s for s, _ in top_sections if s.lower() in ("contributing", "changelog", "history", "changes", "governance")]
    if bad:
        print(f"    ⚠ WARNING: maintenance sections still present: {bad}")


def main() -> None:
    jsonl_files = sorted(DOCS_DIR.glob("*.jsonl"))
    if not jsonl_files:
        print(f"No JSONL files found in {DOCS_DIR}")
        return

    print(f"Docs directory: {DOCS_DIR}")
    print(f"Found {len(jsonl_files)} file(s)\n")

    total_chunks = 0
    for f in jsonl_files:
        audit_file(f)
        lines = f.read_text().splitlines()
        total_chunks += sum(1 for l in lines if l.strip())

    print(f"\n{'='*60}")
    print(f"Total chunks across all JSONL files: {total_chunks}")


if __name__ == "__main__":
    main()
