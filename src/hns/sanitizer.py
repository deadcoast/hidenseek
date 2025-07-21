"""
hns/sanitizer.py
────────────────
File Sanitizer core for Hide N’ Seek.

Capabilities
============
• rename  :  keep original name *or* sanitise to `[NNN_DDMMYY]`
• sort    :  by file-type, by date, or both (type/date hierarchy)
• cleanup :  remove empty dirs after processing
• recursive: walk sub-directories
• dry-run :  preview every move without touching disk
• undo    :  revert the most-recent sanitisation

Implementation notes
--------------------
• History log appended to same ~/.hns_history.json used by fs.py
  Entries are tagged "sanitize" for clear separation.
• “Date” sorting uses file’s **creation time** (Unix `st_ctime`)
  unless *keep_date_saved* is True, in which case it uses “saved”
  (modification) time.
• Works on macOS, Linux, Windows with pathlib + shutil.
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence

HISTORY_FILE = Path.home() / ".hns_history.json"
TODAY = datetime.now().strftime("%d%m%y")


# --------------------------------------------------------------------------- #
# Dataclasses – options & history
# --------------------------------------------------------------------------- #


@dataclass
class SanitizerOptions:
    # Naming
    sani_name: bool = False  # rename to [NNN_DDMMYY]
    # Sorting
    sort_by_type: bool = False
    sort_by_date: bool = False
    # Metadata
    keep_date_saved: bool = False  # mod-time
    keep_date_created: bool = False  # c-time
    # Behaviour
    recursive: bool = False
    cleanup_empty: bool = False
    dry_run: bool = False


@dataclass
class _Move:
    src: str
    dst: str


@dataclass
class _HistoryEntry:
    timestamp: float
    op: str  # "sanitize"
    root: str
    moves: List[_Move]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def sanitize(root: str | Path, opts: SanitizerOptions) -> None:
    """
    Perform sanitisation on *root* according to *opts*.

    Raises
    ------
    FileNotFoundError
        If the root path does not exist.
    RuntimeError
        If conflicting options are provided.
    """
    path = Path(root).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    # Collect targets
    files = _gather_files(path, opts.recursive)
    if not files:
        return  # nothing to do

    moves: List[_Move] = []
    for file in files:
        dst = _target_path(file, path, opts)
        if dst == file:
            continue
        moves.append(_Move(str(file), str(dst)))

    # Execute (or preview)
    for mv in moves:
        _apply_move(Path(mv.src), Path(mv.dst), opts.dry_run)

    # Cleanup empties
    if opts.cleanup_empty:
        _cleanup_empty_dirs(path, opts.dry_run)

    # Record history
    if not opts.dry_run and moves:
        _record_history(_HistoryEntry(time.time(), "sanitize", str(path), moves))


def revert_last_sanitize(dry_run: bool = False) -> None:
    """Undo the most recent sanitise action."""
    entries = _load_history()
    if not entries:
        raise RuntimeError("No history available.")
    last_idx = max(i for i, e in enumerate(entries) if e["op"] == "sanitize")
    entry = entries.pop(last_idx)
    for mv in reversed(entry["moves"]):  # reverse order
        _apply_move(Path(mv["dst"]), Path(mv["src"]), dry_run)
    if not dry_run:
        _save_history(entries)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _gather_files(root: Path, recursive: bool) -> Sequence[Path]:
    if recursive:
        return [p for p in root.rglob("*") if p.is_file()]
    return [p for p in root.iterdir() if p.is_file()]


def _target_path(file: Path, root: Path, opts: SanitizerOptions) -> Path:
    """Compute destination path for *file* according to options."""
    # Determine base folder (sorting)
    base = root
    if opts.sort_by_type:
        base = base / file.suffix.lstrip(".").lower()
    if opts.sort_by_date:
        dt = _file_date(file, opts)
        date_folder = dt.strftime("%Y-%m-%d")
        base = base / date_folder if opts.sort_by_type else base / date_folder

    # Determine filename
    if opts.sani_name:
        rand = f"{random.randint(0, 999):03d}"
        new_name = f"{rand}_{TODAY}{file.suffix.lower()}"
    else:
        new_name = file.name

    return base / new_name


def _file_date(file: Path, opts: SanitizerOptions) -> datetime:
    stat = file.stat()
    if opts.keep_date_saved:
        ts = stat.st_mtime
    else:
        ts = stat.st_ctime
    return datetime.fromtimestamp(ts)


def _apply_move(src: Path, dst: Path, dry_run: bool) -> None:
    if dry_run:
        print("[DRY-RUN]", src, "→", dst)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst = _unique_path(dst)
    src.rename(dst)


def _unique_path(path: Path) -> Path:
    """Ensure *path* is unique, appending _1, _2 … if needed."""
    counter = 1
    candidate = path
    while candidate.exists():
        candidate = path.with_stem(f"{path.stem}_{counter}")
        counter += 1
    return candidate


def _cleanup_empty_dirs(root: Path, dry_run: bool) -> None:
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        p = Path(dirpath)
        if p == root:
            continue
        if not dirnames and not filenames:
            if dry_run:
                print("[DRY-RUN] rmdir", p)
            else:
                p.rmdir()


# --------------------------------------------------------------------------- #
# History persistence (shared with fs.py)
# --------------------------------------------------------------------------- #


def _load_history() -> List[Dict[str, Any]]:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return []


def _save_history(entries: List[Dict[str, Any]]) -> None:
    HISTORY_FILE.write_text(json.dumps(entries, indent=2))


def _record_history(entry: _HistoryEntry) -> None:
    entries = _load_history()
    entries.append(asdict(entry))
    _save_history(entries)
