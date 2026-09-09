#!/usr/bin/env python3
"""Install nanoFinBot.

Creates a virtualenv in a stable per-user location, installs the package in
editable mode (so `git pull` updates are picked up automatically), and puts an
`nfb` launcher on the user PATH. Uses only the standard library.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

APP = "nfb"


def data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or Path.home()
        return Path(base) / APP
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / APP
    return Path.home() / ".local" / "share" / APP


def user_bin_dir() -> Path:
    if sys.platform == "win32":
        return data_dir() / "bin"
    return Path.home() / ".local" / "bin"


def venv_python(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def venv_script(venv: Path, name: str) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / (name + ".exe")
    return venv / "bin" / name


def run(cmd: list[str]) -> None:
    print(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def write_launcher(venv: Path) -> Path:
    bin_dir = user_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        launcher = bin_dir / "nfb.cmd"
        content = f'@echo off\r\n"{venv_script(venv, "nfb")}" %*\r\n'
        launcher.write_text(content, encoding="utf-8")
    else:
        launcher = bin_dir / "nfb"
        content = f'#!/bin/sh\nexec "{venv_script(venv, "nfb")}" "$@"\n'
        launcher.write_text(content, encoding="utf-8")
        launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return launcher


def main() -> int:
    repo = Path(__file__).resolve().parent
    venv = data_dir() / "venv"
    python = venv_python(venv)

    if not python.exists():
        print(f"Creating virtualenv at {venv}")
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)

    run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python), "-m", "pip", "install", "-e", str(repo)])

    launcher = write_launcher(venv)

    print()
    print("nanoFinBot installed.")
    print(f"  venv:     {venv}")
    print(f"  launcher: {launcher}")
    print()
    print("Make sure the bin directory is on your PATH, then run:")
    print("  nfb setup    # configure bot token and group")
    print("  nfb run      # start the bot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
