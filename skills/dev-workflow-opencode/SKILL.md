---
name: dev-workflow-opencode
description: >
  Universal dev lifecycle skill using OpenCode with GLM/MiniMax. Handles the full
  pipeline from task intake to merged PR: plan (feat/bugfix/chore) → user approval
  → create PR + docs/dev-plans → CI triage → review comment triage → coverage →
  phased implementation → local test → push → merge. Uses opencode run with
  pre-configured agents for all code generation and analysis. Sends every approval
  gate and status update via Telegram — never acts without a plan first. Use this
  skill for any development task: implementing features, fixing bugs, chores,
  reviewing PRs, fixing CI, triaging review comments, fixing coverage, or merging.
  Triggers on: PR numbers, "implement", "fix bug", "chore", "review PR", "fix CI",
  "fix coverage", "merge PR", PR URLs, or any request to write or change code.
  Requires opencode-configuration skill to be run first.
---

# Dev Workflow (OpenCode)

Full dev lifecycle with human-in-the-loop approval at every meaningful decision
point. All plans are sent as `.md` files via Telegram before any code is written.
All code generation uses `opencode run` with pre-configured agents.

## Prerequisites

- `gh` CLI authenticated
- `git` with push access
- `opencode` CLI available in PATH
- Telegram bot configured (see `references/telegram.md`)
- OpenCode configured with agents (run `opencode-configuration` skill first)
- Environment variables: `ZAI_API_KEY` and/or `MINIMAX_API_KEY`

## Entry Points

| Situation | Start at |
|---|---|
| New task (feat/bugfix/chore) | Step 1: Plan |
| PR already exists, need CI fix | Step 4: CI Check |
| PR already exists, need review triage | Step 5: Review Triage |
| PR already exists, need coverage | Step 6: Coverage |
| PR ready, need to merge | Step 7: Final Check |

---

## Step 1: Plan

Analyze the codebase with read-only `opencode run`:

```bash
opencode run \
  --agent plan \
  --format json \
  --dir /workspace \
  "$(cat references/prompts/plan.txt)"
```

Generate `/tmp/dev-plan-<slug>.md` — see `references/prompts.md` for the
PLAN_PROMPT template and required document structure.

Send plan file via Telegram. **Gate 1 — wait for approval.**

On `revise: <feedback>` → re-run with PLAN_REVISION_PROMPT, loop.
On `approve` → Step 2.
On `abort` → stop.

---

## Step 2: Create Branch + Draft PR + docs/dev-plans

Orchestrator actions (no `opencode run` needed):

```bash
git checkout -b <type>/<slug>

mkdir -p docs/dev-plans
cp /tmp/dev-plan-<slug>.md docs/dev-plans/<slug>.md
git add docs/dev-plans/<slug>.md
git commit -m "docs: add dev plan for <slug>"

gh pr create --draft \
  --title "<type>: <title>" \
  --body-file /tmp/dev-plan-<slug>.md
```

Save PR number. Telegram update:

```
Draft PR #<N> created.
Branch: <type>/<slug>
Plan saved to docs/dev-plans/<slug>.md
```

→ Step 3: Phase Proposal

---

## Step 3: Phase Proposal

Use `opencode run` (read-only) to break the approved plan into 2–5 discrete phases.
Output must be JSON only — see `references/prompts.md` for PHASE_PROPOSAL_PROMPT.

```bash
opencode run \
  --agent plan \
  --format json \
  --dir /workspace \
  "$PHASE_PROPOSAL_PROMPT"
```

Generate `/tmp/phases-<slug>.md` from the JSON — format:

```markdown
# Implementation Phases — <title>

## Phase 1: <title> [low/medium/high]
<description>
Files: <list>
Test: `<command>`

## Phase 2: <title> [complexity]
...
```

Send file via Telegram. **Gate 2 — wait for approval.**

On `revise` → re-run with PHASE_REVISION_PROMPT, loop.
On `approve` → Step 3a: Implement phases.

---

## Step 3a: Implement Phases (loop)

For each phase, invoke `opencode run` with implement agent:

```bash
opencode run \
  --agent implement \
  --format json \
  --dir /workspace \
  --session "$SESSION_ID" \
  "$IMPLEMENT_PHASE_PROMPT"
```

Save session ID on first invocation for continuity across phases.

After each phase:
```bash
git add -A
git commit -m "impl(<slug>): phase <n> - <title>"
```

Run phase test command. If tests fail → retry with IMPLEMENT_FIX_PROMPT (max 2
attempts). If still failing → send failure report via Telegram and wait for
user guidance before continuing.

After all phases → Step 4.

---

## Step 4: CI Check

```bash
gh pr view <PR#> --json statusCheckRollup
```

Poll until all checks complete (max 30 min, poll every 60s).

