

from src.cli.diagnostics import (
    print_input_error,
    print_regression_artifact_error,
    print_regression_execution_error,
)


def test_print_input_error_writes_stable_message_to_stderr(capsys):
    print_input_error("invalid dataset")

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == "Input error: invalid dataset\n"


def test_print_regression_execution_error_writes_stable_message_to_stderr(capsys):
    print_regression_execution_error("baseline execution failed")

    captured = capsys.readouterr()

    assert captured.out == ""
    assert (
        captured.err
        == "Regression execution error: baseline execution failed\n"
    )


def test_print_regression_artifact_error_writes_stable_message_to_stderr(capsys):
    print_regression_artifact_error("cannot write result")

    captured = capsys.readouterr()

    assert captured.out == ""
    assert (
        captured.err
        == "Regression artifact error: cannot write result\n"
    )
