from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from dsstar.config import load_dotenv_if_available
from dsstar.llm.registry import get_client
from dsstar.loop import run_loop
from dsstar.tools.log_utils import log


SUPPORTED_INPUT_EXTENSIONS = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".xlsm",
    ".json",
    ".txt",
    ".parquet",
    ".db",
    ".sqlite",
    ".sqlite3",
}


def _discover_input_files(input_dir: str) -> List[str]:
    base = Path(input_dir)
    if not base.exists() or not base.is_dir():
        return []

    discovered: List[str] = []
    for child in sorted(base.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_file():
            continue
        if child.name.startswith(".") or child.name == ".gitkeep":
            continue
        if child.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS:
            discovered.append(str(child))
    return discovered


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DS-STAR iterative agent")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the DS-STAR loop")
    run_parser.add_argument("--question", required=True, help="Question or task")
    run_parser.add_argument("--files", nargs="*", default=[], help="Input files")
    run_parser.add_argument("--input-dir", default="input", help="Directory for auto-discovered input files")
    run_parser.add_argument("--max-rounds", type=int, default=12)
    run_parser.add_argument("--provider", default="mock", choices=["mock", "openai", "gemini", "deepseek", "local"])
    run_parser.add_argument("--model", default=None)
    run_parser.add_argument("--timeout-sec", type=int, default=30)
    run_parser.add_argument("--run-dir", default="./runs")
    return parser


def main(argv: List[str] | None = None) -> None:
    load_dotenv_if_available()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "run":
        parser.print_help()
        return

    client = get_client(args.provider, args.model, args.timeout_sec)
    files = args.files
    if files:
        log(f"Using explicit --files ({len(files)}): {files}")
    else:
        files = _discover_input_files(args.input_dir)
        log(f"Discovered files from {args.input_dir}: {files}")

    run_path = run_loop(
        question=args.question,
        files=files,
        client=client,
        max_rounds=args.max_rounds,
        timeout_sec=args.timeout_sec,
        run_root=Path(args.run_dir),
    )
    log(f"Run complete: {run_path}")
    final_answer_path = run_path / "final_answer.md"
    if final_answer_path.exists():
        final_answer = final_answer_path.read_text(encoding="utf-8")
        print("\n=== Final Answer ===\n")
        print(final_answer)
    else:
        log("Final report not generated (run did not fully converge/validate).")
