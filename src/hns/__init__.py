"""
hns package initializer
───────────────────────
• Exposes public API shortcuts
• Provides a robust semantic-version helper
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from .fs import hide, is_hidden, revert_last_change as revert, seek

try:
    # When installed with pip this is the canonical version
    __version__: str = _pkg_version(__name__)
except PackageNotFoundError:  # pragma: no cover
    # Editable checkout or unknown state
    __version__ = "0.0.0.dev0"


def get_version() -> str:
    """Return the current Hide N’ Seek version string."""
    return __version__


__all__ = [
    "hide",
    "seek",
    "revert",
    "is_hidden",
    "get_version",
    "__version__",
]
