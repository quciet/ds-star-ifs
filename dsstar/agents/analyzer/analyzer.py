from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dsstar.agents.analyzer.master_manager import ensure_master, master_version_id
from dsstar.agents.analyzer.signature import compute_signature, probe_sample
from dsstar.llm.base import LLMClient
from dsstar.prompts import master_patch_prompt, override_prompt, promote_judge_prompt
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
        ".sqlite3": "sqlite",
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
        "version": 3,
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
            "signature": "",
            "master_version_id": "",
            "wrapper_path": None,
            "override_path": None,
            "exec": {"exit_code": 0, "stdout": "", "stderr": "", "runtime_ms": 0},
            "description_text": json.dumps(info, ensure_ascii=False),
            "status": "failed",
            "promote_decision": None,
            "file_type": str(info.get("type", "unknown")) if isinstance(info, dict) else "unknown",
            "mtime": int(stat.st_mtime) if stat else 0,
            "size": int(stat.st_size) if stat else 0,
            "sha256": _sha256(Path(file_path)) if Path(file_path).exists() else "",
            "fallback_facts": info if isinstance(info, dict) else {},
        }
    return migrated


def _load_existing(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"version": 3, "records": {}, "warnings": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 3, "records": {}, "warnings": ["Failed to parse existing descriptions.json"]}
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


def _failed_exec(exec_info: Dict[str, Any]) -> bool:
    stdout = str(exec_info.get("stdout", "")).strip()
    if int(exec_info.get("exit_code", 1)) != 0:
        return True
    if not stdout:
        return True
    return "FAILED TO DESCRIBE" in stdout


def _build_wrapper(wrapper_path: Path, file_path: Path, master_used_path: Path, override_path: Optional[Path]) -> str:
    override_literal = f"r'''{str(override_path.resolve())}'''" if override_path else "None"
    content = (
        "from __future__ import annotations\n"
        "import importlib.util\n"
        "import sys\n"
        "from pathlib import Path\n\n"
        "TARGET = Path(r'''" + str(file_path.resolve()) + "''')\n"
        "MASTER = Path(r'''" + str(master_used_path.resolve()) + "''')\n"
        "OVERRIDE = " + override_literal + "\n\n"
        "def _load(path: Path, module_name: str):\n"
        "    spec = importlib.util.spec_from_file_location(module_name, str(path))\n"
        "    if spec is None or spec.loader is None:\n"
        "        raise RuntimeError(f'cannot load module: {path}')\n"
        "    mod = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(mod)\n"
        "    return mod\n\n"
        "def _run() -> int:\n"
        "    errors = []\n"
        "    if OVERRIDE:\n"
        "        try:\n"
        "            omod = _load(Path(OVERRIDE), 'desc_override')\n"
        "            text = omod.describe_file(str(TARGET))\n"
        "            if text and str(text).strip():\n"
        "                print(str(text))\n"
        "                return 0\n"
        "        except Exception as exc:\n"
        "            errors.append(f'override_error: {exc}')\n"
        "    try:\n"
        "        mmod = _load(MASTER, 'desc_master')\n"
        "        text = mmod.describe_file(str(TARGET))\n"
        "        if text and str(text).strip():\n"
        "            print(str(text))\n"
        "            return 0\n"
        "        errors.append('master_empty_output')\n"
        "    except Exception as exc:\n"
        "        errors.append(f'master_error: {exc}')\n"
        "    sys.stderr.write('\\n'.join(errors) + '\\n')\n"
        "    return 1\n\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(_run())\n"
    )
    write_text(wrapper_path, content)
    return content


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return {}
    return {}


def _process_file(
    path: Path,
    run_dir: Path,
    master_used_path: Path,
    current_master_text: str,
    signature: str,
    fallback_facts: Dict[str, Any],
    client: Optional[LLMClient],
    fail_fix_budget: Dict[str, int],
) -> Dict[str, Any]:
    rel = _rel_str(path)
    stat = path.stat()
    mtime = int(stat.st_mtime)
    size = int(stat.st_size)
    sha = _sha256(path)
    file_id = f"{rel}::{mtime}:{size}"

    scripts_dir = run_dir / ".dsstar" / "desc_scripts"
    overrides_dir = run_dir / ".dsstar" / "desc_overrides"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    overrides_dir.mkdir(parents=True, exist_ok=True)

    wrapper_path = scripts_dir / f"{_safe_name(file_id)}.py"
    wrapper_source = _build_wrapper(wrapper_path, path, master_used_path, None)
    exec_info = _execute_script(wrapper_path)

    status = "master_ok"
    override_path: Optional[Path] = None
    promote_decision: Optional[Dict[str, Any]] = None

    if _failed_exec(exec_info):
        status = "failed"
        if client is not None and fail_fix_budget["remaining"] > 0:
            fail_fix_budget["remaining"] -= 1
            override_path = overrides_dir / f"{_safe_name(file_id)}_override.py"
            sample = probe_sample(path)
            log(f"Analyzer LLM call: override_gen ({rel})")
            prompt = override_prompt(
                file_path=str(path.resolve()),
                master_source=current_master_text,
                wrapper_source=wrapper_source,
                failure_stderr=str(exec_info.get("stderr", "")),
                file_sample=sample,
                fallback_facts=fallback_facts,
            )
            try:
                override_source = extract_python_code(client.complete(prompt))
                write_text(override_path, override_source)
                _build_wrapper(wrapper_path, path, master_used_path, override_path)
                exec_info = _execute_script(wrapper_path)
                if not _failed_exec(exec_info):
                    status = "override_ok"
                    log(f"Analyzer LLM call: promote_judge ({rel})")
                    judge_raw = client.complete(
                        promote_judge_prompt(
                            signature=signature,
                            failure_stderr=str(exec_info.get("stderr", "")),
                            override_source=override_source,
                        )
                    )
                    promote_decision = _extract_json(judge_raw)
                else:
                    status = "failed"
            except Exception as exc:  # pylint: disable=broad-except
                exec_info = {
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": f"override generation failed: {exc}",
                    "runtime_ms": 0,
                }

    stdout = str(exec_info.get("stdout", "")).strip()
    description_text = stdout if (not _failed_exec(exec_info) and stdout) else json.dumps(fallback_facts, ensure_ascii=False)

    return {
        "file_path": rel,
        "file_id": file_id,
        "signature": signature,
        "master_version_id": master_version_id(current_master_text),
        "wrapper_path": str(wrapper_path.relative_to(run_dir)),
        "override_path": str(override_path.relative_to(run_dir)) if override_path else None,
        "exec": exec_info,
        "description_text": description_text,
        "status": status,
        "promote_decision": promote_decision,
        "file_type": _file_type(path),
        "mtime": mtime,
        "size": size,
        "sha256": sha,
        "fallback_facts": fallback_facts,
        "desc_script": {"path": str(wrapper_path.relative_to(run_dir))},
        "desc_exec": exec_info,
    }


