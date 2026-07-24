#!/usr/bin/env python3
"""Installer engine test. Zero deps — run: python3 harness/tests/test_install.py

Installs the harness into a fixture target and asserts: assets deployed, roster generated,
the shared-knowledge symlink resolves in-target, the bmm prereq is warned, a pre-existing
file survives (never-delete), and the DEPLOYED harness's own self-test passes.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
INSTALL = HARNESS / "install.py"


def run(target: Path, *args: str) -> tuple[int, str]:
    # --no-graph: tests must never trigger a real graphify build (slow, may invoke the LLM).
    r = subprocess.run([sys.executable, str(INSTALL), "--target", str(target), "--no-graph", *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def case_deploys_and_preserves(root: Path) -> None:
    tgt = root / "proj"; tgt.mkdir()
    (tgt / "KEEP.txt").write_text("preserve me")
    rc, out = run(tgt, "--direction", "test project")
    assert rc == 0, out
    assert (tgt / "harness" / "gate_runner.py").exists(), "gate not deployed"
    assert (tgt / "harness" / "PONYTAIL.md").exists(), "ponytail discipline not deployed (foundation)"
    assert (tgt / "harness.toml").exists(), "config not deployed"
    assert (tgt / ".claude/skills/create-story/SKILL.md").exists(), "delivery skill not deployed"
    assert (tgt / ".claude/skills/_testarch-knowledge").exists(), "shared knowledge not deployed"
    assert (tgt / "team.yaml").exists() and (tgt / "AGENTS.md").exists(), "roster not generated"
    assert (tgt / "KEEP.txt").read_text() == "preserve me", "pre-existing file was clobbered"


def case_symlink_resolves(root: Path) -> None:
    tgt = root / "proj"; tgt.mkdir()
    run(tgt, "--direction", "x")
    kn = tgt / ".claude/skills/testarch-atdd/resources/knowledge"
    assert kn.is_symlink(), "knowledge is not a symlink in target"
    assert list(kn.glob("*.md")), "symlink does not resolve to the shared knowledge in-target"


def case_bmm_prereq_warned(root: Path) -> None:
    tgt = root / "proj"; tgt.mkdir()
    rc, out = run(tgt)
    assert "bmm not detected" in out, f"bmm prereq not warned: {out}"


def case_deployed_harness_selftests(root: Path) -> None:
    tgt = root / "proj"; tgt.mkdir()
    run(tgt)
    r = subprocess.run([sys.executable, str(tgt / "harness/tests/test_gate_smoke.py")],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"deployed harness self-test failed:\n{r.stdout}{r.stderr}"


CASES = [case_deploys_and_preserves, case_symlink_resolves, case_bmm_prereq_warned,
         case_deployed_harness_selftests]


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
    print(f"\n{len(CASES) - failed}/{len(CASES)} installer checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
