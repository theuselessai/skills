---
name: agent-browser-init
description: >
  Install agent-browser as a standalone musl binary in an Alpine Linux sandbox.
  One-time setup skill — run once after sandbox initialization, before using any
  other agent-browser-* skills. Installs Chromium via apk and downloads the
  agent-browser binary from theuselessai/agent-browser-musl releases.
  Triggers on: "install agent-browser", "setup browser", "browser init",
  "agent-browser setup", or any request to set up web browsing in a sandbox.
---

# Agent Browser Init

Install agent-browser as a standalone musl binary in an Alpine Linux sandbox.
Run this skill **once** after sandbox initialization, before using any other
agent-browser-* skills.

## Prerequisites

- Alpine Linux sandbox with `apk` package manager
- `curl` available in PATH
- Internet access to download packages and GitHub releases

## When to Use This Skill

Run this skill exactly once per sandbox — after the sandbox is initialized and
before any other agent-browser-* skill is invoked.

```
Sandbox initialized? ─── No ──→ Wait for sandbox init
        │
       Yes
        │
        ▼
Run setup.sh (one-time)
        │
        ▼
Use agent-browser normally
```

## Workflow

Run the installer script:

```bash
sh ../agent-browser-init/setup.sh
```

The script will:
1. Detect architecture (x86_64 or aarch64)
2. Install Chromium via `apk`
3. Fetch the latest agent-browser release from GitHub
4. Download the correct musl binary to `/usr/local/bin/agent-browser`
5. Configure environment variables and aliases in `/etc/profile`

## Post-Setup Environment

After running `setup.sh`, the following are available:

- `AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium` — exported in `/etc/profile`
- `agent-browser` alias — resolves to `agent-browser --native`

Source the profile or start a new shell to pick up the changes:

```bash
source /etc/profile
```

## Usage Example

```bash
# After setup
source /etc/profile
agent-browser open https://example.com && agent-browser snapshot
```

## Key Rules

1. **Run only once per sandbox.** Re-running is safe but unnecessary.
2. **Alpine only.** This skill uses `apk` and musl binaries — it will not work on glibc-based distributions.
3. **Supported architectures:** x86_64 and aarch64 only. The script exits with error on unsupported architectures.
4. **No npm/node required.** The binary is a standalone executable.
5. **Source `/etc/profile` after setup** to pick up the exported path and alias.
