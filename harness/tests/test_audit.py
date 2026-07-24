#!/usr/bin/env python3
"""Harness self-audit test. Zero deps — run: python3 harness/tests/test_audit.py"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
AUDIT = HARNESS / "audit.py"

WORKFLOW = """| # | step | command | source | purpose |
|---|---|---|---|---|
| 1 | create-story | `create-story {ID}` | ported | x |
| 2 | dev-story | `dev-story {ID}` | ported | x |
"""


def fixture(root: Path) -> Path:
    (root / "harness").mkdir()
    (root / "harness" / "workflow-steps.md").write_text(WORKFLOW)
    sk = root / ".claude" / "skills"
    sk.mkdir(parents=True)
    for name in ["create-story", "bmad-create-story", "bmad-prfaq", "bmad-help", "_shared-thing"]:
        (sk / name).mkdir()
    return root


def run(root: Path) -> str:
    return subprocess.run([sys.executable, str(AUDIT), "--cwd", str(root)],
                          capture_output=True, text=True).stdout


def case_flags_redundant_and_untraceable(root: Path) -> None:
    fixture(root)
    out = run(root)
    assert "bmad-create-story" in out and "REDUNDANT" in out, "redundant not flagged"
    assert "bmad-prfaq" in out and "UNTRACEABLE" in out, "untraceable not flagged"
    # a loop skill and a planning skill are NOT flagged
    lines = [ln.strip("  •") for ln in out.splitlines() if ln.startswith("  •")]
    assert "create-story" not in lines, "loop skill wrongly flagged"
    assert "bmad-help" not in lines, "planning skill wrongly flagged"
    # underscore-prefixed shared dirs are ignored
    assert "_shared-thing" not in lines, "shared dir wrongly flagged"


CASES = [case_flags_redundant_and_untraceable]


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
    print(f"\n{len(CASES) - failed}/{len(CASES)} audit checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
