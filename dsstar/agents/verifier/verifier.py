from __future__ import annotations

import json
from typing import Any, Dict, List

from dsstar.llm.base import LLMClient
from dsstar.prompts import verifier_prompt
from dsstar.tools.log_utils import log


def _default_result(reason: str) -> Dict[str, Any]:
    return {
        "sufficient": False,
        "reason": reason,
        "missing": [],
        "next_action": "add_step",
    }


def run(
    question: str,
    descriptions: Dict[str, Any],
    plan: List[Dict[str, Any]],
    last_code: str,
    last_exec: Dict[str, Any],
    client: LLMClient,
) -> Dict[str, Any]:
    """Return a strict JSON dict describing sufficiency."""
    log("Verifier: evaluating result")
    prompt = verifier_prompt(question, descriptions, plan, last_code, last_exec)
    response = client.complete(prompt)
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        return _default_result("Verifier returned invalid JSON.")

    if not isinstance(parsed, dict):
        return _default_result("Verifier returned non-object JSON.")

    return {
        "sufficient": bool(parsed.get("sufficient", False)),
        "reason": str(parsed.get("reason", "")),
        "missing": list(parsed.get("missing", [])),
        "next_action": str(parsed.get("next_action", "add_step")),
    }
