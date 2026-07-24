---
name: generate-team
description: "Use when setting up or refreshing a project's dev roster — 'generate the team', 'update the team', 'set up simple-dev on this project'. Detects the stack, composes the declarative team.yaml the ScrumMaster reads at dispatch (roles = loop steps, resolved by discipline), and marker-merges the dev block into AGENTS.md. Deterministic table for known stacks; judgment only for gaps, which you then promote into the table."
---

# generate-team (v3)

Compose a project's **declarative roster** — `team.yaml` (machine-readable; the ScrumMaster
reads it per story) + an `AGENTS.md` dev block (human-readable). Hybrid selection: a
deterministic table for known stacks, judgment only for the gaps.

## 1. Run the deterministic core

```
python3 harness/gen_team.py --cwd <project-root> --direction "<one-line PROJECT-DIRECTION>"
```

Detects disciplines via `harness/team_table.py`, writes `team.yaml`, marker-merges `AGENTS.md`,
and prints the disciplines, role count, and any **gaps**. Output is reproducible (no timestamps)
— same `(repo, direction)` → same `team.yaml`.

## 2. Resolve gaps (judgment), then promote

A gap = a stack present in the project the table doesn't map (e.g. `build.gradle` → kotlin). For each:

1. Pick the best-fit subagent for that discipline from the installed Agent types or the broad
   VoltAgent catalog (`subagent-catalog` search).
2. Add its loadout to `team.yaml` under the discipline-varying roles (`implementer`, `test-author`).
3. **Promote** it: add a row to `harness/team_table.py` (`DISCIPLINES`) so the next run is
   deterministic. Note the promotion in the commit message.

## 3. The curation gate (anti-sprawl — the Focus Governor, work scope)

The catalog is broad, so the gate is **per role: a skill enters a role's loadout only if it
traces to that role's job.** `reviewer` gets review skills; `implementer` gets `dev-story`.
Never pad a role's `skills` with anything it won't invoke.

## Schema

`team.yaml`: `meta` · `disciplines` (stack → subagent, `via: table|judgment`) · `roles` (one per
loop step; discipline-varying roles carry `by_discipline` + `default`) · `gaps`. The SM resolves
a step's loadout as `roles[step].by_discipline[touched] or roles[step].default`.

## Part of the project-bootstrap

When simple-dev is installed onto a project (the init/bootstrap), this runs as its team step, so
a freshly-bootstrapped project arrives with its roster already composed.
