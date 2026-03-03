---
name: meeting-mode-claude
description: >
  Meeting capture skill that records working sessions in real time — conversations,
  decisions, action items — and produces structured session summaries. Uses passive
  capture for all messages with explicit triggers for notes, action items, and
  ad-hoc queries via ReAct loop. Delivers final summary via intermediary-delivery
  skill. Uses claude -p for ReAct queries and end-of-session synthesis. Triggers on:
  "let's start a meeting", "start a meeting session", "begin meeting mode",
  "let's have a meeting", or similar intent to capture a working session.
---

# Meeting Mode

Real-time working session capture with passive logging and explicit triggers for
notes, action items, and queries. Produces structured session summaries delivered
via `intermediary-delivery`.

## Prerequisites

- `claude -p` available in PATH
- `intermediary-delivery` skill installed (provides `send.sh` and `send_file.sh`)
- Environment variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Trigger Interface

All triggers are prefix-based, parsed from incoming messages:

| Trigger | Action |
|---|---|
| `"let's start a meeting"` (or similar) | Detect intent, send confirmation, enter meeting mode on `confirm` |
| `note: <text>` | Capture a key point to session log |
| `action: <text>` | Create an action item |
| `? <query>` | Fire ReAct loop for an explicit question |
| `end` | Send confirmation with note/action counts, synthesize on `confirm` |
| _(no prefix)_ | Passive capture — log to batch file, no LLM call |

---

## Step 0: Start Confirmation Gate

**Intent detection:** Detect meeting-mode intent from phrases like "let's start
a meeting", "start a meeting session", "begin meeting mode", "let's have a
meeting" (exact matching not required — use intent detection from the message).

**Confirmation:**
1. Send confirmation prompt: "Start a meeting session? I'll capture notes, action
   items, and decisions. Reply `confirm` to begin, or continue normally."
2. On `confirm` → initialize session state, enter meeting mode (Step 1).
3. On any other input → do not enter meeting mode, continue normal operation.

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

## Step 2: Passive Capture

All messages without an explicit trigger prefix are logged passively.

**On each message:**
1. Append to `current_batch` in `state.json`:
   ```json
   { "role": "user", "content": "<message>", "timestamp": "<ISO 8601>" }
   ```
2. Increment `total_message_count`.
3. No LLM call — write to state file only.

**Batch rotation (every 100 messages):**
1. Write `current_batch` to `meeting_minutes/<slug>/batch-NNN.json` with a
   3–5 sentence summary generated via lightweight model:
   ```bash
   timeout 2m claude -p \
     --max-turns 5 \
     --model claude-haiku-4-5-20251001 \
     "$(cat references/prompts.md | BATCH_SUMMARY_PROMPT)"
   ```
2. Clear `current_batch` in `state.json`.
3. Increment `batch_count`.
4. On timeout: write batch without summary, log warning.

**Size guard:** If `state.json` exceeds 200KB (notes/actions accumulation),
warn user:
```bash
../intermediary-delivery/scripts/telegram/send.sh "Warning: session state exceeds 200KB. Consider ending the session."
```

---

## Step 3: note: and action: Handlers

### `note: <text>`
1. Append to `notes` in `state.json`:
   ```json
   { "text": "<text>", "timestamp": "<ISO 8601>" }
   ```
2. Also log to `current_batch` as a regular message.
3. Confirm:
   ```bash
   ../intermediary-delivery/scripts/telegram/send.sh "Note captured."
   ```

### `action: <text>`
1. Append to `action_items` in `state.json`:
   ```json
   { "text": "<text>", "context": "<surrounding conversation context>", "timestamp": "<ISO 8601>" }
   ```
2. Also log to `current_batch` as a regular message.
3. Confirm:
   ```bash
   ../intermediary-delivery/scripts/telegram/send.sh "Action item captured."
   ```

---

## Step 4: ReAct Loop (? queries)

When a message starts with `? `, fire a ReAct query.

