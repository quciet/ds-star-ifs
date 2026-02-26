import os
import subprocess
import sys
import json
from dataclasses import dataclass
from pathlib import Path

from dsstar.agents.verifier.verifier import run as run_verifier
from dsstar.llm.base import LLMClient
from dsstar.loop import run_loop


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
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        "DSSTAR_REPO_ROOT": str(tmp_path),
    }
    subprocess.run(cmd, check=True, cwd=str(tmp_path), env=env)

    run_root = tmp_path / "runs"
    run_path = _latest_run(run_root)

    assert (run_path / "round_00_code.py").exists()
    assert (tmp_path / "hello.txt").exists()
    assert (run_path / "final_solution.py").exists()
    assert (run_path / "final_answer.md").exists()

    metadata = json.loads((run_path / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["repo_root"] == str(tmp_path.resolve())
    assert metadata["executor_cwd"] == str(tmp_path.resolve())

    exec_result = json.loads((run_path / "round_00_exec.json").read_text(encoding="utf-8"))
    assert exec_result["cwd"] == str(tmp_path.resolve())
    assert exec_result["script_path"] == str((run_path / "round_00_code.py").resolve())


def test_smoke_with_relative_run_dir(tmp_path: Path) -> None:
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
        "runs",
    ]
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
    env["DSSTAR_REPO_ROOT"] = str(tmp_path)
    subprocess.run(cmd, check=True, cwd=str(tmp_path), env=env)

    run_root = tmp_path / "runs"
    run_path = _latest_run(run_root)

    assert (run_path / "round_00_code.py").exists()
    assert (tmp_path / "hello.txt").exists()
    assert (run_path / "final_solution.py").exists()
    assert (run_path / "final_answer.md").exists()

    metadata = json.loads((run_path / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["repo_root"] == str(tmp_path.resolve())
    assert metadata["executor_cwd"] == str(tmp_path.resolve())


@dataclass
class _CountingVerifierClient(LLMClient):
    name: str = "test"
    model: str = "test-model"
    calls: int = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        return json.dumps(
            {
                "sufficient": True,
                "reason": "LLM should not be called for failed execution.",
                "missing": [],
                "next_action": "stop",
            }
        )


def test_verifier_rejects_failed_execution_without_llm() -> None:
    client = _CountingVerifierClient()
    result = run_verifier(
        question="any",
        descriptions={},
        plan=[],
        last_code="raise RuntimeError('boom')",
        last_exec={"exit_code": 1, "stderr": "boom"},
        client=client,
    )

    assert result == {
        "sufficient": False,
        "reason": "Last code execution failed (non-zero exit code).",
        "missing": ["Successful execution (exit_code=0)"],
        "next_action": "debug",
    }
    assert client.calls == 0


@dataclass
class _FailingLoopClient(LLMClient):
    name: str = "test"
    model: str = "test-model"

    def complete(self, prompt: str) -> str:
        if "ROLE: PLANNER" in prompt:
            return json.dumps(
                {
                    "id": 1,
                    "title": "Failing step",
                    "details": "Intentionally fail.",
                    "status": "todo",
                }
            )
        if "ROLE: CODER" in prompt or "ROLE: DEBUGGER_PATCH" in prompt:
            return "raise RuntimeError('forced failure')\n"
        if "ROLE: VERIFIER" in prompt:
            return json.dumps(
                {
                    "sufficient": True,
                    "reason": "incorrectly sufficient",
                    "missing": [],
                    "next_action": "stop",
                }
            )
        if "ROLE: ROUTER" in prompt:
            return json.dumps({"action": "stop", "backtrack_to_step_id": None})
        if "ROLE: DEBUGGER_TRACE_SUMMARY" in prompt:
            return json.dumps({"error_type":"RuntimeError","likely_root_cause":"forced failure","key_trace_lines":["RuntimeError"],"suggested_fix_focus":"fix"})
        if "ROLE: FINALYZER_CODE" in prompt:
            return "from pathlib import Path\n\ndef main():\n    Path('hello.txt').write_text('hello', encoding='utf-8')\n\nif __name__ == '__main__':\n    main()\n"
        if "ROLE: FINALYZER_REPORT" in prompt:
            return "final"
        return "Unsupported prompt."


def test_loop_does_not_stop_on_fix_step_after_failed_exec(tmp_path: Path) -> None:
    run_path = run_loop(
        question="Force an execution failure.",
        files=[],
        client=_FailingLoopClient(),
        max_rounds=2,
        timeout_sec=5,
        run_root=tmp_path / "runs",
    )

    round_00_exec = json.loads((run_path / "round_00_exec.json").read_text(encoding="utf-8"))
    assert round_00_exec["exit_code"] != 0
    assert (run_path / "round_01_code.py").exists()
