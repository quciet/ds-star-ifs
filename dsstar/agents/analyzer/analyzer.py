from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dsstar.llm.base import LLMClient
from dsstar.prompts import description_script_prompt
from dsstar.tools.describe_files import describe_files
from dsstar.tools.log_utils import log, write_json, write_text
from dsstar.tools.text_utils import extract_python_code


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".csv": "csv",
        ".tsv": "tsv",
        ".xlsx": "xlsx",
        ".xls": "xlsx",
        ".db": "sqlite",
        ".sqlite": "sqlite",
        ".parquet": "parquet",
        ".json": "json",
        ".zip": "zip",
    }.get(suffix, "unknown")


def _rel_str(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())


def _sha256(path: Path, max_bytes: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        remaining = max_bytes
        while remaining > 0:
            chunk = handle.read(min(65536, remaining))
            if not chunk:
                break
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value)[:120]


def _migrate(raw: Dict[str, Any]) -> Dict[str, Any]:
    if "records" in raw and isinstance(raw["records"], dict):
        return raw

    migrated: Dict[str, Any] = {
        "version": 2,
        "records": {},
        "warnings": list(raw.get("warnings", [])) if isinstance(raw, dict) else [],
    }
    files = raw.get("files", {}) if isinstance(raw, dict) else {}
    for file_path, info in files.items():
        rel = _rel_str(Path(file_path))
        stat = Path(file_path).stat() if Path(file_path).exists() else None
        file_id = f"{rel}::{int(stat.st_mtime) if stat else 0}:{int(stat.st_size) if stat else 0}"
        migrated["records"][file_id] = {
            "file_path": rel,
            "file_id": file_id,
            "file_type": str(info.get("type", "unknown")) if isinstance(info, dict) else "unknown",
            "mtime": int(stat.st_mtime) if stat else 0,
            "size": int(stat.st_size) if stat else 0,
            "sha256": _sha256(Path(file_path)) if Path(file_path).exists() else "",
            "desc_script": {
                "path": None,
                "content": "",
                "llm_model": "",
                "generated_by": "legacy_migrated",
                "created_at": _now_iso(),
            },
            "desc_exec": {"exit_code": 0, "stdout": "", "stderr": "", "runtime_ms": 0},
            "description_text": json.dumps(info, ensure_ascii=False),
            "fallback_facts": info if isinstance(info, dict) else {},
        }
    return migrated


def _load_existing(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"version": 2, "records": {}, "warnings": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 2, "records": {}, "warnings": ["Failed to parse existing descriptions.json"]}
    return _migrate(raw)


def _heuristic_fallback(path: Path) -> Dict[str, Any]:
    return describe_files([str(path)]).get("files", {}).get(str(path), {})


def _execute_script(script_path: Path, timeout_sec: int = 25) -> Dict[str, Any]:
    start = time.perf_counter()
    proc = subprocess.run(
        [os.environ.get("PYTHON", "python"), str(script_path)],
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    runtime_ms = int((time.perf_counter() - start) * 1000)
    return {
        "exit_code": int(proc.returncode),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "runtime_ms": runtime_ms,
    }


def run(
    files: List[str],
    run_dir: Path,
    client: Optional[LLMClient] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Analyze files by generating and executing per-file description scripts."""
    log("Analyzer: building executable file descriptions")
    descriptions_path = run_dir / "descriptions.json"
    desc_scripts_dir = run_dir / ".dsstar" / "desc_scripts"
    desc_scripts_dir.mkdir(parents=True, exist_ok=True)

    payload = _load_existing(descriptions_path)
    records: Dict[str, Any] = payload.setdefault("records", {})
    warnings: List[str] = payload.setdefault("warnings", [])

    for raw in files:
        path = Path(raw)
        if not path.exists():
            warnings.append(f"Missing file: {raw}")
            continue

        rel = _rel_str(path)
        stat = path.stat()
        mtime = int(stat.st_mtime)
        size = int(stat.st_size)
        sha = _sha256(path)
        file_id = f"{rel}::{mtime}:{size}"

        existing = records.get(file_id)
        if (
            not force
            and existing
            and isinstance(existing.get("desc_exec"), dict)
            and int(existing["desc_exec"].get("exit_code", 1)) == 0
            and str(existing["desc_exec"].get("stdout", "")).strip()
        ):
            log(f"Analyzer: cache hit for {rel}")
            continue

        ftype = _file_type(path)
        fallback_facts = _heuristic_fallback(path)
        prompt = description_script_prompt(str(path.resolve()), ftype)

        script_content = ""
        generated_by = "llm"
        if client is not None:
            try:
                script_content = extract_python_code(client.complete(prompt))
            except Exception as exc:  # pylint: disable=broad-except
                log(f"Analyzer: LLM unavailable for {rel}, using fallback script ({exc})")
                generated_by = "fallback"
        else:
            generated_by = "fallback"

        if not script_content.strip():
            generated_by = "fallback"
            script_content = (
                "from pathlib import Path\n"
                "import json\n"
                f"p=Path(r'''{str(path.resolve())}''')\n"
                "try:\n"
                "    text = p.read_text(encoding='utf-8', errors='replace')[:1200]\n"
                "    print('FILE=' + str(p))\n"
                "    print('TYPE=fallback_text')\n"
                "    print('SIZE=' + str(p.stat().st_size))\n"
                "    print('SNIPPET=' + text.replace('\\n',' '))\n"
                "except Exception as e:\n"
                "    print('FAILED TO DESCRIBE: ' + str(e))\n"
            )

        script_path = desc_scripts_dir / f"{_safe_name(file_id)}.py"
        write_text(script_path, script_content)

        try:
            exec_info = _execute_script(script_path)
        except subprocess.TimeoutExpired:
            exec_info = {
                "exit_code": 124,
                "stdout": "",
                "stderr": "timeout",
                "runtime_ms": 25000,
            }

        stdout = str(exec_info.get("stdout", "")).strip()
        if int(exec_info.get("exit_code", 1)) == 0 and stdout:
            description_text = stdout
        else:
            description_text = json.dumps(fallback_facts, ensure_ascii=False)

        records[file_id] = {
            "file_path": rel,
            "file_id": file_id,
            "file_type": ftype,
            "mtime": mtime,
            "size": size,
            "sha256": sha,
            "desc_script": {
                "path": str(script_path.relative_to(run_dir)),
                "content": script_content,
                "llm_model": client.model if client else "",
                "generated_by": generated_by,
                "created_at": _now_iso(),
            },
            "desc_exec": exec_info,
            "description_text": description_text,
            "fallback_facts": fallback_facts,
        }

    write_json(descriptions_path, payload)
    return payload
