# Development Plan

## Current status

- Single-process CLI orchestrator is in place, and each run writes artifacts to `runs/<timestamp>/`.
- DS-STAR-faithful loop is implemented across analyzer -> planner -> coder -> executor -> debugger -> verifier -> router -> finalyzer.
- Analyzer generates and executes per-file description scripts and stores outputs in `descriptions.json` and `.dsstar/desc_scripts` under the run folder.
- Debugger uses a 2-stage flow (trace summary and patched code generation) before re-execution.
- Router supports `add_step`, `backtrack`, and `stop` decisions.
- Final report generation only occurs after final solution code is re-executed and validated successfully.

## How to test quickly

1. Drop one or more ad-hoc data files in `input/` (for example: CSV, TSV, XLSX, JSON, TXT, Parquet, SQLite).
2. Run with mock provider:
   ```bash
   python -m dsstar run --question "Describe the inputs" --provider mock
   ```
3. Run with DeepSeek provider:
   ```bash
   python -m dsstar run --question "Describe the inputs" --provider deepseek --timeout-sec 120
   ```
4. Inspect outputs in the latest run folder:
   - `runs/<timestamp>/descriptions.json`
   - `runs/<timestamp>/.dsstar/desc_scripts/`

## Next steps (placeholder)

- Add IFs-specific schema and semantic profiling heuristics for analyzer descriptions.
- Add IFs-oriented planner templates for common exploratory and validation task patterns.
- Add domain-aware verifier checks for IFs assumptions and evidence completeness.
- Add IFs benchmark tasks and regression fixtures for end-to-end quality tracking.
