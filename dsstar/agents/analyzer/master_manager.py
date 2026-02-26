from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from dsstar.llm.base import LLMClient
from dsstar.prompts import master_describer_prompt
from dsstar.tools.log_utils import log
from dsstar.tools.text_utils import extract_python_code

MASTER_PATH = Path("dsstar/knowledge/describe_master.py")


FALLBACK_MASTER = '''from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path


def describe_file(path: str) -> str:
    p = Path(path)
    try:
        size = p.stat().st_size
        ext = p.suffix.lower()
        lines = [f"FILE={p}", f"EXT={ext}", f"SIZE={size}"]
        if ext in {".csv", ".tsv"}:
            delim = "\t" if ext == ".tsv" else ","
            with p.open("r", encoding="utf-8", errors="replace") as handle:
                reader = csv.reader(handle, delimiter=delim)
                rows = list(reader)
            if rows:
                lines.append("COLUMNS=" + ",".join(rows[0]))
                lines.append("ROW_COUNT=" + str(max(len(rows) - 1, 0)))
        elif ext in {".json"}:
            payload = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            lines.append("JSON_TYPE=" + type(payload).__name__)
        elif ext in {".db", ".sqlite", ".sqlite3"}:
            conn = sqlite3.connect(str(p))
            cur = conn.cursor()
            tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
            conn.close()
            lines.append("TABLES=" + ",".join(tables))
        else:
            snippet = p.read_text(encoding="utf-8", errors="replace")[:400]
            lines.append("SNIPPET=" + snippet.replace("\n", " "))
        return "\n".join(lines)
    except Exception as exc:
        return f"FAILED TO DESCRIBE: {exc}"
'''


def ensure_master(client: Optional[LLMClient], refresh_master: bool = False) -> Path:
    MASTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MASTER_PATH.exists() and not refresh_master:
        return MASTER_PATH

    content = ""
    if client is not None:
        try:
            log("Analyzer LLM call: master_gen")
            content = extract_python_code(client.complete(master_describer_prompt()))
        except Exception as exc:  # pylint: disable=broad-except
            log(f"Analyzer: master generation failed, using fallback ({exc})")
    if not content.strip():
        content = FALLBACK_MASTER
    MASTER_PATH.write_text(content, encoding="utf-8")
    return MASTER_PATH


def master_version_id(master_content: str) -> str:
    return hashlib.sha256(master_content.encode("utf-8")).hexdigest()
