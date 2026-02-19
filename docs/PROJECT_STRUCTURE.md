# Project Structure Audit

## Repository tree (pruned)

> Excludes: `.git/`, `__pycache__/`, `.venv/`, `node_modules/`, `dist/`, `build/`, large generated run artifacts.

```text
.
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml
├── docs/
│   ├── ARCHITECTURE_OVERVIEW.md
│   ├── ENTRYPOINTS.md
│   └── PROJECT_STRUCTURE.md
├── dsstar/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── loop.py
│   ├── prompts.py
│   ├── state.py
│   ├── agents/
│   │   ├── analyzer/analyzer.py
│   │   ├── coder/coder.py
│   │   ├── debugger/debugger.py
│   │   ├── executor/executor.py
│   │   ├── finalyzer/finalyzer.py
│   │   ├── planner/planner.py
│   │   ├── router/router.py
│   │   └── verifier/verifier.py
│   ├── llm/
│   │   ├── base.py
│   │   ├── gemini_client.py
│   │   ├── local_stub.py
│   │   ├── mock_client.py
│   │   ├── openai_client.py
│   │   └── registry.py
│   └── tools/
│       ├── describe_files.py
│       ├── exec_sandbox.py
│       └── log_utils.py
└── tests/
    └── test_smoke.py
```

## Top-level folder purposes

- **`dsstar/`**: Core application package for the DS-STAR iterative agent loop (CLI, orchestration loop, agent role modules, provider adapters, utility tools).
- **`tests/`**: Smoke/integration-style tests that execute CLI and loop behavior, including verifier safeguards.
- **`docs/`**: Architectural and operational documentation (added by this audit).

## Module inventory

| File/Module | Type (entrypoint/lib/test/script) | Purpose | Key I/O (reads/writes) | Depends on |
|---|---|---|---|---|
| `pyproject.toml` | config/build | Defines package metadata, optional deps, pytest config, and the console command `dsstar`. | Read by pip/build tooling. | hatchling, pytest (optional) |
| `README.md` | docs | Usage guide: install, run with providers, artifact layout. | Read by users. | N/A |
| `dsstar/__main__.py` | entrypoint | Enables `python -m dsstar`; delegates to CLI `main()`. | Reads CLI args indirectly; writes stdout via CLI. | `dsstar.cli` |
| `dsstar/cli.py` | entrypoint | Parses `run` subcommand args, loads dotenv, resolves provider client, starts `run_loop`, prints final answer. | Reads args/env vars; reads `final_answer.md`; writes stdout. | `argparse`, `config`, `llm.registry`, `loop` |
| `dsstar/config.py` | lib | Optional `.env` loading and env variable access helper. | Reads environment and optional `.env`. | `python-dotenv` (optional) |
| `dsstar/loop.py` | entrypoint/lib | Main orchestrator for iterative rounds: analyze -> plan -> code -> execute -> debug (if needed) -> verify -> route -> finalize. | Writes run artifacts (`run_metadata.json`, `plan.json`, round files, `final_answer.md`); reads generated code and execution results. | all agent modules, `state`, `tools.log_utils` |
| `dsstar/prompts.py` | lib | Builds role-specific prompts for analyzer/planner/coder/executor/verifier/router/debugger/finalyzer. | Pure string/json serialization in memory. | `json` |
| `dsstar/state.py` | lib | Dataclasses for plan/exec/verifier/router metadata and serialization helpers. | In-memory objects; serialized by callers. | `dataclasses` |
| `dsstar/agents/analyzer/analyzer.py` | lib role-module | Wraps file description and persists `descriptions.json` per run. | Reads input files via tools; writes `descriptions.json`. | `tools.describe_files`, `tools.log_utils` |
| `dsstar/agents/planner/planner.py` | lib role-module | Produces one new plan step from LLM response, with JSON coercion/fallback normalization. | Reads prompt context; emits dict step. | `prompts.planner_prompt`, LLM client |
| `dsstar/agents/coder/coder.py` | lib role-module | Creates coder prompt, persists it, asks LLM for full Python script, writes round code file. | Writes `round_XX_prompt.txt`, `round_XX_code.py`. | `prompts.coder_prompt`, LLM client, `write_text` |
| `dsstar/agents/executor/executor.py` | lib role-module | Executes generated Python script and writes structured execution log. | Reads `round_XX_code.py`; writes `round_XX_exec.json`. | `tools.exec_sandbox`, `write_json` |
| `dsstar/agents/debugger/debugger.py` | lib role-module | Requests patched code when execution fails. | Reads failing code/stderr context; returns patched code string. | `prompts.debugger_prompt`, LLM client |
| `dsstar/agents/verifier/verifier.py` | lib role-module | Judges whether output is sufficient; hard-fails sufficiency when execution failed; parses strict JSON response. | Reads last code + exec result; emits verifier dict. | `prompts.verifier_prompt`, LLM client |
| `dsstar/agents/router/router.py` | lib role-module | Chooses next control-flow action (`add_step/backtrack/stop`) with guard that forces progress on `fix_step`. | Reads verifier output/plan; emits router decision dict. | `prompts.router_prompt`, LLM client |
| `dsstar/agents/finalyzer/finalyzer.py` | lib role-module | Generates user-facing markdown summary and saves `final_answer.md`. | Writes `final_answer.md`. | `prompts.finalyzer_prompt`, LLM client, `write_text` |
| `dsstar/llm/base.py` | lib | Abstract `LLMClient` contract used by all providers. | In-memory. | `abc`, `dataclasses` |
| `dsstar/llm/registry.py` | lib | Provider selector and env-based fallback logic (`mock/openai/gemini/local`). | Reads env vars; prints warning to stdout. | provider clients, `config.get_env` |
| `dsstar/llm/mock_client.py` | lib/provider | Deterministic fake responses for each role prompt; supports smoke tests/demo. | Pure in-memory prompt->response mapping. | `json`, `LLMClient` |
| `dsstar/llm/openai_client.py` | lib/provider | Calls OpenAI Chat Completions HTTP API with API key/model. | Outbound HTTPS request; returns text response. | `urllib.request`, `json` |
| `dsstar/llm/gemini_client.py` | lib/provider | Calls Gemini `generateContent` HTTP API with API key/model. | Outbound HTTPS request; returns text response. | `urllib.parse/request`, `json` |
| `dsstar/llm/local_stub.py` | lib/provider | Placeholder local provider that raises runtime error until integrated. | Raises exception; no I/O. | `LLMClient` |
| `dsstar/tools/describe_files.py` | lib/tool | Lightweight file introspection for csv/json/xlsx/text + warnings for missing files; optional output dump. | Reads listed input files; optionally writes descriptions json. | `csv`, `json`, `openpyxl` (optional) |
| `dsstar/tools/exec_sandbox.py` | lib/tool | Runs Python script in subprocess with timeout and captures stdout/stderr/exit metadata. | Executes `python <script>` in run dir; returns structured result. | `subprocess`, `time` |
| `dsstar/tools/log_utils.py` | lib/tool | UTC logging, timestamped run directory creation, and JSON/text write helpers. | Writes run directories/files; prints logs. | `datetime`, `pathlib`, `json` |
| `tests/test_smoke.py` | test | Validates CLI run artifacts, relative run-dir behavior, verifier failure guard, and loop behavior under forced failures. | Spawns subprocess CLI; reads artifact files. | `pytest`, `subprocess`, `dsstar` modules |

