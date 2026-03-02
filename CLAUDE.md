# Project: useless-skills

Community skills repository for [Pipelit](https://github.com/theuselessai/Pipelit).

## What This Repo Is

A package registry of skills — folders containing `SKILL.md` instructions that Claude loads dynamically. Skills are organized by category and tracked via `skills.json` (remote registry) and per-skill `version.json` (local manifest).

## Repository Structure

```
/
├── skills.json              # Remote package registry — single source of truth for versions + sha256
├── README.md                # Public-facing docs with Available Skills table
├── CONTRIBUTING.md          # Step-by-step guide for humans and agents submitting skills
├── CLAUDE.md                # You are reading this
├── LICENSE
└── skills/
    └── <skill-name>/
        ├── SKILL.md         # Required — skill definition with YAML frontmatter
        ├── version.json     # Required — local version manifest (no sha256 field)
        └── references/      # Optional — supporting files
```

## Critical Rules

1. **Read `CONTRIBUTING.md` before adding or modifying any skill.** It is the authoritative guide for all conventions.
2. **Names must be consistent everywhere.** Folder name, `SKILL.md` frontmatter `name`, `version.json` `name`, and `skills.json` key must all match exactly.
3. **`sha256` lives only in `skills.json`** — never in `version.json`. This avoids a circular dependency where the hash changes on every update.
4. **Generate sha256 after all files are finalized:**
   ```bash
   find skills/<skill-name> -type f | sort | xargs sha256sum | sha256sum | awk '{print $1}'
   ```
5. **Bump versions in both places** — `version.json` and `skills.json` — when updating a skill.
6. **Update the README** Available Skills table whenever a skill is added, removed, or has a version bump.
7. **`skills.json` `files` array** must list every file in the skill folder. Keep it up to date.
8. **Do not commit secrets, tokens, or credentials.** No `.env` files, no hardcoded API keys.
9. **Always create a new branch before making changes.** Branch naming: `add/<skill-name>` for new skills, `update/<skill-name>` for updates.

## Naming Conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Skill folder | lowercase, hyphens | `dev-workflow` |
| Skill name | lowercase, hyphens | `dev-workflow` |
| Category folder | lowercase, underscores | `software_development` |
| Category label | Title Case | `Software Development` |

## Version Management

- `skills.json` is the **remote registry** — agents fetch this to check for updates
- Each skill's `version.json` is the **local manifest** — stays with the installed skill
- Agents compare `version.json` version vs `skills.json` version to detect updates
- After download, agents verify integrity via the `sha256` in `skills.json`

## When Adding a New Skill

Follow `CONTRIBUTING.md` Steps 3–9. Summary:

1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`)
2. Create `skills/<skill-name>/version.json` (name, version, category, description, requires)
3. Add entry to `skills.json` → `skills` with version, category, path, description, requires, sha256, files
4. Add category to `skills.json` → `categories` if new
5. Add row to README Available Skills table
6. Generate sha256 hash last (after all files are written)

## When Updating an Existing Skill

1. Bump `version` in both `version.json` and `skills.json`
2. Update `skills.json` `files` array if files were added/removed
3. Regenerate sha256
4. Update README table if version or description changed
