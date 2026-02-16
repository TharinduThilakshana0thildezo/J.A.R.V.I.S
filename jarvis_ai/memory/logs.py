from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class ActionLog:
    task: str
    decision: str
    outcome: str
    error: Optional[str]
    timestamp: str


class Logger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def log(self, task: str, decision: str, outcome: str, error: Optional[str] = None) -> None:
        entry = ActionLog(
            task=task,
            decision=decision,
            outcome=outcome,
            error=error,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.__dict__) + "\n")
