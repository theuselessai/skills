# Dev Plan — communication skill

**Type:** feat
**Slug:** communication
**Status:** pending
**PR:** —

---

## Summary

Create a standalone `communication` skill that provides fire-and-forget,
one-way outbound messaging for all other skills. Initially implements Telegram
as the transport layer via two reusable shell scripts (`send.sh`,
`send_file.sh`). Other skills (`dev-workflow-claude`, `dev-workflow-opencode`,
`meeting-mode-claude`, `meeting-mode-opencode`) will reference
`../communication/scripts/` instead of embedding their own telegram helpers.

---

## Goals

- Single source of truth for all outbound notifications
- Transport-agnostic interface (Telegram today, Slack/email later)
- Skills call scripts directly — no LLM needed for communication layer
- SKILL.md documents the interface for agent consumption
- Strict separation: content delivery only; approval gates and reply handling belong to Pipelit's workflow orchestration

---

## Scope

### In scope
- `communication/SKILL.md` — documents the skill interface
- `communication/version.json`
- `communication/scripts/telegram/send.sh` — send plain text message (fire and forget)
- `communication/scripts/telegram/send_file.sh` — send a file with caption (fire and forget)
- Update `skills.json` to register the new skill
- Update `dev-workflow-claude` and `dev-workflow-opencode` to reference
  `../communication/scripts/` instead of `references/telegram.md`

### Out of scope
- Slack transport (future)
- Email transport (future)
- Message formatting/templating (handled by calling skill)

---

## Interface Contract

Scripts are **one-way outbound only** — send and exit, never wait, never block,
never poll. Reply handling and approval routing are Pipelit's responsibility
(see *Approval Gates* below).

All scripts read config from environment variables:

```bash
TELEGRAM_BOT_TOKEN   # required
TELEGRAM_CHAT_ID     # required
```

### `send.sh <message>`
Sends a plain text message. Exits 0 on success.

```bash
../communication/scripts/telegram/send.sh "Build completed — artifact uploaded"
```

### `send_file.sh <filepath> [caption]`
Sends a file (markdown, JSON, etc.) with optional caption. Exits 0 on success.

```bash
../communication/scripts/telegram/send_file.sh /tmp/dev-plan-my-feature.md "Review plan"
```

### Approval Gates — Separation of Concerns

Approval workflows involve two distinct actions handled by different layers:

1. **Content delivery** (communication skill): send the artifact file via
   `send_file.sh`. The script delivers the file and exits — it has no
   knowledge of gates or approvals.
2. **Approval request** (Pipelit workflow orchestration): the agent yields
   execution back to Pipelit. The approval message is sent as a workflow
   interruption by the orchestration layer (`telegram_poller.py` →
   `dispatch_event` → workflow resume), not through a communication script.

This keeps communication scripts stateless and fire-and-forget while letting
Pipelit own the full request/reply lifecycle for approval gates.

---

## Implementation Phases

### Phase 1: Scripts [low]
Write the two telegram shell scripts.
Files: `scripts/telegram/send.sh`, `send_file.sh`
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
| Breaking change if telegram.md removed before skills updated | medium | Migrate in Phase 4, keep telegram.md until confirmed working |
| Bot token / chat ID misconfigured | low | Script validates env vars on startup and exits with clear error |

---

## Dependencies

- None (this skill has no upstream skill dependencies)
- Downstream: `dev-workflow-claude`, `dev-workflow-opencode`, `meeting-mode-claude`, `meeting-mode-opencode`
