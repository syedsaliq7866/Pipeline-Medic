#!/usr/bin/env python3
"""Send Telegram notification for local git commits."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


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
    load_dotenv(repo_root / ".env")

    if not _get_env_flag("TELEGRAM_COMMIT_NOTIFY_ENABLED", "true"):
        return 0

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_ids_raw = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_ids_raw:
        return 0

    chat_ids = [_parse_chat_id(item) for item in chat_ids_raw.split(",") if item.strip()]
    if not chat_ids:
        return 0

    try:
        repo_name = _git_output(["rev-parse", "--show-toplevel"], repo_root)
        repo_name = Path(repo_name).name
        branch = _git_output(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
        short_sha = _git_output(["rev-parse", "--short", "HEAD"], repo_root)
        author = _git_output(["log", "-1", "--pretty=%an"], repo_root)
        subject = _git_output(["log", "-1", "--pretty=%s"], repo_root)
    except Exception:
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
    for chat_id in chat_ids:
        try:
            requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
        except Exception:
            # Avoid blocking commits if Telegram fails.
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
