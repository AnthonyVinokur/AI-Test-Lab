from __future__ import annotations

import argparse
from pathlib import Path

from src.cli.arguments import DEFAULT_PROMPTS
from src.dataset_loader import load_dataset_tests
from src.prompt_loader import load_prompt_tests


def load_test_cases(args: argparse.Namespace) -> list:
    """Load tests from either a managed dataset or prompt JSON file."""

    if args.dataset:
        test_cases = load_dataset_tests(
            args.dataset,
            storage_dir=args.dataset_storage,
            version=args.dataset_version,
        )

        selected_version = (
            str(args.dataset_version)
            if args.dataset_version is not None
            else "latest"
        )

        print(
            f"Loaded {len(test_cases)} test(s) "
            f"from dataset {args.dataset}, "
            f"version {selected_version}."
        )

        return test_cases

    prompt_path: Path = args.prompts or DEFAULT_PROMPTS
    test_cases = load_prompt_tests(prompt_path)

    print(
        f"Loaded {len(test_cases)} test(s) "
        f"from prompt file {prompt_path}."
    )

    return test_cases