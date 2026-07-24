"""Thin git wrapper for the gate scripts. Zero deps, explicit failures."""
from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def git(cwd: str | Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=120
    )
    if check and proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed in {cwd}: {proc.stderr.strip()}")
    return proc


def is_repo(cwd: str | Path) -> bool:
    return git(cwd, "rev-parse", "--git-dir", check=False).returncode == 0


def current_branch(cwd: str | Path) -> str:
    return git(cwd, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def head_sha(cwd: str | Path) -> str:
    return git(cwd, "rev-parse", "HEAD").stdout.strip()


def is_clean(cwd: str | Path) -> bool:
    return git(cwd, "status", "--porcelain").stdout.strip() == ""


def commit_exists(cwd: str | Path, sha: str) -> bool:
    return git(cwd, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0


def branch_exists(cwd: str | Path, branch: str) -> bool:
    return (
        git(cwd, "show-ref", "--verify", f"refs/heads/{branch}", check=False).returncode == 0
    )


def sha_on_branch(cwd: str | Path, sha: str, branch: str) -> bool:
    """True if sha is an ancestor of (or equal to) the branch tip."""
    if not commit_exists(cwd, sha):
        return False
    return (
        git(cwd, "merge-base", "--is-ancestor", sha, branch, check=False).returncode == 0
    )


def last_commit_time(cwd: str | Path, ref: str, path: str | None = None) -> int:
    """Unix time of the last commit touching path (or of ref if no path)."""
    args = ["log", "-1", "--format=%ct", ref]
    if path:
        args += ["--", path]
    out = git(cwd, *args).stdout.strip()
    return int(out) if out else 0


def conflicted_files(cwd: str | Path) -> list[str]:
    out = git(cwd, "diff", "--name-only", "--diff-filter=U", check=False).stdout
    return [line for line in out.splitlines() if line.strip()]
