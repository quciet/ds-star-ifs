from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from dsstar.runtime_paths import find_repo_root


def log(message: str) -> None:
    timestamp = datetime.datetime.utcnow().isoformat(timespec="seconds")
    print(f"[{timestamp}] {message}")


def timestamp_slug() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def create_run_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    run_path = root / timestamp_slug()
    run_path.mkdir(parents=True, exist_ok=True)
    return run_path


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def get_repo_root() -> Path:
    return find_repo_root()
