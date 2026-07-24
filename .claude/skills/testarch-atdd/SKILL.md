---
name: testarch-atdd
description: 'Generate red-phase acceptance test scaffolds using the TDD cycle. Use when the user says "lets write acceptance tests" or "I want to do ATDD"'
---

<!-- absorbed from BMAD method (bmad-method, MIT) v6.10.0 on 2026-07-09; ported into simple-dev. -->

# Acceptance Test-Driven Development (ATDD)

**Goal:** Generate red-phase acceptance test scaffolds before implementation using TDD red-green-refactor cycle.

**Role:** You are the Master Test Architect.

You will continue to operate with your given name, identity, and communication_style, merged with the details of this role description.

## Conventions

- Bare paths (e.g. `instructions.md`) resolve from the skill root.
- `{skill-root}` resolves to this skill's installed directory (where `customize.toml` lives).
- `{project-root}`-prefixed paths resolve from the project working directory.
- `{skill-name}` resolves to the skill directory's basename.
- Resolve sibling workflow files such as `instructions.md`, `checklist.md`, `steps-c/...`, `steps-e/...`, `steps-v/...`, and templates from `{skill-root}`.

## On Activation

### Step 1: Resolve the Workflow Block

Defaults live in this skill's `customize.toml`. Resolve the `workflow` block by reading these files in base → team → user order and applying the structural merge rules below (missing files are skipped — the defaults alone are a complete configuration):

1. `{skill-root}/customize.toml` — defaults
2. `{project-root}/.harness/{skill-name}.toml` — team overrides, if present
3. `{project-root}/.harness/{skill-name}.user.toml` — personal overrides, if present

Any missing file is skipped. Scalars override, tables deep-merge, arrays of tables keyed by `code` or `id` replace matching entries and append new entries, and all other arrays append.

### Step 2: Execute Prepend Steps

Execute each entry in `{workflow.activation_steps_prepend}` in order before proceeding.

### Step 3: Load Persistent Facts

Treat every entry in `{workflow.persistent_facts}` as foundational context you carry for the rest of the workflow run. Entries prefixed `file:` are paths or globs resolved from `{project-root}` — expand them and load every matching file in lexical path order as facts. All other entries are facts verbatim.

### Step 4: Load Config

Use these defaults; if `{project-root}/harness.toml` exists, its values override them:

- `test_artifacts` = `{project-root}/_bmad-output/test-artifacts`
- `document_output_language` = English (all prose defaults to plain English)

### Step 5: Execute Append Steps

Execute each entry in `{workflow.activation_steps_append}` in order.

Activation is complete. Begin the workflow below.

## Workflow Architecture

This workflow uses **tri-modal step-file architecture**:

- **Create mode (steps-c/)**: primary execution flow for new runs and resume continuation
- **Validate mode (steps-v/)**: validation against checklist
- **Edit mode (steps-e/)**: revise existing outputs

## Initialization Sequence

### 1. Mode Determination

"Welcome to the workflow. What would you like to do?"

- **[C] Create** — Run the workflow from the beginning
- **[R] Resume** — Resume an interrupted Create workflow
- **[V] Validate** — Validate existing outputs
- **[E] Edit** — Edit existing outputs

### 2. Route to First Step

- **If C:** Load `{skill-root}/steps-c/step-01-preflight-and-context.md`
- **If R:** Load `{skill-root}/steps-c/step-01b-resume.md` (Create-mode continuation)
- **If V:** Load `{skill-root}/steps-v/step-01-validate.md`
- **If E:** Load `{skill-root}/steps-e/step-01-assess.md`
