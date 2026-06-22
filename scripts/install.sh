#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$HOME/Applications/CodexUsageBar.app"
BIN_DIR="$HOME/.local/bin"
STATE_DIR="$HOME/.local/state/codex-usage-bar"
LAUNCH_AGENT="$HOME/Library/LaunchAgents/com.madness.codexusagebar.plist"

mkdir -p "$BIN_DIR" "$STATE_DIR" "$HOME/Applications" "$HOME/Library/LaunchAgents"

"$ROOT_DIR/scripts/build_app.sh" "$APP_DIR" >/dev/null

chmod +x "$ROOT_DIR/codex_usage_refresh.py" "$ROOT_DIR/codex_usage_remaining.py" "$ROOT_DIR/codex-usage.10m.sh"
ln -sf "$ROOT_DIR/codex_usage_refresh.py" "$BIN_DIR/codex-usage-refresh"
ln -sf "$ROOT_DIR/codex_usage_remaining.py" "$BIN_DIR/codex-usage-remaining"

cat > "$LAUNCH_AGENT" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.madness.codexusagebar</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/open</string>
    <string>$APP_DIR</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/codexusagebar.out.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/codexusagebar.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)" "$LAUNCH_AGENT" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$LAUNCH_AGENT"
launchctl enable "gui/$(id -u)/com.madness.codexusagebar"

pkill -x CodexUsageBar >/dev/null 2>&1 || true
open "$APP_DIR"

echo "Installed Codex Usage Bar"
