# Dev Plan — meeting-mode skill

**Type:** feat
**Slug:** meeting-mode
**Status:** pending
**PR:** —

---

## Summary

Create a `meeting-mode` skill (claude and opencode variants) that captures
working sessions — conversations, decisions, action items — in real time.
Modelled on the ReAct agent loop from the Agent 搭建 - 全流程 diagram, with a
passive capture layer running continuously underneath explicit trigger-based
actions. Outputs a structured session summary via the `intermediary-delivery`
skill at session end.

---

## Goals

- Capture the natural flow of a working session without interrupting it
- Explicit triggers for notes, action items, and ad-hoc queries
- End-of-session synthesis: summary, decisions, action items, references
- Action items feed directly into `dev-workflow` skill
- Telegram delivery of all outputs via `intermediary-delivery` skill
- Two backends: `claude -p` (primary) and `opencode run` (fallback)

---

## Scope

### In scope
- `meeting-mode-claude/SKILL.md`
- `meeting-mode-claude/version.json`
- `meeting-mode-claude/references/prompts.md` — prompt templates
- `meeting-mode-opencode/SKILL.md`
- `meeting-mode-opencode/version.json`
- `meeting-mode-opencode/references/prompts.md`
- `skills.json` — register both variants
- Session state persistence (`meeting_minutes/` folder structure)

### Out of scope
- Voice/audio transcription (future)
- Multi-participant tracking (future)
- Integration with calendar (future)
- Slack transport (handled by intermediary-delivery skill roadmap)

---

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

**Start confirmation gate:** The agent detects meeting-mode intent from
phrases like "let's start a meeting", "start a meeting session", "begin
meeting mode", "let's have a meeting" (exact matching not required — the
agent uses intent detection from the message).

1. Agent sends confirmation prompt: "Start a meeting session? I'll capture
   notes, action items, and decisions. Reply `confirm` to begin, or continue
   normally."
2. On `confirm` → initialize session state, enter meeting mode
3. On any other input → do not enter meeting mode, continue normal operation

**End confirmation gate:** When `end` is detected:

1. Agent sends confirmation via `intermediary-delivery`: "End session? You
   have N notes and M action items. Reply `confirm` to generate summary, or
   continue."
2. On `confirm` → proceed to synthesis
3. On any other input → session continues, `end` request discarded

---

## Agent Flow

Based on the revised Mermaid diagram (meeting-mode-flow.mermaid):

1. **Passive capture layer** — always on, logs all input to batch files
2. **Trigger detection** — routes to appropriate handler
3. **ReAct loop** — only fires on explicit `?` queries
4. **Functions库** — `capture_note`, `create_action_item`, `search_context`,
   `search_past_sessions`, `web_search`, `send_telegram`, `end_session`
5. **Final synthesis** — generates structured output on `end`

### Web Search

Web search is a default agent capability (SearXNG-backed `web_search` tool).
No detection or probing is needed at session start.

On search failure: agent prepends disclaimer "Web search unavailable — answer
from context and training data only" and continues without blocking.

---

## Output Format

End-of-session summary delivered via `intermediary-delivery` skill:

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

Action items are also written to `/tmp/meeting-actions-<slug>.json` for
consumption by `dev-workflow` skill.

---

## Implementation Phases

> **Prerequisite:** `intermediary-delivery` must be fully implemented before
> Phase 2. Phase 1 (trigger parser) can proceed in parallel.

### Phase 1: Trigger parser [low]
Implement trigger detection logic — intent matching for start/end, prefix
parsing for `note:`, `action:`, `?`.
Files: `meeting-mode-claude/SKILL.md` (trigger section), `references/prompts.md`
Test: Manually verify trigger parsing with sample inputs
Validates: All 6 trigger types correctly detected and routed

### Phase 2: Note/action handlers + delivery [low]
Implement `note:` and `action:` handlers. Notes and actions persist to
`state.json`. Send confirmation of capture via `intermediary-delivery`.
Files: `meeting-mode-claude/SKILL.md` (steps 1–3)
Test: Start a session, log several notes and actions, verify state file
Validates: State file contains correct notes/actions, delivery script fires

### Phase 3: End synthesis [medium]
Implement `end` trigger — confirmation gate, batch assembly, synthesis
prompt via `claude -p`, output formatting, delivery via `intermediary-delivery`.
Files: `meeting-mode-claude/SKILL.md` (step 5), `references/prompts.md`
Test: End a test session with notes/actions, verify summary format and delivery
Validates: Summary generated from batch files, delivered successfully

### Phase 4: Passive capture [medium]
Implement the passive capture layer — all non-trigger messages logged to
batch files. Batch rotation every 100 messages with lightweight summary.
Files: `meeting-mode-claude/SKILL.md` (passive capture section)
Test: Send 150+ messages, verify batch-001.json and batch-002.json created
Validates: Batch rotation works, state.json stays lightweight

