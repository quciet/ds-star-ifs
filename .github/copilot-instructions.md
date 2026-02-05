Welcome — this file gives focused, actionable guidance for AI coding agents working on this DS-STAR repository.

Keep this short and concrete. Reference specific files and patterns when possible.

1) Big-picture architecture (what runs where)
- The project implements a minimal DS-STAR iterative agent (see `README.md`). The main entrypoint is the CLI script `dsstar.cli:main` (installed as the `dsstar` console script in `pyproject.toml`). Running `python -m dsstar run ...` executes `dsstar.loop.run_loop` which coordinates role-based agents.
- Major components (under `dsstar/`):
  - `agents/*` — role implementations (analyzer, planner, coder, executor, debugger, verifier, router, finalyzer). Each agent exposes a `run(...)` function and returns simple Python-native types (dicts/strings/paths).
  - `llm/*` — LLM adapter implementations and registry (`get_client`). Supported providers: `mock`, `openai`, `gemini`, `local` (stub).
  - `prompts.py` — canonical prompt builders for every role. Agents call LLM clients with these prompts and expect strict JSON or code in specific formats.
  - `tools/*` — small local utilities (file description, sandboxed execution, logging, run-dir management).
  - `loop.py` — orchestrator: creates run dir, writes artifacts, loops through rounds, calls agents, and writes `final_answer.md`.

2) Data flow and important artifacts
- A single run writes to `./runs/<timestamp>/`. Key artifacts and their producers:
  - `run_metadata.json` — written in `loop.run_loop` from `state.RunMetadata`.
  - `descriptions.json` — produced by `agents.analyzer` (uses `tools.describe_files.describe_files`).
  - `plan.json` — produced and mutated by the planner and the loop.
  - `round_XX_prompt.txt` and `round_XX_code.py` — written by `agents.coder` (uses `prompts.coder_prompt`).
  - `round_XX_exec.json` — produced by `agents.executor` after `tools.exec_sandbox.run_python_script`.
  - `final_answer.md` — produced by `agents.finalyzer`.

3) LLM integration patterns (very important)
- Agents use `client.complete(prompt)` for all LLM calls. The `mock` client returns deterministic, test-friendly values (see `llm/mock_client.py`).
- Prompts have strict expected output formats. Examples:
  - `prompts.planner_prompt` expects a single JSON object describing the new step. Planner code will fallback to using raw text if JSON parse fails (coerce logic in `agents.planner`).
  - `prompts.coder_prompt` expects a Python script as plain text; the `coder` writes the script to `round_XX_code.py` and the executor runs it.
  - `prompts.verifier_prompt` expects JSON: {"sufficient": bool, "reason": str, "missing": [], "next_action": "add_step|fix_step|stop"}. The verifier also enforces failed-execution semantics locally: if last exec had non-zero exit code, the verifier returns fix_step without calling the LLM.
  - `prompts.router_prompt` expects JSON: {"action": "add_step"|"backtrack"|"stop", "backtrack_to_step_id": int|null}.

4) Testing and smoke runs
- The repo includes a pytest smoke test (`tests/test_smoke.py`) which runs the CLI as a subprocess using the `mock` provider. Tests expect the run artifacts to be created and verify verifier behavior without calling an external LLM.
- To run tests locally: use the dev optional dependencies (pytest). The project uses `pyproject.toml` with `hatchling` build-backend.

5) Project-specific conventions and gotchas
- Role functions all follow a simple contract: `run(...)` returns a small Python-native type (string, dict, Path). Keep this when modifying agents.
- Prompts are canonical single-source-of-truth in `prompts.py`. If you change prompt wording, check all agent tests and `runs/` artifacts for expected formats.
- Executor runs scripts with the CWD set to the run directory. Generated code should reference relative paths in the run dir (e.g., `Path('hello.txt')`). `tools.exec_sandbox.run_python_script` calls `python <abs_path>` with `cwd=run_dir` so be careful about path construction.
- The loop writes artifacts with predictable filenames (see `loop.py`). Tests and downstream tooling rely on those exact names (e.g., `round_00_code.py`, `round_00_exec.json`).
- The `local` LLM provider is intentionally a stub and will raise; prefer `mock` for tests and `openai`/`gemini` for real runs with proper API keys in env vars.

6) Examples to copy when generating outputs
- Planner returned JSON example (from `llm/mock_client.py`):
  {"id": 1, "title": "Write hello.txt", "details": "Create hello.txt in the run directory containing 'hello'.", "status": "todo"}
- Coder output example (exact script expected):
  from pathlib import Path
  Path('hello.txt').write_text('hello', encoding='utf-8')
  print('wrote hello.txt')
- Verifier JSON example (exact keys expected):
  {"sufficient": true, "reason": "hello.txt created.", "missing": [], "next_action": "stop"}

7) Suggested priorities for an AI agent contributing code
- Low-risk: update prompts in `prompts.py` to sharpen expected JSON shapes, add fields to `descriptions.json` output, improve logging messages.
- Medium-risk: modify or add LLM adapters in `llm/` (e.g., a new provider). Keep `get_client` fallback behavior intact.
- Higher-risk: changing loop semantics (artifact names, step id logic, router behavior) — these affect tests and backward compatibility and need corresponding test updates.

8) Useful files to inspect when debugging a run
- `dsstar/loop.py` (orchestrator)
- `dsstar/prompts.py` (prompt templates)
- `dsstar/agents/*.py` (role logic; each agent has a small and obvious contract)
- `dsstar/llm/*.py` (adapters and `get_client`)
- `dsstar/tools/*` (sandbox and file describer)
- `tests/test_smoke.py` (example of how the CLI is exercised in CI)

If any of these sections are unclear or you want more examples/caveats (for instance, how to add a provider or change prompt contracts safely), say which part and I'll expand or iterate.
