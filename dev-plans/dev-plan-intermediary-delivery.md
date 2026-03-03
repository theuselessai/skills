# Dev Plan — intermediary-delivery skill

**Type:** feat
**Slug:** intermediary-delivery
**Status:** pending
**PR:** —

---

## Summary

Create a standalone `intermediary-delivery` skill that provides fire-and-forget,
one-way outbound messaging for all other skills. Initially implements Telegram
as the transport layer via two reusable shell scripts (`send.sh`,
`send_file.sh`). Other skills (`dev-workflow-claude`, `dev-workflow-opencode`,
`meeting-mode-claude`, `meeting-mode-opencode`) will reference
`../intermediary-delivery/scripts/` instead of embedding their own telegram helpers.

---

## Goals

- Single source of truth for all outbound notifications
- Transport-agnostic interface (Telegram today, Slack/email later)
- Skills call scripts directly — no LLM needed for delivery layer
- SKILL.md documents the interface for agent consumption
- Strict separation: content delivery only; approval gates and reply handling belong to Pipelit's workflow orchestration

---

## Scope

### In scope
- `intermediary-delivery/SKILL.md` — documents the skill interface
- `intermediary-delivery/version.json`
- `intermediary-delivery/scripts/telegram/send.sh` — send plain text message (fire and forget)
- `intermediary-delivery/scripts/telegram/send_file.sh` — send a file with caption (fire and forget)
- Update `skills.json` to register the new skill
- Update `dev-workflow-claude` and `dev-workflow-opencode` to reference
  `../intermediary-delivery/scripts/` instead of `references/telegram.md`

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
../intermediary-delivery/scripts/telegram/send.sh "Build completed — artifact uploaded"
```

### `send_file.sh <filepath> [caption]`
Sends a file (markdown, JSON, etc.) with optional caption. Exits 0 on success.

```bash
../intermediary-delivery/scripts/telegram/send_file.sh /tmp/dev-plan-my-feature.md "Review plan"
```

### Approval Gates — Separation of Concerns

Approval workflows involve two distinct actions handled by different layers:

1. **Content delivery** (intermediary-delivery skill): send the artifact file via
   `send_file.sh`. The script delivers the file and exits — it has no
   knowledge of gates or approvals.
2. **Approval request** (Pipelit workflow orchestration): the agent yields
   execution back to Pipelit. The approval message is sent as a workflow
   interruption by the orchestration layer (`telegram_poller.py` →
   `dispatch_event` → workflow resume), not through a delivery script.

This keeps delivery scripts stateless and fire-and-forget while letting
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
Add `intermediary-delivery` entry to `skills.json` with sha256, files list.
Files: `skills.json`
Test: Validate JSON schema

### Phase 4: Migrate dev-workflow skills [medium]

#### 4.1 Replace embedded telegram helpers
Delete `references/telegram.md` from both `dev-workflow-claude` and
`dev-workflow-opencode`. Replace all `telegram_send()` / `telegram_file()`
calls with `../intermediary-delivery/scripts/telegram/send.sh` and
`send_file.sh`.

#### 4.2 Rewrite gate sections to separate delivery from yielding
Each of the 6 gates currently combines "send artifact" and "wait for approval"
into one blocking action. Rewrite each gate as two explicit steps:

- **Step A (intermediary-delivery):** Call `send_file.sh` — fire-and-forget,
  script exits immediately.
- **Step B (Pipelit yield):** Yield execution to Pipelit's orchestration
  layer, which handles the approval message, polls for reply, and resumes
  the agent.

#### 4.3 Add intermediary status messages
With agents no longer blocking on send calls, add fire-and-forget `send.sh`
calls at natural checkpoints:

- Before each `claude -p` / `opencode run` invocation
- After each phase commit
- On test failure before retry
- Before CI polling

#### 4.4 Update references section
Update the references section in both `dev-workflow-claude/SKILL.md` and
`dev-workflow-opencode/SKILL.md` to reflect new script paths and remove
`telegram.md` entries.

#### 4.5 Add workflow entry confirmation gate
Before the agent enters the dev-workflow loop, it must confirm with the user.
This makes it clear whether the user wants to plan/discuss vs. start the full
implementation pipeline.

**Trigger detection:** The agent detects dev-workflow intent from task
descriptions (e.g., "implement feature X", "fix bug Y", "add Z to the
codebase").

**Confirmation gate:**
1. Agent summarizes what it understood: "I'll start the dev-workflow pipeline
   for: [task summary]. This includes planning, phase breakdown,
   implementation, CI, and review gates."
2. Agent asks for confirmation: "Reply `confirm` to proceed, or let's discuss
   further."
3. On `confirm` → enter dev-workflow (Step 1: Plan)
4. On any other input → stay in discussion mode, do not enter the pipeline

This prevents the agent from jumping straight into the 6-gate pipeline when
the user just wants to discuss an idea or explore options.

#### 4.6 Add timeout and recovery logic
Each `claude -p` / `opencode run` invocation must include turn limits and
shell timeouts to prevent runaway sessions.

**Max turns:** Cap agentic turns per invocation:
- Read-only analysis (plan, phase proposal, CI analysis, review triage,
  coverage): `--max-turns 20`
- Implementation phases: `--max-turns 50`
- Fix retries: `--max-turns 30`

**Shell timeout:** Wrap every invocation with `timeout`:
- Read-only analysis: `timeout 10m claude -p ...` / `timeout 10m opencode run ...`
- Implementation phases: `timeout 30m ...`
- Fix retries: `timeout 15m ...`

**Recovery on timeout:**
1. Save current state to `.dev-workflow-state.json` (already implemented)
2. Send timeout notification via `intermediary-delivery`:
   "Step X timed out after N minutes (M turns). State saved."
3. Yield to Pipelit — user decides: `retry` (resume from saved state),
   `skip` (move to next step), or `abort`

Files: `dev-workflow-claude/SKILL.md`, `dev-workflow-opencode/SKILL.md`
Test: Dry-run a plan step using the new script paths; test each gate
end-to-end to verify delivery + yield separation

---

## File Tree

```
skills/
  intermediary-delivery/
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
| Gate rewrite introduces subtle behavioral change where agent proceeds past yield | medium | Test each gate end-to-end in Phase 4.2 |

---

## Dependencies

- None (this skill has no upstream skill dependencies)
- Downstream: `dev-workflow-claude`, `dev-workflow-opencode`, `meeting-mode-claude`, `meeting-mode-opencode`
