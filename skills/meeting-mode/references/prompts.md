# Prompt Templates

All templates are Python f-strings. Inject variables before passing to the
classifier or `claude -p`.

---

## CLASSIFY_PROMPT

Used by Haiku 4.5 to classify each incoming message.

```python
CLASSIFY_PROMPT = f"""
Classify this meeting message into exactly one category.

Recent context (last 5 messages):
{recent_context}

Current message: {message}

Categories:
- passive: casual conversation, filler, greetings, acknowledgments
- note: a key point, insight, fact, or decision worth remembering
- action_item: something someone needs to do, with or without a deadline
- needs_research: a question that requires searching code, docs, or the web
- end_session: intent to wrap up or end the meeting

Respond with ONLY the category name, nothing else.
"""
```

---

## NOTE_EXTRACT_PROMPT

Used by Haiku 4.5 to extract the key point from a message classified as `note`.

```python
NOTE_EXTRACT_PROMPT = f"""
Extract the key point from this meeting message as a concise note.

Message: {message}

Respond with ONLY the extracted note — one or two sentences, no preamble.
"""
```

---

## ACTION_EXTRACT_PROMPT

Used by Haiku 4.5 to extract action item details.

```python
ACTION_EXTRACT_PROMPT = f"""
Extract the action item from this meeting message.

Message: {message}
Context: {surrounding_context}

Respond with ONLY a JSON object:
{{"text": "what needs to be done", "assignee": "who (or 'unassigned')", "deadline": "when (or 'none')"}}
"""
```

---

## RESEARCH_PROMPT

Used with `claude -p` when a message needs tool-based research.

```python
RESEARCH_PROMPT = f"""
Answer this question in the context of the current meeting session.

Session ID: {session_id}
Session started: {started_at}

Meeting context (batch summaries):
{batch_summaries}

Current notes:
{notes_json}

Recent messages:
{current_batch_json}

Question: {query}

Use available tools to search the codebase or web if needed. Provide a clear,
concise answer grounded in the session context and any additional research.
"""
```

---

## BATCH_SUMMARY_PROMPT

Used by Haiku 4.5 during batch rotation.

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

## END_SYNTHESIS_PROMPT

Used with `claude -p` for final session synthesis.

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
- [ ] <action> — <context/assignee>

## Decisions
- <decision> — <reasoning>

## Summary
<2-3 paragraph narrative of what was discussed and concluded>

## References
- <url or doc mentioned during session>

Be thorough but concise. Every action item and decision captured during the
session must appear in the summary.
"""
```

---

## Tips

**Classifier should be fast** — Haiku 4.5 classifies in <1s. No tool access
needed for classification, only for research queries via `claude -p`.

**Keep research prompts self-contained** — the subprocess has full tool access
and will explore on its own.
