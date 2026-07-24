# The Focus Governor

The one property this harness exists to keep: **it must not bloat, and no agent must drift.**
Both are the same failure — *getting lost* — at two scales. One law governs both.

> **Nothing exists in the harness, and no work proceeds, unless it serves an explicit goal
> that ladders to the macro objective.**

## Scope 1 — Harness (self-pruning)

Every skill, agent, script, or plugin must trace to a step in [`workflow-steps.md`](./workflow-steps.md).

- The delivery loop is **one table**. Adding a step requires removing or justifying one.
- Anything the loop does not invoke is a **removal candidate**, not a keeper "for later".
- Manual enforcement now (this rule + review discipline); automated in M4 via a scheduled
  audit that flags untraceable components.

This is the guardrail that keeps simple-dev from becoming its predecessors (matilha, enxa-me),
which grew by accretion because nothing ever forced removal.

## Scope 2 — Work (laser focus)

Every story and task carries an explicit **goal-ladder**: `macro/epic goal → story goal → task goal`.

- The ladder lives in the story template (`Focus` block + per-task `goal:`).
- A dispatched subagent is handed all three rungs, so it always sees micro **and** macro.
- The Board renders the live ladder (`[task] → serving [story] → toward [macro]`).
- A diff that does not serve its stated task goal is **drift** — the review layer **blocks** it.
  It is never "cleaned up later".

## The stop test

Before adding anything, ask the ponytail question: *does this need to exist at all?*
If it does not trace to a loop step (harness) or serve a stated goal (work), it does not go in.
