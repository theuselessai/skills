#!/bin/sh
set -e

# Detect architecture
ARCH=$(uname -m)
case "$ARCH" in
  x86_64)
    BINARY_NAME="agent-browser-linux-x64-musl"
    ;;
  aarch64)
    BINARY_NAME="agent-browser-linux-arm64-musl"
    ;;
  *)
    echo "Error: unsupported architecture '$ARCH'. Only x86_64 and aarch64 are supported." >&2
    exit 1
    ;;
esac

# Install Chromium
echo "Installing Chromium..."
apk add --no-cache chromium

# Fetch latest release version
echo "Fetching latest agent-browser release..."
LATEST_VERSION=$(curl -fsSL https://api.github.com/repos/theuselessai/agent-browser-musl/releases/latest | grep '"tag_name"' | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')

# Download binary
DOWNLOAD_URL="https://github.com/theuselessai/agent-browser-musl/releases/download/${LATEST_VERSION}/${BINARY_NAME}"
echo "Downloading ${BINARY_NAME} ${LATEST_VERSION}..."
curl -fsSL -o /usr/local/bin/agent-browser "$DOWNLOAD_URL"
chmod +x /usr/local/bin/agent-browser

# Configure environment
echo 'export AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium' >> /etc/profile
echo "alias agent-browser='agent-browser --native'" >> /etc/profile

echo "agent-browser installed successfully (${LATEST_VERSION}, ${ARCH})"
echo "Run 'source /etc/profile' to load environment."
