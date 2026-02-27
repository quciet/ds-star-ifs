from __future__ import annotations

import os
from pathlib import Path


def find_repo_root() -> Path:
    env_root = os.environ.get("DSSTAR_REPO_ROOT")
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if candidate.exists():
            return candidate

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent

    for parent in [Path.cwd().resolve(), *Path.cwd().resolve().parents]:
        if (parent / ".git").exists():
            return parent

    return Path.cwd().resolve()


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

