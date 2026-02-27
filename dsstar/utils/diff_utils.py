from __future__ import annotations

import difflib
from pathlib import Path


def write_unified_diff(old_text: str, new_text: str, out_path: Path, rel_path: str) -> None:
    """Write a unified diff artifact for a repo-relative file path."""
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    diff = difflib.unified_diff(
        old_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
    )
    out_path.write_text("".join(diff), encoding="utf-8")
