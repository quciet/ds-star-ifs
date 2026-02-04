from __future__ import annotations

import json
from typing import Any, List, Dict


def _header(role: str) -> str:
    return f"ROLE: {role}\n"


def planner_prompt(question: str, plan: List[Dict[str, Any]]) -> str:
    payload = json.dumps(plan, indent=2)
    return (
        _header("PLANNER")
        + "You add exactly one step to the plan.\n"
        + "Plan format: [{\"id\": int, \"title\": str, \"details\": str, \"status\": \"todo|done|failed\"}]\n"
        + f"Question: {question}\n"
        + f"Current plan:\n{payload}\n"
        + "Return only JSON for the new step."
    )


def coder_prompt(question: str, plan: List[Dict[str, Any]], descriptions: Dict[str, Any]) -> str:
    payload = json.dumps(plan, indent=2)
    desc = json.dumps(descriptions, indent=2)
    return (
        _header("CODER")
        + "Write a full Python script that accomplishes all steps up to the next todo step.\n"
        + "Output ONLY Python code, no markdown.\n"
        + f"Question: {question}\n"
        + f"Plan:\n{payload}\n"
        + f"File descriptions:\n{desc}\n"
    )


def debugger_prompt(question: str, plan: List[Dict[str, Any]], code: str, error: str) -> str:
    payload = json.dumps(plan, indent=2)
    return (
        _header("DEBUGGER")
        + "Patch the Python script to fix the failure. Output ONLY Python code.\n"
        + f"Question: {question}\n"
        + f"Plan:\n{payload}\n"
        + f"Code:\n{code}\n"
        + f"Error:\n{error}\n"
    )


def verifier_prompt(question: str, plan: List[Dict[str, Any]], exec_result: Dict[str, Any]) -> str:
    payload = json.dumps(plan, indent=2)
    result = json.dumps(exec_result, indent=2)
    return (
        _header("VERIFIER")
        + "Return strict JSON: "
        + "{\"sufficient\": true/false, \"reason\": \"...\", \"missing\": [\"...\"], "
        + "\"next_action\": \"add_step|fix_step|stop\"}\n"
        + f"Question: {question}\n"
        + f"Plan:\n{payload}\n"
        + f"Execution:\n{result}\n"
    )


def router_prompt(plan: List[Dict[str, Any]], verifier: Dict[str, Any]) -> str:
    payload = json.dumps(plan, indent=2)
    ver = json.dumps(verifier, indent=2)
    return (
        _header("ROUTER")
        + "Return strict JSON: "
        + "{\"action\": \"add_step\"|\"backtrack\", \"backtrack_to_step_id\": int|null}\n"
        + f"Plan:\n{payload}\n"
        + f"Verifier:\n{ver}\n"
    )


def finalizer_prompt(question: str, plan: List[Dict[str, Any]], verifier: Dict[str, Any]) -> str:
    payload = json.dumps(plan, indent=2)
    ver = json.dumps(verifier, indent=2)
    return (
        _header("FINALIZER")
        + "Summarize the final answer for the user.\n"
        + f"Question: {question}\n"
        + f"Plan:\n{payload}\n"
        + f"Verifier:\n{ver}\n"
    )
