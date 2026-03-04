# Prompt Templates

All templates are Python f-strings. Inject variables before passing to `claude -p`.

## System prompt (always use --append-system-prompt)

```
You are a senior software engineer. Work only within /workspace.
All file paths must be relative to /workspace or absolute starting with /workspace.
When asked for JSON output, respond ONLY with valid JSON — no preamble, no markdown
fences, no explanation. When asked for markdown, use clear headers and be concise.
```

---

## PLAN_PROMPT

Tools: `Read,Glob,Grep` | Model: `claude-opus-4-6`

```python
PLAN_PROMPT = f"""
Task type: {task_type}
Task description:
{description}

Explore the relevant files and produce a development plan with these sections:

1. **Problem Statement** (2-3 sentences)
2. **Scope** (files that will change; files that must NOT change)
3. **Proposed Approach** (step-by-step; explain key decisions)
4. **Risks & Mitigations**
5. **Definition of Done** (specific, testable criteria)
6. **Estimated Complexity** (low/medium/high with justification)

Format as clean markdown. Be specific.
"""
```

## PLAN_REVISION_PROMPT

```python
PLAN_REVISION_PROMPT = f"""
Reviewer feedback on the plan:

---
{user_feedback}
---

Revise the plan to address this feedback. Output the full revised plan.
"""
```

---

## PHASE_PROPOSAL_PROMPT

Tools: `Read,Glob,Grep` | Model: `claude-opus-4-6` | Output: JSON only

```python
PHASE_PROPOSAL_PROMPT = f"""
Based on this approved plan, propose a phased implementation of 2-5 discrete phases,
each independently committable and testable.

{approved_plan}

Respond with ONLY a JSON array:
[
  {{
    "phase": 1,
    "title": "short title",
    "description": "what this phase does and why it comes first",
    "files_affected": ["path/to/file.py"],
    "estimated_complexity": "low|medium|high",
    "test_command": "python -m pytest tests/unit/test_x.py",
    "dependencies": []
  }}
]

Rules:
- Each phase must be independently testable
- "files_affected" must be paths that exist in /workspace
- "test_command" must be a real runnable command
"""
```

## PHASE_REVISION_PROMPT

Output: JSON only

```python
PHASE_REVISION_PROMPT = f"""
Reviewer feedback on the proposed phases:

---
{user_feedback}
---

Revise the phase proposal. Respond with ONLY the updated JSON array.
"""
```

---

## IMPLEMENT_PHASE_PROMPT

Tools: `Read,Write,Edit,Bash(git *),Bash(npm *),Bash(python *)` | Model: `claude-sonnet-4-6`

```python
IMPLEMENT_PHASE_PROMPT = f"""
Implement Phase {phase_number} of {total_phases}: "{phase_title}"

{phase_description}

Files to modify:
{chr(10).join(f'- {f}' for f in phase_files_affected)}

Approved plan context:
{approved_plan_summary}

{"Completed phases:" if completed_phases else ""}
{chr(10).join(f'- Phase {p["phase"]}: {p["title"]} ✓' for p in completed_phases)}

Instructions:
1. Read relevant files first
2. Implement the changes
3. Do not modify files outside files_affected unless strictly necessary
4. Do NOT commit — the orchestrator handles commits

{delivery_instructions}

When done, output:
## Phase {phase_number} Complete
- Files modified: [list]
- Key changes: [2-3 bullets]
- Ready for testing: yes/no
"""
```

## IMPLEMENT_FIX_PROMPT

Resume same session after test failure.

```python
IMPLEMENT_FIX_PROMPT = f"""
Tests failed after Phase {phase_number}:

<test_output>
{test_stdout}
{test_stderr}
</test_output>

Fix the failures. Only modify files from the phase {phase_number} files_affected
list unless the root cause is clearly elsewhere.

{delivery_instructions}

Output:
## Fix Applied
- Root cause: [description]
- Files changed: [list]
- Confidence: high/medium/low
"""
```

---

## CI_ANALYSIS_PROMPT

Tools: `Read,Glob,Grep` | Model: `claude-opus-4-6`

```python
CI_ANALYSIS_PROMPT = f"""
Analyze this CI failure and identify the root cause.

Job: {job_name}
Logs:
{job_logs}

Diff introduced by this PR:
{git_diff}

Output:
## Root Cause
<clear explanation>

## Proposed Fix
<what needs to change and where>

## Files to Change
<list>

## Risk
low/medium/high — <why>
"""
```

---

## REVIEW_TRIAGE_PROMPT

Tools: `Read,Glob,Grep` | Model: `claude-opus-4-6`

```python
REVIEW_TRIAGE_PROMPT = f"""
Triage these PR review comments. For each, determine if it is a confirmed bug
that must be fixed, or a false positive that can be dismissed.

PR diff:
{git_diff}

Review comments:
{review_comments_json}

For each comment output:
- Verdict: ✅ Confirmed bug / ❌ False positive
- Reasoning: why
- Proposed fix: (if confirmed) what change to make

Be critical — not every reviewer comment is correct.
"""
```

---

## COVERAGE_ANALYSIS_PROMPT

Tools: `Read,Glob,Grep` | Model: `claude-opus-4-6`

```python
COVERAGE_ANALYSIS_PROMPT = f"""
Analyze these uncovered lines and determine what tests are needed.

Current patch coverage: {current_pct}% (target: {target_pct}%)

Uncovered lines by file:
{uncovered_lines_json}

For each file, output:
- What the uncovered lines do
- Specific test cases to write (name + what it verifies)
- Estimated coverage contribution

Be precise — name real test functions, not vague descriptions.
"""
```

---

## Delivery Instructions (inject into implementation prompts)

The orchestrator loads `subprocess-instructions.md`, resolves the script path,
and injects it into `IMPLEMENT_PHASE_PROMPT` and `IMPLEMENT_FIX_PROMPT`:

```python
DELIVERY_SCRIPTS_DIR = "../intermediary-delivery/scripts/telegram"
with open("../intermediary-delivery/references/subprocess-instructions.md") as f:
    delivery_instructions = f.read().replace("{delivery_scripts_dir}", DELIVERY_SCRIPTS_DIR)
```

---

## Tips

**Inject file contents for small files:**
```python
with open("/workspace/src/models/user.py") as f:
    content = f.read()
prompt = f"Review this:\n\n<file path='src/models/user.py'>\n{content}\n</file>"
```

**Keep multi-turn sessions focused** — always include in each IMPLEMENT prompt:
- What prior phases accomplished
- Current `git status` snippet
- Exactly what this phase needs to do

**Parse JSON output safely:**
```python
import re, json
def parse_json(text: str):
    clean = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
    return json.loads(clean)
```
