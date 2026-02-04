from __future__ import annotations

import datetime


def log(message: str) -> None:
    timestamp = datetime.datetime.utcnow().isoformat(timespec="seconds")
    print(f"[{timestamp}] {message}")
