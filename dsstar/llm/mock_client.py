from __future__ import annotations

import json
from dataclasses import dataclass

from dsstar.llm.base import LLMClient


@dataclass
class MockClient(LLMClient):
    name: str = "mock"
    model: str = "mock-001"

    def complete(self, prompt: str) -> str:
        if "ROLE: ANALYZER_DESC_SCRIPT" in prompt:
            return (
                "try:\n"
                "    print('FILE=mock')\n"
                "    print('TYPE=unknown')\n"
                "    print('SIZE=0')\n"
                "except Exception as e:\n"
                "    print('FAILED TO DESCRIBE: ' + str(e))\n"
            )
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
        if "ROLE: DEBUGGER_TRACE_SUMMARY" in prompt:
            return json.dumps(
                {
                    "error_type": "RuntimeError",
                    "likely_root_cause": "forced failure",
                    "key_trace_lines": ["RuntimeError: forced failure"],
                    "suggested_fix_focus": "Replace intentional failure with intended output write.",
                }
            )
        if "ROLE: DEBUGGER_PATCH" in prompt:
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
        if "ROLE: FINALYZER_CODE" in prompt:
            return (
                "from pathlib import Path\n\n"
                "def main() -> None:\n"
                "    Path('outputs').mkdir(parents=True, exist_ok=True)\n"
                "    Path('hello.txt').write_text('hello', encoding='utf-8')\n"
                "    print('completed: wrote hello.txt')\n\n"
                "if __name__ == '__main__':\n"
                "    main()\n"
            )
        if "ROLE: FINALYZER_REPORT" in prompt:
            return "Created hello.txt in the run directory."
        return "Unsupported prompt."
