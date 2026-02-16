from __future__ import annotations

from pathlib import Path
from typing import Optional

from jarvis_ai.memory.logs import Logger
from jarvis_ai.tools.safety import is_path_allowed, require_confirmation


def read_text(path: Path, root: Path, require_confirm: bool = True, logger: Optional[Logger] = None) -> str:
    if not is_path_allowed(path, root):
        raise PermissionError(f"Path not allowed: {path}")
    if require_confirm and not require_confirmation(f"read file {path}"):
        raise PermissionError("User denied file read")
    try:
        content = path.read_text(encoding="utf-8")
        if logger:
            logger.log(task=f"read_text {path}", decision="read_text", outcome="success")
        return content
    except Exception as exc:
        if logger:
            logger.log(task=f"read_text {path}", decision="read_text", outcome="failed", error=str(exc))
        raise


def write_text(path: Path, text: str, root: Path, require_confirm: bool = True, logger: Optional[Logger] = None) -> None:
    if not is_path_allowed(path, root):
        raise PermissionError(f"Path not allowed: {path}")
    if require_confirm and not require_confirmation(f"write file {path}"):
        raise PermissionError("User denied file write")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if logger:
            logger.log(task=f"write_text {path}", decision="write_text", outcome="success")
    except Exception as exc:
        if logger:
            logger.log(task=f"write_text {path}", decision="write_text", outcome="failed", error=str(exc))
        raise
