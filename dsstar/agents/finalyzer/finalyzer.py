from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from dsstar.llm.base import LLMClient
from dsstar.prompts import finalyzer_prompt
from dsstar.tools.log_utils import log, write_text


def run(
    question: str,
    plan: List[Dict[str, Any]],
    descriptions: Dict[str, Any],
    last_exec: Dict[str, Any],
    artifacts: List[str],
    client: LLMClient,
    run_dir: Path,
) -> str:
    """Generate final markdown answer and write final_answer.md."""
    log("Finalyzer: composing final answer")
    prompt = finalyzer_prompt(question, plan, descriptions, last_exec, artifacts)
    answer = client.complete(prompt)
    final_path = run_dir / "final_answer.md"
    write_text(final_path, answer)
    return answer
