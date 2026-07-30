from src.evaluator import evaluate_response
from src.models import (
    Assertion,
    AssertionType,
    EvaluationStatus,
)


def test_contains_passes() -> None:
    assertion = Assertion(
        type=AssertionType.CONTAINS,
        expected="Guido van Rossum",
    )

    result = evaluate_response(
        actual_response="Python was created by Guido van Rossum.",
        assertion=assertion,
    )

    assert result.passed is True
    assert result.status == EvaluationStatus.PASS


def test_contains_fails() -> None:
    assertion = Assertion(
        type=AssertionType.CONTAINS,
        expected="Guido van Rossum",
    )

    result = evaluate_response(
        actual_response="Python is a programming language.",
        assertion=assertion,
    )

    assert result.passed is False
    assert result.status == EvaluationStatus.FAIL


def test_icontains_passes_ignoring_case() -> None:
    assertion = Assertion(
        type=AssertionType.ICONTAINS,
        expected="hello",
    )

    result = evaluate_response(
        actual_response="Hello World",
        assertion=assertion,
    )

    assert result.status == EvaluationStatus.PASS


def test_icontains_fails_when_text_is_missing() -> None:
    assertion = Assertion(
        type=AssertionType.ICONTAINS,
        expected="python",
    )

    result = evaluate_response(
        actual_response="Hello World",
        assertion=assertion,
    )

    assert result.status == EvaluationStatus.FAIL


def test_starts_with_passes() -> None:
    assertion = Assertion(
        type=AssertionType.STARTS_WITH,
        expected="Hello",
    )

    result = evaluate_response(
        actual_response="Hello from AI Test Lab",
        assertion=assertion,
    )

    assert result.status == EvaluationStatus.PASS


def test_starts_with_fails() -> None:
    assertion = Assertion(
        type=AssertionType.STARTS_WITH,
        expected="Welcome",
    )

    result = evaluate_response(
        actual_response="Hello from AI Test Lab",
        assertion=assertion,
    )

    assert result.status == EvaluationStatus.FAIL


def test_ends_with_passes() -> None:
    assertion = Assertion(
        type=AssertionType.ENDS_WITH,
        expected=".",
    )

    result = evaluate_response(
        actual_response="AI Test Lab is running.",
        assertion=assertion,
    )

    assert result.status == EvaluationStatus.PASS


def test_ends_with_fails() -> None:
    assertion = Assertion(
        type=AssertionType.ENDS_WITH,
        expected="!",
    )

    result = evaluate_response(
        actual_response="AI Test Lab is running.",
        assertion=assertion,
    )

    assert result.status == EvaluationStatus.FAIL


def test_regex_passes() -> None:
    assertion = Assertion(
        type=AssertionType.REGEX,
        expected=r"\b\d{3}-\d{3}-\d{4}\b",
    )

    result = evaluate_response(
        actual_response="The phone number is 555-123-4567.",
        assertion=assertion,
    )

    assert result.status == EvaluationStatus.PASS



def test_regex_fails() -> None:
    assertion = Assertion(
        type=AssertionType.REGEX,
        expected=r"\b\d{3}-\d{3}-\d{4}\b",
    )

    result = evaluate_response(
        actual_response="No phone number was provided.",
        assertion=assertion,
    )

    assert result.status == EvaluationStatus.FAIL


def test_invalid_regex_returns_error() -> None:
    assertion = Assertion(
        type=AssertionType.REGEX,
        expected=r"[invalid",
    )

    result = evaluate_response(
        actual_response="Any response",
        assertion=assertion,
    )

    assert result.status == EvaluationStatus.ERROR
    assert "Invalid regular expression" in result.reason
