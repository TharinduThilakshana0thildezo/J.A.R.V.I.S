from jarvis_ai.brain.agent import JarvisAgent
from jarvis_ai.brain.llm import LLMClient, LLMResponse
from jarvis_ai.brain.planner import Planner, PlanStep
from jarvis_ai.memory.long_term import LongTermMemory
from jarvis_ai.memory.skills import SkillMemory
from jarvis_ai.memory.logs import Logger
from pathlib import Path
import tempfile


class FakeLLM(LLMClient):
    def __init__(self) -> None:
        super().__init__(base_url="", model="")

    def generate(self, prompt: str, system=None) -> LLMResponse:
        if "Create a concise, dependency-aware plan" in prompt:
            return LLMResponse(text='{"steps": [{"id": "s1", "description": "respond", "depends_on": []}]}', raw={})
        return LLMResponse(text='{"intent": "test", "action": "respond", "action_input": "ok", "needs_confirmation": false}', raw={})


def test_execute_plan_success() -> None:
    agent = JarvisAgent(settings={})
    planner = Planner()
    client = FakeLLM()
    plan = [PlanStep(step_id="s1", description="respond")]

    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        long_term = LongTermMemory(base / "long_term.json")
        skills = SkillMemory(base / "skills.json")
        logger = Logger(base / "actions.jsonl")
        outcome, error = agent._execute_plan(
            client=client,
            planner=planner,
            plan=plan,
            user_input="hello",
            skills=skills,
            long_term=long_term,
            safety_settings={"require_confirmations": False},
            logger=logger,
        )

    assert outcome == "success"
    assert error is None
