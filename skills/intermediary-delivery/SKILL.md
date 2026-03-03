---
name: intermediary-delivery
description: >
  Fire-and-forget outbound message delivery for all skills. Provides shell scripts
  for sending text messages and files via Telegram. Skills call scripts directly —
  no LLM needed for the delivery layer. Use this skill whenever you need to send
  notifications, status updates, artifacts, or any outbound messages. Triggers on:
  "send message", "notify", "deliver", "send file", "telegram", or any request
  to communicate outbound to a user.
---

# Intermediary Delivery

One-way outbound message delivery via reusable shell scripts. Send and exit —
never wait, never block, never poll.

## Prerequisites

- `bash` available in PATH
- `curl` available in PATH
- Environment variables set:
  - `TELEGRAM_BOT_TOKEN` — Telegram bot API token
  - `TELEGRAM_CHAT_ID` — Target chat/group ID

## Interface Contract

All scripts are **fire-and-forget**. They send the payload and exit immediately.
Reply handling, approval routing, and workflow orchestration belong to Pipelit —
not to this skill.

## When to Use This Skill

Before calling any delivery script, ask one question:

```
Need a reply? ─── Yes ──→ Do NOT use this skill. Yield to Pipelit.
      │
      No
      │
      ▼
Use send.sh or send_file.sh (fire-and-forget)
```

**No reply needed (use this skill):**
- Status updates ("Build started", "Phase 2/5 complete")
- Progress notifications
- Delivering artifacts for review (plans, diffs, reports)
- Error alerts and failure summaries

**Reply needed (don't use this skill):**
- Approval gates ("Should I proceed?")
- Confirmation prompts ("Merge to main?")
- Any action that requires user response before continuing

If the workflow must wait for a response, that is orchestration — yield to Pipelit.

## Available Scripts

### `send.sh` — Send text message

```bash
../intermediary-delivery/scripts/telegram/send.sh "<message>"
```

Sends a plain text message with Markdown parsing enabled.

**Example:**
```bash
../intermediary-delivery/scripts/telegram/send.sh "Build completed — artifact uploaded"
```

### `send_file.sh` — Send file

```bash
../intermediary-delivery/scripts/telegram/send_file.sh <filepath> [caption]
```

Sends a file (markdown, JSON, logs, etc.) with an optional caption.

**Example:**
```bash
../intermediary-delivery/scripts/telegram/send_file.sh /tmp/dev-plan-my-feature.md "Review plan"
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Message delivered successfully |
| `1` | Error — missing env var, missing file, or API failure |

Both scripts print error details to stderr on failure.

## Separation of Concerns

Approval workflows involve two distinct layers:

1. **Content delivery** (this skill): Call `send_file.sh` to deliver an artifact.
   The script sends the file and exits — it has no knowledge of gates or approvals.

2. **Approval request** (Pipelit orchestration): The agent yields execution back
   to Pipelit. The approval message, reply polling, and workflow resumption are
   handled by the orchestration layer, not by delivery scripts.

This keeps delivery scripts stateless and fire-and-forget while Pipelit owns the
full request/reply lifecycle for approval gates.

## Key Rules

1. **Never block on delivery.** Scripts exit immediately after sending.
2. **Never poll for replies.** Reply handling belongs to Pipelit.
3. **Always validate env vars.** Scripts fail fast with clear error messages.
4. **One script per transport action.** `send.sh` for text, `send_file.sh` for files.
5. **Calling skills format their own content.** This skill delivers raw payloads only.
