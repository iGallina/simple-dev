#!/usr/bin/env python3
"""graph.py check test (staleness). Zero deps, no graphify binary needed —
run: python3 harness/tests/test_graph.py

Uses fixed mtimes (no wall-clock) so stale/fresh are deterministic.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
GRAPH = HARNESS / "graph.py"
OLD, NEW = 1_000_000_000, 2_000_000_000  # fixed epochs, OLD < NEW


def run(root: Path) -> str:
    return subprocess.run([sys.executable, str(GRAPH), "check", "--cwd", str(root)],
                          capture_output=True, text=True).stdout


def case_not_built(root: Path) -> None:
    (root / "a.py").write_text("x = 1\n")
    out = run(root)
    assert "not built" in out, out


def case_stale(root: Path) -> None:
    src = root / "a.py"; src.write_text("x = 1\n"); os.utime(src, (NEW, NEW))
    out = root / "graphify-out"; out.mkdir()
    graph = out / "graph.json"; graph.write_text("{}"); os.utime(graph, (OLD, OLD))
    assert "STALE" in run(root), "stale graph not detected"


def case_fresh(root: Path) -> None:
    src = root / "a.py"; src.write_text("x = 1\n"); os.utime(src, (OLD, OLD))
    out = root / "graphify-out"; out.mkdir()
    graph = out / "graph.json"; graph.write_text("{}"); os.utime(graph, (NEW, NEW))
    assert "fresh" in run(root), "fresh graph not recognized"


CASES = [case_not_built, case_stale, case_fresh]


def main() -> int:
    failed = 0
    for case in CASES:
        with tempfile.TemporaryDirectory() as td:
            try:
                case(Path(td))
                print(f"PASS  {case.__name__}")
            except AssertionError as exc:
                print(f"FAIL  {case.__name__}: {exc}")
                failed += 1
    print(f"\n{len(CASES) - failed}/{len(CASES)} graph checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
