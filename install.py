#!/usr/bin/env python3
"""Install nanoFinBot.

Creates a virtualenv in a stable per-user location, installs the package in
editable mode (so `git pull` updates are picked up automatically), and puts an
`nfb` launcher on the user PATH. Uses only the standard library.
"""

from __future__ import annotations

import os
import shlex
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
    target = venv_script(venv, "nfb")

    if sys.platform == "win32":
        launcher = bin_dir / "nfb.cmd"
        escaped = str(target).replace("%", "%%")
        content = f'@echo off\r\n"{escaped}" %*\r\n'
        launcher.write_text(content, encoding="utf-8")
    else:
        launcher = bin_dir / "nfb"
        content = f'#!/bin/sh\nexec {shlex.quote(str(target))} "$@"\n'
        launcher.write_text(content, encoding="utf-8")
        launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return launcher


def ensure_on_path(bin_dir: Path) -> None:
    """Add the user bin dir to PATH persistently (POSIX). No-op on Windows."""
    if sys.platform == "win32":
        return
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    if str(bin_dir) in path_entries:
        return
    profile = Path.home() / ".profile"
    line = f'export PATH="{bin_dir}:$PATH"'
    try:
        existing = profile.read_text(encoding="utf-8") if profile.exists() else ""
    except OSError:
        return
    if line in existing:
        return
    try:
        with open(profile, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(line + "\n")
    except OSError:
        pass


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
    bin_dir = user_bin_dir()
    ensure_on_path(bin_dir)

    print()
    print("nanoFinBot installed.")
    print(f"  venv:     {venv}")
    print(f"  launcher: {launcher}")
    print()
    if sys.platform == "win32":
        print(f"Add this directory to PATH, then open a new terminal:")
        print(f"  setx PATH \"%PATH%;{bin_dir}\"")
    elif str(bin_dir) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"Added {bin_dir} to ~/.profile. Open a new shell, or run:")
        print(f"  export PATH=\"{bin_dir}:$PATH\"")
    print()
    print("  nfb setup    # configure bot token and group")
    print("  nfb run      # start the bot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
