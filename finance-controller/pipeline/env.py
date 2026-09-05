"""Minimal .env loader -- no new dependency for one small feature.

Reads a `.env` file at the project root (if present) into os.environ, without
overwriting anything already set in the real environment. `.env` is never
read by report/README generation and must never be committed or printed.
"""
from __future__ import annotations

import os
from pathlib import Path

_LOADED = False


def load_dotenv_if_present() -> None:
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value
