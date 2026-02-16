from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class MemoryEntry:
    entry_id: str
    text: str
    tags: List[str]
    embedding: Dict[str, float]
    timestamp: str


class LongTermMemory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: Dict[str, Any] = {
            "version": 1,
            "preferences": {},
            "entries": [],
            "tasks": [],
        }
        self.load()

    def load(self) -> None:
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def add_entry(self, text: str, tags: Optional[Iterable[str]] = None) -> MemoryEntry:
        entry = MemoryEntry(
            entry_id=f"mem_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            text=text,
            tags=list(tags or []),
            embedding=self._embed(text),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.data.setdefault("entries", []).append(entry.__dict__)
        return entry

    def add_task(self, goal: str, outcome: str) -> None:
        self.data.setdefault("tasks", []).append(
            {
                "goal": goal,
                "outcome": outcome,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def set_preference(self, key: str, value: Any) -> None:
        self.data.setdefault("preferences", {})[key] = value

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.data.get("preferences", {}).get(key, default)

    def search(self, query: str, top_k: int = 3, min_score: float = 0.1) -> List[Dict[str, Any]]:
        query_vec = self._embed(query)
        results: List[Dict[str, Any]] = []
        for entry in self.data.get("entries", []):
            score = self._cosine_similarity(query_vec, entry.get("embedding", {}))
            if score >= min_score:
                results.append({"score": score, "entry": entry})
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:top_k]

    def _embed(self, text: str) -> Dict[str, float]:
        tokens = self._tokenize(text)
        counts: Dict[str, float] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0.0) + 1.0
        norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
        return {token: value / norm for token, value in counts.items()}

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        shared = set(vec_a.keys()) & set(vec_b.keys())
        dot = sum(vec_a[token] * vec_b[token] for token in shared)
        return float(dot)
