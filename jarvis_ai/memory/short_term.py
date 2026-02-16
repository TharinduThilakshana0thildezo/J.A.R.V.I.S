from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ShortTermMemory:
    items: List[str] = field(default_factory=list)

    def add(self, text: str) -> None:
        self.items.append(text)

    def recent(self, limit: int = 5) -> List[str]:
        if limit <= 0:
            return []
        return self.items[-limit:]

    def clear(self) -> None:
        self.items.clear()
