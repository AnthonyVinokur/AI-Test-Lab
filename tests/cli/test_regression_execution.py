import json
from types import SimpleNamespace
from unittest.mock import patch

from src.cli.app import main
from src.evaluation_run_regression_result_writer import (
    EvaluationRunRegressionResultWriteError,
)


def test_cli_does_not_execute_regression_without_regression_arguments(
        tmp_path,
) -> None:
    prompts_path = tmp_path / "prompts.json"
    report_path = tmp_path / "report.json"
    html_report_path = tmp_path / "report.html"

    prompts_path.write_text(
        json.dumps(
            [
                {
                    "id": "regression-cli-test",
                    "name": "Regression CLI test",
                    "category": "cli",
                    "prompt": "Say hello.",
                    "assertion": {
                        "type": "contains",
                        "expected": "hello",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    with (
        patch(
            "src.cli.app.MultiModelRunner.run_tests",
            return_value=[],
        ),
        patch(
            "src.cli.app.execute_evaluation_run_regression"
        ) as execute_regression,
        patch(
            "src.cli.app.write_cli_regression_result"
        ) as write_regression_result,
    ):
        exit_code = main(
            [
                "--prompts",
                str(prompts_path),
                "--report",
                str(report_path),
                "--html-report",
                str(html_report_path),
            ]
        )
    execute_regression.assert_not_called()
    write_regression_result.assert_not_called()

    assert exit_code == 0


def test_cli_rejects_regression_for_prompt_file_input(
        tmp_path,
) -> None:
    prompts_path = tmp_path / "prompts.json"
    report_path = tmp_path / "report.json"
    html_report_path = tmp_path / "report.html"
    baseline_report_path = tmp_path / "baseline.json"
    baseline_provenance_path = tmp_path / "baseline-provenance.json"
    regression_output_path = tmp_path / "regression-result.json"

    prompts_path.write_text(
        json.dumps(
            [
                {
                    "id": "regression-cli-test",
                    "name": "Regression CLI test",
                    "category": "cli",
                    "prompt": "Say hello.",
                    "assertion": {
                        "type": "contains",
                        "expected": "hello",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    with (
        patch(
            "src.cli.app.MultiModelRunner.run_tests",
            return_value=[],
        ),
        patch(
            "src.cli.app.execute_evaluation_run_regression"
        ) as execute_regression,
    ):
        exit_code = main(
            [
                "--prompts",
                str(prompts_path),
                "--report",
                str(report_path),
                "--html-report",
                str(html_report_path),
                "--regression-baseline-report",
                str(baseline_report_path),
                "--regression-baseline-provenance",
                str(baseline_provenance_path),
                "--regression-result-output",
                str(regression_output_path),
            ]
        )

    execute_regression.assert_not_called()

    assert exit_code == 2


def test_cli_executes_regression_for_versioned_managed_dataset(
        tmp_path,
) -> None:
    report_path = tmp_path / "report.json"
    html_report_path = tmp_path / "report.html"
    baseline_report_path = tmp_path / "baseline.json"
    baseline_provenance_path = tmp_path / "baseline-provenance.json"
    regression_output_path = tmp_path / "regression-result.json"

    with (
        patch(
            "src.cli.app.load_test_cases",
            return_value=[],
        ),
        patch(
            "src.cli.app.MultiModelRunner.run_tests",
            return_value=[],
        ),
        patch(
            "src.cli.app.execute_evaluation_run_regression"
        ) as execute_regression,
        patch(
            "src.cli.app.build_evaluation_run_regression_result"
        ) as build_regression_result,
        patch(
            "src.cli.app.write_cli_regression_result"
        ) as write_regression_result,
    ):
        execute_regression.return_value = SimpleNamespace(
            enforcement="fake-enforcement",
        )

        build_regression_result.return_value = SimpleNamespace(
            exit_code=SimpleNamespace(code=0),
        )

        exit_code = main(
            [
                "--dataset",
                "candidate-suite",
                "--dataset-version",
                "3",
                "--report",
                str(report_path),
                "--html-report",
                str(html_report_path),
                "--regression-baseline-report",
                str(baseline_report_path),
                "--regression-baseline-provenance",
                str(baseline_provenance_path),
                "--regression-result-output",
                str(regression_output_path),
            ]
        )

    execute_regression.assert_called_once()

    call_kwargs = execute_regression.call_args.kwargs

    assert call_kwargs["candidate_results"] == []
    assert (
            call_kwargs["baseline_report_path"]
            == baseline_report_path
    )
    assert (
            call_kwargs["baseline_provenance_path"]
            == baseline_provenance_path
    )

    candidate_identity = call_kwargs["candidate_identity"]

    assert candidate_identity.model == "llama3.1:latest"
    assert candidate_identity.evaluation_profile == "default"
    assert candidate_identity.dataset == "candidate-suite"

    assert call_kwargs["candidate_dataset_version"] == "3"
    assert call_kwargs["report_schema_version"] == "1.0"

    assert exit_code == 0

    build_regression_result.assert_called_once_with(
        "fake-enforcement"
    )

    write_regression_result.assert_called_once_with(
        build_regression_result.return_value,
        regression_output_path,
    )

    assert exit_code == 0


def test_cli_returns_regression_block_exit_code(
        tmp_path,
) -> None:
    report_path = tmp_path / "report.json"
    html_report_path = tmp_path / "report.html"
    baseline_report_path = tmp_path / "baseline.json"
    baseline_provenance_path = tmp_path / "baseline-provenance.json"
    regression_output_path = tmp_path / "regression-result.json"

    with (
        patch(
            "src.cli.app.load_test_cases",
            return_value=[],
        ),
        patch(
            "src.cli.app.MultiModelRunner.run_tests",
            return_value=[],
        ),
        patch(
            "src.cli.app.execute_evaluation_run_regression"
        ) as execute_regression,
        patch(
            "src.cli.app.build_evaluation_run_regression_result"
        ) as build_regression_result,
        patch(
            "src.cli.app.write_cli_regression_result"
        ) as write_regression_result,
    ):
        execute_regression.return_value = SimpleNamespace(
            enforcement="fake-enforcement",
        )

        build_regression_result.return_value = SimpleNamespace(
            exit_code=SimpleNamespace(code=1),
        )

        exit_code = main(
            [
                "--dataset",
                "candidate-suite",
                "--dataset-version",
                "3",
                "--report",
                str(report_path),
                "--html-report",
                str(html_report_path),
                "--regression-baseline-report",
                str(baseline_report_path),
                "--regression-baseline-provenance",
                str(baseline_provenance_path),
                "--regression-result-output",
                str(regression_output_path),
            ]
        )

    execute_regression.assert_called_once()

    build_regression_result.assert_called_once_with(
        "fake-enforcement"
    )

    write_regression_result.assert_called_once_with(
        build_regression_result.return_value,
        regression_output_path,
    )

    assert exit_code == 1


def test_cli_rejects_regression_with_multiple_models(
    tmp_path,
) -> None:
    report_path = tmp_path / "report.json"
    html_report_path = tmp_path / "report.html"
    baseline_report_path = tmp_path / "baseline.json"
    baseline_provenance_path = tmp_path / "baseline-provenance.json"
    regression_output_path = tmp_path / "regression-result.json"

    with (
        patch(
            "src.cli.app.load_test_cases",
            return_value=[],
        ),
        patch(
            "src.cli.app.MultiModelRunner.run_tests",
            return_value=[],
        ) as run_tests,
        patch(
            "src.cli.app.execute_evaluation_run_regression"
        ) as execute_regression,
    ):
        exit_code = main(
            [
                "--models",
                "model-a",
                "model-b",
                "--dataset",
                "candidate-suite",
                "--dataset-version",
                "3",
                "--report",
                str(report_path),
                "--html-report",
                str(html_report_path),
                "--regression-baseline-report",
                str(baseline_report_path),
                "--regression-baseline-provenance",
                str(baseline_provenance_path),
                "--regression-result-output",
                str(regression_output_path),
            ]
        )

    run_tests.assert_not_called()
    execute_regression.assert_not_called()

    assert exit_code == 2


def test_cli_regression_exit_code_takes_precedence_over_normal_failures(
    tmp_path,
) -> None:
    report_path = tmp_path / "report.json"
    html_report_path = tmp_path / "report.html"
    baseline_report_path = tmp_path / "baseline.json"
    baseline_provenance_path = tmp_path / "baseline-provenance.json"
    regression_output_path = tmp_path / "regression-result.json"

    with (
        patch(
            "src.cli.app.load_test_cases",
            return_value=[],
        ),
        patch(
            "src.cli.app.MultiModelRunner.run_tests",
            return_value=[],
        ),
        patch(
            "src.cli.app.execute_evaluation_run_regression"
        ) as execute_regression,
        patch(
            "src.cli.app.build_evaluation_run_regression_result"
        ) as build_regression_result,
        patch(
            "src.cli.app.write_cli_regression_result",
        ),
        patch(
            "src.cli.app.print_results",
            return_value=(0, 0, 1, 0),
        ),
    ):
        execute_regression.return_value = SimpleNamespace(
            enforcement="fake-enforcement",
        )

        build_regression_result.return_value = SimpleNamespace(
            exit_code=SimpleNamespace(code=0),
        )

        exit_code = main(
            [
                "--dataset",
                "candidate-suite",
                "--dataset-version",
                "3",
                "--report",
                str(report_path),
                "--html-report",
                str(html_report_path),
                "--regression-baseline-report",
                str(baseline_report_path),
                "--regression-baseline-provenance",
                str(baseline_provenance_path),
                "--regression-result-output",
                str(regression_output_path),
            ]
        )

    assert exit_code == 0


def test_cli_returns_artifact_failure_exit_code(
    tmp_path,
    capsys,
) -> None:
    report_path = tmp_path / "report.json"
    html_report_path = tmp_path / "report.html"
    baseline_report_path = tmp_path / "baseline.json"
    baseline_provenance_path = (
        tmp_path / "baseline-provenance.json"
    )
    regression_output_path = (
        tmp_path / "regression-result.json"
    )

    with (
        patch(
            "src.cli.app.load_test_cases",
            return_value=[],
        ),
        patch(
            "src.cli.app.MultiModelRunner.run_tests",
            return_value=[],
        ),
        patch(
            "src.cli.app.execute_evaluation_run_regression"
        ) as execute_regression,
        patch(
            "src.cli.app.build_evaluation_run_regression_result"
        ) as build_regression_result,
        patch(
            "src.cli.app.write_cli_regression_result",
            side_effect=EvaluationRunRegressionResultWriteError(
                "failed to write regression result artifact"
            ),
        ),
    ):
        execute_regression.return_value = SimpleNamespace(
            enforcement="fake-enforcement",
        )

        build_regression_result.return_value = SimpleNamespace(
            exit_code=SimpleNamespace(code=0),
        )

        exit_code = main(
            [
                "--dataset",
                "candidate-suite",
                "--dataset-version",
                "3",
                "--report",
                str(report_path),
                "--html-report",
                str(html_report_path),
                "--regression-baseline-report",
                str(baseline_report_path),
                "--regression-baseline-provenance",
                str(baseline_provenance_path),
                "--regression-result-output",
                str(regression_output_path),
            ]
        )

    captured = capsys.readouterr()

    assert exit_code == 3
    assert (
        "Regression artifact error:"
        in captured.err
    )
    assert (
        "failed to write regression result artifact"
        in captured.err
    )


def test_cli_artifact_failure_takes_precedence_over_block_exit_code(
    tmp_path,
) -> None:
    report_path = tmp_path / "report.json"
    html_report_path = tmp_path / "report.html"
    baseline_report_path = tmp_path / "baseline.json"
    baseline_provenance_path = (
        tmp_path / "baseline-provenance.json"
    )
    regression_output_path = (
        tmp_path / "regression-result.json"
    )

    with (
        patch(
            "src.cli.app.load_test_cases",
            return_value=[],
        ),
        patch(
            "src.cli.app.MultiModelRunner.run_tests",
            return_value=[],
        ),
        patch(
            "src.cli.app.execute_evaluation_run_regression"
        ) as execute_regression,
        patch(
            "src.cli.app.build_evaluation_run_regression_result"
        ) as build_regression_result,
        patch(
            "src.cli.app.write_cli_regression_result",
            side_effect=EvaluationRunRegressionResultWriteError(
                "disk unavailable"
            ),
        ),
    ):
        execute_regression.return_value = SimpleNamespace(
            enforcement="fake-enforcement",
        )

        build_regression_result.return_value = SimpleNamespace(
            exit_code=SimpleNamespace(code=1),
        )

        exit_code = main(
            [
                "--dataset",
                "candidate-suite",
                "--dataset-version",
                "3",
                "--report",
                str(report_path),
                "--html-report",
                str(html_report_path),
                "--regression-baseline-report",
                str(baseline_report_path),
                "--regression-baseline-provenance",
                str(baseline_provenance_path),
                "--regression-result-output",
                str(regression_output_path),
            ]
        )

    assert exit_code == 3

def test_cli_returns_regression_execution_failure_exit_code(
    tmp_path,
    capsys,
) -> None:
    report_path = tmp_path / "report.json"
    html_report_path = tmp_path / "report.html"
    baseline_report_path = tmp_path / "baseline.json"
    baseline_provenance_path = (
        tmp_path / "baseline-provenance.json"
    )
    regression_output_path = (
        tmp_path / "regression-result.json"
    )

    with (
        patch(
            "src.cli.app.load_test_cases",
            return_value=[],
        ),
        patch(
            "src.cli.app.MultiModelRunner.run_tests",
            return_value=[],
        ),
        patch(
            "src.cli.app.execute_evaluation_run_regression",
            side_effect=RuntimeError(
                "baseline regression execution failed"
            ),
        ),
        patch(
            "src.cli.app.build_evaluation_run_regression_result"
        ) as build_regression_result,
        patch(
            "src.cli.app.write_cli_regression_result"
        ) as write_regression_result,
    ):
        exit_code = main(
            [
                "--dataset",
                "candidate-suite",
                "--dataset-version",
                "3",
                "--report",
                str(report_path),
                "--html-report",
                str(html_report_path),
                "--regression-baseline-report",
                str(baseline_report_path),
                "--regression-baseline-provenance",
                str(baseline_provenance_path),
                "--regression-result-output",
                str(regression_output_path),
            ]
        )

    captured = capsys.readouterr()

    assert exit_code == 3
    assert "Regression execution error:" in captured.err
    assert (
        "baseline regression execution failed"
        in captured.err
    )

    build_regression_result.assert_not_called()
    write_regression_result.assert_not_called()

def test_cli_regression_execution_failure_takes_precedence_over_normal_failures(
    tmp_path,
) -> None:
    report_path = tmp_path / "report.json"
    html_report_path = tmp_path / "report.html"
    baseline_report_path = tmp_path / "baseline.json"
    baseline_provenance_path = (
        tmp_path / "baseline-provenance.json"
    )
    regression_output_path = (
        tmp_path / "regression-result.json"
    )

    with (
        patch(
            "src.cli.app.load_test_cases",
            return_value=[],
        ),
        patch(
            "src.cli.app.MultiModelRunner.run_tests",
            return_value=[],
        ),
        patch(
            "src.cli.app.execute_evaluation_run_regression",
            side_effect=RuntimeError(
                "regression runtime unavailable"
            ),
        ),
        patch(
            "src.cli.app.print_results",
            return_value=(0, 0, 1, 1),
        ) as print_results,
    ):
        exit_code = main(
            [
                "--dataset",
                "candidate-suite",
                "--dataset-version",
                "3",
                "--report",
                str(report_path),
                "--html-report",
                str(html_report_path),
                "--regression-baseline-report",
                str(baseline_report_path),
                "--regression-baseline-provenance",
                str(baseline_provenance_path),
                "--regression-result-output",
                str(regression_output_path),
            ]
        )

    assert exit_code == 3
    print_results.assert_not_called()
