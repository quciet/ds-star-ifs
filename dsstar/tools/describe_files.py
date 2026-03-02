from __future__ import annotations

import csv
import json

from pathlib import Path
from typing import Any, Dict, List, Optional


def _infer_type(value: str) -> str:
    if value == "":
        return "empty"
    try:
        int(value)
        return "int"
    except ValueError:
        pass
    try:
        float(value)
        return "float"
    except ValueError:
        pass
    return "str"


def _describe_csv(path: Path) -> Dict[str, Any]:
    rows: List[List[str]] = []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.reader(handle)
        for _ in range(6):
            try:
                rows.append(next(reader))
            except StopIteration:
                break
    header = rows[0] if rows else []
    sample_rows = rows[1:6] if rows else []
    type_hints = []
    if sample_rows and header:
        for col_idx, name in enumerate(header):
            sample_values = [row[col_idx] for row in sample_rows if col_idx < len(row)]
            inferred = {_infer_type(value) for value in sample_values if value is not None}
            type_hints.append({"column": name, "types": sorted(inferred)})
    return {
        "type": "csv",
        "header": header,
        "sample_rows": sample_rows,
        "type_hints": type_hints,
    }


def _describe_text(path: Path) -> Dict[str, Any]:
    content = path.read_text(encoding="utf-8", errors="replace")
    snippet = content[:2000]
    return {"type": "text", "length": len(content), "snippet": snippet}


def _describe_json(path: Path) -> Dict[str, Any]:
    content = path.read_text(encoding="utf-8", errors="replace")
    snippet = content[:2000]
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            summary = {
                "kind": "object",
                "keys": list(parsed.keys())[:20],
            }
        elif isinstance(parsed, list):
            summary = {
                "kind": "list",
                "length": len(parsed),
                "sample": parsed[:5],
            }
        else:
            summary = {"kind": type(parsed).__name__}
    except json.JSONDecodeError:
        summary = {"kind": "invalid_json"}
    return {
        "type": "json",
        "summary": summary,
        "length": len(content),
        "snippet": snippet,
    }


def _read_excel_df(path: Path):
    import pandas as pd
    suffix = path.suffix.lower()
    if suffix == ".xls":
        return pd.read_excel(path, sheet_name=0, engine="xlrd")
    if suffix == ".xlsx":
        return pd.read_excel(path, sheet_name=0)
    raise ValueError(f"Unsupported Excel suffix: {suffix}")


def _describe_excel(path: Path) -> Dict[str, Any]:
    df = _read_excel_df(path)
    sample_rows = df.head(5).fillna("").astype(str).values.tolist()
    return {
        "type": path.suffix.lower().lstrip("."),
        "header": [str(col) for col in df.columns.tolist()],
        "sample_rows": sample_rows,
        "row_count": int(df.shape[0]),
    }


def describe_files(paths: List[str], output_path: Optional[Path] = None) -> Dict[str, Any]:
    descriptions: Dict[str, Any] = {"files": {}, "warnings": []}
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            descriptions["warnings"].append(f"Missing file: {raw}")
            continue
        suffix = path.suffix.lower()
        try:
            if suffix == ".csv":
                info = _describe_csv(path)
            elif suffix in {".xlsx", ".xls"}:
                info = _describe_excel(path)
            elif suffix == ".json":
                info = _describe_json(path)
            elif suffix in {".txt", ".md"}:
                info = _describe_text(path)
            else:
                info = _describe_text(path)
            descriptions["files"][raw] = info
        except Exception as exc:  # pylint: disable=broad-except
            if suffix == ".xls":
                message = f"{exc}. Legacy .xls requires pandas+xlrd; convert to .xlsx if needed."
                descriptions["files"][raw] = {
                    "type": "xls",
                    "path": str(path),
                    "name": path.name,
                    "anomalies": [message],
                }
                descriptions["warnings"].append(f"Failed to describe {raw}: {message}")
                continue
            descriptions["warnings"].append(f"Failed to describe {raw}: {exc}")
    if output_path:
        output_path.write_text(json.dumps(descriptions, indent=2), encoding="utf-8")
    return descriptions
