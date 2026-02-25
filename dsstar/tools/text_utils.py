from __future__ import annotations

import re


def extract_python_code(text: str) -> str:
    """Extract Python code from raw LLM text, handling fenced output defensively."""
    raw = text.strip()
    if not raw:
        return ""

    fenced = re.search(r"```python\s*(.*?)```", raw, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    generic = re.search(r"```\s*(.*?)```", raw, flags=re.DOTALL)
    if generic:
        return generic.group(1).strip()

    return raw
