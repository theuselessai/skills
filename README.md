# Skills

Community skills for [Pipelit](https://github.com/theuselessai/Pipelit) — the self-hosted platform for building and executing LLM agent pipelines through a visual, drag-and-drop interface.

Skills are folders of instructions and resources that Claude loads dynamically to improve performance on specialized tasks. They teach Claude how to complete specific tasks in a repeatable way, whether that's managing development workflows, automating CI/CD pipelines, or orchestrating multi-step processes.

For more information on skills, check out:

- [What are skills?](https://support.claude.com/en/articles/12512176-what-are-skills)
- [How to create custom skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)
- [Equipping agents for the real world with Agent Skills](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

## About This Repository

This repository contains community-built skills designed for use with Pipelit development workflows. Each skill is self-contained in its own folder with a `SKILL.md` file containing the instructions and metadata that Claude uses.

Skills are organized by category and tracked via [`skills.json`](./skills.json) — a package manifest that agents use to compare local skill versions against the repository, similar to how `apt` or `apk` manage packages.

## Version Management

Skills use a two-tier versioning system, similar to how `apt` or `apk` manage packages:

### Remote — `skills.json`

The root [`skills.json`](./skills.json) is the **remote registry**. Agents fetch this single file to discover all available skills, their versions, and checksums.

### Local — `version.json`

Each skill carries its own `version.json` inside its folder. This is the **local manifest** that stays with the installed skill. Agents compare their local `version.json` against the remote `skills.json` to determine if an update is available.

```jsonc
// <category>/<skill-name>/version.json
{
  "name": "dev-workflow",
  "version": "1.0.0",
  "category": "software_development",
  "description": "Universal dev lifecycle skill...",
  "requires": ["gh", "git", "claude"]
}
```

### Update Flow

```
Agent fetches remote skills.json
  → compares version against local <skill>/version.json
  → if remote version is newer, downloads and replaces skill folder
  → verifies sha256 checksum after install
```

When publishing a new skill or updating an existing one, bump the `version` field in both `skills.json` and the skill's `version.json`, then regenerate the `sha256` hash:

```bash
find <category>/<skill-name> -type f | sort | xargs sha256sum | sha256sum | awk '{print $1}'
```

## Available Skills

### Software Development

| Skill | Version | Description |
|-------|---------|-------------|
| [dev-workflow](./software_development/dev-workflow) | 1.0.0 | Universal development lifecycle — full pipeline from task intake to merged PR with human-in-the-loop approval at every gate |

#### dev-workflow

Manages the complete development pipeline:

**Plan → Approval → Branch + Draft PR → Phased Implementation → CI Triage → Review Triage → Coverage → Merge**

- **Human-in-the-loop** — approval gates at every meaningful decision point via Telegram
- **Phased implementation** — breaks work into 2–5 discrete phases, each independently testable
- **Smart model selection** — Opus for planning/analysis, Sonnet for implementation, Haiku for boilerplate
- **CI/CD awareness** — polls CI checks, analyzes failures, proposes fixes
- **Review triage** — critically evaluates PR comments (confirmed bug vs. false positive)
- **Coverage enforcement** — identifies gaps and writes real tests instead of lowering thresholds
- **State persistence** — saves progress for resuming interrupted work

**Requires:** `gh` (authenticated), `git` (with push access), `claude`

## Installation

### Claude Code

Register this repository as a Claude Code Plugin marketplace:

```bash
/plugin marketplace add theuselessai/useless-skills
```

Or install a specific skill:

```bash
/plugin install dev-workflow@theuselessai-useless-skills
```

### Manual

Clone and copy the skill folder into your project:

```bash
git clone https://github.com/theuselessai/useless-skills.git
cp -r useless-skills/software_development/dev-workflow /path/to/your/project/.claude/skills/
```

## Creating a Skill

Skills are simple to create — just a folder with a `SKILL.md` file containing YAML frontmatter and instructions:

```yaml
---
name: my-skill-name
description: A clear description of what this skill does and when to use it
---

# My Skill Name

[Instructions that Claude will follow when this skill is active]

## Examples
- Example usage 1
- Example usage 2

## Guidelines
- Guideline 1
- Guideline 2
```

The frontmatter requires only two fields:

- `name` — A unique identifier for your skill (lowercase, hyphens for spaces)
- `description` — A complete description of what the skill does and when to use it

### Directory Structure

```
skills/
├── skills.json                          # Remote package registry
├── README.md
└── <category>/
    └── <skill-name>/
        ├── SKILL.md                     # Required — skill definition
        ├── version.json                 # Required — local version manifest
        └── references/                  # Optional — supporting files
            ├── prompts.md
            └── helpers.md
```

### Publishing Checklist

1. Create a folder under the appropriate category (or create a new category)
2. Add a `SKILL.md` with proper frontmatter and instructions
3. Add a `version.json` with name, version, category, description, requires, and sha256
4. Add a matching entry to the root `skills.json`
5. Add the category to `skills.json` → `categories` if it's new
6. Update the **Available Skills** table in this README
7. Open a pull request

## Contributing

Contributions are welcome! Read **[CONTRIBUTING.md](./CONTRIBUTING.md)** for the full step-by-step guide — it covers everything from folder structure to PR submission, and is written for both humans and agents.

Skill ideas that would be useful:

- **Testing** — automated test generation, mutation testing, coverage analysis
- **Documentation** — API docs, changelogs, architecture decision records
- **DevOps** — infrastructure as code, deployment pipelines, monitoring setup
- **Security** — dependency auditing, secret scanning, vulnerability triage

## License

Apache 2.0 — see [LICENSE](./LICENSE) for details.
