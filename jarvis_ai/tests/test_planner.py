from jarvis_ai.brain.planner import Planner
from jarvis_ai.brain.llm import LLMClient, LLMResponse


class FakeLLM(LLMClient):
    def __init__(self) -> None:
        super().__init__(base_url="", model="")

    def generate(self, prompt: str, system=None) -> LLMResponse:
        return LLMResponse(
            text='{"steps": [{"id": "s1", "description": "step 1", "depends_on": []}]}',
            raw={},
        )


def test_planner_parses_steps() -> None:
    planner = Planner()
    steps = planner.plan(FakeLLM(), "Do a thing")
    assert steps
    assert steps[0].step_id == "s1"
