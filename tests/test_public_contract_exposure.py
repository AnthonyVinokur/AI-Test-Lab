import pytest
from pydantic import BaseModel, ValidationError

from src.evaluation_models import MetricResult
from src.public_contract import (
    PublicContractExposureError,
    PublicContractModel,
    serialize_public_contract,
)

from src.report_schema import (
    ReportHighlightsV1,
    ReportSummaryV1,
    ReportV1,
)

from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcement,
    EvaluationRunRegressionEnforcementDecision,
)
from src.evaluation_run_regression_public_contract import (
    EvaluationRunRegressionResultV1,
)
from src.evaluation_run_regression_result import (
    build_evaluation_run_regression_result,
)


class ExamplePublicChild(PublicContractModel):
    value: int


class ExamplePublicContract(PublicContractModel):
    name: str
    child: ExamplePublicChild


class OrdinaryPydanticModel(BaseModel):
    value: int


def test_explicit_public_contract_can_be_serialized() -> None:
    contract = ExamplePublicContract(
        name="public-example",
        child=ExamplePublicChild(value=7),
    )

    assert serialize_public_contract(contract) == {
        "name": "public-example",
        "child": {
            "value": 7,
        },
    }


def test_nested_public_contract_is_serialized() -> None:
    contract = ExamplePublicContract(
        name="nested-example",
        child=ExamplePublicChild(value=42),
    )

    payload = serialize_public_contract(contract)

    assert payload["child"] == {
        "value": 42,
    }


def test_internal_runtime_dataclass_is_rejected() -> None:
    internal_result = MetricResult(
        metric_name="contains",
        score=1.0,
        passed=True,
        threshold=1.0,
        engine="builtin",
    )

    with pytest.raises(
        PublicContractExposureError,
        match="Only explicit public-contract models",
    ):
        serialize_public_contract(internal_result)  # type: ignore[arg-type]


def test_arbitrary_pydantic_model_is_rejected() -> None:
    internal_model = OrdinaryPydanticModel(
        value=123,
    )

    with pytest.raises(
        PublicContractExposureError,
        match="Only explicit public-contract models",
    ):
        serialize_public_contract(internal_model)  # type: ignore[arg-type]


def test_unknown_public_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ExamplePublicChild(
            value=7,
            private_score=0.98,
        )

def test_report_v1_is_an_explicit_public_contract() -> None:
    report = ReportV1(
        generated_at="2026-08-29T18:00:00-04:00",
        models=[],
        summary=ReportSummaryV1(
            passed=0,
            failed=0,
            expected_failures=0,
            unexpected_passes=0,
            errors=0,
            total=0,
            pass_rate_percent=0.0,
            total_estimated_cost_usd=0.0,
        ),
        highlights=ReportHighlightsV1(),
        model_comparison=[],
        results=[],
    )

    payload = serialize_public_contract(report)

    assert payload["schema_version"] == "1.0"
    assert payload["models"] == []
    assert payload["results"] == []

def test_regression_public_contract_can_be_serialized() -> None:
    contract = EvaluationRunRegressionResultV1(
        enforcement="allow",
        exit_code=0,
    )

    assert serialize_public_contract(contract) == {
        "enforcement": "allow",
        "exit_code": 0,
    }


def test_internal_regression_result_is_rejected() -> None:
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK,
    )
    internal_result = build_evaluation_run_regression_result(enforcement)

    with pytest.raises(
        PublicContractExposureError,
        match="Only explicit public-contract models",
    ):
        serialize_public_contract(  # type: ignore[arg-type]
            internal_result,
        )


def test_regression_public_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        EvaluationRunRegressionResultV1(
            enforcement="allow",
            exit_code=0,
            internal_regression_score=0.97,
        )
