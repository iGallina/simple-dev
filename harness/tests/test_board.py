#!/usr/bin/env python3
"""Board projection test. Zero framework deps — run: python3 harness/tests/test_board.py

Builds a fixture sprint-status + story, then asserts board.py's one-line emit and BOARD.md
render match the expected projection (active marker, phase bar, cleaned goal-ladder, task counts).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
BOARD = HARNESS / "board.py"

SPRINT = """project: Test Project
development_status:
  epic-1: in-progress
  1-1-alpha: done
  1-2-beta: in-progress
  1-3-gamma: backlog
"""

STORY = """# Story 1.2: Beta

Status: in-progress

## Focus (goal-ladder)

- macro goal: ship the beta  <!-- the epic objective this story serves -->
- story goal: wire the beta endpoint

## Tasks / Subtasks

- [x] Task 1 — goal: scaffold (AC: 1)
  - [x] Subtask 1.1
- [ ] Task 2 — goal: handler (AC: 2)
  - [ ] Subtask 2.1
"""


def make(root: Path) -> Path:
    ia = root / "_bmad-output" / "implementation-artifacts"
    ia.mkdir(parents=True)
    (ia / "sprint-status.yaml").write_text(SPRINT)
    (ia / "1-2-beta.md").write_text(STORY)
    return root


def run(root: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(BOARD), "--cwd", str(root), *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def case_oneline_explicit(root: Path) -> None:
    make(root)
    rc, out = run(root, "--story", "1-2", "--phase", "dev-story", "--quiet")
    assert rc == 0, out
    for want in ["1-2-beta", "phase dev-story", "tasks 1/2", "handler", "wire the beta endpoint"]:
        assert want in out, f"missing {want!r} in: {out}"


def case_board_md_render(root: Path) -> None:
    make(root)
    run(root, "--story", "1-2", "--phase", "dev-story")
    md = (root / "BOARD.md").read_text()
    assert "◀ active" in md and "1-2-beta" in md, "active marker missing"
    assert "dev-story ▶" in md, "phase bar not marking dev-story current"
    assert "«ship the beta»" in md, "macro goal missing/uncleaned"
    assert "[x] Task 1" in md and "[ ] Task 2" in md, "task checkboxes missing"


def case_infer_active_and_phase(root: Path) -> None:
    make(root)  # no --story, no --phase → both inferred
    rc, out = run(root, "--quiet")
    assert rc == 0, out
    assert "1-2-beta" in out, "active story not inferred from in-progress status"
    assert "phase dev-story" in out, "phase not inferred from in-progress status"


def case_goal_comment_stripped(root: Path) -> None:
    make(root)
    run(root, "--story", "1-2")  # renders BOARD.md (macro goal lives there, not in the one-line)
    md = (root / "BOARD.md").read_text()
    assert "«ship the beta»" in md, "macro goal not rendered"
    assert "<!--" not in md, f"HTML comment leaked into the projection:\n{md}"


CASES = [case_oneline_explicit, case_board_md_render, case_infer_active_and_phase, case_goal_comment_stripped]


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
    print(f"\n{len(CASES) - failed}/{len(CASES)} board checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
