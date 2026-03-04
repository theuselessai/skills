---
name: dev-implement
description: >
  Development implementation skill. Takes an approved dev plan, implements it via
  claude -p, commits code, opens a draft PR, and runs a review cycle that triages
  CI results and PR reviews until everything is green. Supports phased implementation
  for large plans. Uses headless-claude-code conventions for all code generation.
  Human-in-the-loop via Pipelit orchestration at every gate. Triggers on: "implement",
  "build", "code", "execute plan", or any request to write code from an existing plan.
---

# Dev Implement

Takes an approved dev plan and implements it. Writes code via `claude -p`, commits,
opens a draft PR, and runs review cycles until CI passes and reviews are resolved.

## Prerequisites

- `gh` CLI authenticated
- `git` with push access
- `claude -p` available in PATH (see `headless-claude-code` skill)
- `intermediary-delivery` skill installed (provides `send.sh` and `send_file.sh`)
- Environment variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Workflow

### Step 0: Entry Confirmation

**Intent detection:** Detect implementation intent from messages (e.g.,
"implement the plan", "build feature X", "execute dev-plans/my-feature.md").

**Confirmation:**
1. Ask for the dev plan path: "Which dev plan should I implement? Provide the
   path (e.g., `dev-plans/my-feature.md`)."
2. Verify the file exists and summarize it.
3. Ask for confirmation: "I'll implement this plan, open a draft PR, and run
   review cycles. Reply `confirm` to proceed."
4. On `confirm` → proceed to Step 1.

---

### Step 1: Implement

Send status update:
```bash
../intermediary-delivery/scripts/telegram/send.sh "Starting implementation for: <slug>"
```

Create branch and invoke `claude -p`:

```bash
git checkout -b feat/<slug>
```

```bash
timeout 30m claude -p \
  --max-turns 50 \
  --verbose \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --disallowedTools "Bash(rm -rf*)" \
  "$IMPLEMENT_PROMPT" \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

The subprocess reads the plan, writes code, and commits. If the plan is too large
for one pass, the subprocess creates implementation phases in
`/implementations/<feature>_<date>/` to survive context runout — but only when it
determines it can't implement everything at once.

After subprocess completes:
```bash
git push -u origin feat/<slug>
gh pr create --draft \
  --title "feat: <slug>" \
  --body-file dev-plans/<slug>.md
```

Send status:
```bash
../intermediary-delivery/scripts/telegram/send.sh "Draft PR #<N> created. Implementation complete, starting review cycle."
```

→ Step 2.

---

### Step 2: Review Cycle

The review cycle triages **all CI results** (tests, linting, coverage) **and**
PR review comments, fixes issues, and pushes until everything is green.

#### 2a: Wait for CI

```bash
gh pr view <PR#> --json statusCheckRollup
```

Poll until all checks complete (max 30 min, poll every 60s).

#### 2b: Triage CI + Reviews

Invoke `claude -p` to analyze all failures and review comments:

```bash
timeout 15m claude -p \
  --max-turns 30 \
  --verbose \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --disallowedTools "Bash(rm -rf*)" \
  "$REVIEW_CYCLE_PROMPT" \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

The subprocess:
1. Reads CI check results and failed job logs
2. Reads PR review comments via `gh api`
3. Triages each issue (confirmed bug vs false positive)
4. Fixes confirmed issues
5. Commits and pushes

**Coverage rule:** Never lower coverage thresholds — write real tests instead.

#### 2c: Loop

After fixes are pushed, loop back to 2a (wait for CI again).

If all CI passes and no unresolved review comments → Step 3.

Send status after each cycle:
```bash
../intermediary-delivery/scripts/telegram/send.sh "Review cycle complete. CI: <status>. Unresolved comments: <N>."
```

---

### Step 3: Merge

Send merge readiness notification:
```bash
../intermediary-delivery/scripts/telegram/send.sh "PR #<N> — all checks passed, reviews resolved. Ready to merge?"
```

**Yield to Pipelit. Gate — merge confirmation via orchestration layer.**

On confirmation:
```bash
timeout 2m claude -p \
  --max-turns 5 \
  --verbose \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --disallowedTools "Bash(rm -rf*)" \
  "Merge PR #<N> using gh pr merge --squash, then delete the remote branch" \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

Send completion:
```bash
../intermediary-delivery/scripts/telegram/send.sh "PR #<N> merged. Branch cleaned up."
```

---

## Timeout Limits

| Invocation | `timeout` | `--max-turns` |
|---|---|---|
| Implementation | `30m` | `50` |
| Review cycle (triage + fix) | `15m` | `30` |
| Merge/cleanup | `2m` | `5` |

**On timeout:** Save state (session ID, current step) → notify via `send.sh` →
yield to Pipelit (retry/skip/abort).

---

## Key Rules

1. **Always start from an approved dev plan.** Never implement without a plan.
2. **Never lower coverage thresholds.** Write real tests to meet coverage.
3. **Triage review comments critically.** Not every reviewer comment is a real bug.
4. **Use the universal invocation template.** See `headless-claude-code` skill.
5. **All code generation happens inside `claude -p`.** Never write code directly
   in the orchestrator.
6. **Re-pass `--dangerously-skip-permissions` on `--resume`.** Flag is not persisted.

---

## References

- `references/prompts.md` — IMPLEMENT_PROMPT, IMPLEMENT_FIX_PROMPT, REVIEW_CYCLE_PROMPT
- `../headless-claude-code/scripts/claude_telegram_relay.py` — Stream relay
- `../intermediary-delivery/scripts/telegram/send.sh` — Status messages
- `../intermediary-delivery/scripts/telegram/send_file.sh` — File delivery
