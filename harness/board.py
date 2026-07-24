#!/usr/bin/env python3
"""The Board — a live projection of delivery state. It has NO state of its own.

Projects `sprint-status.yaml` (story states) × the active story's Tasks/Subtasks × the
pipeline phase × the goal-ladder into a rendered BOARD.md and a one-line log emit. Because
it is a projection, it cannot drift or lie the way a hand-kept todo.md would.

usage: board.py [--cwd .] [--story 1-2] [--phase dev-story] [--artifacts _bmad-output]
                [--out BOARD.md] [--quiet]
  --phase  one of: create-story|atdd|dev-story|code-review|trace|gate (aliases accepted).
           Omitted → inferred from the active story's status.
Prints the one-line board summary to stdout (for logs). Writes BOARD.md unless --quiet.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import frontmatter  # noqa: E402

PHASES = ["create-story", "atdd", "dev-story", "code-review", "trace", "gate"]
PHASE_ALIASES = {
    "create-story": 0, "create": 0,
    "atdd": 1, "red": 1,
    "dev-story": 2, "dev": 2, "green": 2,
    "code-review": 3, "review": 3,
    "trace": 4,
    "gate": 5, "done": 6,
}
# Best-effort phase when --phase is absent, from the story's sprint status.
STATUS_PHASE = {"backlog": -1, "ready-for-dev": 0, "in-progress": 2, "review": 3, "done": 6}
STORY_KEY_RE = re.compile(r"^\d+-\d+(-|$)")
SID_RE = re.compile(r"^(\d+-\d+)")


def _clean(v: str) -> str:
    return re.sub(r"\s*<!--.*?-->\s*$", "", v).strip()


def load_status(artifacts: Path) -> tuple[str, dict]:
    p = artifacts / "implementation-artifacts" / "sprint-status.yaml"
    if not p.exists():
        return "(no sprint-status.yaml)", {}
    fm = frontmatter.parse(p.read_text())
    return str(fm.get("project", "simple-dev")), (fm.get("development_status") or {})


def story_key_for(dev_status: dict, sid: str) -> str | None:
    for k in dev_status:
        if STORY_KEY_RE.match(k) and (k == sid or k.startswith(sid + "-")):
            return k
    return None


def active_story(dev_status: dict) -> str | None:
    """First story whose status is being worked (in-progress > review)."""
    for want in ("in-progress", "review"):
        for k, v in dev_status.items():
            if STORY_KEY_RE.match(k) and v == want:
                m = SID_RE.match(k)
                if m:
                    return m.group(1)
    return None


def parse_story(path: Path | None) -> dict:
    out = {"macro": "", "story": "", "tasks": [], "found": bool(path and path.exists())}
    if not out["found"]:
        return out
    for raw in path.read_text().splitlines():
        stripped = raw.strip()
        gm = re.match(r"-\s*macro goal:\s*(.*)", stripped)
        sg = re.match(r"-\s*story goal:\s*(.*)", stripped)
        if gm:
            out["macro"] = _clean(gm.group(1)); continue
        if sg:
            out["story"] = _clean(sg.group(1)); continue
        cm = re.match(r"-\s*\[([ xX])\]\s*(.*)", stripped)
        if cm:
            indent = len(raw) - len(raw.lstrip(" "))
            text = _clean(cm.group(2))
            done = cm.group(1).lower() == "x"
            if indent == 0:
                gm = re.search(r"goal:\s*(.+?)(?:\s*\(AC[^)]*\))?\s*$", text)
                out["tasks"].append({"text": text, "goal": (gm.group(1).strip() if gm else text),
                                     "done": done, "subtasks": []})
            elif out["tasks"]:
                out["tasks"][-1]["subtasks"].append({"text": text, "done": done})
    return out


def phase_bar(idx: int) -> str:
    cells = []
    for i, name in enumerate(PHASES):
        mark = "✓" if i < idx else ("▶" if i == idx else "")
        cells.append(f"{name} {mark}".rstrip())
    return "[" + " · ".join(cells) + "]"


def render(project: str, dev_status: dict, sid: str | None, key: str | None,
           idx: int, story: dict) -> tuple[str, str]:
    lines = [f"# simple-dev board — {project}",
             "",
             "_A live projection of sprint-status × subtasks × phase × goal-ladder. Never hand-edit._",
             "", "## Stories", ""]
    for k, v in dev_status.items():
        if k.startswith("epic-") and not k.endswith("-retrospective"):
            lines.append(f"\n**{k}**  ·  _{v}_")
        elif STORY_KEY_RE.match(k):
            flag = "  ◀ active" if (key and k == key) else ""
            lines.append(f"- `{v:<13}` {k}{flag}")

    total = len(story["tasks"])
    done = sum(1 for t in story["tasks"] if t["done"])
    cur_task = next((t for t in story["tasks"] if not t["done"]), None)
    last = story["tasks"][-1] if story["tasks"] else None
    task_goal = (cur_task or last or {}).get("goal", "—")

    if key:
        lines += ["", f"## Active — {key}", "",
                  f"phase: {phase_bar(idx)}",
                  f"goal:  task «{task_goal}» → story «{story['story'] or '—'}» → macro «{story['macro'] or '—'}»",
                  f"tasks: {done}/{total} done", ""]
        for t in story["tasks"]:
            lines.append(f"  [{'x' if t['done'] else ' '}] {t['text']}")
            for s in t["subtasks"]:
                lines.append(f"    [{'x' if s['done'] else ' '}] {s['text']}")

    phase_name = PHASES[idx] if 0 <= idx < len(PHASES) else ("done" if idx >= len(PHASES) else "backlog")
    oneline = (f"[board] {key or '(no active story)'} · phase {phase_name} · "
               f"tasks {done}/{total} · goal: «{task_goal}» → «{story['story'] or '—'}»")
    return "\n".join(lines) + "\n", oneline


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--story", default=None, help="active story id, e.g. 1-2 (else inferred)")
    ap.add_argument("--phase", default=None)
    ap.add_argument("--artifacts", default="_bmad-output")
    ap.add_argument("--out", default=None)
    ap.add_argument("--quiet", action="store_true", help="do not write BOARD.md, just print the line")
    args = ap.parse_args()

    cwd = Path(args.cwd).resolve()
    artifacts = cwd / args.artifacts
    project, dev_status = load_status(artifacts)

    sid = args.story or active_story(dev_status)
    key = story_key_for(dev_status, sid) if sid else None
    story = parse_story(artifacts / "implementation-artifacts" / f"{key}.md") if key else parse_story(None)

    if args.phase is not None:
        idx = PHASE_ALIASES.get(args.phase.lower().strip(), 0)
    else:
        status = dev_status.get(key, "backlog") if key else "backlog"
        idx = STATUS_PHASE.get(status, -1)

    board_md, oneline = render(project, dev_status, sid, key, idx, story)
    if not args.quiet:
        out = Path(args.out) if args.out else cwd / "BOARD.md"
        out.write_text(board_md)
    print(oneline)
    return 0


if __name__ == "__main__":
    sys.exit(main())
