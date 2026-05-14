"""Compatibility helpers for Home Assistant version checks."""

from __future__ import annotations

import re


def version_at_least(current: str, minimum: str) -> bool:
    """Compare Home Assistant versions without adding runtime dependencies."""
    return _version_tuple(current) >= _version_tuple(minimum)


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        return (0, 0, 0)
    return tuple(int(part) for part in match.groups())
