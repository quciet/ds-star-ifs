from pathlib import Path

from dsstar.agents.analyzer.analyzer import run as run_analyzer


def test_analyzer_writes_desc_scripts_and_unified_json(tmp_path: Path) -> None:
    data = tmp_path / "data.csv"
    data.write_text("a,b\n1,2\n", encoding="utf-8")

    out = run_analyzer([str(data)], tmp_path, client=None)

    assert "records" in out
    assert len(out["records"]) == 1
    record = next(iter(out["records"].values()))
    assert record["file_path"].endswith("data.csv")
    assert "desc_script" in record and "path" in record["desc_script"]
    assert (tmp_path / record["desc_script"]["path"]).exists()
    assert "desc_exec" in record and "exit_code" in record["desc_exec"]
    assert "description_text" in record