def run(
    files: List[str],
    run_dir: Path,
    client: Optional[LLMClient] = None,
    force: bool = False,
    refresh_master: bool = False,
    cluster_mode: bool = True,
    max_failures_to_fix_per_run: int = 5,
) -> Dict[str, Any]:
    """Analyze files by executing deterministic wrappers around a persistent master describer."""
    log("Analyzer: building executable file descriptions")
    descriptions_path = run_dir / "descriptions.json"
    payload = _load_existing(descriptions_path)
    records: Dict[str, Any] = payload.setdefault("records", {})
    warnings: List[str] = payload.setdefault("warnings", [])

    master_path = ensure_master(client=client, refresh_master=refresh_master)
    master_text = master_path.read_text(encoding="utf-8")
    run_master_path = run_dir / ".dsstar" / "describe_master_used.py"
    run_master_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(run_master_path, master_text)

    existing_by_rel: Dict[str, Dict[str, Any]] = {
        str(v.get("file_path")): v for v in records.values() if isinstance(v, dict) and v.get("file_path")
    }

    valid_files: List[Path] = []
    fallbacks: Dict[str, Dict[str, Any]] = {}
    signatures: Dict[str, str] = {}
    groups: Dict[str, List[Path]] = {}

    for raw in files:
        path = Path(raw)
        if not path.exists():
            warnings.append(f"Missing file: {raw}")
            continue
        rel = _rel_str(path)
        valid_files.append(path)
        fallbacks[rel] = _heuristic_fallback(path)
        sig = compute_signature(path)
        signatures[rel] = sig
        groups.setdefault(sig, []).append(path)

    budget = {"remaining": max_failures_to_fix_per_run}

    ordered: List[Path] = []
    if cluster_mode:
        for sig in sorted(groups.keys()):
            members = groups[sig]
            ordered.extend([members[0], *members[1:]])
    else:
        ordered = valid_files

    for path in ordered:
        rel = _rel_str(path)
        stat = path.stat()
        file_id = f"{rel}::{int(stat.st_mtime)}:{int(stat.st_size)}"
        existing = records.get(file_id) or existing_by_rel.get(rel)
        if (
            existing
            and not force
            and isinstance(existing.get("exec"), dict)
            and int(existing["exec"].get("exit_code", 1)) == 0
            and str(existing["exec"].get("stdout", "")).strip()
        ):
            records[file_id] = existing
            continue

        record = _process_file(
            path=path,
            run_dir=run_dir,
            master_used_path=run_master_path,
            current_master_text=master_text,
            signature=signatures[rel],
            fallback_facts=fallbacks[rel],
            client=client,
            fail_fix_budget=budget,
        )
        records[file_id] = record

        decision = record.get("promote_decision") or {}
        if record.get("status") == "override_ok" and bool(decision.get("promote")) and client is not None:
            override_path = run_dir / str(record["override_path"])
            if override_path.exists():
                log(f"Analyzer LLM call: master_patch ({rel})")
                patch_prompt = master_patch_prompt(
                    current_master=master_text,
                    signature=record["signature"],
                    failure_summary=str(record["exec"].get("stderr", "")),
                    override_code=override_path.read_text(encoding="utf-8"),
                )
                try:
                    patched = extract_python_code(client.complete(patch_prompt))
                    if patched.strip():
                        write_text(master_path, patched)
                        write_text(run_master_path, patched)
                        master_text = patched
                        no_override_wrapper = run_dir / ".dsstar" / "desc_scripts" / f"{_safe_name(record['file_id'])}_master_only.py"
                        _build_wrapper(no_override_wrapper, path, run_master_path, None)
                        check = _execute_script(no_override_wrapper)
                        if not _failed_exec(check):
                            record["status"] = "master_ok"
                            record["override_path"] = record.get("override_path")
                            record["exec"] = check
                            record["description_text"] = str(check.get("stdout", "")).strip()
                            record["master_version_id"] = master_version_id(master_text)
                except Exception as exc:  # pylint: disable=broad-except
                    warnings.append(f"Master patch failed for {rel}: {exc}")

    write_json(descriptions_path, payload)
    return payload
