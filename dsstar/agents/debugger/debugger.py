from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from dsstar.llm.base import LLMClient
from dsstar.prompts import debugger_patch_prompt, debugger_trace_summary_prompt
from dsstar.tools.log_utils import log, write_json, write_text
from dsstar.tools.text_utils import extract_python_code


def _default_trace_summary(stderr: str) -> Dict[str, Any]:
    lines = [line for line in stderr.splitlines() if line.strip()]
    return {
        "error_type": "UnknownError",
        "likely_root_cause": lines[-1] if lines else "No stderr provided",
        "key_trace_lines": lines[-6:],
        "suggested_fix_focus": "Fix the immediate runtime error while preserving behavior.",
    }


def run(
    question: str,
    descriptions: Dict[str, Any],
    plan: List[Dict[str, Any]],
    failing_code: str,
    exec_result: Dict[str, Any],
    client: LLMClient,
    run_dir: Path,
    round_idx: int,
) -> str:
    """Two-stage debugging: summarize traceback, then generate patched code."""
    log("Debugger: stage 1 traceback summarization")
    stderr = str(exec_result.get("stderr", ""))
    exit_code = int(exec_result.get("exit_code", 1))
    command = str(exec_result.get("command", "python round code"))
    tail = "\n".join(failing_code.splitlines()[-80:])

    summary_prompt = debugger_trace_summary_prompt(
        exit_code=exit_code,
        stderr=stderr,
        last_command=command,
        failing_code_tail=tail,
    )
    summary_raw = client.complete(summary_prompt)
    try:
        summary = json.loads(summary_raw)
        if not isinstance(summary, dict):
            summary = _default_trace_summary(stderr)
    except json.JSONDecodeError:
        summary = _default_trace_summary(stderr)

    write_json(run_dir / f"round_{round_idx:02d}_trace_summary.json", summary)

    log("Debugger: stage 2 patch generation")
    patch_prompt = debugger_patch_prompt(
        question=question,
        descriptions=descriptions,
        plan=plan,
        failing_code=failing_code,
        trace_summary=summary,
        strict=False,
    )
    patched = extract_python_code(client.complete(patch_prompt))

    if patched.strip() == failing_code.strip():
        log("Debugger: identical patch, retrying with strict instruction")
        patch_prompt = debugger_patch_prompt(
            question=question,
            descriptions=descriptions,
            plan=plan,
            failing_code=failing_code,
            trace_summary=summary,
            strict=True,
        )
        patched = extract_python_code(client.complete(patch_prompt))

    if not patched.strip() or patched.strip() == failing_code.strip():
        log("Debugger: patch failed, returning original code")
        patched = failing_code

    write_text(run_dir / f"round_{round_idx:02d}_code_patched.py", patched)
    return patched
