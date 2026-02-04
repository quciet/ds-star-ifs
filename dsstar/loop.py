from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dsstar.llm.base import LLMClient
from dsstar.prompts import (
    coder_prompt,
    debugger_prompt,
    finalizer_prompt,
    planner_prompt,
    router_prompt,
    verifier_prompt,
)
from dsstar.tools.describe_files import describe_files
from dsstar.tools.exec_sandbox import run_python_script
from dsstar.tools.log_utils import log


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _next_todo(plan: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for step in plan:
        if step["status"] == "todo":
            return step
    return None


def _ensure_plan_step(plan: List[Dict[str, Any]], new_step: Dict[str, Any]) -> None:
    if not plan:
        plan.append(new_step)
        return
    new_step["id"] = max(step["id"] for step in plan) + 1
    plan.append(new_step)


def run_loop(
    question: str,
    files: List[str],
    client: LLMClient,
    max_rounds: int,
    timeout_sec: int,
    run_root: Path,
) -> Path:
    run_root.mkdir(parents=True, exist_ok=True)
    run_path = run_root / _timestamp()
    run_path.mkdir(parents=True, exist_ok=True)
    log(f"Run path: {run_path}")

    descriptions_path = run_path / "descriptions.json"
    descriptions = describe_files(files, descriptions_path)

    plan: List[Dict[str, Any]] = []
    verifier_state: Dict[str, Any] = {}

    for round_idx in range(max_rounds):
        log(f"Round {round_idx:02d} starting")

        if not plan:
            plan_prompt = planner_prompt(question, plan)
            response = client.complete(plan_prompt)
            try:
                new_step = json.loads(response)
            except json.JSONDecodeError:
                new_step = {
                    "id": 1,
                    "title": "Investigate",
                    "details": response.strip(),
                    "status": "todo",
                }
            _ensure_plan_step(plan, new_step)
            _write_json(run_path / "plan.json", plan)

        coder_text = coder_prompt(question, plan, descriptions)
        prompt_path = run_path / f"round_{round_idx:02d}_prompt.txt"
        prompt_path.write_text(coder_text, encoding="utf-8")
        code = client.complete(coder_text)
        code_path = run_path / f"round_{round_idx:02d}_code.py"
        code_path.write_text(code, encoding="utf-8")

        exec_result = run_python_script(code_path, run_path, timeout_sec)
        exec_path = run_path / f"round_{round_idx:02d}_exec.json"
        _write_json(exec_path, exec_result)

        if exec_result["exit_code"] != 0:
            log("Execution failed; invoking debugger once.")
            debug_prompt_text = debugger_prompt(
                question, plan, code, exec_result.get("stderr", "")
            )
            debug_code = client.complete(debug_prompt_text)
            code_path.write_text(debug_code, encoding="utf-8")
            exec_result = run_python_script(code_path, run_path, timeout_sec)
            _write_json(exec_path, exec_result)

        next_step = _next_todo(plan)
        if exec_result["exit_code"] == 0 and next_step:
            next_step["status"] = "done"
            _write_json(run_path / "plan.json", plan)

        verifier_text = verifier_prompt(question, plan, exec_result)
        verifier_raw = client.complete(verifier_text)
        try:
            verifier_state = json.loads(verifier_raw)
        except json.JSONDecodeError:
            verifier_state = {
                "sufficient": False,
                "reason": "Verifier returned invalid JSON.",
                "missing": [],
                "next_action": "add_step",
            }

        if verifier_state.get("sufficient"):
            break

        router_text = router_prompt(plan, verifier_state)
        router_raw = client.complete(router_text)
        try:
            router_state = json.loads(router_raw)
        except json.JSONDecodeError:
            router_state = {"action": "add_step", "backtrack_to_step_id": None}

        if router_state.get("action") == "backtrack":
            target = router_state.get("backtrack_to_step_id")
            for step in plan:
                if target is not None and step["id"] >= target:
                    step["status"] = "todo"
            _write_json(run_path / "plan.json", plan)
        else:
            plan_prompt = planner_prompt(question, plan)
            response = client.complete(plan_prompt)
            try:
                new_step = json.loads(response)
            except json.JSONDecodeError:
                new_step = {
                    "id": 1,
                    "title": "Investigate",
                    "details": response.strip(),
                    "status": "todo",
                }
            _ensure_plan_step(plan, new_step)
            _write_json(run_path / "plan.json", plan)

    final_text = finalizer_prompt(question, plan, verifier_state)
    final_answer = client.complete(final_text)
    (run_path / "final_answer.md").write_text(final_answer, encoding="utf-8")
    log("Final answer written.")
    return run_path
