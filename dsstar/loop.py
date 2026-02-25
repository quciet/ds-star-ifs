from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from dsstar.agents.analyzer.analyzer import run as run_analyzer
from dsstar.agents.coder.coder import run as run_coder
from dsstar.agents.debugger.debugger import run as run_debugger
from dsstar.agents.executor.executor import run as run_executor
from dsstar.agents.finalyzer.finalyzer import finalyzer_code, finalyzer_report
from dsstar.agents.planner.planner import run as run_planner
from dsstar.agents.router.router import run as run_router
from dsstar.agents.verifier.verifier import run as run_verifier
from dsstar.llm.base import LLMClient
from dsstar.state import RunMetadata
from dsstar.tools.log_utils import create_run_dir, log, write_json


def _next_todo(plan: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for step in plan:
        if step.get("status") == "todo":
            return step
    return None


def _append_plan_step(plan: List[Dict[str, Any]], step: Dict[str, Any]) -> None:
    plan.append(step)


def _truncate_to_before(plan: List[Dict[str, Any]], target_id: Optional[int]) -> None:
    if target_id is None:
        return
    plan[:] = [step for step in plan if int(step.get("id", 0)) < int(target_id)]


def _write_plan(run_dir: Path, plan: List[Dict[str, Any]]) -> None:
    write_json(run_dir / "plan.json", plan)


def run_loop(
    question: str,
    files: List[str],
    client: LLMClient,
    max_rounds: int,
    timeout_sec: int,
    run_root: Path,
) -> Path:
    run_path = create_run_dir(run_root)
    log(f"Run path: {run_path}")

    metadata = RunMetadata(
        provider=client.name,
        model=client.model,
        max_rounds=max_rounds,
        question=question,
        files=files,
    )
    write_json(run_path / "run_metadata.json", metadata.to_dict())

    artifacts: List[str] = ["run_metadata.json"]

    descriptions = run_analyzer(files, run_path, client=client)
    artifacts.append("descriptions.json")

    plan: List[Dict[str, Any]] = []
    last_exec: Optional[Dict[str, Any]] = None
    last_code: str = ""
    verifier_state: Dict[str, Any] = {
        "sufficient": False,
        "reason": "Not evaluated",
        "missing": [],
        "next_action": "add_step",
    }

    for round_idx in range(max_rounds):
        log(f"Round {round_idx:02d} starting")

        next_step = _next_todo(plan)
        if not next_step:
            new_step = run_planner(question, descriptions, plan, last_exec, client)
            _append_plan_step(plan, new_step)
            _write_plan(run_path, plan)
            next_step = new_step

        code_path = run_coder(
            question=question,
            descriptions=descriptions,
            plan=plan,
            next_step=next_step,
            previous_code=last_code,
            last_exec=last_exec,
            client=client,
            run_dir=run_path,
            round_idx=round_idx,
        )
        artifacts.extend([
            f"round_{round_idx:02d}_prompt.txt",
            f"round_{round_idx:02d}_code.py",
        ])

        last_code = code_path.read_text(encoding="utf-8")
        log(f"Round {round_idx:02d} coder success")

        exec_result = run_executor(code_path, run_path, timeout_sec, round_idx)
        artifacts.append(f"round_{round_idx:02d}_exec.json")
        last_exec = exec_result

        if exec_result["exit_code"] != 0:
            log(f"Round {round_idx:02d} executor failed -> debugger route")
            debug_code = run_debugger(
                question=question,
                descriptions=descriptions,
                plan=plan,
                failing_code=last_code,
                exec_result=exec_result,
                client=client,
                run_dir=run_path,
                round_idx=round_idx,
            )
            code_path.write_text(debug_code, encoding="utf-8")
            last_code = debug_code
            artifacts.extend([
                f"round_{round_idx:02d}_trace_summary.json",
                f"round_{round_idx:02d}_code_patched.py",
            ])
            exec_result = run_executor(code_path, run_path, timeout_sec, round_idx)
            last_exec = exec_result

        verifier_state = run_verifier(
            question=question,
            descriptions=descriptions,
            plan=plan,
            last_code=last_code,
            last_exec=last_exec,
            client=client,
        )

        if exec_result["exit_code"] == 0 and next_step:
            next_step["status"] = "done"
            _write_plan(run_path, plan)

        if verifier_state.get("sufficient"):
            log(f"Round {round_idx:02d} verifier sufficient")
            break

        if exec_result["exit_code"] != 0:
            log(f"Round {round_idx:02d} failed even after debugger; skipping router")
            continue

        router_state = run_router(verifier_state, plan, client)
        action = router_state.get("action", "add_step")

        if action == "stop":
            log("Router requested stop")
            break
        if action == "backtrack":
            backtrack_id = router_state.get("backtrack_to_step_id")
            log(f"Router decided backtrack to step_id={backtrack_id}")
            _truncate_to_before(plan, backtrack_id)
            _write_plan(run_path, plan)
        else:
            log("Router decided add_step")
            new_step = run_planner(question, descriptions, plan, last_exec, client)
            _append_plan_step(plan, new_step)
            _write_plan(run_path, plan)

    if verifier_state.get("sufficient") and last_exec and int(last_exec.get("exit_code", 1)) == 0:
        final_code_path = finalyzer_code(
            question=question,
            plan=plan,
            descriptions=descriptions,
            last_working_code=last_code,
            client=client,
            run_dir=run_path,
        )
        artifacts.append("final_solution.py")

        final_exec = run_executor(final_code_path, run_path, timeout_sec, 99)
        write_json(run_path / "final_solution_exec.json", final_exec)
        artifacts.append("final_solution_exec.json")

        if int(final_exec.get("exit_code", 1)) == 0:
            artifact_manifest = {"artifacts": artifacts, "run_path": str(run_path)}
            finalyzer_report(
                question=question,
                plan=plan,
                artifact_manifest=artifact_manifest,
                final_exec=final_exec,
                client=client,
                run_dir=run_path,
            )
            artifacts.append("final_answer.md")
            log("Final answer written")
    return run_path
