from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from dsstar.tools.exec_sandbox import run_python_script
from dsstar.tools.log_utils import get_repo_root, log, write_json


def run(code_path: Path, run_dir: Path, timeout_sec: int, round_idx: int) -> Dict[str, Any]:
    """Execute generated code and write round_XX_exec.json."""
    log(f"Executor: running round {round_idx:02d} code")
    repo_root = get_repo_root().resolve()
    run_dir = run_dir.resolve()
    script_path = code_path.resolve()

    env = os.environ.copy()
    env["DSSTAR_REPO_ROOT"] = str(repo_root)
    env["DSSTAR_RUN_DIR"] = str(run_dir)

    before_entries = {
        p.name
        for p in repo_root.iterdir()
        if p.name not in {"runs", ".git", "__pycache__"}
    }

    # Run with cwd=run_dir so any relative writes are contained under this run.
    exec_result = run_python_script(script_path, run_dir, timeout_sec, env=env)

    after_entries = {
        p.name
        for p in repo_root.iterdir()
        if p.name not in {"runs", ".git", "__pycache__"}
    }
    unexpected = sorted(after_entries - before_entries)
    if unexpected:
        log(f"Executor warning: new repo-root entries outside runs/: {unexpected}")
        exec_result["warnings"] = {
            "unexpected_repo_root_entries": unexpected,
        }

    exec_result["cwd"] = str(run_dir)
    exec_result["script_path"] = str(code_path.resolve())
    exec_path = run_dir / f"round_{round_idx:02d}_exec.json"
    write_json(exec_path, exec_result)
    return exec_result
