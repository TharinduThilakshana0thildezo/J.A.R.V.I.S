from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Dict, List

from jarvis_ai.brain.llm import LLMClient
from jarvis_ai.brain.prompts import REFLECTION_PROMPT
from jarvis_ai.memory.skills import SkillLesson


@dataclass
class ReflectionResult:
    summary: str
    lessons: List[SkillLesson]


def reflect(client: LLMClient, task: str, decision: str, outcome: str, error: str | None) -> ReflectionResult:
    prompt = REFLECTION_PROMPT.format(
        task=task,
        decision=decision,
        outcome=outcome,
        error=error or "(none)",
    )

    summary = f"Task: {task} -> {outcome}"
    lessons: List[SkillLesson] = []
    try:
        response = client.generate(prompt=prompt)
        payload = json.loads(response.text)
        summary = str(payload.get("summary", summary))
        for item in payload.get("lessons", []):
            lessons.append(
                SkillLesson(
                    context=str(item.get("context", "")),
                    problem=str(item.get("problem", "")),
                    lesson=str(item.get("lesson", "")),
                    confidence=float(item.get("confidence", 0.5)),
                )
            )
    except Exception:
        pass

    return ReflectionResult(summary=summary, lessons=lessons)
