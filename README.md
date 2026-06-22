# Codex Usage Bar

macOS menu bar utility that shows Codex usage remaining, formatted as:

```text
5h 87% | Wk 98%
```

The app refreshes every 20 minutes by calling the same Usage & billing backend endpoint used by the Codex app:

```text
https://chatgpt.com/backend-api/wham/usage
```

It uses the local Codex ChatGPT login token from `~/.codex/auth.json`. It does not run `codex exec`, does not send a model prompt, and should not consume Codex model tokens.

## Requirements

- macOS 13+
- Swift compiler / Xcode Command Line Tools
- Python 3
- Codex logged in with ChatGPT auth

Check auth:

```sh
codex login status
```

## Install

```sh
./scripts/install.sh
```

This installs:

- `~/Applications/CodexUsageBar.app`
- `~/.local/bin/codex-usage-refresh`
- `~/.local/bin/codex-usage-remaining`
- `~/Library/LaunchAgents/com.madness.codexusagebar.plist`

Runtime state is stored under:

```text
~/.local/state/codex-usage-bar
```

The state snapshot stores only the fields needed for display: plan type and rate-limit windows.

## Manual Commands

Refresh from the Usage & billing API:

```sh
codex-usage-refresh
```

Print the current display value:

```sh
codex-usage-remaining
```

Print JSON:

```sh
codex-usage-remaining --json
```

SwiftBar/xbar fallback:

```sh
codex-usage-remaining --swiftbar
```

## Uninstall

```sh
./scripts/uninstall.sh
```

## Notes

The Usage & billing endpoint is an internal ChatGPT/Codex endpoint and may change. If the endpoint fails, the reader falls back to the latest local Codex session `rate_limits` event when available.
