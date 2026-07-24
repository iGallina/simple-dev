#!/usr/bin/env python3
"""generate-team v3 test. Zero deps — run: python3 harness/tests/test_gen_team.py

Fixtures a project, runs gen_team.py, and asserts the team.yaml roster, the AGENTS.md
marker-merge (non-destructive), gap detection, and reproducibility (same input → same bytes).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
GEN = HARNESS / "gen_team.py"


def run(root: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(GEN), "--cwd", str(root), *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def py_md_project(root: Path) -> Path:
    (root / "pyproject.toml").write_text("[project]\nname='x'\n")
    sk = root / ".claude" / "skills" / "foo"
    sk.mkdir(parents=True)
    (sk / "SKILL.md").write_text("# foo\n")
    return root


def case_roster_disciplines(root: Path) -> None:
    py_md_project(root)
    rc, out = run(root, "--direction", "test harness")
    assert rc == 0, out
    ty = (root / "team.yaml").read_text()
    assert "python: { subagent_type: python-pro" in ty, ty
    assert "markdown: { subagent_type: technical-writer" in ty, ty
    # implementer is discipline-varying → both disciplines appear under it
    impl = ty[ty.index("implementer:"):ty.index("reviewer:")]
    assert "python:" in impl and "markdown:" in impl and "default:" in impl, impl


def case_agents_marker_merge(root: Path) -> None:
    py_md_project(root)
    (root / "AGENTS.md").write_text("# My Project\n\nKEEP THIS LINE\n")
    run(root)
    md = (root / "AGENTS.md").read_text()
    assert "KEEP THIS LINE" in md, "existing content clobbered"
    assert "SIMPLE-DEV:TEAM:START" in md and "Dev team" in md, "team block not merged in"
    # second run must not duplicate the block
    run(root)
    md2 = (root / "AGENTS.md").read_text()
    assert md2.count("SIMPLE-DEV:TEAM:START") == 1, "marker block duplicated on re-run"


def case_gap_detection(root: Path) -> None:
    py_md_project(root)
    (root / "build.gradle").write_text("// kotlin\n")
    rc, out = run(root, "--quiet")
    assert "GAP" in out and "build.gradle" in out, f"gap not reported: {out}"


def case_reproducible(root: Path) -> None:
    py_md_project(root)
    run(root, "--direction", "same", "--out", str(root / "a.yaml"))
    run(root, "--direction", "same", "--out", str(root / "b.yaml"))
    assert (root / "a.yaml").read_text() == (root / "b.yaml").read_text(), "output not reproducible"


def case_exclude_harness(root: Path) -> None:
    # The deployed harness footprint (harness/*.py + .claude/skills) must NOT count as the
    # project's stack under --exclude-harness; the real project marker (Gemfile) still does.
    (root / "harness").mkdir(); (root / "harness" / "x.py").write_text("x = 1\n")
    sk = root / ".claude" / "skills" / "foo"; sk.mkdir(parents=True); (sk / "SKILL.md").write_text("# foo\n")
    (root / "Gemfile").write_text("gem 'rails'\n")
    run(root, "--exclude-harness", "--direction", "rails app")
    ty = (root / "team.yaml").read_text()
    assert "ruby:" in ty, "real project stack (ruby) not detected"
    assert "python:" not in ty, "harness python leaked into the project roster"
    assert "markdown:" not in ty, "harness skills leaked into the project roster as markdown"


CASES = [case_roster_disciplines, case_agents_marker_merge, case_gap_detection, case_reproducible,
         case_exclude_harness]


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
    print(f"\n{len(CASES) - failed}/{len(CASES)} gen-team checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
