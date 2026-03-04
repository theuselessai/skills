# Prompt Templates

All templates are Python f-strings. Inject variables before passing to `claude -p`.

---

## IMPLEMENT_PROMPT

```python
IMPLEMENT_PROMPT = f"""
Read the development plan at dev-plans/{slug}.md and implement it.

Instructions:
1. Read the plan thoroughly
2. Implement the changes described in the plan
3. Write tests for new functionality
4. Commit your changes with descriptive commit messages
5. Do not modify files outside the scope defined in the plan unless strictly necessary

If the plan is too large to implement in a single pass, create implementation
phases in /implementations/{slug}_{date}/ — write a phases.md describing what
each phase covers, implement what you can in this session, and note what remains.

When done, output:
## Implementation Complete
- Files modified: [list]
- Files created: [list]
- Tests added: [list]
- Key changes: [2-3 bullets]
- Remaining work: [if any phases remain]
"""
```

---

## IMPLEMENT_FIX_PROMPT

Resume same session after test failure.

```python
IMPLEMENT_FIX_PROMPT = f"""
Tests failed after implementation:

<test_output>
{test_stdout}
{test_stderr}
</test_output>

Fix the failures. Only modify files within the scope of the original plan
unless the root cause is clearly elsewhere.

Output:
## Fix Applied
- Root cause: [description]
- Files changed: [list]
- Confidence: high/medium/low
"""
```

---

## REVIEW_CYCLE_PROMPT

```python
REVIEW_CYCLE_PROMPT = f"""
Triage and fix all issues on PR #{pr_number}.

1. Check CI status: run `gh pr view {pr_number} --json statusCheckRollup`
2. For any failed checks, fetch logs and analyze root causes
3. Check PR reviews: run `gh api repos/{{owner}}/{{repo}}/pulls/{pr_number}/comments`
   and `gh pr view {pr_number} --json reviews`
4. For each review comment, determine: confirmed bug or false positive
5. Fix all confirmed issues
6. Commit and push fixes

Rules:
- Never lower coverage thresholds — write real tests
- Be critical of review comments — not every comment is correct
- Group related fixes into single commits with descriptive messages

Output:
## Review Cycle Results
- CI failures found: [count]
- CI failures fixed: [list]
- Review comments triaged: [count]
- Confirmed bugs fixed: [list]
- False positives dismissed: [list with reasoning]
"""
```

---

## Tips

**Keep prompts self-contained** — include all context the subprocess needs.
The `--append-system-prompt` in the universal template handles markdown output
rules; task-specific content goes in the prompt argument.

**Variable injection:**
```python
prompt = IMPLEMENT_PROMPT.format(
    slug=slug,
    date=date,
)
```
