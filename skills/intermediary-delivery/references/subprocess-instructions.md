## Delivery Notifications (optional, non-blocking)

You can send progress notifications to the user during implementation.
These are **fire-and-forget** — delivery failures must never abort your work.

### Decision gate

```
Need a reply? → Do NOT use these scripts. Only for one-way status updates.
```

### Scripts

Send a text message:
```bash
{delivery_scripts_dir}/send.sh "Phase 2/3: models complete, starting routes" || true
```

Send a file:
```bash
{delivery_scripts_dir}/send_file.sh /tmp/debug-output.log "Debug log" || true
```

### Rules

1. **Always append `|| true`** — delivery failures must never stop implementation
2. **Max 2–3 notifications per phase** — don't spam (e.g. start, milestone, done)
3. **Keep messages short** — one line, plain text, no markdown formatting
4. **Never send secrets** — no tokens, passwords, API keys, or .env contents
5. **Never wait for a response** — these are one-way notifications only
