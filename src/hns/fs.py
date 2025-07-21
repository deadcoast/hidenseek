"""
hns/fs.py
─────────
Core filesystem helpers for Hide N’ Seek Directory Manager.

✓ macOS: uses   chflags (hidden / nohidden)
✓ Linux: renames folder → dot-prefixed   (.foo)   and back              [simple, portable]
✓ Windows: uses  attrib  +h /-h  with  /s /d  for recursion

Features
--------
• hide(path, recursive=False, dry_run=False)  – hide the folder
• seek(path, recursive=False, dry_run=False)  – reveal the folder
• revert_last_change()                        – undo the most recent hide/seek
• is_hidden(path)                             – best-effort check
• History log:  ~/.hns_history.json           – stores every action

Exceptions are raised on failure so the CLI can surface them nicely.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

# --------------------------------------------------------------------------- #
# Constants & helpers
# --------------------------------------------------------------------------- #

SYSTEM = platform.system()  # 'Darwin', 'Linux', 'Windows'
HISTORY_FILE = Path.home() / ".hns_history.json"


@dataclass
class Action:
    """Represents one hide/seek operation for undo purposes."""

    timestamp: float
    path: str
    op: str  # 'hide' or 'seek'
    recursive: bool

    def inverse(self) -> "Action":
        return Action(
            timestamp=time.time(),
            path=self.path,
            op="seek" if self.op == "hide" else "hide",
            recursive=self.recursive,
        )


# --------------------------------------------------------------------------- #
# History handling
# --------------------------------------------------------------------------- #


def _load_history() -> List[Dict[str, Any]]:
    if HISTORY_FILE.exists():
        with HISTORY_FILE.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    return []


def _save_history(entries: List[Dict[str, Any]]) -> None:
    HISTORY_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _record_action(action: Action) -> None:
    entries = _load_history()
    entries.append(asdict(action))
    _save_history(entries)


def revert_last_change(dry_run: bool = False) -> None:
    """
    Undo the last hide/seek action.

    Raises
    ------
    RuntimeError
        If there is no history to revert.
    """
    entries = _load_history()
    if not entries:
        raise RuntimeError("No actions to revert.")
    last = Action(**entries.pop())
    inverse = last.inverse()

    # Perform inverse operation
    _dispatch(inverse, dry_run=dry_run)

    # Pop the reverted action off history only if it succeeded
    if not dry_run:
        _save_history(entries)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def hide(path: str | Path, recursive: bool = False, dry_run: bool = False) -> None:
    """Hide *path*."""
    _dispatch(Action(time.time(), str(path), "hide", recursive), dry_run=dry_run)


def seek(path: str | Path, recursive: bool = False, dry_run: bool = False) -> None:
    """Reveal *path*."""
    _dispatch(Action(time.time(), str(path), "seek", recursive), dry_run=dry_run)


def is_hidden(path: str | Path) -> bool:
    """
    Best-effort hidden check (not 100 % fool-proof, but fast).

    • macOS   – checks chflags output for 'hidden'
    • Linux   – leading '.' in name
    • Windows – attrib output contains 'H'
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)

    if SYSTEM == "Darwin":
        result = subprocess.run(
            ["ls", "-ldO", str(p)],
            capture_output=True,
            text=True,
            check=True,
        )
        return "hidden" in result.stdout.split()
    elif SYSTEM == "Linux":
        return p.name.startswith(".")
    elif SYSTEM == "Windows":
        result = subprocess.run(
            ["attrib", str(p)],
            capture_output=True,
            text=True,
            check=True,
        )
        return " H " in result.stdout or result.stdout.rstrip().endswith("H")
    return False  # Fallback


# --------------------------------------------------------------------------- #
# Internal dispatch
# --------------------------------------------------------------------------- #


def _dispatch(action: Action, dry_run: bool = False) -> None:
    if SYSTEM == "Darwin":
        _macos(action, dry_run)
    elif SYSTEM == "Linux":
        _linux(action, dry_run)
    elif SYSTEM == "Windows":
        _windows(action, dry_run)
    else:
        raise NotImplementedError(f"Unsupported OS: {SYSTEM}")

    if not dry_run:
        _record_action(action)


# --------------------------------------------------------------------------- #
# OS-specific implementations
# --------------------------------------------------------------------------- #


def _macos(action: Action, dry_run: bool) -> None:
    flag = "hidden" if action.op == "hide" else "nohidden"
    cmd = ["chflags"]
    if action.recursive:
        cmd.append("-R")
    cmd.extend([flag, action.path])
    _run(cmd, dry_run)


def _linux(action: Action, dry_run: bool) -> None:
    """
    Portable solution: rename folder → .name  (hide)  or remove dot (seek).

    Recursive rename is trickier; we *mirror* behaviour:
    • If recursive=True, operate on all sub-folders too.
    """
    p = Path(action.path)
    if not p.exists():
        raise FileNotFoundError(action.path)

    if action.op == "hide":
        _linux_hide_path(p, dry_run)
        if action.recursive:
            for sub in _descend_dirs(p):
                _linux_hide_path(sub, dry_run)
    else:
        _linux_seek_path(p, dry_run)
        if action.recursive:
            for sub in _descend_dirs(p):
                _linux_seek_path(sub, dry_run)


def _linux_hide_path(path: Path, dry_run: bool) -> None:
    if path.name.startswith("."):
        return  # already hidden
    target = path.with_name(f".{path.name}")
    _run(["mv", str(path), str(target)], dry_run)


def _linux_seek_path(path: Path, dry_run: bool) -> None:
    if not path.name.startswith("."):
        return  # already visible
    target = path.with_name(path.name.lstrip("."))
    _run(["mv", str(path), str(target)], dry_run)


def _descend_dirs(root: Path) -> List[Path]:
    return [d for d, _, _ in os.walk(root)][1:]  # skip root itself


def _windows(action: Action, dry_run: bool) -> None:
    flag = "+h" if action.op == "hide" else "-h"
    cmd = ["attrib", flag]
    if action.recursive:
        cmd.extend(["/s", "/d"])
    cmd.append(str(action.path))
    _run(cmd, dry_run)


# --------------------------------------------------------------------------- #
# Utility
# --------------------------------------------------------------------------- #


def _run(cmd: List[str], dry_run: bool) -> None:
    if dry_run:
        print("[DRY-RUN]", " ".join(cmd))
        return
    subprocess.run(cmd, check=True)


# --------------------------------------------------------------------------- #
# Self-test (optional)
# --------------------------------------------------------------------------- #

if __name__ == "__main__" and "--demo" in sys.argv:
    """Quick demo:  python -m hns.fs --demo /tmp/foo"""
    try:
        demo_path = Path(sys.argv[-1])
        demo_path.mkdir(exist_ok=True)
        print("Hiding …")
        hide(demo_path, recursive=True, dry_run=False)
        print("Hidden?", is_hidden(demo_path))
        print("Seeking …")
        seek(demo_path, recursive=True, dry_run=False)
        print("Hidden?", is_hidden(demo_path))
        print("Reverting last action …")
        revert_last_change()
        print("Hidden?", is_hidden(demo_path))
    except Exception as exc:
        print("Error:", exc)
