#!/usr/bin/env python3
"""Harness self-audit — the Focus Governor, harness scope.

Flags skills that don't trace to a workflow-steps.md loop step or the planning/lifecycle
allowlist: removal candidates. Reports only — NEVER deletes. Run it on a cadence (or from the
scrum-master skill) to keep the harness from re-bloating.

usage: audit.py [--cwd .]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Planning/lifecycle skills that legitimately run OUTSIDE the delivery loop.
PLANNING = {
    "bmad-create-prd", "bmad-prd", "bmad-edit-prd", "bmad-validate-prd", "bmad-product-brief",
    "bmad-create-architecture", "bmad-create-epics-and-stories", "bmad-sprint-planning",
    "bmad-sprint-status", "bmad-generate-project-context", "bmad-document-project",
    "bmad-correct-course", "bmad-retrospective", "bmad-index-docs", "bmad-shard-doc", "bmad-help",
}
# Harness-native skills (loop machinery, invoked by story-worktree / scrum-master).
HARNESS_SKILLS = {"story-worktree", "scrum-master", "generate-team"}
# Review layers invoked by code-review.
REVIEW_DEPS = {"bmad-review-edge-case-hunter", "bmad-review-adversarial-general"}
# Known redundant: superseded by the ported delivery skills.
REDUNDANT = {"bmad-create-story", "bmad-dev-story", "bmad-code-review"}


def loop_skills(workflow_steps: Path) -> set[str]:
    """The skill named in each loop-table row's `command` column (first backtick token)."""
    skills = set()
    for line in workflow_steps.read_text().splitlines():
        m = re.match(r"\|\s*\d+\s*\|[^|]*\|\s*`([a-z][a-z0-9-]+)", line)
        if m:
            skills.add(m.group(1))
    return skills


def audit(cwd: Path) -> tuple[list[str], list[str], set[str]]:
    ws = cwd / "harness" / "workflow-steps.md"
    skills_dir = cwd / ".claude" / "skills"
    traced = PLANNING | HARNESS_SKILLS | REVIEW_DEPS
    if ws.exists():
        traced |= loop_skills(ws)
    present = sorted(d.name for d in skills_dir.iterdir()
                     if d.is_dir() and not d.name.startswith("_")) if skills_dir.exists() else []
    redundant = [s for s in present if s in REDUNDANT]
    untraceable = [s for s in present if s not in traced and s not in REDUNDANT]
    return redundant, untraceable, traced


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", default=".")
    args = ap.parse_args()
    cwd = Path(args.cwd).resolve()

    if not (cwd / ".claude" / "skills").exists():
        print("[audit] no .claude/skills — nothing to audit")
        return 0

    redundant, untraceable, _ = audit(cwd)
    print(f"[audit] redundant: {len(redundant)} · untraceable: {len(untraceable)}")
    if redundant:
        print("\nREDUNDANT (superseded by the ported delivery skills — remove at your discretion):")
        for s in redundant:
            print(f"  • {s}")
    if untraceable:
        print("\nUNTRACEABLE (no loop step or planning role — review for removal):")
        for s in untraceable:
            print(f"  • {s}")
    if not redundant and not untraceable:
        print("  clean — every skill traces to a loop step or a planning role.")
    print("\nGovernor: nothing is auto-removed. Prune with explicit intent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
