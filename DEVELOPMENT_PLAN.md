# Development Plan

## Analyzer flow (updated)
1. Analyzer reuses a persistent master describer at `dsstar/knowledge/describe_master.py`; it is generated once via LLM only when missing or when `--refresh-master` is set.
2. For every run, analyzer snapshots the active master to `runs/<ts>/.dsstar/describe_master_used.py` for reproducibility.
3. Files are grouped by deterministic format signature (extension + size bucket + lightweight format probes).
4. Analyzer still creates a per-file executable wrapper script in `runs/<ts>/.dsstar/desc_scripts/`.
5. Wrappers call `describe_file(path)` from run-local master, and optionally call a file override first when present.
6. Wrapper stdout is the canonical `d_i`; wrapper failure means non-zero, empty stdout, or `FAILED TO DESCRIBE` marker.
7. On failure only, analyzer may call LLM to generate `runs/<ts>/.dsstar/desc_overrides/<file>_override.py`.
8. Successful overrides trigger a cheap LLM promotion judge (`promote` JSON decision).
9. If promoted, analyzer requests an LLM master patch, writes updated master KB, and re-validates representative via master-only wrapper.
10. `descriptions.json` remains unified and now records signature, master version hash, wrapper path, override path, exec info, status, and promotion decision.

## Cost note (LLM-call triggers)
- `master_gen`: at most once when no master exists (or forced refresh).
- `override_gen`: only on wrapper failures, capped by `--max-failures-to-fix-per-run`.
- `promote_judge`: only after successful override.
- `master_patch`: only when judge says promotion is generalizable.
- Clustering reduces calls by reusing the same master behavior across same-signature files before considering per-file overrides.

## Smoke / acceptance commands
```bash
python -m dsstar run --question "Describe the input files" --provider deepseek --model deepseek-reasoner --timeout-sec 240
```
Expected checks:
- One master generation at most (if absent) and minimal overrides.
- Wrapper scripts exist for every file under run `.dsstar/desc_scripts/`.
- `descriptions.json` includes `master_version_id` and `status` per file.
- Same-schema CSV cluster reuses master without per-file script-generation LLM calls.
