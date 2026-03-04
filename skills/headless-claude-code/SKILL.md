---
name: headless-claude-code
description: >
  CLI conventions and invocation patterns for running Claude Code headlessly via
  claude -p. Provides the universal invocation template, timeout/turn conventions,
  session management (--resume, --dangerously-skip-permissions on resume), and the
  stream relay pattern for live output visibility. Use this skill whenever spawning
  Claude as a subprocess for code generation, analysis, or any automated task.
  Triggers on: "run claude", "spawn claude", "claude -p", "headless", or any
  request to invoke Claude CLI programmatically.
---

# Headless Claude Code

Conventions and patterns for running Claude Code headlessly via `claude -p`.
Provides a universal invocation template, session management, and the stream
relay pattern for live output visibility.

## Prerequisites

- `claude` CLI available in PATH
- `python3` available in PATH (for relay script)
- `intermediary-delivery` skill installed (provides `send.sh` and `send_file.sh`)
- Environment variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Universal Invocation Template

All headless `claude -p` calls use this template. Only `timeout` and `--max-turns`
vary per use case:

```bash
timeout <Xm> claude -p \
  --max-turns <N> \
  --verbose \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --disallowedTools "Bash(rm -rf*)" \
  "<prompt>" \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

### What's included

- **Full tool access** — Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch,
  git, gh, curl — everything Claude Code normally has
- **Single exclusion** — `rm -rf` is disallowed to prevent destructive accidents
- **Stream relay** — output piped through relay script for live Telegram visibility
- **Verbose mode** — captures tool use and reasoning in the stream

### What's NOT included

- No `--model` — uses the default model configured in Claude CLI
- No `--allowedTools` — full tool access by default
- No `--append-system-prompt` — prompts are self-contained

## Timeout and Turn Conventions

| Use case | `timeout` | `--max-turns` |
|---|---|---|
| Read-only analysis (plan, triage, review) | `10m` | `20` |
| Implementation (writing code) | `30m` | `50` |
| Fix retries (after test/CI failure) | `15m` | `30` |
| Lightweight tasks (batch summary, quick query) | `2m` | `5` |
| Research queries (codebase + web) | `5m` | `10` |

## Session Management

### First invocation

```bash
timeout 30m claude -p \
  --max-turns 50 \
  --verbose \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --disallowedTools "Bash(rm -rf*)" \
  "$PROMPT" \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

Capture the session ID from the stream output for subsequent resume calls.

### Resuming a session

```bash
timeout 15m claude -p \
  --max-turns 30 \
  --verbose \
  --resume "$SESSION_ID" \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --disallowedTools "Bash(rm -rf*)" \
  "$FOLLOWUP_PROMPT" \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

**Critical:** Always re-pass `--dangerously-skip-permissions` on `--resume` calls.
The flag is not persisted across sessions — omitting it will cause the subprocess
to hang waiting for permission prompts.

## Stream Relay Pattern

The relay script (`claude_telegram_relay.py`) reads Claude's `stream-json` output
line by line and forwards key events to Telegram in real time:

- **Assistant text** — streamed as the subprocess generates it
- **Tool use** — tool names and key parameters shown as they execute
- **Results** — tool outputs summarized
- **Errors** — failures surfaced immediately

This gives the orchestrator (and user) live visibility into what the subprocess
is doing without waiting for it to finish.

### Architecture

```
Orchestrator (Pipelit/skill)
  │
  ├─ claude -p ... | claude_telegram_relay.py    ← live visibility
  │
  ├─ send_file.sh artifact.md "caption"          ← artifact delivery after exit
  │
  └─ send.sh "status update"                     ← orchestrator status between calls
```

- **Relay** = live visibility during subprocess execution
- **`send_file.sh`** = artifact delivery after subprocess exits
- **`send.sh`** = orchestrator-level status messages between subprocess calls

## Relay Script

The relay script lives at `scripts/claude_telegram_relay.py`. It:

1. Reads `stream-json` lines from stdin
2. Parses JSON events (assistant text, tool use, tool results, errors)
3. Batches and forwards content to Telegram via Bot API
4. Handles rate limiting and message length limits
5. Exits when stdin closes (subprocess finished)

### Usage

Always pipe `claude -p --output-format stream-json` output through the relay:

```bash
claude -p \
  --output-format stream-json \
  --verbose \
  ... \
| python3 ../headless-claude-code/scripts/claude_telegram_relay.py
```

The script requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` environment
variables (same as intermediary-delivery scripts).

## Timeout Recovery

On timeout, the subprocess is killed by `timeout`. The orchestrator should:

1. Save any state (session ID, current step, progress)
2. Notify user via `send.sh`: "Step X timed out after Ym (Z turns). State saved."
3. Yield to orchestration layer for user decision (retry/skip/abort)
4. On retry, use `--resume` with the saved session ID

## Key Rules

1. **Always use the universal template.** No custom `--model`, `--allowedTools`,
   or `--append-system-prompt` flags.
2. **Always pipe through the relay.** Every `claude -p` call gets live visibility.
3. **Always wrap with `timeout` and `--max-turns`.** Prevent runaway sessions.
4. **Re-pass `--dangerously-skip-permissions` on resume.** Flag is not persisted.
5. **Prompts are self-contained.** No system prompt injection — put everything in
   the prompt argument.
6. **`rm -rf` is always disallowed.** Non-negotiable safety guard.

## References

- `scripts/claude_telegram_relay.py` — Stream relay script
- `../intermediary-delivery/scripts/telegram/send.sh` — Post-exit text delivery
- `../intermediary-delivery/scripts/telegram/send_file.sh` — Post-exit file delivery
