import json
from dataclasses import dataclass

from dsstar.agents.router.router import run as run_router
from dsstar.llm.base import LLMClient


@dataclass
class _RouterClient(LLMClient):
    name: str = "test"
    model: str = "test-model"
    response: str = "{}"

    def complete(self, prompt: str) -> str:
        return self.response


def test_router_accepts_numeric_string_backtrack() -> None:
    plan = [{"id": 1, "status": "done"}, {"id": 2, "status": "todo"}]
    client = _RouterClient(response=json.dumps({"action": "backtrack", "backtrack_to_step_id": "2"}))
    out = run_router({"sufficient": False}, plan, client)
    assert out == {"action": "backtrack", "backtrack_to_step_id": 2}


def test_router_invalid_backtrack_defaults_add_step() -> None:
    plan = [{"id": 1, "status": "done"}]
    client = _RouterClient(response=json.dumps({"action": "backtrack", "backtrack_to_step_id": "9"}))
    out = run_router({"sufficient": False}, plan, client)
    assert out == {"action": "add_step", "backtrack_to_step_id": None}
