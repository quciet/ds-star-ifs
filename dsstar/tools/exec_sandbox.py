from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Dict, Any


def run_python_script(script_path: Path, cwd: Path, timeout_sec: int) -> Dict[str, Any]:
    start = time.time()
    try:
        proc = subprocess.run(
            ["python", str(script_path)],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        duration = time.time() - start
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "duration_sec": round(duration, 3),
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        duration = time.time() - start
        return {
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "Execution timed out.",
            "exit_code": -1,
            "duration_sec": round(duration, 3),
            "timeout": True,
        }
