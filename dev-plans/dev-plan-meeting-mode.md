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
actions. Outputs a structured session summary via the `communication` skill at
session end.

---

## Goals

- Capture the natural flow of a working session without interrupting it
- Explicit triggers for notes, action items, and ad-hoc queries
- End-of-session synthesis: summary, decisions, action items, references
- Action items feed directly into `dev-workflow` skill
- Telegram delivery of all outputs via `communication` skill
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
- Session state persistence (`meeting-state.json`)

### Out of scope
- Voice/audio transcription (future)
- Multi-participant tracking (future)
- Integration with calendar (future)
- Slack transport (handled by communication skill roadmap)

---

## Trigger Interface

All triggers are prefix-based, parsed from incoming messages:

| Trigger | Action |
|---|---|
| `start` | Begin session, initialise state |
| `note: <text>` | Capture a key point to session log |
| `action: <text>` | Create an action item |
| `? <query>` | Fire ReAct loop for an explicit question |
| `end` | Trigger final synthesis and send summary |
| _(no prefix)_ | Passive capture — log to histories, no LLM call |

---

## Agent Flow

Based on the revised Mermaid diagram (meeting-mode-flow.mermaid):

1. **Passive capture layer** — always on, logs all input to `histories`
2. **Trigger detection** — routes to appropriate handler
3. **ReAct loop** — only fires on explicit `?` queries
4. **Functions库** — `capture_note`, `create_action_item`, `search_context`,
   `search_past_sessions`, `web_search`, `send_telegram`, `end_session`
5. **Final synthesis** — generates structured output on `end`

### Web Search Capability

The `?` query ReAct loop benefits from web search for answering ad-hoc
questions during sessions (e.g., "? what's the latest on React 20 release?").

**Fallback chain:**

| Priority | Backend | Mechanism | Notes |
|---|---|---|---|
| 1 | Claude API | Built-in `web_search_20250305` tool | Best quality, server-side |
| 2 | OpenCode | `websearch` / `webfetch` permissions | Depends on provider support |
| 3 | Shell | `curl` via bash to known URLs | Manual URL fetch only, no search |
| 4 | None | Graceful degradation | "Web search unavailable — answer from context only" |

The skill should detect which backend is available at session start and
configure the ReAct loop accordingly. If no web search is available, the
agent responds using only session context and its training data, with a
clear disclaimer.

---

## Output Format

End-of-session summary delivered via `communication` skill:

```markdown
# Session Summary — <date> <time>

## 📋 Action Items
- [ ] <action> — <context>

## 📝 Decisions
- <decision> — <reasoning>

## 💬 Summary
<2-3 paragraph narrative of what was discussed and concluded>

## 🔗 References
- <url or doc mentioned during session>
```

Action items are also written to `/tmp/meeting-actions-<slug>.json` for
consumption by `dev-workflow` skill.

---

## Implementation Phases

### Phase 1: State + trigger parser [low]
Implement session state shape and trigger detection logic.
Files: `meeting-mode-claude/SKILL.md` (state section), `references/prompts.md`
Test: Manually verify trigger parsing with sample inputs

### Phase 2: Passive capture + note/action handlers [medium]
Implement the passive capture loop and `note:` / `action:` trigger handlers.
Files: `meeting-mode-claude/SKILL.md` (steps 1–3)
Test: Start a session, log several notes and actions, verify state file

### Phase 3: ReAct loop for `?` queries [medium]
Wire up `claude -p` invocation for explicit queries, including Functions库.
Files: `meeting-mode-claude/SKILL.md` (step 4), `references/prompts.md`
Test: Fire a `? <query>` and verify observation loop completes

### Phase 4: Final synthesis + output [medium]
Implement `end` trigger — synthesis prompt, output formatting, Telegram delivery.
Files: `meeting-mode-claude/SKILL.md` (step 5), `references/prompts.md`
Test: End a test session, verify summary format and Telegram delivery

### Phase 5: OpenCode variant [low]
Mirror `meeting-mode-claude` for `meeting-mode-opencode` with GLM/MiniMax models.
Files: `meeting-mode-opencode/SKILL.md`, `references/prompts.md`
Test: Repeat Phase 2–4 tests using opencode backend

### Phase 6: skills.json registration [low]
Add both variants to `skills.json`.
Files: `skills.json`
Test: Validate JSON schema

---

## State Shape

```json
{
  "session_id": "meeting-2026-03-03-001",
  "started_at": "2026-03-03T10:00:00+10:30",
  "status": "active",
  "histories": [
    { "role": "user", "content": "...", "timestamp": "..." }
  ],
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
| ReAct loop queries | `claude-opus-4-6` | `zai-coding-plan/glm-5` |
| Final synthesis | `claude-opus-4-6` | `zai-coding-plan/glm-5` |
| Passive capture / note handling | `claude-haiku-4-5-20251001` | `minimax-coding-plan/m2.1` |

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

- `communication` skill — must be implemented first (Telegram delivery)
- `dev-workflow-claude` / `dev-workflow-opencode` — downstream consumer of action items

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Passive capture loop flooding LLM with unnecessary calls | medium | Only fire LLM on explicit triggers, passive = write to state only |
| Session state growing too large for context window | medium | Summarise histories periodically, keep full log in file |
| `end` trigger fired accidentally mid-session | low | Require confirmation gate before final synthesis |
| OpenCode session continuity across long meetings | medium | Persist session_id, test `--session` flag behaviour |
| Web search unavailable on some providers/backends | medium | Fallback chain: Claude web_search → OpenCode websearch → curl → graceful "no web access" response |
