# Dev Plan — communication skill

**Type:** feat
**Slug:** communication
**Status:** pending
**PR:** —

---

## Summary

Create a standalone `communication` skill that provides shared messaging
abstractions for all other skills. Initially implements Telegram as the
transport layer via reusable shell scripts. Other skills (`dev-workflow-claude`,
`dev-workflow-opencode`, `meeting-mode-claude`, `meeting-mode-opencode`) will
reference `../communication/scripts/` instead of embedding their own telegram
helpers.

---

## Goals

- Single source of truth for all outbound notifications
- Transport-agnostic interface (Telegram today, Slack/email later)
- Skills call scripts directly — no LLM needed for communication layer
- SKILL.md documents the interface for agent consumption

---

## Scope

### In scope
- `communication/SKILL.md` — documents the skill interface
- `communication/version.json`
- `communication/scripts/telegram/send.sh` — send plain text message
- `communication/scripts/telegram/send_file.sh` — send a file with caption
- `communication/scripts/telegram/wait_reply.sh` — poll for reply, return text
- Update `skills.json` to register the new skill
- Update `dev-workflow-claude` and `dev-workflow-opencode` to reference
  `../communication/scripts/` instead of `references/telegram.md`

### Out of scope
- Slack transport (future)
- Email transport (future)
- Message formatting/templating (handled by calling skill)

---

## Interface Contract

All scripts read config from environment variables:

```bash
TELEGRAM_BOT_TOKEN   # required
TELEGRAM_CHAT_ID     # required
```

### `send.sh <message>`
Sends a plain text message. Exits 0 on success.

```bash
../communication/scripts/telegram/send.sh "Gate 1 — plan ready for approval"
```

### `send_file.sh <filepath> [caption]`
Sends a file (markdown, JSON, etc.) with optional caption. Exits 0 on success.

```bash
../communication/scripts/telegram/send_file.sh /tmp/dev-plan-my-feature.md "Review plan"
```

### `wait_reply.sh [timeout_seconds]`
Polls Telegram for the next reply. Prints the message text to stdout.
Default timeout: 3600s (1 hour). Exits 1 on timeout.

```bash
REPLY=$(../communication/scripts/telegram/wait_reply.sh 1800)
# $REPLY will be "approve", "revise: ...", or "abort"
```

---

## Implementation Phases

### Phase 1: Scripts [low]
Write the three telegram shell scripts.
Files: `scripts/telegram/send.sh`, `send_file.sh`, `wait_reply.sh`
Test: `bash scripts/telegram/send.sh "test message"` with valid env vars

### Phase 2: SKILL.md + version.json [low]
Write the skill documentation following existing skill conventions.
Files: `SKILL.md`, `version.json`
Test: Manual review against dev-workflow-claude SKILL.md structure

### Phase 3: skills.json registration [low]
Add `communication` entry to `skills.json` with sha256, files list.
Files: `skills.json`
Test: Validate JSON schema

### Phase 4: Migrate dev-workflow skills [medium]
Remove `references/telegram.md` from `dev-workflow-claude` and
`dev-workflow-opencode`. Update SKILL.md references to point to
`../communication/scripts/`.
Files: `dev-workflow-claude/SKILL.md`, `dev-workflow-opencode/SKILL.md`
Test: Dry-run a plan step using the new script paths

---

## File Tree

```
skills/
  communication/
    SKILL.md
    version.json
    scripts/
      telegram/
        send.sh
        send_file.sh
        wait_reply.sh
  skills.json                          ← updated
  dev-workflow-claude/
    SKILL.md                           ← updated (remove telegram.md ref)
    references/
      prompts.md
      telegram.md                      ← deprecated, remove after migration
  dev-workflow-opencode/
    SKILL.md                           ← updated (remove telegram.md ref)
    references/
      prompts.md
      telegram.md                      ← deprecated, remove after migration
```

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Telegram API rate limits on wait_reply polling | low | Add sleep interval between polls |
| Breaking change if telegram.md removed before skills updated | medium | Migrate in Phase 4, keep telegram.md until confirmed working |
| Bot token / chat ID misconfigured | low | Script validates env vars on startup and exits with clear error |

---

## Dependencies

- None (this skill has no upstream skill dependencies)
- Downstream: `dev-workflow-claude`, `dev-workflow-opencode`, `meeting-mode-claude`, `meeting-mode-opencode`
