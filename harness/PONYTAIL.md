# The Discipline (ponytail)

The behavioral foundation of simple-dev. Every agent the harness dispatches works under this —
it is not an optional plugin, it is baked in and travels with every install. It is the engine of
the [Focus Governor](./GOVERNANCE.md): the Governor decides *what may exist*; this decides *how it
gets built*. Faithful to the `ponytail` discipline (DietrichGebert/ponytail); embedded here so the
reflex never depends on an external plugin being enabled.

> Lazy means efficient, not careless. The best code is the code never written.

## The ladder — stop at the first rung that holds

1. **Does this need to exist at all?** Speculative need → skip it, say so in one line. (YAGNI)
2. **Already in this codebase?** A helper, util, type, or pattern that already lives here → reuse it.
3. **Stdlib does it?** Use it.
4. **Native platform feature covers it?** Prefer it (a DB constraint over app code, CSS over JS…).
5. **An already-installed dependency solves it?** Use it. Never add a new dep for a few lines.
6. **Can it be one line?** One line.
7. **Only then:** the minimum code that works.

The ladder runs *after* you understand the problem, never instead of it. Read the task and the code
it touches, trace the real flow end to end, **then** climb. The first lazy solution that works —
once you actually know what the change must touch — is the right one.

## Rules

- No unrequested abstractions: no interface with one implementation, no factory for one product, no
  config for a value that never changes. No boilerplate or scaffolding "for later".
- Deletion over addition. Boring over clever. Fewest files, shortest **working** diff.
- **Bug fix = root cause, not symptom.** Grep every caller of the function you're about to touch;
  fix it once where they all route through, not per-caller.
- Mark a deliberate corner cut (global lock, O(n²) scan, naive heuristic) with a `ponytail:` comment
  naming the ceiling and the upgrade path.

## When NOT to be lazy

Never simplify away: input validation at trust boundaries, error handling that prevents data loss,
security, accessibility basics, anything explicitly requested. **Never lazy about understanding the
problem** — laziness that skips comprehension to ship a small diff ships a confident wrong fix.

## Leave a check

Non-trivial logic (a branch, a loop, a parser, a money/security path) leaves exactly ONE runnable
check — the smallest thing that fails if the logic breaks. No frameworks, no fixtures unless asked.
Trivial one-liners need none; YAGNI applies to tests too.

**The shortest path to done is the right path — but only once you understand the problem.**
