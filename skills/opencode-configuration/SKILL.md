---
name: opencode-configuration
description: >
  Skill for configuring OpenCode with GLM and MiniMax providers. Teaches the agent
  how to create and manage opencode.json, agent definitions, and provider
  configurations. Use this skill when setting up OpenCode for the first time,
  adding new providers, creating custom agents, or modifying existing
  configurations. Triggers on: "configure opencode", "setup opencode",
  "add agent", "create agent", "update opencode config", "switch model",
  "add provider", "opencode init".
---

# OpenCode Configuration

Configure OpenCode with GLM (Z.AI) and MiniMax providers. This skill teaches you
how to create and manage OpenCode configurations.

## Prerequisites

- `opencode` CLI available in PATH
- Environment variables set: `ZAI_CODING_PLAN_API_KEY` and/or `MINIMAX_CODING_PLAN_API_KEY`
- Write access to project directory

## Configuration Location

OpenCode looks for configuration in this order:

1. `OPENCODE_CONFIG` environment variable (custom path)
2. `.opencode/opencode.json` in project root
3. `~/.config/opencode/opencode.json` (global)

For project-specific setups, always use `.opencode/opencode.json`.

---

## Initial Setup

### 1. Create Directory Structure

```bash
mkdir -p .opencode/agents
```

### 2. Create Base Configuration

Create `.opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "zai-coding-plan/glm-4.7",
  "small_model": "zai-coding-plan/glm-4-flash",
  "provider": {
    "zai-coding-plan": {
      "options": {
        "apiKey": "{env:ZAI_CODING_PLAN_API_KEY}"
      }
    },
    "minimax-coding-plan": {
      "options": {
        "apiKey": "{env:MINIMAX_CODING_PLAN_API_KEY}"
      }
    }
  },
  "permission": {
    "edit": "allow",
    "bash": "allow",
    "webfetch": "allow"
  }
}
```

---

## Agent Definitions

Agents are specialized configurations with specific prompts, tools, and models.
Create them as markdown files in `.opencode/agents/`.

### Agent File Format

```markdown
---
description: <what this agent does>
mode: primary | subagent
model: <provider/model>
tools:
  <tool-name>: true | false
permission:
  <permission-name>: allow | ask | deny
---

<System prompt for the agent>
```

### Standard Agents for Dev Workflow

#### Plan Agent (`.opencode/agents/plan.md`)

```markdown
---
description: Read-only agent for analysis, planning, and code exploration
mode: primary
model: zai-coding-plan/glm-5
tools:
  read: true
  glob: true
  grep: true
  write: false
  edit: false
  bash: false
permission:
  edit: deny
  bash: deny
---

You are a senior software architect. Analyze codebases and create detailed
development plans. You have read-only access — never modify files.

When creating plans:
1. Explore the relevant files first
2. Understand the existing patterns and conventions
3. Propose specific, actionable steps
4. Identify risks and mitigations
5. Define clear acceptance criteria

Output plans as structured markdown with sections for:
- Problem Statement
- Scope (files to change, files to NOT change)
- Proposed Approach (step-by-step)
- Risks & Mitigations
- Definition of Done
```

#### Implement Agent (`.opencode/agents/implement.md`)

```markdown
---
description: Agent for code generation and file modifications
mode: primary
model: zai-coding-plan/glm-4.7
tools:
  read: true
  write: true
  edit: true
  bash: true
  glob: true
  grep: true
permission:
  edit: allow
  bash: allow
---

You are a senior software engineer. Implement features and fixes based on
approved plans. You have full access to read, write, and execute commands.

Rules:
1. Follow the approved plan exactly
2. Maintain existing code style and conventions
3. Write tests for new functionality
4. Keep changes minimal and focused
5. Do not commit — the orchestrator handles commits

After implementation, summarize:
- Files modified
- Key changes made
- Tests to run
```

#### Review Agent (`.opencode/agents/review.md`)

