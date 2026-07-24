#!/usr/bin/env python3
"""simple-dev installer — deploy the harness into a target project.

Copies the harness machinery + delivery skills into <target>, then generates the target's
team.yaml/AGENTS.md. NEVER deletes anything: an existing enxa install (or a missing bmm
prereq) is REPORTED for you to act on, not touched.

usage: install.py --target <dir> [--direction "one line"] [--dry-run]
Exposed as the `simple-dev install` console command via pyproject.toml.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent  # the simple-dev repo root

# simple-dev's own delivery assets (bmm planning skills come from the target's bmm install).
DELIVERY_SKILLS = [
    "create-story", "dev-story", "code-review", "testarch-atdd", "testarch-trace",
    "story-worktree", "_testarch-knowledge", "generate-team",
]
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")


def copy_tree(src: Path, dst: Path, dry: bool) -> None:
    if dry:
        print(f"  would copy {src.name}/ → {dst}")
        return
    shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=True, ignore=_IGNORE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--direction", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"error: target is not a directory: {target}")
        return 2
    if target == SRC:
        print("error: refusing to install onto the simple-dev source repo itself")
        return 2

    print(f"[install] simple-dev → {target}" + ("  (dry-run)" if args.dry_run else ""))

    # 1. Harness machinery.
    copy_tree(SRC / "harness", target / "harness", args.dry_run)
    if not args.dry_run:
        shutil.copy2(SRC / "harness.toml", target / "harness.toml")
    else:
        print("  would copy harness.toml")

    # 2. Delivery skills (symlinks preserved → shared _testarch-knowledge resolves in-target).
    for name in DELIVERY_SKILLS:
        src = SRC / ".claude" / "skills" / name
        if src.exists():
            copy_tree(src, target / ".claude" / "skills" / name, args.dry_run)

    # 3. Generate the target's roster.
    if not args.dry_run:
        gen = subprocess.run(
            [sys.executable, str(target / "harness" / "gen_team.py"),
             "--cwd", str(target), "--direction", args.direction],
            capture_output=True, text=True)
        print("  " + (gen.stdout.strip() or gen.stderr.strip()))

    # 4. Prereq + residue reports (never acted on).
    warnings = []
    if not (target / "_bmad").exists() and not (target / "_bmad-output").exists():
        warnings.append("bmm not detected (_bmad/ absent) — run `npx bmad-method install "
                        "--modules bmm --tools claude-code` for the planning half of the loop")
    residue = []
    if (target / ".enxa").exists():
        residue.append(".enxa/ (legacy enxa harness — supersede then remove at your discretion)")
    stale_bmad = list((target / ".claude" / "skills").glob("bmad-create-story")) if (target / ".claude/skills").exists() else []
    if stale_bmad:
        residue.append("vanilla bmad delivery skills (bmad-create-story/dev-story/code-review) — "
                       "now redundant with the ported ones; the Governor self-audit will flag them")

    if warnings:
        print("\nPREREQS:")
        for w in warnings:
            print(f"  ⚠ {w}")
    if residue:
        print("\nRESIDUE (reported only — never auto-removed):")
        for r in residue:
            print(f"  • {r}")
    print("\n[install] done. Next: read AGENTS.md + team.yaml, then run story-worktree on a story.")
    return 0


def cli() -> None:
    """Console entry (`simple-dev`). Accepts the npx-style verb: `simple-dev install --target …`."""
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        sys.argv.pop(1)
    raise SystemExit(main())


if __name__ == "__main__":
    sys.exit(main())
