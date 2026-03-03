# Prompt Templates

All templates are Python f-strings. Inject variables before passing to `claude -p`.

## System prompt (always use --append-system-prompt)

```
You are a meeting assistant. Your role is to capture, organize, and synthesize
working session content. Be concise and structured. When asked for JSON output,
respond ONLY with valid JSON. When asked for markdown, use clear headers.
```

---

## BATCH_SUMMARY_PROMPT

Model: `claude-haiku-4-5-20251001` | Max turns: `5` | Timeout: `2m`

```python
BATCH_SUMMARY_PROMPT = f"""
Summarize the following batch of {message_count} meeting messages in 3-5 sentences.
Focus on key topics discussed, decisions made, and any action items mentioned.

Messages:
{batch_messages_json}

Respond with a plain text summary only — no JSON, no markdown headers.
"""
```

---

## REACT_QUERY_PROMPT

Model: `claude-opus-4-6` | Tools: `Read,Glob,Grep,WebSearch` | Max turns: `10` | Timeout: `5m`

```python
REACT_QUERY_PROMPT = f"""
Answer this question in the context of the current meeting session.

Session ID: {session_id}
Session started: {started_at}

Meeting context (batch summaries):
{batch_summaries}

Current notes:
{notes_json}

Current action items:
{action_items_json}

Recent messages (current batch):
{current_batch_json}

Question: {query}

Use available tools to search the codebase or web if needed. Provide a clear,
concise answer grounded in the session context and any additional research.
"""
```

---

## END_SYNTHESIS_PROMPT

Model: `claude-opus-4-6` | Tools: `Read` | Max turns: `15` | Timeout: `10m`

```python
END_SYNTHESIS_PROMPT = f"""
Generate a complete session summary for this meeting.

Session ID: {session_id}
Started: {started_at}
Total messages: {total_message_count}
Total batches: {batch_count}

Batch summaries:
{all_batch_summaries}

All notes captured:
{notes_json}

All action items captured:
{action_items_json}

All decisions recorded:
{decisions_json}

References mentioned:
{references_json}

Read any batch files from meeting_minutes/{session_id}/ if you need full message
context beyond the summaries.

Output format:

# Session Summary — {date} {time}

## Action Items
- [ ] <action> — <context>

## Decisions
- <decision> — <reasoning>

## Summary
<2-3 paragraph narrative of what was discussed and concluded>

## References
- <url or doc mentioned during session>

Be thorough but concise. Every action item and decision captured during the
session must appear in the summary. The narrative should give someone who wasn't
present a clear understanding of what happened.
"""
```

---

## Tips

**Assemble batch summaries for context:**
```python
import json, glob

batch_files = sorted(glob.glob(f"meeting_minutes/{slug}/batch-*.json"))
summaries = []
for bf in batch_files:
    with open(bf) as f:
        data = json.load(f)
        summaries.append(data.get("summary", "(no summary)"))
batch_summaries = "\n\n".join(f"Batch {i+1}: {s}" for i, s in enumerate(summaries))
```

**Keep ReAct queries focused** — include only batch summaries (not full messages)
to stay within context limits. Full messages are available via Read tool if needed.