```markdown
---
description: Agent for PR review triage and code analysis
mode: subagent
model: zai-coding-plan/glm-5
tools:
  read: true
  glob: true
  grep: true
  write: false
  edit: false
  bash: false
permission:
  edit: deny
  bash: deny
---

You are a code reviewer. Analyze PR comments and triage them as confirmed bugs
or false positives. Be critical — not every reviewer comment is correct.

For each comment, output:
- Verdict: Confirmed bug / False positive
- Reasoning: why
- Proposed fix: (if confirmed) what change to make

Consider:
- The actual code change context
- Whether the comment addresses a real issue
- Edge cases and potential regressions
```

#### CI Analysis Agent (`.opencode/agents/ci-analysis.md`)

```markdown
---
description: Agent for analyzing CI failures and proposing fixes
mode: subagent
model: zai-coding-plan/glm-5
tools:
  read: true
  glob: true
  grep: true
  write: false
  edit: false
  bash: false
permission:
  edit: deny
  bash: deny
---

You are a CI/CD specialist. Analyze failed CI jobs and identify root causes.

For each failure:
1. Parse the error messages and stack traces
2. Identify the failing test or check
3. Correlate with recent code changes
4. Propose a specific fix

Output:
- Root cause (clear explanation)
- Proposed fix (what to change)
- Files affected
- Risk level (low/medium/high)
```

#### Coverage Agent (`.opencode/agents/coverage.md`)

```markdown
---
description: Agent for identifying coverage gaps and proposing tests
mode: subagent
model: zai-coding-plan/glm-5
tools:
  read: true
  glob: true
  grep: true
  write: false
  edit: false
  bash: false
permission:
  edit: deny
  bash: deny
---

You are a test engineer. Analyze coverage reports and identify gaps.

For each uncovered area:
1. Understand what the code does
2. Identify the test cases needed
3. Name specific test functions
4. Estimate coverage contribution

Output:
- Uncovered lines by file
- What each section does
- Specific test cases to write (name + what it verifies)
- Estimated coverage after tests
```

---

## Common Operations

### Switch Default Model

Update `.opencode/opencode.json`:

```json
{
  "model": "minimax-coding-plan/m2.1"
}
```

### Add Custom Agent

Create `.opencode/agents/<name>.md` with frontmatter and system prompt.

### Update Agent Model

Edit the `model` field in the agent's frontmatter.

### Change Permissions

Update the `permission` block in `opencode.json` or agent frontmatter.

---

## Environment Variables

OpenCode reads API keys from environment variables. Use `{env:VAR_NAME}` in config:

| Provider | Env Variable | Config Reference |
|----------|-------------|------------------|
| Z.AI Coding Plan (GLM) | `ZAI_CODING_PLAN_API_KEY` | `{env:ZAI_CODING_PLAN_API_KEY}` |
| MiniMax Coding Plan | `MINIMAX_CODING_PLAN_API_KEY` | `{env:MINIMAX_CODING_PLAN_API_KEY}` |

Never hardcode API keys in configuration files.

---

## Available Models

### Z.AI Coding Plan (GLM)

| Model ID | Description |
|----------|-------------|
| `zai-coding-plan/glm-5` | Most capable, for planning and analysis |
| `zai-coding-plan/glm-4.7` | Balanced, for implementation |
| `zai-coding-plan/glm-4-flash` | Fast, for simple tasks |

### MiniMax Coding Plan

| Model ID | Description |
|----------|-------------|
| `minimax-coding-plan/m2.1` | Balanced performance |
| `minimax-coding-plan/m2.1-compact` | Faster, lower cost |

---

## Key Rules

1. **Never hardcode API keys** — always use `{env:VAR_NAME}`.
2. **Keep descriptions in sync** — SKILL.md, version.json, skills.json.
3. **Validate JSON** — ensure config files are valid before writing.
4. **Check before overwrite** — preserve existing configs when appropriate.

---

## References

- `references/config-template.json` — Full configuration template
- `references/agent-templates/` — Agent definition templates
