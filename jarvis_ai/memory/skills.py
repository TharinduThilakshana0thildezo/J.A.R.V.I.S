from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class SkillLesson:
    context: str
    problem: str
    lesson: str
    confidence: float


@dataclass
class SkillMemory:
    path: Path
    version: int = 1
    lessons: List[SkillLesson] = field(default_factory=list)

    def load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.version = raw.get("version", 1)
        self.lessons = [SkillLesson(**item) for item in raw.get("lessons", [])]

    def save(self) -> None:
        payload = {
            "version": self.version,
            "lessons": [lesson.__dict__ for lesson in self.lessons],
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def upsert(self, lesson: SkillLesson) -> None:
        for existing in self.lessons:
            if existing.context == lesson.context and existing.problem == lesson.problem:
                existing.lesson = lesson.lesson
                existing.confidence = lesson.confidence
                return
        self.lessons.append(lesson)

    def relevant(self, text: str, limit: int = 5) -> List[SkillLesson]:
        haystack = text.lower()
        matches = [
            lesson
            for lesson in self.lessons
            if lesson.context.lower() in haystack or lesson.problem.lower() in haystack
        ]
        return matches[:limit]
