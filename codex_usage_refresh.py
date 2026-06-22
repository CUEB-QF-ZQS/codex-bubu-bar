#!/usr/bin/env python3
import fcntl
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


STATE_DIR = Path(os.environ.get("CODEX_USAGE_BAR_STATE_DIR", "~/.local/state/codex-usage-bar")).expanduser()
LOCK_PATH = STATE_DIR / "refresh.lock"
USAGE_PATH = STATE_DIR / "usage.json"
STDOUT_PATH = STATE_DIR / "last-refresh.json"
STDERR_PATH = STATE_DIR / "last-refresh.err.log"
META_PATH = STATE_DIR / "last-refresh-meta.json"
AUTH_PATH = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser() / "auth.json"
USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"


def load_access_token():
    data = json.loads(AUTH_PATH.read_text())
    token = (data.get("tokens") or {}).get("access_token")
    if not token:
        raise RuntimeError("No ChatGPT access token found in Codex auth storage")
    return token


def fetch_usage():
    token = load_access_token()
    request = urllib.request.Request(
        USAGE_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "CodexUsageBar/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def slim_usage(usage):
    return {
        "plan_type": usage.get("plan_type"),
        "rate_limit": usage.get("rate_limit"),
        "code_review_rate_limit": usage.get("code_review_rate_limit"),
    }


def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    with LOCK_PATH.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0

        start = time.time()
        error = None
        code = 0
        try:
            usage = slim_usage(fetch_usage())
            payload = {
                "ok": True,
                "fetched_at": time.time(),
                "usage": usage,
            }
            USAGE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
            STDOUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
            STDERR_PATH.write_text("")
        except urllib.error.HTTPError as exc:
            code = 1
            error = f"HTTP {exc.code}"
            STDERR_PATH.write_text(exc.read().decode("utf-8", errors="replace"))
        except Exception as exc:
            code = 1
            error = str(exc)
            STDERR_PATH.write_text(error)

        META_PATH.write_text(
            json.dumps(
                {
                    "started_at": start,
                    "finished_at": time.time(),
                    "exit_code": code,
                    "error": error,
                },
                indent=2,
            )
        )
        return code


if __name__ == "__main__":
    sys.exit(main())
