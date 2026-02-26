from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from dsstar.llm.base import LLMClient
from dsstar.prompts import router_prompt
from dsstar.tools.log_utils import log


def _parse_backtrack_id(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def run(
    verifier_output: Dict[str, Any],
    plan: List[Dict[str, Any]],
    client: LLMClient,
) -> Dict[str, Any]:
    """Route between add_step/backtrack per verifier signal and plan state."""
    if bool(verifier_output.get("sufficient", False)):
        log("Router: verifier sufficient -> stop")
        return {"action": "stop", "backtrack_to_step_id": None}

    log("Router: deciding add_step/backtrack")
    prompt = router_prompt(plan, verifier_output)
    response = client.complete(prompt)
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        log("Router: invalid JSON, defaulting to add_step")
        return {"action": "add_step", "backtrack_to_step_id": None}

    if not isinstance(parsed, dict):
        return {"action": "add_step", "backtrack_to_step_id": None}

    action = str(parsed.get("action", "add_step"))
    if action not in {"add_step", "backtrack", "stop"}:
        action = "add_step"

    backtrack_id = _parse_backtrack_id(parsed.get("backtrack_to_step_id"))
    valid_ids = {int(step.get("id")) for step in plan if isinstance(step.get("id"), int)}
    if action == "backtrack":
        if backtrack_id is None or backtrack_id not in valid_ids:
            log("Router: invalid backtrack id, defaulting to add_step")
            return {"action": "add_step", "backtrack_to_step_id": None}

    return {"action": action, "backtrack_to_step_id": backtrack_id}
