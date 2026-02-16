from __future__ import annotations

from pathlib import Path
from typing import Iterable


def require_confirmation(action: str) -> bool:
    reply = input(f"Confirm action '{action}'? [y/N]: ")
    return reply.strip().lower() in {"y", "yes"}


def is_allowed_app(app_name: str, allowlist: Iterable[str]) -> bool:
    normalized = app_name.strip().lower()
    allowed = {item.strip().lower() for item in allowlist if item.strip()}
    if not allowed:
        return False
    return normalized in allowed


def is_path_allowed(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve()
        root_resolved = root.resolve()
    except Exception:
        return False
    return root_resolved in resolved.parents or resolved == root_resolved
