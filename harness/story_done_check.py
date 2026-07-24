#!/usr/bin/env python3
"""Validate a STORY-DONE completion contract. Machine truth over agent claims.

usage: story_done_check.py --story <id> [--artifacts <dir>] [--cwd <repo>]
exit:  0 valid | 1 invalid (errors as JSON on stdout) | 40 environment error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import gitio  # noqa: E402
from lib.frontmatter import FrontmatterError, read_frontmatter  # noqa: E402

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:?\d{2})$")


def normalize_story_id(sid) -> str:
    return str(sid).strip().replace(".", "-")


def validate(story_id: str, artifacts: Path, cwd: Path) -> tuple[dict, list[str]]:
    errors: list[str] = []
    sid = normalize_story_id(story_id)
    path = artifacts / "implementation-artifacts" / "done" / f"story-{sid}-done.md"
    if not path.exists():
        return {"path": str(path)}, [f"STORY-DONE file missing: {path}"]

    try:
        fm, _body = read_frontmatter(path)
    except FrontmatterError as exc:
        return {"path": str(path)}, [f"frontmatter invalid: {exc}"]

    if fm.get("type") != "story-done":
        errors.append(f"type must be 'story-done', got {fm.get('type')!r}")
    if normalize_story_id(fm.get("story_id", "")) != sid:
        errors.append(
            f"story_id mismatch: file says {fm.get('story_id')!r}, gating {sid!r} "
            "(context drift — this STORY-DONE belongs to another story)"
        )
    if fm.get("status") != "completed":
        errors.append(f"status must be the literal 'completed', got {fm.get('status')!r}")
    completed_at = str(fm.get("completed_at", ""))
    if not ISO_RE.match(completed_at):
        errors.append(f"completed_at is not ISO-8601: {completed_at!r}")

    commits = fm.get("commits") or []
    if not isinstance(commits, list) or not commits:
        errors.append("commits must be a non-empty list of SHAs on this branch")
    else:
        for sha in commits:
            if not gitio.commit_exists(cwd, str(sha)):
                errors.append(f"commit {sha} does not exist in this repository")

    tests = fm.get("tests") or {}
    if not isinstance(tests, dict):
        errors.append("tests must be a map with passed/count")
    else:
        if tests.get("passed") is not True:
            errors.append(f"tests.passed must be the literal true, got {tests.get('passed')!r}")
        count = tests.get("count")
        if not isinstance(count, int) or count <= 0:
            errors.append(f"tests.count must be an int > 0, got {count!r}")

    touches = fm.get("touches")
    if touches is not None and not isinstance(touches, list):
        errors.append("touches, when present, must be a list of paths")

    return {"path": str(path), "frontmatter": fm}, errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", required=True)
    ap.add_argument("--artifacts", default="_bmad-output")
    ap.add_argument("--cwd", default=".")
    args = ap.parse_args()

    cwd = Path(args.cwd).resolve()
    if not gitio.is_repo(cwd):
        print(json.dumps({"errors": [f"not a git repository: {cwd}"]}))
        return 40

    info, errors = validate(args.story, cwd / args.artifacts, cwd)
    print(json.dumps({"path": info.get("path"), "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
