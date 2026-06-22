#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import sys
from datetime import datetime, timezone


CODEX_HOME = pathlib.Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
SEARCH_DIRS = [CODEX_HOME / "sessions", CODEX_HOME / "archived_sessions"]
STATE_DIR = pathlib.Path(os.environ.get("CODEX_USAGE_BAR_STATE_DIR", "~/.local/state/codex-usage-bar")).expanduser()
USAGE_SNAPSHOT = STATE_DIR / "usage.json"
MAX_FILES = 40
TAIL_BYTES = 256 * 1024


def clamp_percent(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(100.0, number))


def remaining_from(limit):
    if not isinstance(limit, dict):
        return None
    reset_epoch = limit.get("resets_at")
    try:
        if reset_epoch is not None and float(reset_epoch) <= datetime.now(tz=timezone.utc).timestamp():
            return 100
    except (TypeError, ValueError):
        pass
    used = clamp_percent(limit.get("used_percent"))
    if used is None:
        return None
    return int(round(100.0 - used))


def label_from_window_minutes(minutes):
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return "Limit"
    if minutes == 300:
        return "5h"
    if minutes == 10080:
        return "Wk"
    if minutes % 1440 == 0:
        return f"{minutes // 1440}d"
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes}m"


def label_from_window_seconds(seconds):
    try:
        return label_from_window_minutes(int(seconds) // 60)
    except (TypeError, ValueError):
        return "Limit"


def iso_from_epoch(seconds):
    try:
        return datetime.fromtimestamp(float(seconds), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def iter_recent_jsonl_files():
    files = []
    for directory in SEARCH_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*.jsonl"):
            try:
                stat = path.stat()
            except OSError:
                continue
            files.append((stat.st_mtime, path))
    files.sort(reverse=True)
    for _, path in files[:MAX_FILES]:
        yield path


def tail_lines(path):
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - TAIL_BYTES))
            data = handle.read()
    except OSError:
        return []

    if data and not data.startswith(b"{"):
        data = data.split(b"\n", 1)[-1]
    return data.splitlines()


def find_latest_rate_limits():
    best = None
    for path in iter_recent_jsonl_files():
        for raw_line in reversed(tail_lines(path)):
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            rate_limits = event.get("rate_limits")
            if rate_limits is None and isinstance(event.get("payload"), dict):
                rate_limits = event["payload"].get("rate_limits")
            if not isinstance(rate_limits, dict):
                continue

            timestamp = event.get("timestamp")
            candidate = {
                "timestamp": timestamp,
                "source": str(path),
                "rate_limits": rate_limits,
            }
            if best is None or str(timestamp) > str(best.get("timestamp")):
                best = candidate
            break
    return best


def payload_from_api_snapshot(snapshot):
    usage = snapshot.get("usage") or {}
    rate_limit = usage.get("rate_limit") or {}
    primary = rate_limit.get("primary_window") or {}
    secondary = rate_limit.get("secondary_window") or {}

    primary_used = clamp_percent(primary.get("used_percent"))
    secondary_used = clamp_percent(secondary.get("used_percent"))
    primary_remaining = None if primary_used is None else int(round(100 - primary_used))
    secondary_remaining = None if secondary_used is None else int(round(100 - secondary_used))

    if primary_remaining is None and secondary_remaining is None:
        return None

    primary_label = label_from_window_seconds(primary.get("limit_window_seconds"))
    secondary_label = label_from_window_seconds(secondary.get("limit_window_seconds")) if secondary else None
    parts = []
    if primary_remaining is not None:
        parts.append(f"{primary_label} {primary_remaining}%")
    if secondary_remaining is not None:
        parts.append(f"{secondary_label} {secondary_remaining}%")

    fetched_at = snapshot.get("fetched_at")
    return {
        "ok": True,
        "display": " | ".join(parts),
        "primary_label": primary_label,
        "secondary_label": secondary_label,
        "primary_remaining_percent": primary_remaining,
        "secondary_remaining_percent": secondary_remaining,
        "five_hour_remaining_percent": primary_remaining if primary_label == "5h" else None,
        "weekly_remaining_percent": secondary_remaining if secondary_label == "Wk" else None,
        "plan_type": usage.get("plan_type"),
        "limit_id": "wham_usage",
        "source": str(USAGE_SNAPSHOT),
        "timestamp": iso_from_epoch(fetched_at) if fetched_at else None,
        "primary_resets_at": iso_from_epoch(primary.get("reset_at")),
        "secondary_resets_at": iso_from_epoch(secondary.get("reset_at")),
    }


