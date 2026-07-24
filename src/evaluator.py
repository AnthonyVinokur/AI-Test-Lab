import re

from src.models import (
    Assertion,
    AssertionType,
    EvaluationResult,
    EvaluationStatus,
)


def evaluate_response(
    actual_response: str,
    assertion: Assertion,
) -> EvaluationResult:
    expected = assertion.expected

    if assertion.type == AssertionType.CONTAINS:
        passed = expected in actual_response
        reason = (
            f"Response contains expected text: {expected!r}"
            if passed
            else f"Response does not contain expected text: {expected!r}"
        )

    elif assertion.type == AssertionType.NOT_CONTAINS:
        passed = expected not in actual_response
        reason = (
            f"Response does not contain prohibited text: {expected!r}"
            if passed
            else f"Response contains prohibited text: {expected!r}"
        )

    elif assertion.type == AssertionType.EQUALS:
        passed = actual_response.strip() == expected.strip()
        reason = (
            "Response exactly matches expected text."
            if passed
            else (
                "Response does not exactly match expected text. "
                f"Expected: {expected!r}"
            )
        )

    elif assertion.type == AssertionType.ICONTAINS:
        passed = expected.casefold() in actual_response.casefold()
        reason = (
            f"Response contains expected text ignoring case: {expected!r}"
            if passed
            else (
                "Response does not contain expected text ignoring case: "
                f"{expected!r}"
            )
        )

    elif assertion.type == AssertionType.STARTS_WITH:
        passed = actual_response.strip().startswith(expected)
        reason = (
            f"Response starts with expected text: {expected!r}"
            if passed
            else f"Response does not start with expected text: {expected!r}"
        )

    elif assertion.type == AssertionType.ENDS_WITH:
        passed = actual_response.strip().endswith(expected)
        reason = (
            f"Response ends with expected text: {expected!r}"
            if passed
            else f"Response does not end with expected text: {expected!r}"
        )

    elif assertion.type == AssertionType.REGEX:
        try:
            passed = re.search(expected, actual_response) is not None
        except re.error as error:
            return EvaluationResult(
                passed=False,
                status=EvaluationStatus.ERROR,
                assertion_type=assertion.type,
                expected=expected,
                reason=f"Invalid regular expression: {error}",
            )

        reason = (
            f"Response matches regex pattern: {expected!r}"
            if passed
            else f"Response does not match regex pattern: {expected!r}"
        )

    else:
        return EvaluationResult(
            passed=False,
            status=EvaluationStatus.ERROR,
            assertion_type=assertion.type,
            expected=expected,
            reason=f"Unsupported assertion type: {assertion.type}",
        )

    return EvaluationResult(
        passed=passed,
        status=(
            EvaluationStatus.PASS
            if passed
            else EvaluationStatus.FAIL
        ),
        assertion_type=assertion.type,
        expected=expected,
        reason=reason,
    )


