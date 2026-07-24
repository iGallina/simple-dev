# simple-dev workflow steps — the ONE loop

This table is the single source of truth for the delivery loop. Pipeline skills read step
commands FROM HERE — never hardcode command names in SKILL bodies (that is how the
stale-name bug class happened in enxa).

Per the [Focus Governor](./GOVERNANCE.md): **every harness component must trace to a step in
this table.** If it is not here, it is a removal candidate.

## The story delivery loop (in order, fail-fast)

| # | step | command | source | purpose |
|---|------|---------|--------|---------|
| 1 | create-story | `create-story {ID}` | ported (gate-coupled) | Story file from epic + context, with the goal-ladder (`Focus` block) |
| 2 | atdd (red) | `testarch-atdd {ID}` | ported | Failing acceptance scaffolds BEFORE implementation |
| 3 | dev-story (green) | `dev-story {ID}` | ported | Red-green-refactor per task; ticks subtasks; **writes the `STORY-DONE` contract** |
| 4 | code-review | `code-review {ID}` | ported | 3-layer adversarial (blind / edge-case / acceptance); goal-alignment layer added in G3 |
| 5 | trace (gate input) | `testarch-trace {ID}` | ported | Coverage matrix; emits `gate-decision-{ID}.json` |

Full port of the 5 delivery skills (testarch knowledge de-duplicated to one shared copy). Vanilla
bmm supplies PLANNING (create-prd → architecture → epics → sprint-planning); its
`bmad-{create-story,dev-story,code-review}` are now redundant — the Governor self-audit (G2)
flags them. The goal-alignment review layer is added in G3. **No seal step:** `dev-story` writes
`STORY-DONE` natively.

## The hard gate (after step 5 — mechanical, non-negotiable)

```
python3 harness/gate_runner.py --story {ID}
```

Exit 0 = merge permitted. Anything else = HALT: preserve the worktree, print the verdict
`reasons` + recovery, stop. Never merge on non-zero exit.
Exit map: `10` tests failed · `20` STORY-DONE missing/invalid · `30` trace gate · `40` environment.

## The merge (the only path)

```
python3 harness/gate_merge.py --story {ID} --branch story/{ID} [--cleanup --worktree <path>]
```

Exit 0 = merged + post-merge regression passed. `11` verdict not PASS/stale · `12` pre-flight ·
`13` conflict (aborted, tree restored) · `14` regression failed (recovery printed — a human runs
it, never the agent).

## Conventions

- Branch: `story/{ID}` · Worktree: `../simple-dev-story-{ID}`
- Each step runs as a fresh subagent (its loadout comes from `team.yaml`, Phase E), fail-fast.
- Status updates (`sprint-status.yaml` → done, story file → done) happen in the worktree
  BEFORE the gate, so they are part of the gated commit set.
- The Board: at each step transition the loop runs
  `python3 harness/board.py --story {ID} --phase {step}`, which rewrites `BOARD.md` and prints
  the one-line log (including the live goal-ladder). The projector exists (Phase C); the
  physical wiring into the loop-runner lands with the runner in Phase D.
