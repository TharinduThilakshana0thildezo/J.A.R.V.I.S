from __future__ import annotations

import os
import subprocess
from typing import Iterable, Optional

from jarvis_ai.memory.logs import Logger
from jarvis_ai.tools.safety import is_allowed_app, require_confirmation


def open_app(
    app_name: str,
    allowlist: Iterable[str],
    require_confirm: bool = True,
    logger: Optional[Logger] = None,
) -> None:
    if not is_allowed_app(app_name, allowlist):
        raise PermissionError(f"App not in allowlist: {app_name}")
    if require_confirm and not require_confirmation(f"open app {app_name}"):
        raise PermissionError("User denied app launch")

    try:
        if os.path.exists(app_name):
            os.startfile(app_name)
        else:
            subprocess.Popen(app_name, shell=True)
        if logger:
            logger.log(task=f"open_app {app_name}", decision="open_app", outcome="success")
    except Exception as exc:
        if logger:
            logger.log(task=f"open_app {app_name}", decision="open_app", outcome="failed", error=str(exc))
        raise
