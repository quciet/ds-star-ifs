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


def description_script_prompt(file_path: str, file_type: str) -> str:
    return (
        _header("ANALYZER_DESC_SCRIPT")
        + "Generate a single, self-contained Python script for one input file.\n"
        + "Return ONLY Python code, no markdown fences or commentary.\n"
        + "The script must print a deterministic plain-text description to stdout.\n"
        + "Include file-type detection for csv/tsv/xlsx/sqlite/parquet/json/zip/unknown.\n"
        + "Report schema/columns, row count if feasible, identifiers, time coverage hints, missingness highlights, metadata/units if available, and anomalies.\n"
        + "For Excel: list sheets + key schema samples. For SQLite: tables, columns, row counts, sample rows. For zip: list entries + next-step hints.\n"
        + "Avoid heavy loads; sample rows when needed. Always wrap top-level execution in try/except and print 'FAILED TO DESCRIBE: <error>'.\n"
        + "Prefer stdlib + pandas/openpyxl/sqlite3 only when available, with graceful fallback if imports fail.\n"
        + f"Target file path: {file_path}\n"
        + f"Observed extension/type hint: {file_type}\n"
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
        + "\"missing\": [\"...\"], \"next_action\": \"add_step|debug|stop\"}.\n"
        + f"Question: {question}\n"
        + f"Descriptions:\n{json.dumps(descriptions, indent=2)}\n"
        + f"Plan:\n{json.dumps(plan, indent=2)}\n"
        + f"Last code:\n{last_code}\n"
        + f"Execution:\n{json.dumps(exec_result, indent=2)}\n"
    )


def router_prompt(plan: List[Dict[str, Any]], verifier: Dict[str, Any]) -> str:
    return (
        _header("ROUTER")
        + 'Return strict JSON: {"action": "add_step"|"backtrack"|"stop", '
        + '"backtrack_to_step_id": int|null}.\n'
        + "Rules: use backtrack only if a specific earlier step is wrong/inconsistent; choose the earliest erroneous step id to revise.\n"
        + "Use add_step if the plan is missing a required step.\n"
        + "Use stop only if the task cannot be completed with the given files/constraints.\n"
        + "Output JSON only.\n"
        + f"Plan:\n{json.dumps(plan, indent=2)}\n"
        + f"Verifier:\n{json.dumps(verifier, indent=2)}\n"
    )

def debugger_trace_summary_prompt(
    exit_code: int,
    stderr: str,
    last_command: str,
    failing_code_tail: str,
) -> str:
    return (
        _header("DEBUGGER_TRACE_SUMMARY")
        + "Summarize traceback into strict JSON only: "
        + '{"error_type":"...","likely_root_cause":"...","key_trace_lines":["..."],"suggested_fix_focus":"..."}.\n'
        + f"exit_code: {exit_code}\n"
        + f"last_command: {last_command}\n"
        + f"stderr:\n{stderr}\n"
        + f"failing_code_tail:\n{failing_code_tail}\n"
    )


def debugger_patch_prompt(
    question: str,
    descriptions: Dict[str, Any],
    plan: List[Dict[str, Any]],
    failing_code: str,
    trace_summary: Dict[str, Any],
    strict: bool = False,
) -> str:
    return (
        _header("DEBUGGER_PATCH")
        + "Patch the full Python script to fix the failure while preserving core program behavior and intent.\n"
        + "Return ONLY Python code, no markdown.\n"
        + ("You must materially change the code to address the error.\n" if strict else "")
        + f"Question: {question}\n"
        + f"Descriptions:\n{json.dumps(descriptions, indent=2)}\n"
        + f"Plan:\n{json.dumps(plan, indent=2)}\n"
        + f"Code:\n{failing_code}\n"
        + f"Trace summary:\n{json.dumps(trace_summary, indent=2)}\n"
    )


