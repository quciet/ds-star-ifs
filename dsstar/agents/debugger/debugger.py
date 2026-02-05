from __future__ import annotations

from typing import Any, Dict, List

from dsstar.llm.base import LLMClient
from dsstar.prompts import debugger_prompt
from dsstar.tools.log_utils import log


def run(
    question: str,
    descriptions: Dict[str, Any],
    plan: List[Dict[str, Any]],
    failing_code: str,
    exec_stderr: str,
    client: LLMClient,
) -> str:
    """Return patched Python code when execution fails."""
    log("Debugger: attempting patch")
    prompt = debugger_prompt(
        question=question,
        descriptions=descriptions,
        plan=plan,
        failing_code=failing_code,
        exec_stderr=exec_stderr,
    )
    return client.complete(prompt)
