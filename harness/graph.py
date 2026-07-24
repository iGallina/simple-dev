#!/usr/bin/env python3
"""Thin graphify wrapper for the loop. Graphify OWNS codebase context (what *is*); this wires
it into the delivery loop and degrades GRACEFULLY — if graphify isn't installed or the graph
isn't built, it warns and returns 0, never blocking a story.

usage: graph.py check|update|affected|query [--cwd .] [--query "X"]
  check    — warn if graphify-out/ is missing or stale (source changed since last build)
  update   — `graphify update <cwd>` (incremental, AST, no LLM) if graphify is installed
  affected — `graphify affected "X"` — reverse traversal / blast-radius, for story context
  query    — `graphify query "X"`
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SKIP = {".git", "graphify-out", "harness", "node_modules", "__pycache__", ".claude", "_bmad", "_bmad-output"}
SRC_EXT = {".py", ".rb", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".ex", ".php", ".kt", ".swift"}


def newest_src_mtime(root: Path) -> float:
    newest = 0.0
    for p in root.rglob("*"):
        if any(part in SKIP for part in p.relative_to(root).parts):
            continue
        if p.is_file() and p.suffix in SRC_EXT:
            newest = max(newest, p.stat().st_mtime)
    return newest


def check(root: Path) -> int:
    out = root / "graphify-out"
    if not out.exists():
        print(f"[graph] not built — run `graphify {root}` for blast-radius context (non-blocking)")
        return 0
    graph = out / "graph.json"
    if graph.exists() and newest_src_mtime(root) > graph.stat().st_mtime:
        print(f"[graph] STALE — run `graphify update {root}` (source changed since last build)")
    else:
        print("[graph] fresh")
    return 0


def passthrough(action: str, root: Path, query: str) -> int:
    if not shutil.which("graphify"):
        print(f"[graph] graphify not installed — skipping `{action}` (non-blocking)")
        return 0
    if action == "build":
        args, timeout = ["graphify", str(root)], 180        # full build (first time)
    elif action == "update":
        args, timeout = ["graphify", "update", str(root)], 120  # incremental (AST, no LLM)
    else:
        args, timeout = ["graphify", action, query], 60
    try:
        r = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=timeout)
        print((r.stdout or r.stderr).strip())
    except subprocess.TimeoutExpired:
        print(f"[graph] `{action}` exceeded {timeout}s — run `graphify {root}` manually (non-blocking)")
    except OSError as exc:
        print(f"[graph] `{action}` skipped — {exc} (non-blocking)")
    return 0  # never block the loop on a context tool


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["check", "build", "update", "affected", "query"])
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--query", default="")
    args = ap.parse_args()
    root = Path(args.cwd).resolve()
    if args.action == "check":
        return check(root)
    if args.action in ("build", "update"):
        return passthrough(args.action, root, "")
    return passthrough(args.action, root, args.query)


if __name__ == "__main__":
    sys.exit(main())
