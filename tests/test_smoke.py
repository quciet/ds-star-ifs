import subprocess
import sys
from pathlib import Path


def _latest_run(run_root: Path) -> Path:
    runs = [path for path in run_root.iterdir() if path.is_dir()]
    assert runs, "Run folder missing."
    return max(runs, key=lambda path: path.name)


def test_smoke(tmp_path: Path) -> None:
    cmd = [
        sys.executable,
        "-m",
        "dsstar",
        "run",
        "--question",
        "Create a python script that writes hello.txt with the text 'hello'.",
        "--provider",
        "mock",
        "--run-dir",
        str(tmp_path / "runs"),
    ]
    subprocess.run(cmd, check=True)

    run_root = tmp_path / "runs"
    run_path = _latest_run(run_root)

    assert (run_path / "round_00_code.py").exists()
    assert (run_path / "hello.txt").exists()
    assert (run_path / "final_answer.md").exists()
