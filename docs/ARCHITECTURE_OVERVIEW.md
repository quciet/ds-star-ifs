# Architecture Overview

This repository implements a **single-process Python orchestration loop** for a DS-STAR-style iterative coding agent. The system is not an Electron/React stack; instead, it is a CLI-driven Python package that coordinates role-oriented modules (analyzer, planner, coder, executor, debugger, verifier, router, finalyzer), a pluggable LLM client layer, and file-based run artifacts.

At runtime, `dsstar.cli:main` parses the `run` command, loads environment variables (and optionally `.env`), then selects an LLM provider (`mock`, `openai`, `gemini`, `local`). `run_loop` creates a timestamped run folder and iteratively executes:

1. **Analyze** user-provided input files.
2. **Plan** one todo step.
3. **Code** a full Python script for the next step.
4. **Execute** script in subprocess sandbox with timeout.
5. **Debug** and re-execute if the first execution fails.
6. **Verify** sufficiency (with hard guard that failed execution cannot be “sufficient”).
7. **Route** next action (add/backtrack/stop) and continue.
8. **Finalize** answer markdown.

All persisted state is file-based in `runs/<timestamp>/`. There is no database dependency in the codebase.

## Component diagram

```mermaid
flowchart LR
    User[User CLI command] --> CLI[dsstar.cli/main]
    CLI --> Config[config.py\n.env + env vars]
    CLI --> Registry[llm/registry.py]
    Registry --> LLM[(LLM Provider\nmock/openai/gemini/local)]

    CLI --> Loop[loop.run_loop]
    Loop --> Analyzer[agents/analyzer]
    Analyzer --> FileTool[tools/describe_files]

    Loop --> Planner[agents/planner]
    Loop --> Coder[agents/coder]
    Loop --> Executor[agents/executor]
    Executor --> Sandbox[tools/exec_sandbox]
    Loop --> Debugger[agents/debugger]
    Loop --> Verifier[agents/verifier]
    Loop --> Router[agents/router]
    Loop --> Finalyzer[agents/finalyzer]

    Loop --> Runs[(runs/<timestamp>/ artifacts)]
    Finalyzer --> Runs
```

## Sequence diagram (core workflow: one run with potential retry)

```mermaid
sequenceDiagram
    participant U as User
    participant C as CLI
    participant L as run_loop
    participant P as LLM client
    participant X as Python subprocess
    participant F as Run artifacts dir

    U->>C: dsstar run --question ... --provider ...
    C->>C: load dotenv/env + parse args
    C->>L: run_loop(question, files, client, ...)
    L->>F: write run_metadata.json
    L->>F: write descriptions.json (via analyzer)

    loop each round
        L->>P: planner prompt
        P-->>L: new step JSON
        L->>P: coder prompt
        P-->>L: python code
        L->>F: write round_XX_prompt.txt + round_XX_code.py

        L->>X: execute round_XX_code.py
        X-->>L: stdout/stderr/exit_code
        L->>F: write round_XX_exec.json

        alt first execution failed
            L->>P: debugger prompt (code + stderr)
            P-->>L: patched python code
            L->>F: overwrite round_XX_code.py
            L->>X: re-execute
            X-->>L: new execution result
        end

        L->>P: verifier prompt (or forced fail on non-zero exit)
        P-->>L: verifier JSON
        L->>P: router prompt (unless verifier sufficient)
        P-->>L: action JSON
    end

    L->>P: finalyzer prompt
    P-->>L: final markdown
    L->>F: write final_answer.md
    L-->>C: run path
    C-->>U: print final answer
```

## Critical invariants (must not break)

1. **Run artifact contract**
   - `run_loop` and tests assume timestamped run directory plus files like `round_00_code.py`, `round_00_exec.json`, and `final_answer.md`.
2. **Role-tag prompt protocol**
   - Mock/test clients branch on `ROLE: ...` markers (`PLANNER`, `CODER`, etc.); changing role headers without coordinated updates will break behavior/tests.
3. **Verifier failure guard**
   - If `exit_code != 0`, verifier must return insufficient/fix_step without calling the LLM; this prevents false success states.
4. **Router safety behavior**
   - `next_action == fix_step` must not be converted into stop; control flow forces additional work.
5. **Provider fallback semantics**
   - Missing `OPENAI_API_KEY` or `GEMINI_API_KEY` must fall back to `mock` with warning, keeping CLI runnable in low-config environments.
6. **Execution cwd semantics**
   - Generated scripts execute with cwd set to run directory, so relative writes (e.g., `hello.txt`) land in that run folder.
7. **Optional dependency behavior**
   - `.env` loading only occurs when `python-dotenv` is installed; `.xlsx` introspection only occurs when `openpyxl` is installed.
