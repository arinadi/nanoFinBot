"""Command-line entry point for nanoFinBot."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import getpass
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from nanofinbot import __version__
from nanofinbot.config import (
    ConfigError,
    config_dir,
    data_dir,
    load_config,
    save_config,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nfb", description="nanoFinBot finance bot")
    parser.add_argument(
        "--version",
        action="version",
        version=f"nfb {__version__}",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("setup", help="configure the bot token and group id")
    sub.add_parser("run", help="start the bot")
    sub.add_parser("update", help="pull latest git and restart the bot")
    return parser


def cmd_setup() -> int:
    token = getpass.getpass("Telegram bot token: ").strip()
    group_raw = input("Group chat id (optional, leave empty to skip): ").strip()
    group_id = None
    if group_raw:
        try:
            group_id = int(group_raw)
        except ValueError:
            print("Invalid group id; storing as none.", file=sys.stderr)

    cfg = load_config()
    cfg.telegram_token = token
    cfg.group_id = group_id
    save_config(cfg)
    print(f"Config written to {config_dir()}")
    return 0


def cmd_run() -> int:
    try:
        cfg = load_config()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 1
    if not cfg.telegram_token:
        print("No token configured. Run `nfb setup` first.", file=sys.stderr)
        return 1

    from nanofinbot.bot import main as bot_main

    _write_pid()
    try:
        asyncio.run(bot_main(cfg))
    finally:
        _remove_pid()
    return 0


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _pid_path() -> Path:
    return data_dir() / "nfb.pid"


def _write_pid() -> None:
    p = _pid_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(os.getpid()))


def _remove_pid() -> None:
    with contextlib.suppress(OSError):
        _pid_path().unlink(missing_ok=True)


def _read_pid() -> int | None:
    p = _pid_path()
    if not p.exists():
        return None
    try:
        return int(p.read_text().strip())
    except (ValueError, OSError):
        return None


def _is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def _terminate_and_wait(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    for _ in range(50):
        if not _is_alive(pid):
            return
        time.sleep(0.1)
    with contextlib.suppress(OSError):
        os.kill(pid, signal.SIGKILL)


def _relaunch() -> int | None:
    log = data_dir() / "nfb.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
        )
    else:
        kwargs["start_new_session"] = True
    with open(log, "ab") as f:
        proc = subprocess.Popen(
            [sys.executable, "-m", "nanofinbot.cli", "run"],
            stdout=f,
            stderr=subprocess.STDOUT,
            **kwargs,
        )
    return proc.pid


def _save_update_log(text: str) -> None:
    p = data_dir() / "last_update.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _classify_update(output: str, returncode: int) -> str:
    if returncode != 0:
        return "failed"
    if "already up to date" in output.lower():
        return "up-to-date"
    return "updated"


def _notify_group(text: str) -> None:
    try:
        cfg = load_config()
    except ConfigError:
        return
    if not cfg.telegram_token or cfg.group_id is None:
        return

    from aiogram import Bot

    async def _send() -> None:
        bot = Bot(token=cfg.telegram_token)
        try:
            await bot.send_message(cfg.group_id, text[:4000])
        finally:
            await bot.session.close()

    with contextlib.suppress(Exception):
        asyncio.run(_send())


def cmd_update() -> int:
    repo = _repo_root()
    result = subprocess.run(
        ["git", "-C", str(repo), "pull", "--ff-only"],
        capture_output=True,
        text=True,
    )
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    _save_update_log(output)

    state = _classify_update(output, result.returncode)
    if state == "failed":
        print("git pull failed.", file=sys.stderr)
        _notify_group(output or "git pull failed")
        return 1

    _notify_group(output)

    if state == "up-to-date":
        print("Already up to date. No restart.")
        return 0

    pid = _read_pid()
    if pid is not None and _is_alive(pid):
        print(f"Stopping running bot (PID {pid})...")
        _terminate_and_wait(pid)
        new_pid = _relaunch()
        print(f"Updated and restarted (PID {new_pid}). Log: {data_dir() / 'nfb.log'}")
    else:
        print("Updated. Bot is not running; start it with `nfb run`.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "setup":
        return cmd_setup()
    if args.command == "run":
        return cmd_run()
    if args.command == "update":
        return cmd_update()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
