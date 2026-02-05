from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _header(role: str) -> str:
    return f"ROLE: {role}\n"


def analyzer_prompt(question: str, files: List[str]) -> str:
    return (
        _header("ANALYZER")
        + "You describe input files. Use local tooling, not the LLM, when available.\n"
        + f"Question: {question}\n"
        + f"Files: {files}\n"
    )


def planner_prompt(
    question: str,
    descriptions: Dict[str, Any],
    plan: List[Dict[str, Any]],
    last_exec: Optional[Dict[str, Any]],
) -> str:
    return (
        _header("PLANNER")
        + "You add exactly one step to the plan.\n"
        + "Plan step format: {\"id\": int, \"title\": str, \"details\": str, \"status\": \"todo\"}.\n"
        + f"Question: {question}\n"
        + f"Descriptions:\n{json.dumps(descriptions, indent=2)}\n"
        + f"Current plan:\n{json.dumps(plan, indent=2)}\n"
        + f"Last execution:\n{json.dumps(last_exec, indent=2) if last_exec else 'null'}\n"
        + "Return only JSON for the new step."
    )


def coder_prompt(
    question: str,
    descriptions: Dict[str, Any],
    plan: List[Dict[str, Any]],
    next_step: Dict[str, Any],
    previous_code: Optional[str],
    last_exec: Optional[Dict[str, Any]],
) -> str:
    return (
        _header("CODER")
        + "Write a full Python script that accomplishes all steps up to the next todo step.\n"
        + "Output ONLY Python code, no markdown fences.\n"
        + f"Question: {question}\n"
        + f"Next step:\n{json.dumps(next_step, indent=2)}\n"
        + f"Plan:\n{json.dumps(plan, indent=2)}\n"
        + f"Descriptions:\n{json.dumps(descriptions, indent=2)}\n"
        + f"Previous code:\n{previous_code or ''}\n"
        + f"Last execution:\n{json.dumps(last_exec, indent=2) if last_exec else 'null'}\n"
    )


def executor_prompt(code_path: str) -> str:
    return _header("EXECUTOR") + f"Execute script at {code_path}.\n"


def verifier_prompt(
    question: str,
    descriptions: Dict[str, Any],
    plan: List[Dict[str, Any]],
    last_code: str,
    exec_result: Dict[str, Any],
) -> str:
    return (
        _header("VERIFIER")
        + "Return strict JSON: {\"sufficient\": true/false, \"reason\": \"...\", "
        + "\"missing\": [\"...\"], \"next_action\": \"add_step|fix_step|stop\"}.\n"
        + f"Question: {question}\n"
        + f"Descriptions:\n{json.dumps(descriptions, indent=2)}\n"
        + f"Plan:\n{json.dumps(plan, indent=2)}\n"
        + f"Last code:\n{last_code}\n"
        + f"Execution:\n{json.dumps(exec_result, indent=2)}\n"
    )


def router_prompt(plan: List[Dict[str, Any]], verifier: Dict[str, Any]) -> str:
    return (
        _header("ROUTER")
        + "Return strict JSON: {\"action\": \"add_step\"|\"backtrack\"|\"stop\", "
        + "\"backtrack_to_step_id\": int|null}.\n"
        + f"Plan:\n{json.dumps(plan, indent=2)}\n"
        + f"Verifier:\n{json.dumps(verifier, indent=2)}\n"
    )


def debugger_prompt(
    question: str,
    descriptions: Dict[str, Any],
    plan: List[Dict[str, Any]],
    failing_code: str,
    exec_stderr: str,
) -> str:
    return (
        _header("DEBUGGER")
        + "Patch the Python script to fix the failure. Output ONLY Python code.\n"
        + f"Question: {question}\n"
        + f"Descriptions:\n{json.dumps(descriptions, indent=2)}\n"
        + f"Plan:\n{json.dumps(plan, indent=2)}\n"
        + f"Code:\n{failing_code}\n"
        + f"Error:\n{exec_stderr}\n"
    )


def finalyzer_prompt(
    question: str,
    plan: List[Dict[str, Any]],
    descriptions: Dict[str, Any],
    last_exec: Dict[str, Any],
    artifacts: List[str],
) -> str:
    return (
        _header("FINALYZER")
        + "Summarize the final answer for the user in markdown.\n"
        + f"Question: {question}\n"
        + f"Plan:\n{json.dumps(plan, indent=2)}\n"
        + f"Descriptions:\n{json.dumps(descriptions, indent=2)}\n"
        + f"Last execution:\n{json.dumps(last_exec, indent=2)}\n"
        + f"Artifacts: {artifacts}\n"
    )