def finalyzer_code_prompt(
    question: str,
    plan: List[Dict[str, Any]],
    descriptions: Dict[str, Any],
    last_working_code: str,
) -> str:
    return (
        _header("FINALYZER_CODE")
        + "Produce the final solution script. Return ONLY Python code.\n"
        + "Requirements: include main() and if __name__ == '__main__': main().\n"
        + "Write outputs to stable paths under outputs/ and print a concise completion summary.\n"
        + f"Question: {question}\n"
        + f"Plan:\n{json.dumps(plan, indent=2)}\n"
        + f"Descriptions:\n{json.dumps(descriptions, indent=2)}\n"
        + f"Last working code:\n{last_working_code}\n"
    )


def finalyzer_report_prompt(
    question: str,
    plan: List[Dict[str, Any]],
    artifact_manifest: Dict[str, Any],
    final_exec: Dict[str, Any],
) -> str:
    return (
        _header("FINALYZER_REPORT")
        + "Write a concise markdown report after successful convergence and validation.\n"
        + "Use only structured inputs. Do not include full source code.\n"
        + f"Question: {question}\n"
        + f"Plan:\n{json.dumps(plan, indent=2)}\n"
        + f"Artifact manifest:\n{json.dumps(artifact_manifest, indent=2)}\n"
        + f"Final execution:\n{json.dumps(final_exec, indent=2)}\n"
    )


def master_describer_prompt() -> str:
    return (
        _header("ANALYZER_MASTER_DESCRIBER")
        + "Return ONLY Python code for a reusable master describer module.\n"
        + "Must define describe_file(path: str) -> str and use progressive strategies across csv/tsv/xlsx/sqlite/json/parquet/zip/text/unknown.\n"
        + "Never crash: on failure return exactly 'FAILED TO DESCRIBE: <error>'.\n"
        + "Avoid heavy full-file loads where possible; emit deterministic plain-text summaries.\n"
    )


def override_prompt(
    file_path: str,
    master_source: str,
    wrapper_source: str,
    failure_stderr: str,
    file_sample: str,
    fallback_facts: Dict[str, Any],
) -> str:
    return (
        _header("ANALYZER_OVERRIDE")
        + "Return ONLY Python code.\n"
        + "Provide describe_file(path: str) -> str.\n"
        + "Do not re-implement the whole toolkit. Only implement what is needed to handle this file.\n"
        + "Avoid hardcoding file names unless unavoidable.\n"
        + f"Target file: {file_path}\n"
        + f"Master source:\n{master_source}\n"
        + f"Wrapper source:\n{wrapper_source}\n"
        + f"Failure stderr/traceback:\n{failure_stderr}\n"
        + f"File sample/metadata:\n{file_sample}\n"
        + f"Fallback facts:\n{json.dumps(fallback_facts, indent=2)}\n"
    )


def promote_judge_prompt(signature: str, failure_stderr: str, override_source: str) -> str:
    return (
        _header("ANALYZER_PROMOTE_JUDGE")
        + "Return JSON only with schema: "
        + '{"promote": true|false, "reason": "...", "general_pattern": "...", "patch_strategy": "master"|"keep_override"}.\n'
        + "Promote only if fix is generalizable to a detectable signature/pattern and not file-name specific.\n"
        + f"Signature: {signature}\n"
        + f"Failure context:\n{failure_stderr}\n"
        + f"Successful override code:\n{override_source}\n"
    )


def master_patch_prompt(current_master: str, signature: str, failure_summary: str, override_code: str) -> str:
    return (
        _header("ANALYZER_MASTER_PATCH")
        + "Return ONLY full Python code for the patched master describer module.\n"
        + "Patch must add a generalizable fallback/handler keyed by detectable signature traits.\n"
        + "Do NOT hardcode a single file path/name. Preserve prior behavior.\n"
        + f"Current master code:\n{current_master}\n"
        + f"Target signature: {signature}\n"
        + f"Failure summary:\n{failure_summary}\n"
        + f"Reference successful override:\n{override_code}\n"
    )
