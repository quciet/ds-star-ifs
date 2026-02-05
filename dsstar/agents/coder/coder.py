from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from dsstar.llm.base import LLMClient
from dsstar.prompts import coder_prompt
from dsstar.tools.log_utils import log, write_text


def run(
    question: str,
    descriptions: Dict[str, Any],
    plan: List[Dict[str, Any]],
    next_step: Dict[str, Any],
    previous_code: Optional[str],
    last_exec: Optional[Dict[str, Any]],
    client: LLMClient,
    run_dir: Path,
    round_idx: int,
) -> Path:
    """Generate Python code and write round_XX_code.py."""
    log(f"Coder: generating code for round {round_idx:02d}")
    prompt = coder_prompt(
        question=question,
        descriptions=descriptions,
        plan=plan,
        next_step=next_step,
        previous_code=previous_code,
        last_exec=last_exec,
    )
    prompt_path = run_dir / f"round_{round_idx:02d}_prompt.txt"
    write_text(prompt_path, prompt)
    code = client.complete(prompt)
    code_path = run_dir / f"round_{round_idx:02d}_code.py"
    write_text(code_path, code)
    return code_path
