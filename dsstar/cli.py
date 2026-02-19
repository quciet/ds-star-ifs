from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from dsstar.config import load_dotenv_if_available
from dsstar.llm.registry import get_client
from dsstar.loop import run_loop
from dsstar.tools.log_utils import log


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DS-STAR iterative agent")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the DS-STAR loop")
    run_parser.add_argument("--question", required=True, help="Question or task")
    run_parser.add_argument("--files", nargs="*", default=[], help="Input files")
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

    client = get_client(args.provider, args.model)
    run_path = run_loop(
        question=args.question,
        files=args.files,
        client=client,
        max_rounds=args.max_rounds,
        timeout_sec=args.timeout_sec,
        run_root=Path(args.run_dir),
    )
    log(f"Run complete: {run_path}")
    final_answer = (run_path / "final_answer.md").read_text(encoding="utf-8")
    print("\n=== Final Answer ===\n")
    print(final_answer)
