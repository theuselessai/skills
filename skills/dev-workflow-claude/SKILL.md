---
name: dev-workflow-claude
description: >
  Universal dev lifecycle skill. Handles the full pipeline from task intake to
  merged PR: plan (feat/bugfix/chore) → user approval → create PR + docs/dev-plans
  → CI triage → review comment triage → coverage → phased implementation → local
  test → push → merge. Uses claude -p for all code generation and analysis.
  Sends every approval gate and status update via Telegram — never acts without
  a plan first. Use this skill for any development task: implementing features,
  fixing bugs, chores, reviewing PRs, fixing CI, triaging review comments,
  fixing coverage, or merging. Triggers on: PR numbers, "implement", "fix bug",
  "chore", "review PR", "fix CI", "fix coverage", "merge PR", PR URLs, or any
  request to write or change code.
---

# Dev Workflow

Full dev lifecycle with human-in-the-loop approval at every meaningful decision
point. All plans are sent as `.md` files via Telegram before any code is written.
All code generation uses `claude -p`.

## Prerequisites

- `gh` CLI authenticated
- `git` with push access
- `claude -p` available in PATH
- Telegram bot configured (see `references/telegram.md`)

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

Analyze the codebase with read-only `claude -p`:

```bash
claude -p \
  --output-format stream-json \
  --model claude-opus-4-6 \
  --allowedTools "Read,Glob,Grep" \
  "$(cat references/prompts.md)"
```

Generate `/tmp/dev-plan-<slug>.md` — see `references/prompts.md` for the
PLAN_PROMPT template and required document structure.

Send plan file via Telegram. **Gate 1 — wait for approval.**

On `revise: <feedback>` → re-run with PLAN_REVISION_PROMPT, loop.
On `approve` → Step 2.
On `abort` → stop.

---

## Step 2: Create Branch + Draft PR + docs/dev-plans

Orchestrator actions (no `claude -p` needed):

```bash
# Branch
git checkout -b <type>/<slug>

# Commit plan doc
mkdir -p docs/dev-plans
cp /tmp/dev-plan-<slug>.md docs/dev-plans/<slug>.md
git add docs/dev-plans/<slug>.md
git commit -m "docs: add dev plan for <slug>"

# Draft PR
gh pr create --draft \
  --title "<type>: <title>" \
  --body-file /tmp/dev-plan-<slug>.md
```

Save PR number. Telegram update:

```
📝 Draft PR #<N> created.
Branch: <type>/<slug>
Plan saved to docs/dev-plans/<slug>.md
```

→ Step 3: Phase Proposal

---

## Step 3: Phase Proposal

Use `claude -p` (read-only) to break the approved plan into 2–5 discrete phases.
Output must be JSON only — see `references/prompts.md` for PHASE_PROPOSAL_PROMPT.

```bash
claude -p \
  --output-format stream-json \
  --model claude-opus-4-6 \
  --allowedTools "Read,Glob,Grep" \
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

For each phase, invoke `claude -p` with write access:

```bash
claude -p \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --model claude-sonnet-4-6 \
  --allowedTools "Read,Write,Edit,Bash(git *),Bash(npm *),Bash(python *)" \
  --disallowedTools "Bash(rm -rf*)" \
  --resume "$SESSION_ID" \
  "$IMPLEMENT_PHASE_PROMPT"
```

Save `session_id` on first invocation. Re-pass `--dangerously-skip-permissions`
on every `--resume` call (known issue: flag is not persisted).

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
📋 PR #<N> CI Status:
✅ backend-tests
✅ frontend-lint
❌ codecov/patch (58%, target 92%)
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

Use `claude -p` to analyze failed job logs before writing the plan.

Send file via Telegram. **Gate 3 — wait for approval.**

After approval → apply fixes with `claude -p`, commit, push, loop back to Step 4.

---

## Step 5: Review Triage

```bash
gh pr view <PR#> --json comments,reviews,reviewRequests
```

Use `claude -p` (read-only) to triage each review comment — confirmed bug vs
false positive.

Generate `/tmp/pr-<N>-triage-report.md`:

```markdown
# Review Triage — PR #<N>

## Issue #1: <title>
- **Reviewer:** <name>
- **File:** <path:lines>
- **Verdict:** ✅ Confirmed bug / ❌ False positive
- **Reasoning:** <why>
- **Proposed fix:** <summary>

## Summary
Confirmed: X | False positives: Y
```

Send file via Telegram. **Gate 4 — wait for approval.**

After approval → fix confirmed issues with `claude -p`, commit, push → Step 4
(re-check CI).

If no review comments → Step 6.

---

## Step 6: Coverage

Check codecov status from CI results. If passing → Step 7.

If failing, use `claude -p` to identify uncovered lines and what tests are needed.

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

After approval → write tests with `claude -p`, commit, push → Step 4.

---

## Step 7: Final Check + Merge

Poll all CI checks. Send Telegram summary:

```
🏁 PR #<N> Ready:
✅ backend-tests
✅ frontend-lint  
✅ codecov/patch
✅ All review comments resolved

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
✅ PR #<N> merged. Dev plan updated.
```

---

## Key Rules

1. **Never write code without a plan sent to Telegram first.**
2. **Never lower coverage thresholds** — write real tests.
3. **Triage review comments critically** — not every comment is a real bug.
4. **Always re-pass `--dangerously-skip-permissions` on `--resume` calls.**
5. **Persist state** to `.dev-workflow-state.json` so work survives interruption.
6. **Use `claude -p` for all code gen and analysis** — never write code directly.

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

## Model Selection

| Phase | Model |
|---|---|
| Plan, code review, phase proposal, CI/triage analysis | `claude-opus-4-6` |
| Implementation, test writing, coverage fixes | `claude-sonnet-4-6` |
| Chore / boilerplate | `claude-haiku-4-5-20251001` |

---

## References

- `references/prompts.md` — Prompt templates for every phase
- `references/telegram.md` — Telegram send helpers (text + file)
