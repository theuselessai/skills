# Contributing Skills

This guide is for **both humans and agents**. Read it before forking, creating a skill, and opening a pull request.

## Before You Start

1. Check [skills.json](./skills.json) and the [Available Skills](./README.md#available-skills) table to make sure your skill doesn't already exist
2. If it overlaps with an existing skill, consider improving that skill instead of creating a new one
3. Decide which category your skill belongs to — check `skills.json` → `categories` for existing ones

## Repository Structure

```
/
├── skills.json                          # Remote package registry (version + sha256)
├── README.md
├── CONTRIBUTING.md                      # You are here
├── CLAUDE.md                            # Project conventions for Claude Code
├── LICENSE
└── skills/
    └── <skill-name>/
        ├── SKILL.md                     # Required — skill definition
        ├── version.json                 # Required — local version manifest
        └── references/                  # Optional — supporting files
```

## Step-by-Step: Creating a Skill

### 1. Fork and Clone

```bash
gh repo fork theuselessai/useless-skills --clone
cd useless-skills
```

### 2. Create a Branch

```bash
git checkout -b add/<skill-name>
```

### 3. Create the Skill Folder

All skills live under the `skills/` directory.

```bash
mkdir -p skills/<skill-name>/references
```

### 4. Write `SKILL.md`

This is the core of your skill — the instructions Claude loads. It **must** include YAML frontmatter:

```yaml
---
name: my-skill-name
description: >
  A complete description of what this skill does and when to use it.
  Include trigger phrases so agents know when to activate this skill.
  Be specific — vague descriptions lead to poor skill matching.
---

# My Skill Name

Brief summary of what this skill does.

## Prerequisites

- List required tools, CLIs, or access
- e.g. `gh` CLI authenticated, `docker` available

## Instructions

Step-by-step instructions for Claude to follow.
Be explicit — Claude follows these literally.

## Key Rules

1. Non-negotiable constraints
2. Safety guardrails
3. Quality standards
```

**SKILL.md requirements:**

| Field | Required | Notes |
|-------|----------|-------|
| `name` (frontmatter) | Yes | Lowercase, hyphens for spaces, must match folder name |
| `description` (frontmatter) | Yes | Complete — include trigger phrases and use cases |
| Prerequisites section | Recommended | List all external dependencies |
| Step-by-step instructions | Yes | The actual skill logic |
| Key rules / constraints | Recommended | Safety guardrails and non-negotiable rules |

### 5. Write `version.json`

Every skill must include a `version.json` in its root folder:

```json
{
  "name": "my-skill-name",
  "version": "1.0.0",
  "category": "software_development",
  "description": "Same description as SKILL.md frontmatter — keep them in sync.",
  "requires": ["gh", "git"]
}
```

**version.json fields:**

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Must match SKILL.md frontmatter `name` and folder name |
| `version` | Yes | Semver — start at `1.0.0` for new skills |
| `category` | Yes | Must match the category key in `skills.json` |
| `description` | Yes | Keep in sync with SKILL.md frontmatter |
| `requires` | Yes | Array of CLI tools / dependencies needed (empty array `[]` if none) |

**Note:** `sha256` is intentionally **not** in `version.json` — it lives only in the root `skills.json` to avoid a circular dependency (the hash would change every time you update it).

### 6. Add References (Optional)

Place supporting files in a `references/` subfolder:

- Prompt templates
- Helper scripts
- Configuration examples
- API documentation snippets

Keep references focused. Don't include entire external docs — link to them instead.

### 7. Update `skills.json`

Add your skill entry to the root `skills.json`:

```json
{
  "my-skill-name": {
    "version": "1.0.0",
    "category": "my_category",
    "path": "skills/my-skill-name",
    "description": "Same description — keep in sync.",
    "requires": ["gh", "git"],
    "sha256": "<generate this>",
    "files": [
      "SKILL.md",
      "version.json",
      "references/example.md"
    ]
  }
}
```

If your skill introduces a new category, also add it to the `categories` object:

```json
{
  "categories": {
    "my_category": {
      "label": "My Category",
      "description": "What this category covers"
    }
  }
}
```

### 8. Generate the SHA256 Hash

From the repository root:

```bash
find skills/<skill-name> -type f | sort | xargs sha256sum | sha256sum | awk '{print $1}'
```

Put the resulting hash in `skills.json` → `skills` → `<your-skill>` → `sha256`.

**Important:** Generate the hash **after** all skill files are finalized. Any file change (including `version.json`) invalidates the hash.

### 9. Update the README

Add your skill to the **Available Skills** table in `README.md` under the appropriate category heading. If you created a new category, add a new `### Category Name` section.

### 10. Commit and Open a PR

```bash
git add skills/<skill-name>/ skills.json README.md
git commit -m "feat: add <skill-name> skill"
git push -u origin add/<skill-name>
gh pr create --title "Add <skill-name> skill" --body "$(cat <<'EOF'
## Summary
- Adds the `<skill-name>` skill
- <brief description of what it does>

## Checklist
- [ ] `SKILL.md` has proper frontmatter (`name`, `description`)
- [ ] `version.json` is present and fields match `SKILL.md`
- [ ] Entry added to root `skills.json` with sha256
- [ ] `files` array in `skills.json` lists all files in the skill folder
- [ ] README updated with skill in the Available Skills table
- [ ] Skill name is consistent across folder name, `SKILL.md`, `version.json`, and `skills.json`
- [ ] `requires` array lists all external dependencies
EOF
)"
```

## Naming Conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Skill folder | lowercase, hyphens | `dev-workflow` |
| Skill name (frontmatter) | lowercase, hyphens | `dev-workflow` |
| Category folder | lowercase, underscores | `software_development` |
| Category label | Title Case | `Software Development` |
| Branch | `add/<skill-name>` | `add/dev-workflow` |
| Version | Semver | `1.0.0` |

## Versioning Rules

- **Patch** (`1.0.0` → `1.0.1`): Typo fixes, minor wording improvements, no behavior change
- **Minor** (`1.0.0` → `1.1.0`): New optional features, added references, expanded instructions
- **Major** (`1.0.0` → `2.0.0`): Breaking changes to workflow, renamed triggers, restructured steps

When updating an existing skill, bump the version in **both** `version.json` and `skills.json`, then regenerate the sha256.

## Quality Guidelines

**Do:**
- Write clear, step-by-step instructions that Claude can follow literally
- Include safety guardrails and constraints
- List all prerequisites and external dependencies
- Test the skill in a real environment before submitting
- Keep descriptions specific — include trigger phrases

**Don't:**
- Submit skills that duplicate existing ones
- Include secrets, tokens, or credentials in any file
- Hardcode paths, usernames, or environment-specific values
- Write vague descriptions like "helps with development"
- Add unnecessary dependencies

## For Agents

If you are an AI agent preparing a contribution:

1. Fetch and read this file first
2. Read `skills.json` to understand existing skills and categories
3. Follow every step above exactly — do not skip the sha256 generation or README update
4. Ensure all names are consistent: folder name = `SKILL.md` name = `version.json` name = `skills.json` key
5. The PR checklist in Step 10 is not optional — verify every item
