---
name: dev-plan
description: >
  Development planning skill. Explores the codebase, generates a structured dev
  plan as a markdown file, commits it to dev-plans/, and opens a draft PR. Supports
  revision loops and abort. Uses claude -p via headless-claude-code conventions for
  all codebase exploration and plan generation. Human-in-the-loop via Pipelit
  orchestration at every gate. Triggers on: "plan", "create a plan", "dev plan",
  "design", or any request to analyze and plan before implementing.
---

# Dev Plan

Codebase exploration and structured development plan generation. Produces a
`dev-plans/<slug>.md` file, commits it, and opens a draft PR for review.

## Prerequisites

- `gh` CLI authenticated
- `git` with push access
- `claude -p` available in PATH (see `headless-claude-code` skill)
- `intermediary-delivery` skill installed (provides `send.sh` and `send_file.sh`)
- Environment variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Workflow

### Step 0: Entry Confirmation

**Intent detection:** Detect planning intent from task descriptions (e.g.,
"plan feature X", "design approach for Y", "create a dev plan").

**Confirmation:**
1. Summarize what you understood: "I'll create a dev plan for: [task summary].
   This includes codebase exploration, plan generation, and a draft PR."
2. Ask for confirmation: "Reply `confirm` to proceed, or let's discuss further."
3. On `confirm` → proceed to Step 1.
4. On any other input → stay in discussion mode.

---

### Step 1: Explore + Generate Plan

Send status update:
```bash
../intermediary-delivery/scripts/telegram/send.sh "Starting plan generation for: <slug>"
```

Invoke `claude -p` to explore the codebase and write the plan:

```bash
timeout 10m claude -p \
  --max-turns 20 \
  --verbose \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --disallowedTools "Bash(rm -rf*)" \
  "$PLAN_PROMPT" \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

The subprocess explores relevant files and produces `dev-plans/<slug>.md` with
the structure defined in `references/prompts.md`.

After subprocess completes:
```bash
git add dev-plans/<slug>.md
git commit -m "docs: add dev plan for <slug>"
gh pr create --draft \
  --title "plan: <slug>" \
  --body-file dev-plans/<slug>.md
```

**Step A:** Send plan file via intermediary-delivery:
```bash
../intermediary-delivery/scripts/telegram/send_file.sh dev-plans/<slug>.md "Dev plan — <slug>"
```

**Step B:** Yield to Pipelit. **Gate — approval via orchestration layer.**

---

### Step 2: Revision Loop

On user response:

**`merge`** → merge the PR:
```bash
timeout 2m claude -p \
  --max-turns 5 \
  --verbose \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --disallowedTools "Bash(rm -rf*)" \
  "Merge PR #<N> using gh pr merge --squash" \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

**`revise: <feedback>`** → revise the plan:
```bash
timeout 10m claude -p \
  --max-turns 20 \
  --verbose \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --disallowedTools "Bash(rm -rf*)" \
  "$PLAN_REVISION_PROMPT" \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

After revision, commit and push:
```bash
git add dev-plans/<slug>.md
git commit -m "docs: revise dev plan for <slug>"
git push
```

Send updated plan and loop back to Gate.

**`abort`** → close the PR:
```bash
timeout 2m claude -p \
  --max-turns 5 \
  --verbose \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --disallowedTools "Bash(rm -rf*)" \
  "Close PR #<N> using gh pr close" \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

---

## Plan Document Structure

The generated `dev-plans/<slug>.md` must include:

1. **Problem Statement** (2-3 sentences)
2. **Scope** (files that will change; files that must NOT change)
3. **Proposed Approach** (step-by-step; explain key decisions)
4. **Risks & Mitigations**
5. **Definition of Done** (specific, testable criteria)
6. **Estimated Complexity** (low/medium/high with justification)

---

## Timeout Limits

| Invocation | `timeout` | `--max-turns` |
|---|---|---|
| Plan generation | `10m` | `20` |
| Plan revision | `10m` | `20` |
| Merge/close PR | `2m` | `5` |

---

## Key Rules

1. **Never write implementation code.** This skill only produces plans.
2. **All codebase exploration happens inside `claude -p`.** The subprocess reads
   files, searches patterns, and writes the plan document.
3. **Always commit the plan to `dev-plans/`.** Plans are tracked in git.
4. **Always open a draft PR.** Plans are reviewed via PR workflow.
5. **Use the universal invocation template.** See `headless-claude-code` skill.

---

## References

- `references/prompts.md` — PLAN_PROMPT, PLAN_REVISION_PROMPT templates
- `../headless-claude-code/scripts/claude_telegram_relay.py` — Stream relay
- `../intermediary-delivery/scripts/telegram/send.sh` — Status messages
- `../intermediary-delivery/scripts/telegram/send_file.sh` — File delivery
