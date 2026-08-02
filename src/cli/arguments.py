from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_PROMPTS = Path("prompts/prompts.json")
DEFAULT_DATASET_STORAGE = Path("datasets")
DEFAULT_JSON_REPORT = Path("results/latest_results.json")
DEFAULT_HTML_REPORT = Path("results/latest_report.html")


def build_parser() -> argparse.ArgumentParser:
    """Build and configure the AI Test Lab argument parser."""

    parser = argparse.ArgumentParser(
        prog="ai-test-lab",
        description="Run AI Test Lab evaluations against one or more models.",
    )

    parser.add_argument(
        "--models",
        nargs="+",
        default=["llama3.1:latest"],
        help="One or more Ollama model names.",
    )

    source_group = parser.add_mutually_exclusive_group()

    source_group.add_argument(
        "--prompts",
        type=Path,
        default=None,
        help=(
            "Path to a prompt JSON file. "
            "Defaults to prompts/prompts.json when --dataset is omitted."
        ),
    )

    source_group.add_argument(
        "--dataset",
        help="ID of an active managed dataset.",
    )

    parser.add_argument(
        "--dataset-storage",
        type=Path,
        default=DEFAULT_DATASET_STORAGE,
        help="Directory containing managed dataset JSON files.",
    )

    parser.add_argument(
        "--dataset-version",
        type=int,
        default=None,
        help="Specific dataset version. The latest version is used by default.",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_JSON_REPORT,
        help="Destination path for the JSON report.",
    )

    parser.add_argument(
        "--html-report",
        type=Path,
        default=DEFAULT_HTML_REPORT,
        help="Destination path for the HTML report.",
    )

    return parser


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    """Parse CLI arguments and validate cross-argument requirements."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.dataset_version is not None and args.dataset is None:
        parser.error("--dataset-version requires --dataset")

    return args