# Prompt Templates

All templates are Python f-strings. Inject variables before passing to `claude -p`.

---

## PLAN_PROMPT

```python
PLAN_PROMPT = f"""
Task type: {task_type}
Task description:
{description}

Explore the relevant files in the codebase and produce a development plan.
Write the plan to dev-plans/{slug}.md with these sections:

1. **Problem Statement** (2-3 sentences)
2. **Scope** (files that will change; files that must NOT change)
3. **Proposed Approach** (step-by-step; explain key decisions)
4. **Risks & Mitigations**
5. **Definition of Done** (specific, testable criteria)
6. **Estimated Complexity** (low/medium/high with justification)

Be specific — reference actual file paths, function names, and line numbers.
Format as clean markdown.
"""
```

---

## PLAN_REVISION_PROMPT

```python
PLAN_REVISION_PROMPT = f"""
Reviewer feedback on the plan at dev-plans/{slug}.md:

---
{user_feedback}
---

Read the existing plan, then revise it to address this feedback.
Write the full revised plan back to dev-plans/{slug}.md.
"""
```

---

## Tips

**Keep prompts self-contained** — include all context the subprocess needs.
No `--append-system-prompt`, no external injection. The subprocess has full
tool access and will explore the codebase on its own.

**Variable injection:**
```python
prompt = PLAN_PROMPT.format(
    task_type=task_type,
    description=description,
    slug=slug,
)
```
