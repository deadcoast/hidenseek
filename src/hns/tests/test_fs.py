"""
pytest suite for hns.fs
───────────────────────
Ensures hide/seek/revert logic functions and the
dry-run flag leaves the filesystem untouched.
"""

from __future__ import annotations

import platform
from pathlib import Path

import pytest

from hns import fs


def _hidden_variant(path: Path) -> Path:
    """
    Return the pathname that *fs.hide()* would create on this OS.
    Only relevant for Linux (dot-prefix strategy).
    """
    system = platform.system()
    if system == "Linux":
        return path.with_name(f".{path.name}")
    return path


@pytest.mark.parametrize("recursive", (False, True))
def test_hide_seek_revert(tmp_path: Path, recursive: bool) -> None:
    # tmp_path = /private/var/…/pytest-…  (unique per test)
    root = tmp_path / "demo"
    sub = root / "child"
    sub.mkdir(parents=True)

    # 1. Hide
    fs.hide(root, recursive=recursive)
    root_hidden_path = _hidden_variant(root)
    assert fs.is_hidden(root_hidden_path)
    if recursive:
        assert fs.is_hidden(_hidden_variant(sub))
    else:
        # sub should remain visible when recursion is off
        assert not fs.is_hidden(sub)

    # 2. Seek (non-recursive for this step)
    fs.seek(root_hidden_path, recursive=False)
    root_visible_path = root_hidden_path if platform.system() != "Linux" else root
    assert not fs.is_hidden(root_visible_path)

    # 3. Undo
    fs.revert_last_change()
    assert fs.is_hidden(_hidden_variant(root_visible_path))

    # 4. Seek recursive → fully visible again
    fs.seek(_hidden_variant(root_visible_path), recursive=True)
    assert not fs.is_hidden(root_visible_path)
    assert not fs.is_hidden(sub)


def test_dry_run_leaves_filesystem_untouched(tmp_path: Path) -> None:
    path = tmp_path / "drydemo"
    path.mkdir()

    fs.hide(path, recursive=True, dry_run=True)
    # On Linux the folder would *not* be renamed in dry-run mode
    assert path.exists()
    assert not fs.is_hidden(path)
