#!/usr/bin/env python3
"""Static disjunction check + wave planner for parallel story dispatch.

Stories declare `touches:` (files; trailing slash = directory subtree) and
optional `depends_on:` in their frontmatter. Overlapping stories must not run
in the same wave — proven here BEFORE any worktree exists.

usage: touches_check.py --stories 2-1,2-2 [--artifacts <dir>] [--plan] [--json]
exit:  0 disjoint/plan ok | 1 violations | 2 unplannable story (check mode) | 40 env
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.frontmatter import FrontmatterError, read_frontmatter  # noqa: E402


def normalize(p: str) -> str:
    return p.strip().lstrip("./")


def overlaps(a: str, b: str) -> bool:
    a, b = normalize(a), normalize(b)
    if a == b:
        return True
    a_dir, b_dir = a.endswith("/"), b.endswith("/")
    if a_dir and b.startswith(a):
        return True
    if b_dir and a.startswith(b):
        return True
    if a_dir and b_dir and (a.startswith(b) or b.startswith(a)):
        return True
    return False


def find_story_file(artifacts: Path, sid: str) -> Path | None:
    impl = artifacts / "implementation-artifacts"
    if not impl.exists():
        return None
    hits = sorted(impl.glob(f"story-{sid}-*.md")) or sorted(impl.glob(f"{sid}-*.md"))
    hits = [h for h in hits if "/done/" not in str(h)]
    return hits[0] if hits else None


def load_stories(artifacts: Path, ids: list[str]) -> tuple[dict, list[str]]:
    stories, problems = {}, []
    for sid in ids:
        path = find_story_file(artifacts, sid)
        if path is None:
            problems.append(f"{sid}: story file not found under {artifacts}/implementation-artifacts")
            stories[sid] = {"touches": [], "depends_on": [], "file": None}
            continue
        try:
            fm, _ = read_frontmatter(path)
        except FrontmatterError as exc:
            problems.append(f"{sid}: frontmatter invalid ({exc})")
            stories[sid] = {"touches": [], "depends_on": [], "file": str(path)}
            continue
        touches = fm.get("touches") or []
        deps = [str(d).replace(".", "-") for d in (fm.get("depends_on") or [])]
        if not touches:
            problems.append(f"{sid}: no touches declared — unplannable for parallel dispatch")
        stories[sid] = {"touches": touches, "depends_on": deps, "file": str(path)}
    return stories, problems


def violations(stories: dict) -> list[dict]:
    out = []
    ids = sorted(stories)
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            files = [
                f"{ta}  ~  {tb}" if normalize(ta) != normalize(tb) else normalize(ta)
                for ta in stories[a]["touches"]
                for tb in stories[b]["touches"]
                if overlaps(ta, tb)
            ]
            if files:
                out.append({"stories": [a, b], "overlap": sorted(set(files))})
    return out


def plan_waves(stories: dict, problems: list[str]) -> dict:
    """Greedy wave assignment: earliest wave with no conflicts and all deps earlier."""
    unplannable = {p.split(":")[0] for p in problems}
    waves: list[list[str]] = []
    placed: dict[str, int] = {}
    for sid in sorted(stories):
        if sid in unplannable:
            waves.append([sid])  # forced solo wave
            placed[sid] = len(waves) - 1
            continue
        target = 0
        for dep in stories[sid]["depends_on"]:
            if dep in placed:
                target = max(target, placed[dep] + 1)
        w = target
        while True:
            if w >= len(waves):
                waves.append([])
            conflict = any(
                other not in unplannable
                and any(overlaps(ta, tb) for ta in stories[sid]["touches"] for tb in stories[other]["touches"])
                for other in waves[w]
            )
            if not conflict:
                waves[w].append(sid)
                placed[sid] = w
                break
            w += 1
    return {
        "waves": {f"w{i+1}": sorted(w) for i, w in enumerate(waves) if w},
        "merge_order": {f"w{i+1}": sorted(w) for i, w in enumerate(waves) if w},
        "solo_forced": sorted(unplannable & set(stories)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stories", required=True, help="comma-separated story ids")
    ap.add_argument("--artifacts", default="_bmad-output")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ids = [s.strip().replace(".", "-") for s in args.stories.split(",") if s.strip()]
    artifacts = Path(args.artifacts)
    stories, problems = load_stories(artifacts, ids)

    if args.plan:
        result = plan_waves(stories, problems)
        result["problems"] = problems
        print(json.dumps(result, indent=2))
        return 0

    viols = violations({k: v for k, v in stories.items() if v["touches"]})
    report = {"violations": viols, "problems": problems}
    if args.json or True:
        print(json.dumps(report, indent=2))
    if not viols and not problems:
        return 0
    if viols:
        for v in viols:
            print(f"CONFLICT: {' and '.join(v['stories'])} both touch: "
                  f"{'; '.join(v['overlap'])}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
