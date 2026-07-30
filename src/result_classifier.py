from src.models import EvaluationStatus, PromptTest


def classify_status(
    prompt_test: PromptTest,
    assertion_passed: bool,
) -> EvaluationStatus:
    if prompt_test.expected_to_fail:
        if assertion_passed:
            return EvaluationStatus.XPASS

        return EvaluationStatus.XFAIL

    if assertion_passed:
        return EvaluationStatus.PASS

    return EvaluationStatus.FAIL