Send Telegram status update:
```
PR #<N> CI Status:
[check] backend-tests
[check] frontend-lint
[x] codecov/patch (58%, target 92%)
```

If all pass → Step 5.
If failures → generate `/tmp/pr-<N>-ci-fix-plan.md`:

```markdown
# CI Fix Plan — PR #<N>

## Failure: <job-name>
- **Root cause:** <analysis>
- **Proposed fix:** <description>
- **Files to change:** <list>
- **Risk:** low/medium/high
```

Use `opencode run --agent ci-analysis` to analyze failed job logs before writing the plan.

Send file via Telegram. **Gate 3 — wait for approval.**

After approval → apply fixes with `opencode run --agent implement`, commit, push, loop back to Step 4.

---

## Step 5: Review Triage

```bash
gh pr view <PR#> --json comments,reviews,reviewRequests
```

Use `opencode run --agent review` (read-only) to triage each review comment —
confirmed bug vs false positive.

Generate `/tmp/pr-<N>-triage-report.md`:

```markdown
# Review Triage — PR #<N>

## Issue #1: <title>
- **Reviewer:** <name>
- **File:** <path:lines>
- **Verdict:** [check] Confirmed bug / [x] False positive
- **Reasoning:** <why>
- **Proposed fix:** <summary>

## Summary
Confirmed: X | False positives: Y
```

Send file via Telegram. **Gate 4 — wait for approval.**

After approval → fix confirmed issues with `opencode run --agent implement`,
commit, push → Step 4 (re-check CI).

If no review comments → Step 6.

---

## Step 6: Coverage

Check codecov status from CI results. If passing → Step 7.

If failing, use `opencode run --agent coverage` to identify uncovered lines and
what tests are needed.

Generate `/tmp/pr-<N>-coverage-plan.md`:

```markdown
# Coverage Plan — PR #<N>

Current: X% (target: Y%)

## File: <path> (N lines uncovered)
- **Lines:** <range>
- **What they do:** <description>
- **Tests to write:**
  - `test_<name>`: <what it verifies>

## Estimated coverage after tests: ~X%
```

Send file via Telegram. **Gate 5 — wait for approval.**

After approval → write tests with `opencode run --agent implement`, commit, push → Step 4.

---

## Step 7: Final Check + Merge

Poll all CI checks. Send Telegram summary:

```
PR #<N> Ready:
[check] backend-tests
[check] frontend-lint
[check] codecov/patch
[check] All review comments resolved

Ready to merge?
```

**Gate 6 — wait for merge confirmation.**

```bash
gh pr merge <PR#> --squash --admin
```

Update `docs/dev-plans/<slug>.md`:
```
**Status:** done
**PR:** <url>
```

```bash
git add docs/dev-plans/<slug>.md
git commit -m "docs: mark <slug> as done"
git push
```

Send Telegram:
```
[check] PR #<N> merged. Dev plan updated.
```

---

## Key Rules

1. **Never write code without a plan sent to Telegram first.**
2. **Never lower coverage thresholds** — write real tests.
3. **Triage review comments critically** — not every comment is a real bug.
4. **Persist state** to `.dev-workflow-state.json` so work survives interruption.
5. **Use `opencode run` with pre-configured agents** — never write code directly.
6. **Ensure opencode-configuration has been run** before using this skill.

---

## State Persistence

```python
import json, pathlib

STATE_FILE = pathlib.Path(".dev-workflow-state.json")

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def load_state() -> dict | None:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else None
```

Minimum state shape:
```json
{
  "slug": "my-feature",
  "task_type": "feat",
  "pr_number": 42,
  "branch": "feat/my-feature",
  "current_step": "IMPLEMENT",
  "current_phase": 2,
  "session_id": "ses_...",
  "phases": []
}
```

---

## Pre-configured Agents

This skill requires the following agents to be configured in `.opencode/agents/`:

| Agent | Purpose | Tools |
|---|---|---|
| `plan` | Analysis, planning, read-only exploration | read, glob, grep |
| `implement` | Code generation, file modifications | read, write, edit, bash, glob, grep |
| `review` | PR review triage | read, glob, grep |
| `ci-analysis` | CI log analysis | read, glob, grep |
| `coverage` | Coverage gap identification | read, glob, grep |

Run the `opencode-configuration` skill to set up these agents.

---

## Model Selection

| Phase | Agent | Recommended Model |
|---|---|---|
| Plan, code review, phase proposal, CI/triage analysis | `plan` | `zai/glm-5` |
| Implementation, test writing, coverage fixes | `implement` | `zai/glm-4.7` |
| Chore / boilerplate | `implement` | `minimax/m2.1` |

---

## References

- `references/prompts.md` — Prompt templates for every phase
- `references/telegram.md` — Telegram send helpers (text + file)
