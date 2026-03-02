from pathlib import Path

from dsstar.cli import _discover_input_files
from dsstar.tools.describe_files import describe_files


def test_discover_input_files_includes_xls(tmp_path: Path) -> None:
    (tmp_path / "b.xlsx").write_text("xlsx", encoding="utf-8")
    (tmp_path / "a.xls").write_text("xls", encoding="utf-8")
    (tmp_path / "c.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    discovered = _discover_input_files(str(tmp_path))

    assert discovered == [
        str(tmp_path / "a.xls"),
        str(tmp_path / "b.xlsx"),
        str(tmp_path / "c.csv"),
    ]


def test_describe_xls_includes_fallback_entry_on_read_error(tmp_path: Path) -> None:
    xls_path = tmp_path / "legacy.xls"
    xls_path.write_text("not-a-real-xls", encoding="utf-8")

    descriptions = describe_files([str(xls_path)])

    assert str(xls_path) in descriptions["files"]
    entry = descriptions["files"][str(xls_path)]
    assert entry["type"] == "xls"
    assert "Legacy .xls requires pandas+xlrd" in entry["anomalies"][0]
