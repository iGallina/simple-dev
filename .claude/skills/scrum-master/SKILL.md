---
name: scrum-master
description: "Use when the user asks to drive delivery — 'run the sprint', 'deliver the next story', 'work the backlog', 'be the scrum master'. The thin decider above the loop: reads sprint-status + team.yaml, picks the next story, dispatches each loop step with its team.yaml loadout via story-worktree, enforces the hard gate, updates the Board, and moves to the next. The user sets direction/priority; this drives."
---

# scrum-master

The decider above the loop. Ponytail is the discipline (injected into every child via its
SubagentStart hook); the Board + `sprint-status.yaml` + `team.yaml` are the state; this skill is
the judgment that picks and dispatches. It holds no state of its own — it reads the files.

## What the PO controls (everything else is machine-driven)

- **direction** → regenerate `team.yaml` (`generate-team`) when the project's PROJECT-DIRECTION changes.
- **priority** → which epic/story is next (or let it take the lowest ready one).
- **gate** → nothing to control; the gate is machine-verified (exit code). Review the merged result.

## The drive loop

1. **Pick** the next story: first `ready-for-dev` (else `backlog`) in `sprint-status.yaml`, lowest
   epic then story — unless the user named one. Announce the pick + its goal-ladder
   (macro → story) in one line. Emit the Board: `python3 harness/board.py --story {ID} --phase create-story`.
2. **Dispatch** it through the `story-worktree` skill. For each loop step, resolve the loadout
   from `team.yaml`: `roles[step].by_discipline[touched] or roles[step].default` → spawn a
   subagent of that `subagent_type` carrying those `skills` **and the goal-ladder** (task goal +
   its story/macro parents). Ponytail governs every child.
3. **Gate** is story-worktree's hard gate (`gate_runner` exit code). Exit 0 → merge via
   `gate_merge`. Non-zero → HALT: surface the verdict `reasons`, preserve the worktree, stop.
   Never override the exit code.
4. **Board** updates at every transition (story-worktree emits it). On merge → mark the story
   `done` in sprint-status.yaml, emit `--phase done`, pick the next.
5. **Stop** when the backlog is empty, a story HALTs, or the user says stop. One-line summary per
   story: id, gate verdict, merge SHA (or the HALT reason).

## Roles → steps (from team.yaml)

`create-story → test-author (atdd) → implementer (dev-story) → reviewer (code-review) → tracer (trace)`.
`implementer` and `test-author` subagents vary by the discipline the story touches; the rest use
their `default`. If a story touches a discipline with no `team.yaml` entry, that's a roster gap —
run `generate-team` to resolve and promote it before dispatching.

## Governor (both scopes)

- **Work scope:** every dispatch hands the goal-ladder down. The `code-review` step's goal-alignment
  layer blocks a diff that exceeds or misses its task goal — drift dies there, not "later".
- **Harness scope:** periodically run `python3 harness/audit.py` — it flags any skill/agent that
  doesn't trace to a `workflow-steps.md` step (removal candidate). Nothing is auto-removed; prune
  with explicit intent.
