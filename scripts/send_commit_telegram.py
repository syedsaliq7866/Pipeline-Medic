#!/usr/bin/env python3
"""Send Telegram notification for local git commits."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib import error, request


def _load_dotenv(dotenv_path: Path) -> None:
    """Minimal .env loader to avoid runtime dependency on python-dotenv."""
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _parse_chat_id(raw: str) -> int | str:
    raw = raw.strip()
    if raw.startswith("-") and raw[1:].isdigit():
        return int(raw)
    if raw.isdigit():
        return int(raw)
    return raw


def _get_env_flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _git_output(args: list[str], cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=str(cwd), text=True).strip()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    _load_dotenv(repo_root / ".env")

    if not _get_env_flag("TELEGRAM_COMMIT_NOTIFY_ENABLED", "true"):
        print("commit-telegram: disabled")
        return 0

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_ids_raw = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_ids_raw:
        print("commit-telegram: missing token or chat id")
        return 0

    chat_ids = [_parse_chat_id(item) for item in chat_ids_raw.split(",") if item.strip()]
    if not chat_ids:
        print("commit-telegram: no valid chat ids")
        return 0

    try:
        repo_name = _git_output(["rev-parse", "--show-toplevel"], repo_root)
        repo_name = Path(repo_name).name
        branch = _git_output(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
        short_sha = _git_output(["rev-parse", "--short", "HEAD"], repo_root)
        author = _git_output(["log", "-1", "--pretty=%an"], repo_root)
        subject = _git_output(["log", "-1", "--pretty=%s"], repo_root)
    except Exception:
        print("commit-telegram: unable to read git commit metadata")
        return 0

    text = (
        "✅ <b>New Commit</b>\n"
        f"Repo: <code>{repo_name}</code>\n"
        f"Branch: <code>{branch}</code>\n"
        f"Commit: <code>{short_sha}</code>\n"
        f"Author: <b>{author}</b>\n"
        f"Message: {subject}"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload_template = {
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    for chat_id in chat_ids:
        try:
            payload = dict(payload_template)
            payload["chat_id"] = chat_id
            body = json.dumps(payload).encode("utf-8")
            req = request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=10) as resp:
                # Non-2xx should raise, but keep a defensive check.
                if resp.status < 200 or resp.status >= 300:
                    print(f"commit-telegram: unexpected status for chat {chat_id}: {resp.status}")
                    return 0
            print(f"commit-telegram: sent to chat {chat_id}")
        except (error.URLError, TimeoutError, ValueError):
            # Avoid blocking commits if Telegram fails.
            print(f"commit-telegram: failed for chat {chat_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