**Context assembly:** Read all batch summaries from `batch-NNN.json` files +
current `state.json` (notes, actions, current_batch) to build session context.

```bash
timeout 5m claude -p \
  --max-turns 10 \
  --model claude-opus-4-6 \
  --allowedTools "Read,Glob,Grep,WebSearch" \
  "$REACT_QUERY_PROMPT"
```

See `references/prompts.md` for `REACT_QUERY_PROMPT` template.

**On timeout:** Return via `send.sh`: "Query timed out — try rephrasing or
breaking into smaller questions."

Log the query and response to `current_batch`.

---

## Step 5: End Gate + Synthesis

When `end` is detected:

**Confirmation gate:**
1. Send confirmation:
   ```bash
   ../intermediary-delivery/scripts/telegram/send.sh "End session? You have N notes and M action items. Reply confirm to generate summary, or continue."
   ```
2. On `confirm` → proceed to synthesis.
3. On any other input → session continues, `end` request discarded.

**Synthesis:**
1. Flush any remaining messages in `current_batch` as a final batch.
2. Invoke synthesis:
   ```bash
   timeout 10m claude -p \
     --max-turns 15 \
     --model claude-opus-4-6 \
     --allowedTools "Read" \
     "$END_SYNTHESIS_PROMPT"
   ```
   See `references/prompts.md` for `END_SYNTHESIS_PROMPT` template.
3. Write output to `meeting_minutes/<slug>/summary.md`.
4. Write action items to `/tmp/meeting-actions-<slug>.json` for `dev-workflow` consumption.
5. Deliver:
   ```bash
   ../intermediary-delivery/scripts/telegram/send_file.sh meeting_minutes/<slug>/summary.md "Session Summary — <slug>"
   ```
6. Update `state.json`: set `status` to `"completed"`.

**On timeout:** Save partial synthesis to `meeting_minutes/<slug>/summary-partial.md`,
notify user via `send.sh`, offer retry.

---

## Output Format

End-of-session summary:

```markdown
# Session Summary — <date> <time>

## Action Items
- [ ] <action> — <context>

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

### state.json schema

```json
{
  "session_id": "meeting-2026-03-04-001",
  "started_at": "2026-03-04T10:00:00+10:30",
  "status": "active",
  "current_batch": [
    { "role": "user", "content": "...", "timestamp": "..." }
  ],
  "batch_count": 1,
  "total_message_count": 42,
  "notes": [
    { "text": "...", "timestamp": "..." }
  ],
  "action_items": [
    { "text": "...", "context": "...", "timestamp": "..." }
  ],
  "decisions": [
    { "text": "...", "timestamp": "..." }
  ],
  "references": []
}
```

**Size guard:** If `state.json` exceeds 200KB, warn user via `intermediary-delivery`.

---

## Model Selection

| Phase | Model |
|---|---|
| ReAct loop queries | `claude-opus-4-6` |
| Final synthesis | `claude-opus-4-6` |
| Passive capture / batch summary | `claude-haiku-4-5-20251001` |

---

## Timeout Limits

| Invocation | `timeout` | `--max-turns` |
|---|---|---|
| ReAct query (`?`) | `5m` | `10` |
| End synthesis | `10m` | `15` |
| Batch summary | `2m` | `5` |

---

## Key Rules

1. **Passive capture has zero LLM cost.** Only write to batch file, no model call.
2. **ReAct fires only on explicit `?` queries.** Never on passive messages.
3. **Batch rotation every 100 messages.** Keeps `state.json` lightweight.
4. **Confirm before entering and exiting.** Prevents accidental activation/deactivation.
5. **All delivery via intermediary-delivery scripts.** Fire-and-forget only.
6. **Action items exported for dev-workflow.** Written to `/tmp/meeting-actions-<slug>.json`.

---

## References

- `references/prompts.md` — Prompt templates for batch summary, ReAct query, end synthesis
- `../intermediary-delivery/scripts/telegram/send.sh` — Send text message
- `../intermediary-delivery/scripts/telegram/send_file.sh` — Send file with caption
