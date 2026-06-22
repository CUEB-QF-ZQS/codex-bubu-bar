#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/Applications/CodexUsageBar.app"
BIN_DIR="$HOME/.local/bin"
LAUNCH_AGENT="$HOME/Library/LaunchAgents/com.madness.codexusagebar.plist"

launchctl bootout "gui/$(id -u)" "$LAUNCH_AGENT" >/dev/null 2>&1 || true
pkill -x CodexUsageBar >/dev/null 2>&1 || true

rm -f "$BIN_DIR/codex-usage-refresh" "$BIN_DIR/codex-usage-remaining"
rm -f "$LAUNCH_AGENT"
rm -rf "$APP_DIR"

echo "Uninstalled Codex Usage Bar"