### Phase 5: ReAct loop for `?` queries [high]
Wire up `claude -p` invocation for explicit queries, including Functions库.
Requires careful context assembly from batch files + current state.
Files: `meeting-mode-claude/SKILL.md` (step 4), `references/prompts.md`
Test: Fire a `? <query>` and verify observation loop completes
Validates: ReAct loop converges, context assembled correctly from batches

### Phase 6: OpenCode variant [low]
Mirror `meeting-mode-claude` for `meeting-mode-opencode`. Use provider
default models (verify current model names against `opencode-configuration`
before implementation).
Files: `meeting-mode-opencode/SKILL.md`, `references/prompts.md`
Test: Repeat Phase 2–5 tests using opencode backend
Validates: Feature parity with claude variant

### Phase 7: skills.json registration [low]
Add both variants to `skills.json`.
Files: `skills.json`
Test: Validate JSON schema

---

## Session Persistence

Instead of keeping all history in a state JSON (which risks context
compression), meeting data is persisted to disk in a `meeting_minutes/`
folder structure.

### Folder structure

```
meeting_minutes/
  <session-slug>/          # e.g., meeting-2026-03-04-001
    state.json             # Current session state (lightweight — no histories)
    batch-001.json         # Messages 1-100 + batch summary
    batch-002.json         # Messages 101-200 + batch summary
    ...
    summary.md             # Final synthesis output (generated at end)
```

### Batch logging

Every 100 messages, the agent:

1. Writes the batch to `batch-NNN.json` with all 100 messages + a 3-5
   sentence summary (generated via lightweight model: haiku / m2.1)
2. Clears the in-memory `histories` buffer — only the current (incomplete)
   batch stays in `state.json`
3. This means the session survives any context compression since all data
   is on disk

### state.json (lightweight)

Contains only:
- Session metadata (`id`, `started_at`, `status`)
- Current batch buffer (≤100 messages, not yet flushed)
- Notes, action items, decisions (always retained in full)
- `batch_count` and `total_message_count` counters

**Size guard:** If `state.json` exceeds 200KB (notes/actions accumulation),
warn user via `intermediary-delivery`.

### End-of-session synthesis

When `end` is confirmed:

1. Flush any remaining messages as a final batch
2. Invoke `claude -p` or `opencode run` with the full context (all batch
   files + notes + actions + decisions) — these have larger context windows
   than the inline agent
3. Write the final `summary.md` to the session folder
4. Deliver via `intermediary-delivery`

---

## State Shape

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

---

## Model Selection

| Phase | Model (Claude) | Model (OpenCode) |
|---|---|---|
| ReAct loop queries | `claude-opus-4-6` | Provider default (verify current model) |
| Final synthesis | `claude-opus-4-6` | Provider default (verify current model) |
| Passive capture / batch summary | `claude-haiku-4-5-20251001` | Provider default (verify current model) |

> **Note:** OpenCode model names should be confirmed against
> `opencode-configuration` before implementation. Model availability and
> names change across providers.

---

## Timeout Limits

### ReAct loop (`?` queries)
These are the only LLM calls during a session (besides end synthesis).
- `--max-turns 10` per query (ReAct should converge quickly)
- `timeout 5m` per query invocation
- On timeout: return "Query timed out — try rephrasing or breaking into
  smaller questions" via `intermediary-delivery`

### End synthesis
Can be expensive with large session state.
- `--max-turns 15`
- `timeout 10m`
- On timeout: save partial synthesis to `meeting_minutes/<slug>/summary-partial.md`,
  notify user via `intermediary-delivery`, offer retry

### Passive capture
No LLM calls (write to batch file only), no timeout concern.

### Batch summary generation
Lightweight model call when rotating batches.
- `--max-turns 5`
- `timeout 2m`
- On timeout: write batch without summary, log warning

---

## File Tree

```
skills/
  meeting-mode-claude/
    SKILL.md
    version.json
    references/
      prompts.md
  meeting-mode-opencode/
    SKILL.md
    version.json
    references/
      prompts.md
  skills.json                          ← updated
```

---

## Dependencies

- `intermediary-delivery` skill — **hard dependency**. Phases 2–5 call
  `send.sh` / `send_file.sh` for delivery. Phase 1 (trigger parser) can
  proceed in parallel since it only parses input without sending anything.
- `dev-workflow-claude` / `dev-workflow-opencode` — downstream consumer of
  action items

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Passive capture loop flooding LLM with unnecessary calls | medium | Only fire LLM on explicit triggers, passive = write to batch file only |
| Session state growing too large for context window | low | Batch rotation every 100 messages; state.json stays lightweight; 200KB size guard |
| `end` trigger fired accidentally mid-session | low | Confirmation gate: agent shows note/action counts, requires `confirm` reply |
| OpenCode session continuity across long meetings | medium | Persist session_id, test `--session` flag behaviour |
| ReAct query runs too long or loops indefinitely | medium | `--max-turns 10` + `timeout 5m` per query |
