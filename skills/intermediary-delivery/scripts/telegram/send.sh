#!/usr/bin/env bash
set -euo pipefail

# Send a plain text message via Telegram.
# Usage: send.sh <message>
# Env:   TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN is not set" >&2
  exit 1
fi

if [[ -z "${TELEGRAM_CHAT_ID:-}" ]]; then
  echo "ERROR: TELEGRAM_CHAT_ID is not set" >&2
  exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: send.sh <message>" >&2
  exit 1
fi

MESSAGE="$1"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -F chat_id="$TELEGRAM_CHAT_ID" \
  -F text="$MESSAGE" \
  -F parse_mode="Markdown" \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage")

if [[ "$HTTP_CODE" -ne 200 ]]; then
  echo "ERROR: Telegram API returned HTTP $HTTP_CODE" >&2
  exit 1
fi

exit 0
