#!/usr/bin/env python3
"""Smoke test for the merge gate. Proves gate_runner + gate_merge exit codes against
isolated temp git fixtures. Zero framework deps — run with: python3 harness/tests/test_gate_smoke.py

Each case builds a throwaway git repo, so nothing here touches simple-dev itself, and the
inner test_command is trivial (`true`/`false`) — no recursion into this suite.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
RUNNER = HARNESS / "gate_runner.py"
MERGE = HARNESS / "gate_merge.py"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def make_repo(root: Path, test_command: str = "true") -> tuple[Path, str]:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / "harness.toml").write_text(
        f'[gate]\ntest_command = "{test_command}"\ntrace_gate = "off"\n'
        '[merge]\ntarget_branch = "main"\n'
    )
    (repo / "README.md").write_text("seed\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "seed")
    return repo, git(repo, "rev-parse", "HEAD")


def write_story_done(repo: Path, sid: str, sha: str, passed: bool = True, count: int = 3) -> None:
    d = repo / "_bmad-output" / "implementation-artifacts" / "done"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"story-{sid}-done.md").write_text(
        "---\n"
        "type: story-done\n"
        f"story_id: {sid}\n"
        "status: completed\n"
        "completed_at: 2026-07-24T00:00:00Z\n"
        "commits:\n"
        f"  - {sha}\n"
        "tests:\n"
        f"  passed: {'true' if passed else 'false'}\n"
        f"  count: {count}\n"
        "---\n\nDone.\n"
    )


def run(script: Path, repo: Path, *args: str) -> int:
    return subprocess.run(
        [sys.executable, str(script), "--cwd", str(repo), *args],
        capture_output=True, text=True,
    ).returncode


def case_pass(root: Path) -> None:
    repo, sha = make_repo(root, test_command="true")
    write_story_done(repo, "1-1", sha)
    rc = run(RUNNER, repo, "--story", "1-1")
    assert rc == 0, f"expected 0 (PASS), got {rc}"


def case_missing_story_done(root: Path) -> None:
    repo, _ = make_repo(root, test_command="true")
    rc = run(RUNNER, repo, "--story", "1-1")
    assert rc == 20, f"expected 20 (STORY-DONE missing), got {rc}"


def case_tests_fail(root: Path) -> None:
    repo, sha = make_repo(root, test_command="false")
    write_story_done(repo, "1-1", sha)
    rc = run(RUNNER, repo, "--story", "1-1")
    assert rc == 10, f"expected 10 (tests failed), got {rc}"


def case_merge_refuses_without_verdict(root: Path) -> None:
    repo, _ = make_repo(root)
    git(repo, "branch", "story/1-1")
    rc = run(MERGE, repo, "--story", "1-1", "--branch", "story/1-1", "--target", "main")
    assert rc == 11, f"expected 11 (no PASS verdict), got {rc}"


CASES = [case_pass, case_missing_story_done, case_tests_fail, case_merge_refuses_without_verdict]


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
    print(f"\n{len(CASES) - failed}/{len(CASES)} gate smoke checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
