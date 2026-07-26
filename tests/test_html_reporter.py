from src.html_reporter import HtmlReporter
from src.models import (
    AssertionType,
    EvaluationStatus,
    TestResult as ResultModel,
)


def create_result(
    *,
    model: str,
    status: EvaluationStatus,
    response_time: float,
) -> ResultModel:
    return ResultModel(
        test_id="greeting-001",
        name="Greeting test",
        category="functional",
        prompt="Say hello",
        model=model,
        actual_response="Hello",
        passed=status == EvaluationStatus.PASS,
        status=status,
        assertion_type=AssertionType.CONTAINS,
        expected="Hello",
        reason="Evaluation completed",
        response_time_seconds=response_time,
        prompt_tokens=10,
        output_tokens=5,
        prompt_latency_seconds=0.2,
        generation_latency_seconds=0.8,
        model_load_seconds=0.1,
        prompt_tokens_per_second=20.0,
        generation_tokens_per_second=6.25,
    )


def test_html_report_contains_model_comparison_table(
    tmp_path,
) -> None:
    results = [
        create_result(
            model="model-a",
            status=EvaluationStatus.PASS,
            response_time=1.0,
        ),
        create_result(
            model="model-b",
            status=EvaluationStatus.FAIL,
            response_time=2.0,
        ),
    ]

    report_path = tmp_path / "report.html"

    reporter = HtmlReporter(report_path)
    reporter.write(results)

    html = report_path.read_text(encoding="utf-8")

    assert report_path.exists()
    assert "Model Comparison" in html

    assert "model-a" in html
    assert "model-b" in html

    assert "100.00%" in html
    assert "0.00%" in html

    assert "Highest score" in html
    assert "Fastest" in html

    assert "Avg Response" in html
    assert "Avg Generation" in html
    assert "Avg Speed" in html
    assert "Avg Output Tokens" in html

def test_html_report_contains_expandable_result_details(
    tmp_path,
) -> None:
    results = [
        create_result(
            model="model-a",
            status=EvaluationStatus.PASS,
            response_time=1.0,
        )
    ]

    report_path = tmp_path / "report.html"

    HtmlReporter(report_path).write(results)

    html = report_path.read_text(encoding="utf-8")

    assert "<details" in html
    assert "<summary>View details</summary>" in html
    assert "Test Information" in html
    assert "Actual Response" in html
    assert "Evaluation Reason" in html
    assert "Performance Metrics" in html
    assert "Prompt tokens" in html
    assert "Generation speed" in html