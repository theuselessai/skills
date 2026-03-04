---
name: dev-workflow-claude
description: >
  Universal dev lifecycle skill. Handles the full pipeline from task intake to
  merged PR: entry confirmation → plan (feat/bugfix/chore) → user approval →
  create PR + docs/dev-plans → CI triage → review comment triage → coverage →
  phased implementation → local test → push → merge. Uses claude -p for all
  code generation and analysis. Sends every status update via intermediary-delivery
  scripts and yields to Pipelit at every approval gate — never acts without a plan
  first. Use this skill for any development task: implementing features, fixing
  bugs, chores, reviewing PRs, fixing CI, triaging review comments, fixing
  coverage, or merging. Triggers on: PR numbers, "implement", "fix bug", "chore",
  "review PR", "fix CI", "fix coverage", "merge PR", PR URLs, or any request to
  write or change code.
---

# Dev Workflow

Full dev lifecycle with human-in-the-loop approval at every meaningful decision
point. All plans are sent as `.md` files via `intermediary-delivery` before any
code is written. All code generation uses `claude -p`.

## Prerequisites

- `gh` CLI authenticated
- `git` with push access
- `claude -p` available in PATH
- `intermediary-delivery` skill installed (provides `send.sh` and `send_file.sh`)
- Environment variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Entry Points

| Situation | Start at |
|---|---|
| New task (feat/bugfix/chore) | Step 0: Workflow Entry Confirmation |
| PR already exists, need CI fix | Step 4: CI Check |
| PR already exists, need review triage | Step 5: Review Triage |
| PR already exists, need coverage | Step 6: Coverage |
| PR ready, need to merge | Step 7: Final Check |

---

## Step 0: Workflow Entry Confirmation

Before entering the pipeline, confirm intent with the user.

**Trigger detection:** Detect dev-workflow intent from task descriptions (e.g.,
"implement feature X", "fix bug Y", "add Z to the codebase").

**Confirmation:**
1. Summarize what you understood: "I'll start the dev-workflow pipeline for:
   [task summary]. This includes planning, phase breakdown, implementation,
   CI, and review gates."
2. Ask for confirmation: "Reply `confirm` to proceed, or let's discuss further."
3. On `confirm` → proceed to Step 1: Plan.
4. On any other input → stay in discussion mode, do not enter the pipeline.

---

## Step 1: Plan

Send status update:
```bash
../intermediary-delivery/scripts/telegram/send.sh "Starting plan generation for: <slug>"
```

Analyze the codebase with read-only `claude -p`:

```bash
timeout 10m claude -p \
  --max-turns 20 \
  --output-format stream-json \
  --model claude-opus-4-6 \
  --allowedTools "Read,Glob,Grep" \
  "$(cat references/prompts.md)"
```

Generate `/tmp/dev-plan-<slug>.md` — see `references/prompts.md` for the
PLAN_PROMPT template and required document structure.

**Step A:** Send plan file via `intermediary-delivery`:
```bash
../intermediary-delivery/scripts/telegram/send_file.sh /tmp/dev-plan-<slug>.md "Dev plan — <slug>"
```

**Step B:** Yield to Pipelit. **Gate 1 — approval via orchestration layer.**

On `revise: <feedback>` → re-run with PLAN_REVISION_PROMPT, loop.
On `approve` → Step 2.
On `abort` → stop.

**Recovery on timeout:** Save state → notify via `send.sh`: "Step 1 (Plan) timed
out after 10 minutes. State saved." → yield to Pipelit (retry/skip/abort).

---

## Step 2: Create Branch + Draft PR + docs/dev-plans

Orchestrator actions (no `claude -p` needed):

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

Save PR number. Status update:
```bash
../intermediary-delivery/scripts/telegram/send.sh "Draft PR #<N> created. Branch: <type>/<slug>"
```

→ Step 3: Phase Proposal

---

## Step 3: Phase Proposal

Use `claude -p` (read-only) to break the approved plan into 2–5 discrete phases.
Output must be JSON only — see `references/prompts.md` for PHASE_PROPOSAL_PROMPT.

```bash
timeout 10m claude -p \
  --max-turns 20 \
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

**Step A:** Send file:
```bash
../intermediary-delivery/scripts/telegram/send_file.sh /tmp/phases-<slug>.md "Phase proposal — <slug>"
```

**Step B:** Yield to Pipelit. **Gate 2 — approval via orchestration layer.**

On `revise` → re-run with PHASE_REVISION_PROMPT, loop.
On `approve` → Step 3a: Implement phases.

---

## Step 3a: Implement Phases (loop)

For each phase, send status update then invoke `claude -p` with write access:

```bash
../intermediary-delivery/scripts/telegram/send.sh "Starting Phase <n>/<total>: <title>"
```

```bash
timeout 30m claude -p \
  --max-turns 50 \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --model claude-sonnet-4-6 \
  --allowedTools "Read,Write,Edit,Bash(git *),Bash(npm *),Bash(python *),Bash(../intermediary-delivery/scripts/telegram/send.sh *),Bash(../intermediary-delivery/scripts/telegram/send_file.sh *)" \
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

```bash
../intermediary-delivery/scripts/telegram/send.sh "Phase <n> committed."
```

Run phase test command. If tests fail:
```bash
../intermediary-delivery/scripts/telegram/send.sh "Tests failed for Phase <n>. Retrying fix..."
```

