# Entrypoints

This file enumerates runnable entrypoints and how to invoke them.

## 1) Python module entry: `python -m dsstar`

- **Entry file**: `dsstar/__main__.py`
- **Code path**: `main()` from `dsstar/cli.py`
- **Working directory**: any; outputs go to `--run-dir` (default `./runs` relative to cwd).
- **Command example**:

```bash
python -m dsstar run --question "Create a python script that writes hello.txt" --provider mock
```

- **Required env vars**:
  - None for `mock`.
  - For `openai`: `OPENAI_API_KEY` (optional `OPENAI_MODEL`).
  - For `gemini`: `GEMINI_API_KEY` (optional `GEMINI_MODEL`).
  - For `deepseek`: `DEEPSEEK_API_KEY` (optional `DEEPSEEK_MODEL`, `DEEPSEEK_BASE_URL`).
  - For `local`: no required env var, but provider currently raises a runtime error.
- **Expected outputs**:
  - New run folder under `--run-dir` containing `run_metadata.json`, `descriptions.json`, `plan.json`, `round_XX_*`, `final_answer.md`.
  - Final answer printed to stdout.

## 2) Console script entry: `dsstar`

- **Entrypoint declaration**: `pyproject.toml` `[project.scripts] dsstar = "dsstar.cli:main"`
- **Prerequisite**: package installed (`pip install -e .`).
- **Command example**:

```bash
dsstar run --question "Summarize the dataset" --files data.csv --provider openai

# DeepSeek smoke test
export DEEPSEEK_API_KEY=...
dsstar run --provider deepseek --question "Reply with OK"
```

- **Required env vars**: same as module entry above.
- **Working directory**: any; same run-dir semantics.
- **Expected outputs**: same as module entry.

## 3) Test entrypoint: `pytest`

- **Test file**: `tests/test_smoke.py`
- **Working directory**: repository root.
- **Command examples**:

```bash
pytest
pytest tests/test_smoke.py::test_smoke -q
```

- **Required env vars**: none (tests use mock/fake clients).
- **Expected outputs**:
  - Pass/fail test report.
  - Temporary run folders in pytest tmp paths.

## 4) Direct library-level invocation (developer/internal)

These are not separate CLI scripts, but are runtime entry functions called by main flow:

- `dsstar.loop.run_loop(...)`
- Agent role runners:
  - `dsstar.agents.analyzer.analyzer.run(...)`
  - `dsstar.agents.planner.planner.run(...)`
  - `dsstar.agents.coder.coder.run(...)`
  - `dsstar.agents.executor.executor.run(...)`
  - `dsstar.agents.debugger.debugger.run(...)`
  - `dsstar.agents.verifier.verifier.run(...)`
  - `dsstar.agents.router.router.run(...)`
  - `dsstar.agents.finalyzer.finalyzer.run(...)`

These are intended to be imported and orchestrated by `run_loop` rather than launched as standalone scripts.

## 5) Batch/shell scripts

- No `scripts/*.py`, shell batch files, or cron-style executables were found in this repository.

## Runtime notes

- `--timeout-sec` controls subprocess timeout when executing generated code.
- `--max-rounds` controls loop iteration cap.
- `--run-dir` controls where all artifacts are created.
- Optional `.env` auto-loading occurs only if `python-dotenv` is installed.
