---
name: meeting-mode
description: >
  Meeting capture skill that records working sessions in real time — conversations,
  decisions, action items — and produces structured session summaries. Uses Haiku 4.5
  as orchestrator with natural language classification instead of prefix triggers.
  Users just talk naturally; Haiku classifies each message and routes accordingly.
  Spawns claude -p via headless-claude-code only when research requiring tool access
  is needed. Delivers final summary via intermediary-delivery. Triggers on: "let's
  start a meeting", "start a meeting session", "begin meeting mode", "let's have a
  meeting", or similar intent to capture a working session.
---

# Meeting Mode

Real-time working session capture with natural language classification. Users talk
naturally — Haiku 4.5 classifies every message and routes it to the right handler.
No prefix triggers needed.

## Prerequisites

- `claude -p` available in PATH (see `headless-claude-code` skill)
- `intermediary-delivery` skill installed (provides `send.sh` and `send_file.sh`)
- Environment variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Architecture

Haiku 4.5 acts as the lightweight orchestrator, classifying every message into
one of these categories:

| Classification | Action |
|---|---|
| **passive** | Log to batch file, no processing |
| **note** | Extract and store as a key point |
| **action_item** | Extract and store as an action item with context |
| **needs_research** | Spawn `claude -p` for codebase/web research |
| **end_session** | Trigger end confirmation and synthesis |

Users don't need to use `note:`, `action:`, or `?` prefixes. Haiku detects
intent from natural language:

- "We should remember that the API rate limit is 100/min" → **note**
- "John needs to update the deployment script by Friday" → **action_item**
- "What does the auth middleware actually do?" → **needs_research**
- "Let's wrap up" → **end_session**
- Everything else → **passive**

---

## Step 0: Start Confirmation Gate

**Intent detection:** Detect meeting-mode intent from phrases like "let's start
a meeting", "start a meeting session", "begin meeting mode", "let's have a
meeting" (use intent detection, not exact matching).

**Confirmation:**
1. Send confirmation prompt via intermediary-delivery:
   ```bash
   ../intermediary-delivery/scripts/telegram/send.sh "Start a meeting session? I'll capture notes, action items, and decisions naturally — just talk normally. Reply confirm to begin."
   ```
2. **Yield to Pipelit. Gate — start confirmation via orchestration layer.**
3. On `confirm` → proceed to Step 1.
4. On any other input → do not enter meeting mode, exit skill.

---

## Step 1: Session Init

Create session folder and initialize state:

```bash
SLUG="meeting-$(date +%Y-%m-%d)-001"
mkdir -p meeting_minutes/$SLUG
```

Initialize `meeting_minutes/<slug>/state.json`:
```json
{
  "session_id": "<slug>",
  "started_at": "<ISO 8601 timestamp>",
  "status": "active",
  "current_batch": [],
  "batch_count": 0,
  "total_message_count": 0,
  "notes": [],
  "action_items": [],
  "decisions": [],
  "references": []
}
```

Confirm session started:
```bash
../intermediary-delivery/scripts/telegram/send.sh "Meeting session started: <slug>"
```

---

## Step 2: Message Processing Loop

For each incoming message:

### 2a: Classify with Haiku

Use Haiku 4.5 (via API or lightweight call) to classify the message:

```python
classification = classify_message(message, session_context)
# Returns: "passive" | "note" | "action_item" | "needs_research" | "end_session"
```

The classifier considers:
- Message content and intent
- Recent conversation context (last 5-10 messages)
- Whether the message implies something worth capturing vs casual conversation

### 2b: Route by Classification

**passive** → Append to `current_batch` in `state.json`. No LLM call.

**note** → Haiku extracts the key point:
1. Append to `notes` in `state.json`
2. Log to `current_batch`
3. Confirm: `send.sh "Note captured."`

**action_item** → Haiku extracts the action and assignee:
1. Append to `action_items` in `state.json` with context
2. Log to `current_batch`
3. Confirm: `send.sh "Action item captured."`

