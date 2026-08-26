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

    parser.add_argument(
        "--evaluation-profile",
        type=Path,
        default=None,
        help=(
            "Built-in evaluation profile name or path to a YAML/JSON "
            "evaluation profile."
        ),
    )
    parser.add_argument(
        "--list-evaluation-profiles",
        action="store_true",
        help="List built-in evaluation profiles and exit.",
    )

    source_group = parser.add_mutually_exclusive_group()

    source_group.add_argument(
        "--prompts",
        type=Path,
        default=None,
        help=(
            "Path to a prompt JSON file. "
            "Defaults to prompts/prompts.json when no dataset source "
            "is supplied."
        ),
    )

    source_group.add_argument(
        "--dataset",
        help="ID of an active managed dataset.",
    )

    source_group.add_argument(
        "--validate-dataset",
        metavar="DATASET_ID",
        help=(
            "Validate a managed dataset without running model "
            "evaluations."
        ),
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
        help=(
            "Specific dataset version. "
            "The latest version is used by default."
        ),
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

    parser.add_argument(
        "--regression-baseline-report",
        type=Path,
        default=None,
        help="Path to the baseline public evaluation report.",
    )

    parser.add_argument(
        "--regression-baseline-provenance",
        type=Path,
        default=None,
        help="Path to the stored baseline evaluation-run provenance.",
    )

    parser.add_argument(
        "--regression-result-output",
        type=Path,
        default=None,
        help=(
            "Optional destination path for the public regression "
            "result JSON."
        ),
    )

    parser.add_argument(
        "--engine",
        choices=["builtin", "deepeval"],
        default="builtin",
        help="Evaluation engine to use.",
    )

    return parser


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    """Parse CLI arguments and validate cross-argument requirements."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if (
        args.dataset_version is not None
        and args.dataset is None
        and args.validate_dataset is None
    ):
        parser.error(
            "--dataset-version requires "
            "--dataset or --validate-dataset"
        )

    if args.dataset_version is not None and args.dataset_version < 1:
        parser.error("--dataset-version must be 1 or greater")

    regression_arguments = (
        args.regression_baseline_report,
        args.regression_baseline_provenance,
        args.regression_result_output,
    )

    if any(value is not None for value in regression_arguments) and not all(
            value is not None for value in regression_arguments
    ):
        parser.error(
            "--regression-baseline-report, "
            "--regression-baseline-provenance, and "
            "--regression-result-output must be supplied together"
        )

    return args