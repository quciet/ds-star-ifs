from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from typing import Optional


def load_dotenv_if_available() -> None:
    if importlib.util.find_spec("dotenv") is None:
        return
    from dotenv import load_dotenv

    load_dotenv()


@dataclass
class ProviderConfig:
    provider: str
    model: Optional[str]
    timeout_sec: int
    run_dir: str


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(key, default)
