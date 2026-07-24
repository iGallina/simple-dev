---
name: story-worktree
description: "Use when the user asks to run/deliver/implement a story end-to-end in isolation — 'run story 2-1', 'deliver the next story'. The simple-dev workhorse: git-worktree isolation → create-story → ATDD red → dev-story green (writes STORY-DONE) → 3-layer adversarial review → trace → HARD GATE (gate_runner exit code, never LLM judgment) → gate_merge with post-merge regression. Emits the Board at every phase. Merges only on machine-verified PASS; failures preserve the worktree with recovery commands."
---

<!-- simple-dev core pipeline. Lineage: bmad-story-pipeline-worktree,
     hardened with deterministic gates. -->

# story-worktree

Deliver one story in an isolated worktree; merge only after the machine says PASS. Every
phase transition emits the Board (`harness/board.py`) so the logs show exactly where we are —
the goal-ladder included.

## Preconditions

- `harness/workflow-steps.md` exists — read it NOW. All step commands, the gate command, and
  conventions come from there. Do not improvise command names.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` exists with a backlog.

## Phase 0 — Resolve the story

No ID given → pick the first backlog/ready story from sprint-status.yaml (lowest epic, lowest
story). Confirm the pick in one line. Story already `done` → say so, stop.

## Phase 1 — Worktree

```
git worktree add -b story/{ID} ../simple-dev-story-{ID} main
```
All subsequent phases run INSIDE the worktree. If the branch/worktree already exists: a
previous run failed — inspect its state (verdict file, STORY-DONE), resume from the first
incomplete step; never `--force` over it.

## Phase 2 — Pipeline steps (emit the Board at each transition)

Run steps 1–5 from `harness/workflow-steps.md` in order. Execute each step in a fresh worker
context when the harness supports it (its loadout comes from `team.yaml`, its discipline from
`harness/PONYTAIL.md`); otherwise in the current context. Fail-fast: a step that reports failure or HALT stops the pipeline (leave
everything for inspection, report which step and why).

**Context is graphify's — read the project through it, keep it fresh.** Before step 1, run
`python3 harness/graph.py check`; if it reports STALE, `graphify update .`. **Every step's worker
reads code via graphify FIRST** — `graph.py query "<what>"` / `affected "<area>"` /
`explain "<symbol>"` — before falling back to blind file scans; `create-story` bakes the
blast-radius into the story's Dev Notes. graph.py degrades gracefully — a missing graph never
blocks a story, and the graph is refreshed post-merge (Phase 5) so it never drifts far.

**After each step transition, emit the Board:**
```
python3 harness/board.py --story {ID} --phase {step}
```
where `{step}` runs `create-story`, `atdd`, `dev-story`, `code-review`, then `trace`. Each
call rewrites `BOARD.md` and prints the one-line log with the live goal-ladder.

Step 3 (dev-story) MUST end with a committed STORY-DONE file — if missing after the step, that
is a step failure, not something to patch up silently.

## Phase 3 — Status updates (inside the worktree, before the gate)

Mark the story `done` in sprint-status.yaml and in the story file; commit with the
explicit-path rule from workflow-steps.md conventions.

## Phase 4 — THE HARD GATE

```
python3 harness/board.py --story {ID} --phase gate
python3 harness/gate_runner.py --story {ID}
```
Read the EXIT CODE:
- **0** → commit the verdict file if untracked, proceed to Phase 5.
- **non-zero** → HALT. Print the verdict `reasons`, the exit-code meaning, the preserved
  worktree path, and recovery: fix inside the worktree → re-run the failed step → re-run
  gate_runner. NEVER merge. The exit code is the truth.

## Phase 5 — Merge

From the ORIGINAL repo (not the worktree):
```
python3 harness/gate_merge.py --story {ID} --branch story/{ID} --cleanup --worktree <path>
```
Exit 0 → `python3 harness/board.py --story {ID} --phase done` and `python3 harness/graph.py
update` (refresh the graph with the merged code); report the merge SHA + regression time.
Exit 11/12/13/14 → print its JSON verbatim (it contains recovery) and stop.
Exit 14's `git reset --hard` recovery is printed for the HUMAN — never execute it.

## Output

One-screen summary: story, steps run, gate verdict path, merge SHA (or the HALT report). No
JSON dumps beyond what failures require.
