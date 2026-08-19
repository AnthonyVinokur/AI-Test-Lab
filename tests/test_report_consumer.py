import ast
import inspect
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest
import src.report_consumer as report_consumer_module
from src.report_consumer import ReportConsumption, consume_report
from src.report_contract_validator import ReportContractValidationError
from src.report_reader import ReportReadError

FIXTURE = Path("tests/fixtures/report-v1.0.json")

def test_consume_report_returns_public_consumption():
    consumption = consume_report(FIXTURE)

    assert isinstance(consumption, ReportConsumption)
    assert consumption.report.schema_version == "1.0"
    assert consumption.summary.schema_version == "1.0"
    assert consumption.decision.schema_version == "1.0"
    assert consumption.assessment.schema_version == "1.0"


def test_consumption_outputs_are_consistent():
    consumption = consume_report(FIXTURE)

    assert consumption.decision.status == consumption.assessment.status
    assert consumption.summary.total == consumption.decision.total
    assert consumption.summary.passed == consumption.decision.passed
    assert consumption.summary.failed == consumption.decision.failed
    assert consumption.summary.errors == consumption.decision.errors


def test_report_consumption_is_immutable():
    consumption = consume_report(FIXTURE)

    with pytest.raises(FrozenInstanceError):
        setattr(consumption, "summary", None)


def test_consume_report_rejects_invalid_json(tmp_path):
    report_path = tmp_path / "invalid.json"
    report_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ReportReadError):
        consume_report(report_path)


def test_consume_report_rejects_invalid_public_contract(tmp_path):
    report_path = tmp_path / "invalid-report.json"
    report_path.write_text(
        '{"schema_version": "1.0"}',
        encoding="utf-8",
    )

    with pytest.raises(ReportContractValidationError):
        consume_report(report_path)


def test_report_consumer_does_not_import_private_runtime_modules():
    source = inspect.getsource(report_consumer_module)
    tree = ast.parse(source)

    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)

        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden_prefixes = (
        "src.evaluation",
        "src.evaluation_config",
        "src.evaluation_plugins",
        "src.models",
        "src.runner",
    )

    assert not any(
        module.startswith(forbidden_prefixes)
        for module in imported_modules
    )


def test_consume_report_rejects_unsupported_schema_version(
        tmp_path,
):
    payload = json.loads(
        FIXTURE.read_text(encoding="utf-8")
    )
    payload["schema_version"] = "9.0"

    report_path = tmp_path / "unsupported-report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
            ReportContractValidationError,
            match="Unsupported public report schema version",
    ):
        consume_report(report_path)

@pytest.mark.parametrize(
    ("mutation", "expected_validator"),
    [
        (
            lambda payload: payload["summary"].__setitem__(
                "passed",
                "banana",
            ),
            "type",
        ),
        (
            lambda payload: payload["summary"].__setitem__(
                "passed",
                -1,
            ),
            "minimum",
        ),
        (
            lambda payload: payload["summary"].pop("passed"),
            "required",
        ),
        (
            lambda payload: payload.__setitem__(
                "secret_internal_score",
                99,
            ),
            "additionalProperties",
        ),
        (
            lambda payload: payload["results"][0].__setitem__(
                "prompt_tokens",
                "many",
            ),
            "type",
        ),
    ],
)
def test_consume_report_rejects_malformed_supported_contract(
    tmp_path,
    mutation,
    expected_validator,
):
    payload = json.loads(
        FIXTURE.read_text(encoding="utf-8")
    )

    mutation(payload)

    report_path = tmp_path / "malformed-report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ReportContractValidationError,
        match=rf"\[{expected_validator}\]",
    ):
        consume_report(report_path)
