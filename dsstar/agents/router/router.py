from __future__ import annotations

import json
from typing import Any, Dict, List

from dsstar.llm.base import LLMClient
from dsstar.prompts import router_prompt
from dsstar.tools.log_utils import log


def run(
    verifier_output: Dict[str, Any],
    plan: List[Dict[str, Any]],
    client: LLMClient,
) -> Dict[str, Any]:
    """Return a strict JSON dict describing routing."""
    log("Router: deciding next action")
    prompt = router_prompt(plan, verifier_output)
    response = client.complete(prompt)
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        return {"action": "add_step", "backtrack_to_step_id": None}

    if not isinstance(parsed, dict):
        return {"action": "add_step", "backtrack_to_step_id": None}

    action = str(parsed.get("action", "add_step"))
    backtrack = parsed.get("backtrack_to_step_id")
    backtrack_id = int(backtrack) if isinstance(backtrack, int) else None
    if action not in {"add_step", "backtrack", "stop"}:
        action = "add_step"
    return {"action": action, "backtrack_to_step_id": backtrack_id}
