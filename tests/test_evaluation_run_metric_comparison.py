import pytest

from src.evaluation_run_metric_comparison import (
    EvaluationRunMetricResult,
    compare_evaluation_run_metrics,
)

def test_baseline_results_must_be_tuple():
    with pytest.raises(TypeError, match="baseline_results must be a tuple"):
        compare_evaluation_run_metrics(
            baseline_results=[],
            candidate_results=(),
        )


def test_candidate_results_must_be_tuple():
    with pytest.raises(TypeError, match="candidate_results must be a tuple"):
        compare_evaluation_run_metrics(
            baseline_results=(),
            candidate_results=[],
        )


def test_baseline_results_must_contain_metric_results():
    with pytest.raises(
        TypeError,
        match="baseline_results must contain EvaluationRunMetricResult objects",
    ):
        compare_evaluation_run_metrics(
            baseline_results=("bad",),
            candidate_results=(),
        )


def test_candidate_results_must_contain_metric_results():
    valid = EvaluationRunMetricResult(
        case_id="case-001",
        metric_name="answer_relevancy",
        score=0.80,
    )

    with pytest.raises(
        TypeError,
        match="candidate_results must contain EvaluationRunMetricResult objects",
    ):
        compare_evaluation_run_metrics(
            baseline_results=(valid,),
            candidate_results=("bad",),
        )
def test_metric_score_increase_produces_positive_delta():
    baseline = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.80,
        ),
    )
    candidate = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.90,
        ),
    )

    result = compare_evaluation_run_metrics(
        baseline_results=baseline,
        candidate_results=candidate,
    )

    comparison = result.metric_comparisons[0]

    assert comparison.case_id == "case-001"
    assert comparison.metric_name == "answer_relevancy"
    assert comparison.baseline_score == 0.80
    assert comparison.candidate_score == 0.90
    assert comparison.delta == pytest.approx(0.10)


def test_metric_score_decrease_produces_negative_delta():
    baseline = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="faithfulness",
            score=0.90,
        ),
    )
    candidate = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="faithfulness",
            score=0.75,
        ),
    )

    result = compare_evaluation_run_metrics(
        baseline_results=baseline,
        candidate_results=candidate,
    )

    assert result.metric_comparisons[0].delta == pytest.approx(-0.15)


def test_equal_metric_scores_produce_zero_delta():
    baseline = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.85,
        ),
    )
    candidate = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.85,
        ),
    )

    result = compare_evaluation_run_metrics(
        baseline_results=baseline,
        candidate_results=candidate,
    )

    assert result.metric_comparisons[0].delta == pytest.approx(0.0)


def test_multiple_metrics_are_ordered_deterministically():
    baseline = (
        EvaluationRunMetricResult(
            case_id="case-002",
            metric_name="faithfulness",
            score=0.70,
        ),
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.80,
        ),
    )
    candidate = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.85,
        ),
        EvaluationRunMetricResult(
            case_id="case-002",
            metric_name="faithfulness",
            score=0.75,
        ),
    )

    result = compare_evaluation_run_metrics(
        baseline_results=baseline,
        candidate_results=candidate,
    )

    assert [
               (item.case_id, item.metric_name)
               for item in result.metric_comparisons
           ] == [
               ("case-001", "answer_relevancy"),
               ("case-002", "faithfulness"),
           ]


def test_missing_candidate_metric_is_rejected():
    baseline = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.80,
        ),
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="faithfulness",
            score=0.90,
        ),
    )
    candidate = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.85,
        ),
    )

    with pytest.raises(ValueError, match="metric result sets do not match"):
        compare_evaluation_run_metrics(
            baseline_results=baseline,
            candidate_results=candidate,
        )


def test_missing_baseline_metric_is_rejected():
    baseline = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.80,
        ),
    )
    candidate = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.85,
        ),
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="faithfulness",
            score=0.90,
        ),
    )

    with pytest.raises(ValueError, match="metric result sets do not match"):
        compare_evaluation_run_metrics(
            baseline_results=baseline,
            candidate_results=candidate,
        )


def test_duplicate_metric_result_is_rejected():
    baseline = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.80,
        ),
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.81,
        ),
    )
    candidate = (
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=0.85,
        ),
    )

    with pytest.raises(ValueError, match="duplicate metric result"):
        compare_evaluation_run_metrics(
            baseline_results=baseline,
            candidate_results=candidate,
        )


@pytest.mark.parametrize(
    "case_id",
    [
        "",
        "   ",
    ],
)
def test_invalid_case_id_is_rejected(case_id):
    with pytest.raises(ValueError, match="case_id must be a non-empty string"):
        EvaluationRunMetricResult(
            case_id=case_id,
            metric_name="answer_relevancy",
            score=0.80,
        )


@pytest.mark.parametrize(
    "metric_name",
    [
        "",
        "   ",
    ],
)
def test_invalid_metric_name_is_rejected(metric_name):
    with pytest.raises(
            ValueError,
            match="metric_name must be a non-empty string",
    ):
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name=metric_name,
            score=0.80,
        )


@pytest.mark.parametrize(
    "score",
    [
        -0.01,
        1.01,
    ],
)
def test_out_of_range_score_is_rejected(score):
    with pytest.raises(ValueError, match="score must be between 0.0 and 1.0"):
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score=score,
        )


def test_non_numeric_score_is_rejected():
    with pytest.raises(TypeError, match="score must be a number"):
        EvaluationRunMetricResult(
            case_id="case-001",
            metric_name="answer_relevancy",
            score="0.80",
        )


def test_empty_metric_sets_compare_deterministically():
    result = compare_evaluation_run_metrics(
        baseline_results=(),
        candidate_results=(),
    )

    assert result.metric_comparisons == ()
