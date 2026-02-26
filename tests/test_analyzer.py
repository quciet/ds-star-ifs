from pathlib import Path

from dsstar.agents.analyzer.analyzer import run as run_analyzer


def test_analyzer_writes_wrappers_and_unified_json(tmp_path: Path) -> None:
    data = tmp_path / "data.csv"
    data.write_text("a,b\n1,2\n", encoding="utf-8")

    out = run_analyzer([str(data)], tmp_path, client=None)

    assert "records" in out
    assert len(out["records"]) == 1
    record = next(iter(out["records"].values()))
    assert record["file_path"].endswith("data.csv")
    assert record["wrapper_path"].endswith(".py")
    assert (tmp_path / record["wrapper_path"]).exists()
    assert "exec" in record and "exit_code" in record["exec"]
    assert "description_text" in record
    assert "master_version_id" in record
    assert record["status"] in {"master_ok", "override_ok", "failed"}
