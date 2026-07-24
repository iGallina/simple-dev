"""The deterministic selection table for generate-team v3.

This is the "table" half of the hybrid selection: known stacks map to a subagent here,
reproducibly. When the generator hits a stack this table doesn't cover, it reports a GAP;
the wrapping skill resolves it by judgment and you PROMOTE the choice by adding a row here.

Broad catalog, gated per role: `subagent_type` may be any installed Agent type; a skill
enters a role's loadout only if it traces to that role's job (see ROLES).
"""

# (discipline, [detector markers], subagent_type). A marker prefixed "glob:" is a glob.
# First matching marker wins for that discipline.
DISCIPLINES = [
    ("python",   ["pyproject.toml", "setup.py", "requirements.txt", "glob:**/*.py"], "python-pro"),
    ("node",     ["package.json"],                                   "typescript-pro"),
    ("rust",     ["Cargo.toml"],                                     "rust-engineer"),
    ("go",       ["go.mod"],                                         "golang-pro"),
    ("ruby",     ["Gemfile"],                                        "rails-expert"),
    ("markdown", ["glob:.claude/skills/**/*.md"],                    "technical-writer"),
]

# Stacks NOT in the table above — presence flags a GAP (judgment + promote), never a guess.
KNOWN_UNMAPPED = {
    "build.gradle": "kotlin/java",
    "build.gradle.kts": "kotlin",
    "composer.json": "php",
    "pubspec.yaml": "dart/flutter",
    "mix.exs": "elixir",
    "glob:*.csproj": "csharp",
}

# Loop-step roles → base loadout. Roles in DISCIPLINE_VARYING also get by_discipline entries
# (their subagent_type comes from the matched discipline). `skills` are the ONLY skills that
# trace to that role's job — the per-role curation gate.
ROLES = {
    "create-story": {"subagent_type": "general-purpose", "skills": ["create-story"],
                     "context": ["affected {touches}", "epics.md"]},
    "test-author":  {"subagent_type": "test-automator", "skills": ["testarch-atdd"]},
    "implementer":  {"subagent_type": "general-purpose", "skills": ["dev-story"]},
    "reviewer":     {"subagent_type": "code-reviewer",
                     "skills": ["code-review", "bmad-review-edge-case-hunter",
                                "bmad-review-adversarial-general"],
                     "context": ["affected {touches}"]},
    "tracer":       {"subagent_type": "qa-expert", "skills": ["testarch-trace"]},
}

# Roles whose subagent_type varies by the discipline the story touches.
DISCIPLINE_VARYING = ["implementer", "test-author"]
