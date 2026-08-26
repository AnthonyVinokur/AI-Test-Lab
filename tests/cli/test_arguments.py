from pathlib import Path

import pytest

from src.cli.arguments import parse_args


def test_default_arguments() -> None:
    args = parse_args([])

    assert args.models == ["llama3.1:latest"]
    assert args.prompts is None
    assert args.dataset is None
    assert args.dataset_storage == Path("datasets")
    assert args.dataset_version is None
    assert args.report == Path("results/latest_results.json")
    assert args.html_report == Path("results/latest_report.html")
    assert args.regression_baseline_report is None
    assert args.regression_baseline_provenance is None
    assert args.regression_result_output is None
    assert args.evaluation_profile is None
    assert args.list_evaluation_profiles is False


def test_regression_arguments_default_to_none() -> None:
    args = parse_args([])

    assert args.regression_baseline_report is None
    assert args.regression_baseline_provenance is None
    assert args.regression_result_output is None


def test_complete_regression_arguments() -> None:
    args = parse_args(
        [
            "--regression-baseline-report",
            "results/baseline.json",
            "--regression-baseline-provenance",
            "results/baseline-provenance.json",
            "--regression-result-output",
            "results/regression-result.json",
        ]
    )

    assert args.regression_baseline_report == Path(
        "results/baseline.json"
    )
    assert args.regression_baseline_provenance == Path(
        "results/baseline-provenance.json"
    )
    assert args.regression_result_output == Path(
        "results/regression-result.json"
    )


@pytest.mark.parametrize(
    "arguments",
    [
        [
            "--regression-baseline-report",
            "results/baseline.json",
        ],
        [
            "--regression-baseline-provenance",
            "results/baseline-provenance.json",
        ],
        [
            "--regression-result-output",
            "results/regression-result.json",
        ],
        [
            "--regression-baseline-report",
            "results/baseline.json",
            "--regression-baseline-provenance",
            "results/baseline-provenance.json",
        ],
        [
            "--regression-baseline-report",
            "results/baseline.json",
            "--regression-result-output",
            "results/regression-result.json",
        ],
        [
            "--regression-baseline-provenance",
            "results/baseline-provenance.json",
            "--regression-result-output",
            "results/regression-result.json",
        ],
    ],
)

def test_incomplete_regression_arguments_are_rejected(
        arguments: list[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        parse_args(arguments)

    assert error.value.code == 2


def test_multiple_models() -> None:
    args = parse_args(
        [
            "--models",
            "llama3.1:latest",
            "qwen2.5-coder:7b",
        ]
    )

    assert args.models == [
        "llama3.1:latest",
        "qwen2.5-coder:7b",
    ]


def test_prompt_file_argument() -> None:
    args = parse_args(
        [
            "--prompts",
            "prompts/custom.json",
        ]
    )

    assert args.prompts == Path("prompts/custom.json")
    assert args.dataset is None


def test_dataset_argument() -> None:
    args = parse_args(
        [
            "--dataset",
            "regression-suite",
            "--dataset-version",
            "3",
        ]
    )

    assert args.dataset == "regression-suite"
    assert args.dataset_version == 3


def test_dataset_version_requires_dataset() -> None:
    with pytest.raises(SystemExit) as error:
        parse_args(["--dataset-version", "2"])

    assert error.value.code == 2


def test_prompts_and_dataset_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit) as error:
        parse_args(
            [
                "--prompts",
                "prompts/prompts.json",
                "--dataset",
                "regression-suite",
            ]
        )

    assert error.value.code == 2


def test_evaluation_profile_argument() -> None:
    args = parse_args(
        [
            "--evaluation-profile",
            "fast-ci",
        ]
    )

    assert args.evaluation_profile == Path("fast-ci")


def test_list_evaluation_profiles_argument() -> None:
    args = parse_args(
        [
            "--list-evaluation-profiles",
        ]
    )

    assert args.list_evaluation_profiles is True
