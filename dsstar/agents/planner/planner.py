from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from dsstar.llm.base import LLMClient
from dsstar.prompts import planner_prompt
from dsstar.tools.log_utils import log


def _coerce_step(raw: Dict[str, Any], next_id: int) -> Dict[str, Any]:
    return {
        "id": int(raw.get("id", next_id)),
        "title": str(raw.get("title", "Plan step")),
        "details": str(raw.get("details", "")),
        "status": "todo",
    }


def run(
    question: str,
    descriptions: Dict[str, Any],
    plan: List[Dict[str, Any]],
    last_exec: Optional[Dict[str, Any]],
    client: LLMClient,
) -> Dict[str, Any]:
    """Generate exactly one new plan step to append."""
    log("Planner: generating next plan step")
    prompt = planner_prompt(question, descriptions, plan, last_exec)
    response = client.complete(prompt)
    next_id = max([step["id"] for step in plan], default=0) + 1
    try:
        parsed = json.loads(response)
        step = _coerce_step(parsed, next_id)
    except json.JSONDecodeError:
        step = {
            "id": next_id,
            "title": "Plan step",
            "details": response.strip(),
            "status": "todo",
        }
    step["id"] = next_id
    step["status"] = "todo"
    return step
