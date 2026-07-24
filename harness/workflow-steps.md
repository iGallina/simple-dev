# simple-dev workflow steps — the ONE loop

This table is the single source of truth for the delivery loop. Pipeline skills read step
commands FROM HERE — never hardcode command names in SKILL bodies (that is how the
stale-name bug class happened in enxa).

Per the [Focus Governor](./GOVERNANCE.md): **every harness component must trace to a step in
this table.** If it is not here, it is a removal candidate.

## The story delivery loop (in order, fail-fast)

| # | step | command | source | purpose |
|---|------|---------|--------|---------|
| 1 | create-story | `bmad-create-story {ID}` | vanilla bmm | Story file from epic + context, with the goal-ladder (`Focus` block) |
| 2 | atdd (red) | `testarch-atdd {ID}` | enxa feeder | Failing acceptance scaffolds BEFORE implementation |
| 3 | dev-story (green) | `bmad-dev-story {ID}` | vanilla bmm | Red-green-refactor per task; ticks subtask checkboxes |
| 4 | seal | `harness/seal_story.py {ID}` | new (M4) | Writes the `STORY-DONE` contract (commits + tests) the gate consumes |
| 5 | code-review | `bmad-code-review {ID}` + goal-alignment layer | vanilla bmm + M4 | Adversarial review; a diff that misses its task goal is BLOCKED (drift dies here) |
| 6 | trace (gate input) | `testarch-trace {ID}` | enxa feeder | Coverage matrix; emits `gate-decision-{ID}.json` |

Net port from enxa's method skills: **2** (atdd, trace). The 3 standard skills are vanilla bmm.
`seal_story.py` and the goal-alignment review layer are built during loop wiring (M4).

## The hard gate (after step 6 — mechanical, non-negotiable)

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
- Each step runs as a fresh subagent (its loadout comes from `team.yaml`, M2), fail-fast.
- Status updates (`sprint-status.yaml` → done, story file → done) happen in the worktree
  BEFORE the gate, so they are part of the gated commit set.
- The Board (M1) emits one line per step transition, including the live goal-ladder.
