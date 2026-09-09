"""Command-line entry point for nanoFinBot."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from nanofinbot import __version__
from nanofinbot.config import Config, ConfigError, config_dir, load_config, save_config


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

    asyncio.run(bot_main(cfg))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "setup":
        return cmd_setup()
    if args.command == "run":
        return cmd_run()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