Retry with IMPLEMENT_FIX_PROMPT (max 2 attempts):
```bash
timeout 15m claude -p \
  --max-turns 30 \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --model claude-sonnet-4-6 \
  --allowedTools "Read,Write,Edit,Bash(git *),Bash(npm *),Bash(python *),Bash(../intermediary-delivery/scripts/telegram/send.sh *),Bash(../intermediary-delivery/scripts/telegram/send_file.sh *)" \
  --disallowedTools "Bash(rm -rf*)" \
  --resume "$SESSION_ID" \
  "$IMPLEMENT_FIX_PROMPT"
```

If still failing → send failure report via `send_file.sh` and yield to Pipelit
for user guidance before continuing.

**Recovery on timeout:** Save state → notify via `send.sh`: "Phase <n>
implementation timed out after 30 minutes (50 turns). State saved." → yield to
Pipelit (retry/skip/abort).

After all phases → Step 4.

---

## Step 4: CI Check

```bash
../intermediary-delivery/scripts/telegram/send.sh "Polling CI for PR #<N>..."
```

```bash
gh pr view <PR#> --json statusCheckRollup
```

Poll until all checks complete (max 30 min, poll every 60s).

Status update:
```bash
../intermediary-delivery/scripts/telegram/send.sh "PR #<N> CI Status: <results>"
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

Use `claude -p` to analyze failed job logs before writing the plan:
```bash
timeout 10m claude -p \
  --max-turns 20 \
  --output-format stream-json \
  --model claude-opus-4-6 \
  --allowedTools "Read,Glob,Grep" \
  "$CI_ANALYSIS_PROMPT"
```

**Step A:** Send file:
```bash
../intermediary-delivery/scripts/telegram/send_file.sh /tmp/pr-<N>-ci-fix-plan.md "CI Fix Plan"
```

**Step B:** Yield to Pipelit. **Gate 3 — approval via orchestration layer.**

After approval → apply fixes with `claude -p`, commit, push, loop back to Step 4.

---

## Step 5: Review Triage

```bash
gh pr view <PR#> --json comments,reviews,reviewRequests
```

Use `claude -p` (read-only) to triage each review comment — confirmed bug vs
false positive:

```bash
timeout 10m claude -p \
  --max-turns 20 \
  --output-format stream-json \
  --model claude-opus-4-6 \
  --allowedTools "Read,Glob,Grep" \
  "$REVIEW_TRIAGE_PROMPT"
```

Generate `/tmp/pr-<N>-triage-report.md`:

```markdown
# Review Triage — PR #<N>

## Issue #1: <title>
- **Reviewer:** <name>
- **File:** <path:lines>
- **Verdict:** Confirmed bug / False positive
- **Reasoning:** <why>
- **Proposed fix:** <summary>

## Summary
Confirmed: X | False positives: Y
```

**Step A:** Send file:
```bash
../intermediary-delivery/scripts/telegram/send_file.sh /tmp/pr-<N>-triage-report.md "Review Triage"
```

**Step B:** Yield to Pipelit. **Gate 4 — approval via orchestration layer.**

After approval → fix confirmed issues with `claude -p`, commit, push → Step 4
(re-check CI).

If no review comments → Step 6.

---

## Step 6: Coverage

Check codecov status from CI results. If passing → Step 7.

If failing, use `claude -p` to identify uncovered lines and what tests are needed:

```bash
timeout 10m claude -p \
  --max-turns 20 \
  --output-format stream-json \
  --model claude-opus-4-6 \
  --allowedTools "Read,Glob,Grep" \
  "$COVERAGE_ANALYSIS_PROMPT"
```

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

**Step A:** Send file:
```bash
../intermediary-delivery/scripts/telegram/send_file.sh /tmp/pr-<N>-coverage-plan.md "Coverage Plan"
```

**Step B:** Yield to Pipelit. **Gate 5 — approval via orchestration layer.**

After approval → write tests with `claude -p`, commit, push → Step 4.

---

## Step 7: Final Check + Merge

Poll all CI checks. Send status:
```bash
../intermediary-delivery/scripts/telegram/send.sh "PR #<N> — all checks passed. Ready to merge?"
```

**Step A:** Send summary:
```bash
../intermediary-delivery/scripts/telegram/send.sh "PR #<N> Ready: all CI passed, reviews resolved."
```

**Step B:** Yield to Pipelit. **Gate 6 — merge confirmation via orchestration layer.**

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

```bash
../intermediary-delivery/scripts/telegram/send.sh "PR #<N> merged. Dev plan updated."
```

---

## Key Rules

1. **Never write code without a plan sent via intermediary-delivery first.**
2. **Never lower coverage thresholds** — write real tests.
3. **Triage review comments critically** — not every comment is a real bug.
4. **Always re-pass `--dangerously-skip-permissions` on `--resume` calls.**
5. **Persist state** to `.dev-workflow-state.json` so work survives interruption.
6. **Use `claude -p` for all code gen and analysis** — never write code directly.
7. **Always wrap `claude -p` with `timeout` and `--max-turns`** — prevent runaway sessions.
8. **Confirm intent before entering the pipeline** — Step 0 prevents accidental activation.

---

## Timeout Limits

| Invocation type | `timeout` | `--max-turns` |
|---|---|---|
| Read-only (plan, phase proposal, CI analysis, review triage, coverage) | `10m` | `20` |
| Implementation phases | `30m` | `50` |
| Fix retries | `15m` | `30` |

**On timeout:** Save state to `.dev-workflow-state.json` → notify via `send.sh` →
yield to Pipelit. User decides: `retry` (resume from saved state), `skip` (move
to next step), or `abort`.

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
- `../intermediary-delivery/scripts/telegram/send.sh` — Send text message
- `../intermediary-delivery/scripts/telegram/send_file.sh` — Send file with caption
