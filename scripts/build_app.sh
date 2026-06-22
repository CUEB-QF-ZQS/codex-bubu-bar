#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${1:-$HOME/Applications/CodexUsageBar.app}"

mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"
cp "$ROOT_DIR/Info.plist" "$APP_DIR/Contents/Info.plist"
cp "$ROOT_DIR/assets/bear-logo-menubar.png" "$APP_DIR/Contents/Resources/bear-logo-menubar.png"
swiftc "$ROOT_DIR/CodexUsageBar.swift" -o "$APP_DIR/Contents/MacOS/CodexUsageBar"
chmod +x "$APP_DIR/Contents/MacOS/CodexUsageBar"

echo "$APP_DIR"
