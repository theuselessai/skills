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
find skills/<skill-name> -type f | sort | xargs sha256sum | sha256sum | awk '{print $1}'
```

## Available Skills

### Software Development

| Skill | Version | Description |
|-------|---------|-------------|
| [headless-claude-code](./skills/headless-claude-code) | 1.1.0 | CLI conventions for running Claude Code headlessly — universal invocation template, stream relay |
| [dev-plan](./skills/dev-plan) | 1.0.2 | Codebase exploration and structured dev plan generation with draft PR |
| [dev-implement](./skills/dev-implement) | 1.0.1 | Implementation from approved dev plans with CI/review triage cycles |
| [opencode-configuration](./skills/opencode-configuration) | 1.0.0 | Configure OpenCode with GLM/MiniMax providers and pre-defined agents |
| [intermediary-delivery](./skills/intermediary-delivery) | 2.0.0 | Fire-and-forget outbound message delivery via Telegram scripts |

### Productivity

| Skill | Version | Description |
|-------|---------|-------------|
| [meeting-mode](./skills/meeting-mode) | 1.0.2 | Meeting capture with natural language classification — no prefix triggers needed |

#### headless-claude-code

Conventions and patterns for running Claude Code headlessly via `claude -p`:

- **Universal template** — one invocation pattern for all subprocess calls, only `timeout` and `--max-turns` vary
- **Full tool access** — everything except `rm -rf`, no `--model` or `--allowedTools` restrictions
- **Stream relay** — `claude_telegram_relay.py` pipes `stream-json` output to Telegram in real time
- **Session management** — `--resume` with `--dangerously-skip-permissions` re-passed on every resume
- **Timeout conventions** — single default: 30m timeout, 50 max turns

**Requires:** `claude`, `python3`, `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` environment variables

#### dev-plan

Codebase exploration and structured development plan generation:

- **Explore + plan** — `claude -p` reads the codebase and writes `dev-plans/<slug>.md`
- **Draft PR** — plan committed and opened as draft PR for review
- **Revision loop** — user sends feedback, subprocess revises, loop until approved
- **Abort** — close PR on user request

**Requires:** `gh` (authenticated), `git` (with push access), `headless-claude-code` skill

#### dev-implement

Implementation from approved dev plans with automated review cycles:

- **Plan-driven** — reads an approved `dev-plans/<slug>.md` and implements it
- **Phased implementation** — large plans split into phases automatically when needed
- **Review cycle** — triages all CI results and PR review comments, fixes issues, loops until green
- **Coverage enforcement** — never lowers thresholds, writes real tests

**Requires:** `gh` (authenticated), `git` (with push access), `headless-claude-code` skill

#### opencode-configuration

Configures OpenCode for use with GLM/MiniMax providers:

- **Provider setup** — Z.AI (GLM) and MiniMax via environment variables
- **Agent definitions** — creates plan, implement, review, ci-analysis, coverage agents

**Requires:** `opencode`, `ZAI_API_KEY` and/or `MINIMAX_API_KEY` environment variables

#### intermediary-delivery

Fire-and-forget outbound message delivery for orchestrator-level communication:

- **Text messages** — `send.sh` sends plain text via Telegram API
- **File delivery** — `send_file.sh` sends files with optional captions
- **Stateless** — scripts deliver and exit, no blocking or polling
- **Orchestrator use** — status updates between subprocess calls and artifact delivery after exit
- **Subprocess visibility** — handled by stream relay pattern (see headless-claude-code)

**Requires:** `bash`, `curl`, `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` environment variables

#### meeting-mode

Real-time working session capture with natural language classification:

- **Haiku 4.5 orchestrator** — classifies every message naturally (passive/note/action item/research/end)
- **No prefix triggers** — users just talk, Haiku sorts it out
- **Passive capture** — zero LLM cost for casual conversation
- **Research queries** — `claude -p` spawned only when tool access is needed
- **Batch rotation** — every 100 messages with Haiku summaries
- **End-of-session synthesis** — structured summary delivered via intermediary-delivery

**Requires:** `headless-claude-code` skill

## Installation

### Use

Clone the repository:

```bash
git clone https://github.com/theuselessai/useless-skills.git
```

### Contribute

Fork, then clone your fork:

```bash
gh repo fork theuselessai/useless-skills --clone
cd useless-skills
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
/
├── skills.json                          # Remote package registry
├── README.md
├── CONTRIBUTING.md
├── CLAUDE.md
├── LICENSE
└── skills/
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
3. Add a `version.json` with name, version, category, description, and requires
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
