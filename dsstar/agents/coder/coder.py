from __future__ import annotations

import py_compile
from pathlib import Path
from typing import Any, Dict, List, Optional

from dsstar.llm.base import LLMClient
from dsstar.prompts import coder_prompt
from dsstar.tools.log_utils import log, write_text
from dsstar.tools.text_utils import extract_python_code


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
    raw_code = client.complete(prompt)
    code = extract_python_code(raw_code)
    code_path = run_dir / f"round_{round_idx:02d}_code.py"
    write_text(code_path, code)

    try:
        py_compile.compile(str(code_path), doraise=True)
    except py_compile.PyCompileError as exc:
        log(f"Coder: syntax pre-check failed for round {round_idx:02d}: {exc}")

    return code_path
