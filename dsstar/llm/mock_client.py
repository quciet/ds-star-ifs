from __future__ import annotations

import json
from dataclasses import dataclass

from dsstar.llm.base import LLMClient


@dataclass
class MockClient(LLMClient):
    name: str = "mock"
    model: str = "mock-001"

    def complete(self, prompt: str) -> str:
        if "ROLE: PLANNER" in prompt:
            return json.dumps(
                {
                    "id": 1,
                    "title": "Write hello.txt",
                    "details": "Create hello.txt in the run directory containing 'hello'.",
                    "status": "todo",
                }
            )
        if "ROLE: CODER" in prompt:
            return (
                "from pathlib import Path\n"
                "Path('hello.txt').write_text('hello', encoding='utf-8')\n"
                "print('wrote hello.txt')\n"
            )
        if "ROLE: DEBUGGER" in prompt:
            return (
                "from pathlib import Path\n"
                "Path('hello.txt').write_text('hello', encoding='utf-8')\n"
                "print('wrote hello.txt')\n"
            )
        if "ROLE: VERIFIER" in prompt:
            return json.dumps(
                {
                    "sufficient": True,
                    "reason": "hello.txt created.",
                    "missing": [],
                    "next_action": "stop",
                }
            )
        if "ROLE: ROUTER" in prompt:
            return json.dumps({"action": "add_step", "backtrack_to_step_id": None})
        if "ROLE: FINALIZER" in prompt:
            return "Created hello.txt in the run directory."
        return "Unsupported prompt."
