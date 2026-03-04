#!/usr/bin/env python3
"""
claude_telegram_relay.py

Pipe claude --output-format stream-json output to this script to relay events to Telegram.

Usage:
  claude -p "your prompt" --output-format stream-json --verbose | python3 claude_telegram_relay.py

Environment variables:
  TELEGRAM_BOT_TOKEN   Your bot token from @BotFather
  TELEGRAM_CHAT_ID     Target chat/group ID
  RELAY_LEVEL          What to relay: "all" | "summary" | "text" (default: "all")
"""

import sys
import json
import os
import urllib.request
import urllib.error
import time

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")
RELAY_LEVEL = os.environ.get("RELAY_LEVEL", "all")   # all | summary | text

MAX_MSG_LEN = 4096   # Telegram hard limit
RATE_DELAY  = 0.05   # seconds between sends to avoid flood limits

# ── Telegram sender ───────────────────────────────────────────────────────────
def send_telegram(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to Telegram. Returns True on success."""
    if not BOT_TOKEN or not CHAT_ID:
        print(f"[NO TOKEN] {text}", file=sys.stderr)
        return False

    # Chunk if over limit
    chunks = [text[i:i+MAX_MSG_LEN] for i in range(0, len(text), MAX_MSG_LEN)]
    for chunk in chunks:
        payload = json.dumps({
            "chat_id":    CHAT_ID,
            "text":       chunk,
            "parse_mode": parse_mode,
        }).encode()
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10)
            time.sleep(RATE_DELAY)
        except urllib.error.HTTPError as e:
            print(f"[TG HTTP ERROR {e.code}] {e.read().decode()}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"[TG ERROR] {e}", file=sys.stderr)
            return False
    return True

# ── Formatters ────────────────────────────────────────────────────────────────
def esc(text: str) -> str:
    """Escape HTML special chars for Telegram."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def format_init(data: dict) -> str | None:
    model   = data.get("model", "?")
    session = data.get("session_id", "?")[:8]
    cwd     = data.get("cwd", "?")
    return (f"\U0001f916 <b>Claude session started</b>\n"
            f"Model: <code>{esc(model)}</code>\n"
            f"Session: <code>{esc(session)}\u2026</code>\n"
            f"CWD: <code>{esc(cwd)}</code>")

def format_assistant(data: dict) -> str | None:
    msg = data.get("message", {})
    parts = []
    for block in msg.get("content", []):
        btype = block.get("type")
        if btype == "text" and block.get("text", "").strip():
            parts.append(f"\U0001f4ac {esc(block['text'].strip())}")
        elif btype == "tool_use" and RELAY_LEVEL == "all":
            name  = block.get("name", "?")
            inp   = block.get("input", {})
            desc  = inp.get("description") or inp.get("command", "")
            parts.append(f"\U0001f527 <b>{esc(name)}</b>"
                         + (f"\n<i>{esc(str(desc)[:200])}</i>" if desc else ""))
    return "\n".join(parts) if parts else None

def format_tool_result(data: dict) -> str | None:
    if RELAY_LEVEL != "all":
        return None
    raw = data.get("tool_use_result", {})
    # tool_use_result can be a plain string (e.g. permission denial message)
    if isinstance(raw, str):
        return f"\u26a0\ufe0f <code>{esc(raw[:500])}</code>" if raw.strip() else None
    result = raw if isinstance(raw, dict) else {}
    stdout = (result.get("stdout") or "").strip()
    stderr = (result.get("stderr") or "").strip()
    is_err = result.get("isImage") or data.get("message", {}).get("content", [{}])[0].get("is_error", False)

    lines = []
    if stdout:
        preview = stdout[:500] + ("\u2026" if len(stdout) > 500 else "")
        lines.append(f"{'\u274c' if is_err else '\u2705'} <code>{esc(preview)}</code>")
    if stderr:
        preview = stderr[:200] + ("\u2026" if len(stderr) > 200 else "")
        lines.append(f"\u26a0\ufe0f <code>{esc(preview)}</code>")
    return "\n".join(lines) if lines else None

def format_result(data: dict) -> str | None:
    ok      = not data.get("is_error", False)
    result  = (data.get("result") or "").strip()
    cost    = data.get("total_cost_usd")
    turns   = data.get("num_turns", "?")
    dur_ms  = data.get("duration_ms", 0)
    dur_s   = dur_ms / 1000

    cost_str = f"${cost:.4f}" if cost is not None else "?"
    icon = "\u2705" if ok else "\u274c"
    msg = (f"{icon} <b>Session complete</b>\n"
           f"Turns: {turns} | Duration: {dur_s:.1f}s | Cost: {cost_str}\n")
    if result:
        preview = result[:300] + ("\u2026" if len(result) > 300 else "")
        msg += f"\n<b>Result:</b> {esc(preview)}"
    return msg

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("\u26a0\ufe0f  TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.", file=sys.stderr)
        print("    Messages will be printed to stderr instead.\n", file=sys.stderr)

    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        # Echo the raw JSONL through (so you can still pipe further)
        print(raw_line)
        sys.stdout.flush()

        try:
            data = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        event_type = data.get("type")
        subtype    = data.get("subtype")
        msg_role   = data.get("message", {}).get("role")

        text = None

        if event_type == "system" and subtype == "init":
            text = format_init(data)

        elif event_type == "assistant" and msg_role == "assistant":
            if RELAY_LEVEL in ("all", "text", "summary"):
                text = format_assistant(data)

        elif event_type == "user":
            # tool_result lives here
            content = data.get("message", {}).get("content", [])
            if content and isinstance(content, list) and content[0].get("type") == "tool_result":
                text = format_tool_result(data)

        elif event_type == "result":
            text = format_result(data)

        if text:
            send_telegram(text)


if __name__ == "__main__":
    main()
