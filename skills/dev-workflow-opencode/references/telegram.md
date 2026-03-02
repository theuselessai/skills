# Telegram Helpers

Bot token and chat ID are read from environment:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Send text

```bash
telegram_send() {
  curl -s \
    -F chat_id="$TELEGRAM_CHAT_ID" \
    -F text="$1" \
    -F parse_mode="Markdown" \
    "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage"
}
```

## Send file

```bash
telegram_file() {
  # $1 = file path, $2 = optional caption
  curl -s \
    -F chat_id="$TELEGRAM_CHAT_ID" \
    -F document=@"$1" \
    -F caption="${2:-}" \
    "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendDocument"
}
```

## Approval gate pattern

Send the plan file, then poll for a reply:

```bash
telegram_file "/tmp/pr-42-ci-fix-plan.md" "CI Fix Plan — awaiting approval"

# Then wait for user to reply "approve", "revise: <feedback>", or "abort"
# via whatever mechanism your agent uses to receive Telegram replies
```

## Standard message formats

**Step start:**
```
🔄 PR #<N>: starting <step name>
```

**Gate — awaiting approval:**
```
🔵 PR #<N>: <plan name> sent for review
```

**Step complete:**
```
✅ PR #<N>: <step> done
```

**Error / needs input:**
```
⚠️ PR #<N>: <what happened> — needs your input
```

**Final merge:**
```
✅ PR #<N> merged.
Branch: <branch>
Dev plan: docs/dev-plans/<slug>.md updated
```
