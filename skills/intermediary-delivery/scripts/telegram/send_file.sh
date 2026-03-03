#!/usr/bin/env bash
set -euo pipefail

# Send a file via Telegram with optional caption.
# Usage: send_file.sh <filepath> [caption]
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
  echo "Usage: send_file.sh <filepath> [caption]" >&2
  exit 1
fi

FILEPATH="$1"
CAPTION="${2:-}"

if [[ ! -f "$FILEPATH" ]]; then
  echo "ERROR: File not found: $FILEPATH" >&2
  exit 1
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -F chat_id="$TELEGRAM_CHAT_ID" \
  -F document=@"$FILEPATH" \
  -F caption="$CAPTION" \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument")

if [[ "$HTTP_CODE" -ne 200 ]]; then
  echo "ERROR: Telegram API returned HTTP $HTTP_CODE" >&2
  exit 1
fi

exit 0