def read_api_snapshot_payload():
    try:
        snapshot = json.loads(USAGE_SNAPSHOT.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not snapshot.get("ok"):
        return None
    return payload_from_api_snapshot(snapshot)


def build_payload():
    api_payload = read_api_snapshot_payload()
    if api_payload:
        return api_payload

    found = find_latest_rate_limits()
    if not found:
        return {
            "ok": False,
            "error": "No Codex rate-limit events found",
            "display": "5h --% | Wk --%",
        }

    rate_limits = found["rate_limits"]
    primary = rate_limits.get("primary") or {}
    secondary = rate_limits.get("secondary") or {}
    primary_remaining = remaining_from(primary)
    secondary_remaining = remaining_from(secondary)
    primary_label = label_from_window_minutes(primary.get("window_minutes"))
    secondary_label = label_from_window_minutes(secondary.get("window_minutes")) if secondary else None

    if primary_remaining is None and secondary_remaining is None:
        return {
            "ok": False,
            "error": "Latest Codex rate-limit event has no usable remaining percentage",
            "source": found["source"],
            "timestamp": found["timestamp"],
            "display": "5h --% | Wk --%",
        }

    parts = []
    if primary_remaining is not None:
        parts.append(f"{primary_label} {primary_remaining}%")
    if secondary_remaining is not None:
        parts.append(f"{secondary_label} {secondary_remaining}%")

    return {
        "ok": True,
        "display": " | ".join(parts),
        "primary_label": primary_label,
        "secondary_label": secondary_label,
        "primary_remaining_percent": primary_remaining,
        "secondary_remaining_percent": secondary_remaining,
        "five_hour_remaining_percent": primary_remaining if primary_label == "5h" else None,
        "weekly_remaining_percent": secondary_remaining if secondary_label == "Wk" else None,
        "plan_type": rate_limits.get("plan_type"),
        "limit_id": rate_limits.get("limit_id"),
        "source": found["source"],
        "timestamp": found["timestamp"],
        "primary_resets_at": iso_from_epoch(primary.get("resets_at")),
        "secondary_resets_at": iso_from_epoch(secondary.get("resets_at")),
    }


def main():
    parser = argparse.ArgumentParser(description="Read Codex remaining usage from local session logs.")
    parser.add_argument("--json", action="store_true", help="Print a JSON payload.")
    parser.add_argument("--swiftbar", action="store_true", help="Print SwiftBar/xbar menu output.")
    args = parser.parse_args()

    payload = build_payload()

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("ok") else 1

    if args.swiftbar:
        print(payload["display"])
        print("---")
        if payload.get("ok"):
            primary_label = payload.get("primary_label") or "Primary"
            print(f"{primary_label} remaining: {payload.get('primary_remaining_percent')}%")
            if payload.get("secondary_label") and payload.get("secondary_remaining_percent") is not None:
                print(f"{payload['secondary_label']} remaining: {payload['secondary_remaining_percent']}%")
            else:
                print("Secondary window: not exposed by this account")
            if payload.get("primary_resets_at"):
                print(f"{primary_label} reset: {payload['primary_resets_at']}")
            if payload.get("secondary_resets_at"):
                print(f"{payload.get('secondary_label') or 'Secondary'} reset: {payload['secondary_resets_at']}")
            print(f"Source: {payload['source']} | length=80")
        else:
            print(payload.get("error", "Unknown error"))
        print("Refresh | refresh=true")
        return 0

    print(payload["display"])
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
