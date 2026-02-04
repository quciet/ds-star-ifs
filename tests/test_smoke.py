import subprocess
import sys
from pathlib import Path


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
    runs = list(run_root.iterdir())
    assert runs, "Run folder missing."
    run_path = runs[0]

    assert (run_path / "round_00_code.py").exists()
    assert (run_path / "hello.txt").exists()
    assert (run_path / "final_answer.md").exists()
