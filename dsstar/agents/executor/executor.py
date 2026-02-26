from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from dsstar.tools.exec_sandbox import run_python_script
from dsstar.tools.log_utils import get_repo_root, log, write_json


def run(code_path: Path, run_dir: Path, timeout_sec: int, round_idx: int) -> Dict[str, Any]:
    """Execute generated code and write round_XX_exec.json."""
    log(f"Executor: running round {round_idx:02d} code")
    repo_root = get_repo_root()
    # Use repo root so generated code can resolve repo-relative paths like input/... .
    exec_result = run_python_script(code_path.resolve(), repo_root, timeout_sec)
    exec_result["cwd"] = str(repo_root)
    exec_result["script_path"] = str(code_path.resolve())
    exec_path = run_dir / f"round_{round_idx:02d}_exec.json"
    write_json(exec_path, exec_result)
    return exec_result
