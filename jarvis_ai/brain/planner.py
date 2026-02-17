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
    def plan(self, client: LLMClient, goal: str, history: str = "", memory: str = "") -> tuple[List[PlanStep], Optional[str]]:
        prompt = PLAN_PROMPT.format(goal=goal, history=history, memory=memory)
        try:
            response = client.generate(prompt=prompt, system=SYSTEM_PROMPT)
            # If the local backend returns nothing, surface a user-facing fallback.
            if not str(response.text).strip():
                return [], "I could not get a reply from the local model. Please ensure Ollama is running and the model is pulled."
            try:
                payload = json.loads(response.text)
            except json.JSONDecodeError:
                # If model returns raw text instead of JSON, treat it as a direct response
                print("[JARVIS][Planner] Model returned non-JSON response. Treating as direct chat.", flush=True)
                return [], str(response.text).strip()
            
            # Fast path: direct response
            if "response" in payload:
                return [], str(payload["response"])

            steps = []
            for item in payload.get("steps", []):
                steps.append(
                    PlanStep(
                        step_id=str(item.get("id", "")),
                        description=str(item.get("description", "")),
                        depends_on=[str(dep) for dep in item.get("depends_on", [])],
                    )
                )
            # Fallback if steps is empty but no response field
            result_steps = [step for step in steps if step.step_id and step.description]
            if not result_steps:
                 return [PlanStep(step_id="step_1", description=goal)], None
            return result_steps, None
        except Exception as e:
            print(f"[JARVIS][Planner] LLM request failed: {e}", flush=True)
            return [PlanStep(step_id="step_1", description=goal)], None

    def ready_steps(self, steps: List[PlanStep]) -> List[PlanStep]:
        completed = {step.step_id for step in steps if step.status == "done"}
        return [
            step
            for step in steps
            if step.status == "pending" and all(dep in completed for dep in step.depends_on)
        ]
