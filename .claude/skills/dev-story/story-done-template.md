<!-- STORY-DONE completion contract template. The merge gate
(story_done_check.py) validates this file mechanically — every frontmatter
field below is required and type-checked. An invalid or missing STORY-DONE
blocks the merge. -->
<!-- design absorbed from matilha-gather (SP-DONE machine-checked completion
contract) by danilods (MIT, v0.3.0) on 2026-07-09; ported into simple-dev. -->

---
type: story-done
story_id: "{{epic_num}}-{{story_num}}"
epic: {{epic_num}}
status: completed
completed_at: "{{iso8601_utc_timestamp}}"
commits:
  - "{{real_sha_on_this_branch}}"
tests:
  passed: true
  count: {{passing_test_count}}
touches:
  - "{{path/relative/to/repo/root}}"
---

# STORY-DONE: {{story_key}}

{{One-paragraph completion summary: what shipped, which ACs it satisfies, and
where the evidence lives (test files, story file Dev Agent Record).}}

## Field rules (enforced by the gate — do not hand-wave)

- `type` — the literal `story-done`.
- `story_id` — this story's id; `1.2` and `1-2` are equivalent (the gate
  normalizes dots to dashes). Must match the story being gated.
- `epic` — the epic number.
- `status` — the literal `completed`.
- `completed_at` — ISO-8601 UTC (e.g. `2026-07-09T18:30:00Z`). Take it from
  `date -u +%Y-%m-%dT%H:%M:%SZ`, never invent it.
- `commits` — non-empty list of REAL commit SHAs that exist on this branch
  (take them from `git log`; the gate runs `git cat-file` on each).
- `tests.passed` — the literal `true`, only after a fresh full-suite run.
- `tests.count` — integer > 0: the number of passing tests in that run.
- `touches` — the files actually modified by this story (mirror the story's
  File List, paths relative to repo root).
