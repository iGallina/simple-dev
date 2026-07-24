# simple-dev

A small, opinionated delivery harness for [Claude Code](https://docs.claude.com/en/docs/claude-code).
It turns "build this feature" into a fixed, repeatable pipeline where **a story is only *done*
when a machine says so** — and gives you a live board so you always know what's being built, what
step it's on, and what's next.

It exists for one problem: keeping agent-driven development **accountable** and stopping it from
sprawling over time. One loop. One board. One gate. One rule that keeps the whole thing from
bloating.

> **Status:** a personal harness, recently made public. It runs real projects, but it's
> opinionated and specific to Claude Code. Expect sharp edges, and read the code before you trust
> it with yours.

---

## The idea

Most delivery work is mechanical, so simple-dev makes it mechanical and verifiable:

- **One loop** — every story goes through the same steps:
  `create-story → write failing acceptance tests (ATDD) → implement → adversarial review → trace coverage`,
  then a **hard gate**.
- **One gate** — the gate runs *your* tests and validates a completion contract, then returns an
  **exit code, not an opinion**. A story merges only on exit `0`. There is no "looks good to me."
- **One board** — a live kanban *projected* from your sprint status × the current story's subtasks
  × the pipeline phase. It can't drift, because it's a projection of the real state, not a file you
  hand-edit.
- **One Governor** — a single rule enforced at two scales: *nothing stays in the harness unless it's
  used, and no change ships unless it serves the story's stated goal.* That's what stops simple-dev
  from slowly becoming the bloated thing you were trying to escape.

The whole harness is ~2k lines of pure-stdlib Python plus a handful of Claude Code skills. You can
read all of it in an afternoon.

---

## Requirements

**Required**

| | Why |
|---|---|
| **[Claude Code](https://docs.claude.com/en/docs/claude-code)** | simple-dev *is* a set of Claude Code skills + scripts. It runs inside Claude Code. |
| **Python 3.10+** | The harness scripts (gate, board, generators) are pure standard library — **zero pip dependencies**. |
| **git** | The gate and per-story worktree isolation need a git repository. |
| **[BMAD](https://github.com/bmad-code-org/BMAD-METHOD) `bmm` module** | Provides the *planning* half (PRD → architecture → epics → sprint plan) that produces the backlog simple-dev delivers, plus two review skills the loop calls. Installed per project. |

**Optional — simple-dev works without all of these:**

- **[uv](https://docs.astral.sh/uv/)** — only for the convenience `simple-dev` command. Without it,
  call the installer script directly (shown below).
- **graphify** — a codebase knowledge-graph tool. If present, the loop reads your code *through* it
  (dependency queries, blast-radius) and keeps a fresh graph. If absent, it degrades gracefully and
  **never blocks a story**.
- **the `ponytail` plugin** — the "build the least that works" discipline is **baked in**
  (`harness/PONYTAIL.md`, deployed with every install), so you don't need the plugin. If you happen
  to have it, it simply layers on top.

---

## Install

```sh
# 1. Get simple-dev and expose the `simple-dev` command (needs uv)
git clone https://github.com/iGallina/simple-dev.git
uv tool install --editable ./simple-dev

# 2. In the project you want to deliver, install the planning half (BMAD bmm)
cd /path/to/your-project
npx bmad-method install --modules bmm --tools claude-code

# 3. Install simple-dev's harness into that project
simple-dev install --target . --direction "one line on where this project is heading"
```

Step 3 deploys `harness/` + the delivery skills into your project, generates a `team.yaml` roster
from your detected stack, writes an `AGENTS.md` dev block, and (if graphify is installed) seeds a
code graph.

**No `uv`?** Skip step 1 and run the installer directly:

```sh
python3 /path/to/simple-dev/harness/install.py --target .
```

---

## Delivering a story

Open your project in Claude Code and invoke the **`scrum-master`** skill to deliver the next story
(or **`story-worktree`** to run a specific one). It then:

1. **Isolates** the story in its own git worktree — nothing touches your main branch until it passes.
2. **Runs the loop**, dispatching each step to the right kind of agent based on `team.yaml` and the
   part of the codebase the story touches.
3. **Emits a board line** at every transition, so your logs read like a kanban.
4. **Hits the hard gate:** `harness/gate_runner.py` runs your tests + validates the completion
   contract → exit code. On `0`, `harness/gate_merge.py` merges and runs a post-merge regression.
   On anything else it **halts**, preserves the worktree, and prints the reasons. It never merges
   unproven work.

You set direction, priority, and review the merged result. The gate is the definition of *done*.

---

## What's in the box

| Piece | File(s) | What it does |
|---|---|---|
| **Gate** | `harness/gate_runner.py` → `gate_merge.py` | Runs your tests + a completion contract, returns an exit code. The *only* path to merge. No LLM verdict. |
| **Board** | `harness/board.py` | Renders a live kanban (story states × subtasks × phase × goal). A projection — it can't lie. |
| **Roster** | `harness/gen_team.py` → `team.yaml` | Detects your stack and writes a per-role loadout: which kind of agent + which skills handle each loop step. |
| **Governor** | `harness/GOVERNANCE.md`, `audit.py` | Enforces "nothing exists unless it serves a goal": a self-audit flags unused skills; a review layer blocks off-goal changes. |
| **Discipline** | `harness/PONYTAIL.md` | The build-the-least-that-works reflex every worker runs under. |
| **Context** | `harness/graph.py` | Wraps graphify — read the code through it, keep it fresh. Optional, graceful. |

---

## Verify it works

```sh
cd /path/to/simple-dev
for t in harness/tests/test_*.py; do python3 "$t"; done   # 23 checks, zero framework deps
```

Every check builds its own throwaway fixtures, so nothing touches your machine.

---

## Credits & license

MIT — see [`LICENSE`](./LICENSE). simple-dev is greenfielded from and vendors
[BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) (MIT); the "ponytail" discipline is
credited to [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail).
