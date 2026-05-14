#!/usr/bin/env python3
"""Fail if common local secret files or token-like values are committed."""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}

BANNED_PATH_PARTS = {
    ".claude",
    ".codex",
    ".storage",
}

BANNED_FILENAMES = {
    "CLAUDE.md",
    "known_devices.yaml",
    "secrets.yaml",
}

BANNED_SUFFIXES = {
    ".key",
    ".pem",
    ".p12",
}

SECRET_PATTERNS = {
    "OpenAI API key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "Private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "Bearer token literal": re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}\b"),
}


def main() -> int:
    failures: list[str] = []
    for path in iter_files(ROOT):
        rel = path.relative_to(ROOT)
        if is_banned_path(path):
            failures.append(f"banned file: {rel}")
            continue
        text = read_text(path)
        if text is None:
            continue
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                failures.append(f"{name}: {rel}")

    if failures:
        print("Potential secrets or local-only files found:", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    return 0


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            files.append(path)
    return files


def is_banned_path(path: Path) -> bool:
    if any(part in BANNED_PATH_PARTS for part in path.relative_to(ROOT).parts):
        return True
    name = path.name
    if name in BANNED_FILENAMES:
        return True
    if name.startswith(".env") and name != ".env.example":
        return True
    return path.suffix in BANNED_SUFFIXES


def read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="ignore")


if __name__ == "__main__":
    raise SystemExit(main())