**needs_research** → Spawn `claude -p` for tool-requiring research:

**Critical:** Haiku must NOT attempt to answer the research question itself.
Always spawn `claude -p` — only a subprocess with full tool access can search
the codebase, read files, and query the web.

```bash
timeout 30m claude -p \
  --max-turns 50 \
  --verbose \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --disallowedTools "Bash(rm -rf*)" \
  "$RESEARCH_PROMPT" \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

Log query and response to `current_batch`. See `references/prompts.md` for
`RESEARCH_PROMPT` template.

**end_session** → Go to Step 3.

### 2c: Batch Rotation

Every 100 messages:
1. Haiku generates a 3-5 sentence batch summary
2. Write `current_batch` + summary to `meeting_minutes/<slug>/batch-NNN.json`
3. Clear `current_batch` in `state.json`
4. Increment `batch_count`

**Size guard:** If `state.json` exceeds 200KB, warn user via `send.sh`.

---

## Step 3: End Gate + Synthesis

When Haiku classifies a message as `end_session`:

**Confirmation gate:**
1. Send end confirmation:
   ```bash
   ../intermediary-delivery/scripts/telegram/send.sh "End session? You have N notes and M action items. Reply confirm to generate summary, or continue."
   ```
2. **Yield to Pipelit. Gate — end confirmation via orchestration layer.**
3. On `confirm` → proceed to synthesis.
4. On any other input → session continues, end request discarded.

**Synthesis:**
1. Flush remaining messages as final batch.
2. Invoke `claude -p` for synthesis:
   ```bash
   timeout 30m claude -p \
     --max-turns 50 \
     --verbose \
     --dangerously-skip-permissions \
     --output-format stream-json \
     --disallowedTools "Bash(rm -rf*)" \
     "$END_SYNTHESIS_PROMPT" \
   | python3 ../headless-claude-code/scripts/claude_telegram_relay.py
   ```
3. Write output to `meeting_minutes/<slug>/summary.md`.
4. Deliver: `send_file.sh meeting_minutes/<slug>/summary.md "Session Summary — <slug>"`
5. Update `state.json`: set `status` to `"completed"`.

---

## Output Format

End-of-session summary:

```markdown
# Session Summary — <date> <time>

## Action Items
- [ ] <action> — <context/assignee>

## Decisions
- <decision> — <reasoning>

## Summary
<2-3 paragraph narrative of what was discussed and concluded>

## References
- <url or doc mentioned during session>
```

---

## State Persistence

### Folder structure

```
meeting_minutes/
  <session-slug>/
    state.json           # Current session state (lightweight)
    batch-001.json       # Messages 1-100 + batch summary
    batch-002.json       # Messages 101-200 + batch summary
    ...
    summary.md           # Final synthesis output
```

---

## Timeout Limits

| Use case | `timeout` | `--max-turns` |
|---|---|---|
| Default (all use cases) | `30m` | `50` |

---

## Key Rules

1. **Natural language classification.** No prefix triggers — Haiku sorts it out.
2. **Passive capture has zero LLM cost.** Only write to batch file.
3. **`claude -p` spawned for ALL research.** Haiku must never answer research
   questions inline — always dispatch to a subprocess with tool access.
4. **Batch rotation every 100 messages.** Keeps state lightweight.
5. **Confirm before entering and exiting.** Prevents accidental activation.
6. **All delivery via intermediary-delivery scripts.** Fire-and-forget only.
7. **Use the universal invocation template.** See `headless-claude-code` skill.

---

## References

- `references/prompts.md` — Classification, research, and synthesis prompt templates
- `../headless-claude-code/scripts/claude_telegram_relay.py` — Stream relay
- `../intermediary-delivery/scripts/telegram/send.sh` — Text delivery
- `../intermediary-delivery/scripts/telegram/send_file.sh` — File delivery
