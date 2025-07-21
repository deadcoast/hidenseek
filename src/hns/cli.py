"""
hns/cli.py
──────────
Hide N' Seek Directory Manager – interactive Rich CLI powered by Typer.

Usage
-----
$ hns                              # open interactive menu
$ hns /path/to/folder --hide       # one-shot hide
$ hns /path/to/folder --seek       # one-shot seek
$ hns --help                       # full CLI help

Menus
-----
Main, Hide, Seek, Config – all keyboard-driven with simple number keys.

Config persistence
------------------
~/.hns_config.json keeps:
• default_path
• recursive_global_hide
• recursive_global_seek
• dry_run
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from . import fs
from .sanitizer_menu import launch_sanitizer_menu

# --------------------------------------------------------------------------- #
# Typer app set-up
# --------------------------------------------------------------------------- #

app = typer.Typer(
    help="Hide N' Seek – hide or reveal folders (interactive when no args).",
    add_completion=False,
)

console = Console(highlight=False)
ON = "●"
OFF = "○"

# --------------------------------------------------------------------------- #
# Configuration handling
# --------------------------------------------------------------------------- #

CONFIG_FILE = Path.home() / ".hns_config.json"


@dataclass
class Config:
    default_path: Optional[str] = None
    recursive_global_hide: bool = False
    recursive_global_seek: bool = True
    dry_run: bool = False

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                return cls(**data)
            except Exception:  # pragma: no cover
                pass  # fall through to default
        return cls()

    def save(self) -> None:
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2))


cfg = Config.load()

# --------------------------------------------------------------------------- #
# CLI – non-interactive one-shot mode
# --------------------------------------------------------------------------- #


@app.callback(invoke_without_command=True)
def _entrypoint(
    ctx: typer.Context,
    path: Optional[Path] = typer.Argument(
        None,
        exists=False,
        dir_okay=True,
        file_okay=False,
        resolve_path=True,
        metavar="PATH",
    ),
    hide: bool = typer.Option(False, "--hide", help="Hide the folder at PATH"),
    seek: bool = typer.Option(False, "--seek", help="Reveal the folder at PATH"),
    recursive: bool = typer.Option(
        None,
        "--recursive/--no-recursive",
        help="Override recursive behaviour for this command only",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Stage the changes without applying them",
    ),
) -> None:
    """
    When PATH + flag(s) are supplied, perform the action directly.
    Otherwise, drop into the interactive Rich menu.
    """
    if path and (hide ^ seek):  # XOR → exactly one flag
        rec = (
            recursive
            if recursive is not None
            else (hide and cfg.recursive_global_hide) or (seek and cfg.recursive_global_seek)
        )
        if hide:
            fs.hide(path, recursive=rec, dry_run=dry_run or cfg.dry_run)
        else:
            fs.seek(path, recursive=rec, dry_run=dry_run or cfg.dry_run)
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        _interactive_menu()


# --------------------------------------------------------------------------- #
# Interactive menus
# --------------------------------------------------------------------------- #


def _interactive_menu() -> None:
    while True:
        console.clear()
        console.print(Panel.fit("[bold cyan]Welcome to Hide N' Seek Directory Manager[/]"))
        table = Table(show_header=False)
        table.add_row("[1]", "Hide")
        table.add_row("[2]", "Seek")
        table.add_row("[3]", "Config")
        table.add_row("[4]", "File Sanitizer")
        table.add_row("[h]", "Help")
        table.add_row("[q]", "Quit")
        console.print(table)

        choice = Prompt.ask("> ").strip().lower()
        if choice == "1":
            _hide_menu()
        elif choice == "2":
            _seek_menu()
        elif choice == "3":
            _config_menu()
        elif choice == "4":
            launch_sanitizer_menu()
        elif choice == "h":
            typer.echo(app.get_help())
            typer.echo("Press Enter to continue…")
            input()
        elif choice == "q":
            sys.exit(0)


def _hide_menu() -> None:
    _operation_menu(
        title="Hide Menu - Hide Folders",
        op="hide",
        cfg_recursive=lambda: cfg.recursive_global_hide,
    )


def _seek_menu() -> None:
    _operation_menu(
        title="Seek Menu - Reveal Folders",
        op="seek",
        cfg_recursive=lambda: cfg.recursive_global_seek,
    )


def _operation_menu(title: str, op: str, cfg_recursive) -> None:
    local_recursive = cfg_recursive()
    local_dry_run = cfg.dry_run
    while True:
        console.clear()
        console.print(Panel.fit(f"[bold green]{title}[/]"))
        default_note = f"(default: {cfg.default_path})" if cfg.default_path else ""
        console.print(f"Press [bold]Enter[/] to provide a folder path {default_note}")
        table = Table(show_header=False)
        table.add_row("[1]", f"[{ON if local_recursive else OFF}] Recursive {op.capitalize()}")
        table.add_row("[2]", f"[{ON if local_dry_run else OFF}] Dry Run")
        table.add_row("[3]", "Config")
        table.add_row("[h]", "Help")
        table.add_row("[q]", "Back: Main Menu")
        console.print(table)

        choice = Prompt.ask("> ").strip().lower()
        if choice == "":
            path = Prompt.ask("Folder path", default=cfg.default_path or "").strip()
            if not path:
                continue
            try:
                kwargs = dict(recursive=local_recursive, dry_run=local_dry_run)
                (fs.hide if op == "hide" else fs.seek)(path, **kwargs)
                console.print("[green]✔ Operation completed.[/]")
            except Exception as exc:
                console.print(f"[red]Error:[/] {exc}")
            input("Press Enter to continue…")
        elif choice == "1":
            local_recursive = not local_recursive
        elif choice == "2":
            local_dry_run = not local_dry_run
        elif choice == "3":
            _config_menu()
        elif choice == "h":
            typer.echo(app.get_help())
            input("Press Enter to continue…")
        elif choice == "q":
            break


def _config_menu() -> None:
    while True:
        console.clear()
        console.print(Panel.fit("[bold magenta]Config Menu - Edit Settings[/]"))
        table = Table(show_header=False)
        table.add_row("[1]", f"Set Path → [bold]{cfg.default_path or 'None'}[/]")
        table.add_row("[2]", "Revert Last Change")
        table.add_row(
            "[3]", f"[{ON if cfg.recursive_global_seek else OFF}] Recursive Seek  [Global]"
        )
        table.add_row(
            "[4]", f"[{ON if cfg.recursive_global_hide else OFF}] Recursive Hide  [Global]"
        )
        table.add_row("[5]", f"[{ON if cfg.dry_run else OFF}] Dry Run")
        table.add_row("[q]", "Back: Main Menu")
        console.print(table)

        choice = Prompt.ask("> ").strip().lower()
        if choice == "1":
            new_path = Prompt.ask(
                "Default folder path (blank to clear)", default=cfg.default_path or ""
            ).strip()
            cfg.default_path = new_path or None
            cfg.save()
        elif choice == "2":
            try:
                fs.revert_last_change(dry_run=cfg.dry_run)
                console.print("[green]✔ Last change reverted.[/]")
            except Exception as exc:
                console.print(f"[red]Error:[/] {exc}")
            input("Press Enter to continue…")
        elif choice == "3":
            cfg.recursive_global_seek = not cfg.recursive_global_seek
            cfg.save()
        elif choice == "4":
            cfg.recursive_global_hide = not cfg.recursive_global_hide
            cfg.save()
        elif choice == "5":
            cfg.dry_run = not cfg.dry_run
            cfg.save()
        elif choice == "q":
            break


# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #


def run() -> None:  # helper for setup.py entry-point
    app()


if __name__ == "__main__":
    run()
