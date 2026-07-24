# simple-dev

A minimal, accountable dev-delivery harness. **One loop, one board, one gate, one Governor.**

Greenfield from vanilla BMAD `bmm`, with a deterministic merge gate ported from enxa and the
**Focus Governor** (self-pruning + goal-ladder) baked in. Replaces enxa-me.

## Install into a project

```sh
uv tool install --editable ~/Projetos/simple-dev            # once — provides the `simple-dev` command
simple-dev install --target <project-dir> --direction "one line on where the project is heading"
```

Deploys `harness/` + the delivery skills, generates the project's `team.yaml` / `AGENTS.md`, and
seeds the graphify context graph. Requires BMAD `bmm` for the planning half
(`npx bmad-method install --modules bmm --tools claude-code`).

## The loop

`create-story → atdd → dev-story → code-review → trace → HARD GATE → merge`

Drive it with the `scrum-master` or `story-worktree` skills. A story is done **only** when
`harness/gate_runner.py` exits 0 and `harness/gate_merge.py` merges — exit-code truth, no LLM
verdict. The Board emits at every phase transition.

## Foundations

| Piece | File | Role |
|---|---|---|
| Gate | `harness/gate_runner.py` → `gate_merge.py` | the accountability spine (deterministic) |
| Board | `harness/board.py` | live kanban projection — can't drift |
| Roster | `harness/gen_team.py` → `team.yaml` | declarative per-role loadouts the ScrumMaster dispatches from |
| Governor | `harness/GOVERNANCE.md` + `audit.py` | nothing exists unless it serves a goal |
| Discipline | `harness/PONYTAIL.md` | build the least that works; every worker runs under it |
| Context | `harness/graph.py` (graphify) | owns codebase knowledge; read through it, kept fresh |

## Tests

```sh
for t in harness/tests/test_*.py; do python3 "$t"; done   # 23 checks, zero framework deps
```

Vendors [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) (MIT). The ponytail discipline
is credited to [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail).
