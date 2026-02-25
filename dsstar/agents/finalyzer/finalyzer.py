from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from dsstar.llm.base import LLMClient
from dsstar.prompts import finalyzer_code_prompt, finalyzer_report_prompt
from dsstar.tools.log_utils import log, write_text
from dsstar.tools.text_utils import extract_python_code


def finalyzer_code(
    question: str,
    plan: List[Dict[str, Any]],
    descriptions: Dict[str, Any],
    last_working_code: str,
    client: LLMClient,
    run_dir: Path,
) -> Path:
    log("Finalyzer: generating final solution code")
    prompt = finalyzer_code_prompt(question, plan, descriptions, last_working_code)
    code = extract_python_code(client.complete(prompt))
    code_path = run_dir / "final_solution.py"
    write_text(code_path, code)
    return code_path


def finalyzer_report(
    question: str,
    plan: List[Dict[str, Any]],
    artifact_manifest: Dict[str, Any],
    final_exec: Dict[str, Any],
    client: LLMClient,
    run_dir: Path,
) -> str:
    log("Finalyzer: composing final report")
    prompt = finalyzer_report_prompt(question, plan, artifact_manifest, final_exec)
    answer = client.complete(prompt)
    final_path = run_dir / "final_answer.md"
    write_text(final_path, answer)
    return answer


def run(*args: Any, **kwargs: Any) -> str:
    """Backward compatible alias for report generation only."""
    return finalyzer_report(*args, **kwargs)