## Entrypoints

### Primary app run

- **Module entrypoint**: `python -m dsstar run --question "..." --provider mock`
  - Flows through `dsstar/__main__.py` -> `dsstar.cli:main` -> `run_loop`.
- **Console script entrypoint**: `dsstar run --question "..." --provider mock`
  - Installed via `[project.scripts] dsstar = "dsstar.cli:main"`.

### Backend/engine scripts

- There are **no standalone backend services** or daemon processes in this repo.
- Role modules under `dsstar/agents/*` are invoked programmatically by `run_loop`.

### Tests

- `pytest` runs `tests/test_smoke.py`, including CLI subprocess tests and direct loop tests.

### Typical reproduction flow

1. Install editable package and optional extras.
2. Run `python -m dsstar run ...` with desired provider.
3. Inspect generated artifacts in `runs/<timestamp>/`.
4. Run `pytest` to validate basic functionality.

## Data & DB

- **No database layer** (no sqlite/postgres configs or DB schema files found).
- Runtime data is file-based under `runs/<timestamp>/`:
  - metadata (`run_metadata.json`), file descriptions (`descriptions.json`), plan (`plan.json`), round prompts/code/execution JSON, and final markdown answer.
- Input datasets are user-provided file paths passed through `--files` and interpreted by `describe_files`.
- Optional `.xlsx` inspection depends on `openpyxl` extra.

## Config locations and execution effects

- `pyproject.toml`
  - Declares package entrypoint and optional dependency groups (`dev`, `xlsx`, `dotenv`, `rich`).
- Environment variables (resolved in `llm/registry.py`):
  - `OPENAI_API_KEY`, `OPENAI_MODEL`
  - `GEMINI_API_KEY`, `GEMINI_MODEL`
  - `LOCAL_LLM_MODEL` (stub default only)
- Optional `.env` support:
  - `load_dotenv_if_available()` loads `.env` only if `python-dotenv` is installed.
- Runtime flags in CLI:
  - `--max-rounds`, `--timeout-sec`, `--run-dir` directly control iteration limit, script timeout, and artifact output location.
