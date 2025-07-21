"""
hns/sanitizer_menu.py
─────────────────────
Interactive Rich menu for the File Sanitizer module.

• Uses SanitizerOptions (from sanitizer.py) to build a job definition
• ANSI icon spec:
    ●  ON-icon
    ▶  Option has sub-options
    ↔  Sub-option separator (visual only)
    🔒  Lock (forces parent OFF, disables toggles)
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .sanitizer import SanitizerOptions, revert_last_sanitize, sanitize

console = Console(highlight=False)

ON = "●"
ARROW = "▶"
SEP = "↔"
LOCK = "🔒"


# --------------------------------------------------------------------------- #
# Small state wrapper
# --------------------------------------------------------------------------- #


class _State:
    """Holds all toggleable flags for the interactive session."""

    # Meta – FileName
    sani_name: bool = False
    fname_lock: bool = False
    # Meta – Date
    date_saved: bool = False
    date_created: bool = False
    date_lock: bool = False
    # Master toggle
    complete_sanitize: bool = False
    recursive: bool = False

    # SaniSort
    sort_filetype: bool = False
    sort_date: bool = False
    sort_recursive: bool = False
    cleanup: bool = False
    sort_lock: bool = False  # part of master menu

    def to_opts(self) -> SanitizerOptions:
        """Convert current flags to SanitizerOptions for the backend."""
        if self.complete_sanitize:
            # strict preset
            return SanitizerOptions(
                sani_name=True,
                sort_by_type=True,
                sort_by_date=True,
                recursive=True,
                cleanup_empty=True,
            )
        return SanitizerOptions(
            sani_name=bool(self.sani_name and not self.fname_lock),
            sort_by_type=bool(self.sort_filetype and not self.sort_lock),
            sort_by_date=bool(self.sort_date and not self.sort_lock),
            recursive=bool(self.recursive or self.sort_recursive),
            cleanup_empty=bool(self.cleanup),
            keep_date_saved=self.date_saved and not self.date_lock,
            keep_date_created=self.date_created and not self.date_lock,
        )


S = _State()  # session-global


# --------------------------------------------------------------------------- #
# Helper renderers
# --------------------------------------------------------------------------- #


def _box(flag: bool) -> str:
    return f"[{ON}]" if flag else "[ ]"


def _option_icon(has_sub: bool, locked: bool, active: bool) -> str:
    if locked:
        return f"[{LOCK}]"
    if has_sub:
        return f"[{ARROW}]"
    return _box(active)


# --------------------------------------------------------------------------- #
# Menu entry-point
# --------------------------------------------------------------------------- #


def launch_sanitizer_menu() -> None:
    """Top-level File Sanitizer main menu loop."""
    while True:
        console.clear()
        console.print(Panel.fit("[bold cyan]File Sanitizer – MainMenu[/]"))
        console.print(
            "Press [bold]Enter[/] to provide a folder path for sanitisation\n"
            "or select an option below."
        )
        tbl = Table(show_header=False)
        tbl.add_row("[1]", "Metadata Options")
        tbl.add_row("[2]", "SaniSort Options")
        tbl.add_row("[3]", "Master Options")
        tbl.add_row("[u]", "Undo last sanitise")
        tbl.add_row("[q]", "Quit")
        console.print(tbl)

        choice = Prompt.ask("> ").strip().lower()
        if choice == "":
            _run_sanitiser()
        elif choice == "1":
            _metadata_menu()
        elif choice == "2":
            _sanisort_menu()
        elif choice == "3":
            _master_menu()
        elif choice == "u":
            _undo()
        elif choice == "q":
            break


# --------------------------------------------------------------------------- #
# Sub-menus
# --------------------------------------------------------------------------- #


def _metadata_menu() -> None:
    while True:
        console.clear()
        console.print(Panel.fit("[bold green]MetaData – Options[/]"))
        tbl = Table(show_header=False)
        # FileName row
        fname_active = S.sani_name
        fname_icon = _option_icon(True, S.fname_lock, fname_active)
        tbl.add_row(
            "[1]",
            f"{fname_icon}FileName: {_box(S.sani_name)}SaniName {SEP} {_box(S.fname_lock)}Lock",
        )
        # Date row
        date_any = S.date_saved or S.date_created
        date_icon = _option_icon(True, S.date_lock, date_any)
        tbl.add_row(
            "[2]",
            f"{date_icon}Date: {_box(S.date_saved)}Saved {SEP} "
            f"{_box(S.date_created)}Created {SEP} {_box(S.date_lock)}Lock",
        )
        tbl.add_row("[3]", f"{_box(S.complete_sanitize)}CompleteSanitize")
        tbl.add_row("[q]", "Back")
        console.print(tbl)

        choice = Prompt.ask("> ").strip().lower()
        if choice == "1":
            _toggle_fname_sub()
        elif choice == "2":
            _toggle_date_sub()
        elif choice == "3":
            S.complete_sanitize = not S.complete_sanitize
        elif choice == "q":
            break


def _toggle_fname_sub() -> None:
    while True:
        console.clear()
        console.print(Panel.fit("[bold]FileName Options[/]"))
        tbl = Table(show_header=False)
        tbl.add_row("[1]", f"{_box(S.sani_name)}SaniName")
        tbl.add_row("[2]", f"{_box(S.fname_lock)}Lock")
        tbl.add_row("[q]", "Back")
        console.print(tbl)
        choice = Prompt.ask("> ").strip().lower()
        if choice == "1" and not S.fname_lock:
            S.sani_name = not S.sani_name
        elif choice == "2":
            S.fname_lock = not S.fname_lock
            if S.fname_lock:
                S.sani_name = False
        elif choice == "q":
            break


def _toggle_date_sub() -> None:
    while True:
        console.clear()
        console.print(Panel.fit("[bold]Date Options[/]"))
        tbl = Table(show_header=False)
        tbl.add_row("[1]", f"{_box(S.date_saved)}Saved")
        tbl.add_row("[2]", f"{_box(S.date_created)}Created")
        tbl.add_row("[3]", f"{_box(S.date_lock)}Lock")
        tbl.add_row("[q]", "Back")
        console.print(tbl)
        choice = Prompt.ask("> ").strip().lower()
        if choice == "1" and not S.date_lock:
            S.date_saved = not S.date_saved
        elif choice == "2" and not S.date_lock:
            S.date_created = not S.date_created
        elif choice == "3":
            S.date_lock = not S.date_lock
            if S.date_lock:
                S.date_saved = S.date_created = False
        elif choice == "q":
            break


def _sanisort_menu() -> None:
    while True:
        console.clear()
        console.print(Panel.fit("[bold yellow]SaniSort – Options[/]"))
        sort_any = S.sort_filetype or S.sort_date
        sort_icon = _option_icon(True, S.sort_lock, sort_any)
        tbl = Table(show_header=False)
        tbl.add_row(
            "[1]",
            f"{sort_icon}Sort: {_box(S.sort_filetype)}FileType {SEP} " f"{_box(S.sort_date)}Date",
        )
        tbl.add_row("[2]", f"{_box(S.sort_recursive)}Recursive")
        tbl.add_row("[3]", f"{_box(S.cleanup)}Cleanup")
        tbl.add_row("[q]", "Back")
        console.print(tbl)

        choice = Prompt.ask("> ").strip().lower()
        if choice == "1":
            _toggle_sort_sub()
        elif choice == "2":
            S.sort_recursive = not S.sort_recursive
        elif choice == "3":
            S.cleanup = not S.cleanup
        elif choice == "q":
            break


def _toggle_sort_sub() -> None:
    while True:
        console.clear()
        console.print(Panel.fit("[bold]Sort Options[/]"))
        tbl = Table(show_header=False)
        tbl.add_row("[1]", f"{_box(S.sort_filetype)}FileType")
        tbl.add_row("[2]", f"{_box(S.sort_date)}Date")
        tbl.add_row("[3]", f"{_box(S.sort_lock)}Lock")
        tbl.add_row("[q]", "Back")
        console.print(tbl)
        choice = Prompt.ask("> ").strip().lower()
        if choice == "1" and not S.sort_lock:
            S.sort_filetype = not S.sort_filetype
        elif choice == "2" and not S.sort_lock:
            S.sort_date = not S.sort_date
        elif choice == "3":
            S.sort_lock = not S.sort_lock
            if S.sort_lock:
                S.sort_filetype = S.sort_date = False
        elif choice == "q":
            break


def _master_menu() -> None:
    """Read-only dashboard & a place for quick global toggles."""
    while True:
        console.clear()
        console.print(Panel.fit("[bold magenta]MasterMenu – Overview[/]"))

        tbl = Table(show_header=False)
        tbl.add_row("MetaData Options", "")
        tbl.add_row(
            "  FileName",
            f"{_box(S.sani_name)}SaniName {SEP} {_box(S.fname_lock)}Lock",
        )
        tbl.add_row(
            "  Date",
            f"{_box(S.date_saved)}Saved {SEP} {_box(S.date_created)}Created "
            f"{SEP} {_box(S.date_lock)}Lock",
        )
        tbl.add_row("  Recursive", _box(S.recursive))
        tbl.add_row("  CompleteSanitize", _box(S.complete_sanitize))
        tbl.add_row("", "")  # spacer
        tbl.add_row("SaniSort Options", "")
        tbl.add_row(
            "  Sort",
            f"{_box(S.sort_filetype)}FileType {SEP} {_box(S.sort_date)}Date",
        )
        tbl.add_row("  Recursive", _box(S.sort_recursive))
        tbl.add_row("  Cleanup", _box(S.cleanup))
        tbl.add_row("[q]", "Back")
        console.print(tbl)
        if Prompt.ask("> ").strip().lower() == "q":
            break


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #


def _run_sanitiser() -> None:
    folder = Prompt.ask("Folder path", default=str(Path.cwd())).strip()
    if not folder:
        return
    opts = S.to_opts()
    try:
        sanitize(folder, opts)
        console.print("[green]✔ Sanitisation completed.[/]")
    except Exception as exc:
        console.print(f"[red]Error:[/] {exc}")
    input("Press Enter to continue…")


def _undo() -> None:
    try:
        revert_last_sanitize()
        console.print("[green]✔ Reverted last sanitise.[/]")
    except Exception as exc:
        console.print(f"[red]Error:[/] {exc}")
    input("Press Enter to continue…")
