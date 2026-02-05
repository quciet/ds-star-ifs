from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from dsstar.tools.describe_files import describe_files
from dsstar.tools.log_utils import log


def run(files: List[str], run_dir: Path) -> Dict[str, Any]:
    """Analyze input files and write descriptions.json in the run directory."""
    log("Analyzer: describing input files")
    descriptions_path = run_dir / "descriptions.json"
    return describe_files(files, descriptions_path)
