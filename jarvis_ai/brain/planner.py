from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import List

from jarvis_ai.brain.llm import LLMClient
from jarvis_ai.brain.prompts import PLAN_PROMPT, SYSTEM_PROMPT


@dataclass
class PlanStep:
    step_id: str
    description: str
    depends_on: List[str] = field(default_factory=list)
    status: str = "pending"


class Planner:
    def plan(self, client: LLMClient, goal: str) -> List[PlanStep]:
        prompt = PLAN_PROMPT.format(goal=goal)
        try:
            response = client.generate(prompt=prompt, system=SYSTEM_PROMPT)
            payload = json.loads(response.text)
            steps = []
            for item in payload.get("steps", []):
                steps.append(
                    PlanStep(
                        step_id=str(item.get("id", "")),
                        description=str(item.get("description", "")),
                        depends_on=[str(dep) for dep in item.get("depends_on", [])],
                    )
                )
            return [step for step in steps if step.step_id and step.description] or [
                PlanStep(step_id="step_1", description=goal)
            ]
        except Exception:
            return [PlanStep(step_id="step_1", description=goal)]

    def ready_steps(self, steps: List[PlanStep]) -> List[PlanStep]:
        completed = {step.step_id for step in steps if step.status == "done"}
        return [
            step
            for step in steps
            if step.status == "pending" and all(dep in completed for dep in step.depends_on)
        ]
