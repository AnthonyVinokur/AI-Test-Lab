import pytest

from src.evaluation_run_provenance import EvaluationRunProvenance


def make_provenance(**overrides):
    values = {
        "run_id": "run-123",
        "model": "llama3.1:latest",
        "evaluation_profile": "fast-ci",
        "dataset": "smoke-tests",
        "dataset_version": "1",
        "report_contract": "public-report-v1",
        "report_contract_fingerprint": "abc123",
    }
    values.update(overrides)

    return EvaluationRunProvenance(**values)


def test_provenance_captures_run_identity():
    provenance = make_provenance()

    assert provenance.run_id == "run-123"


def test_provenance_captures_reproducibility_fields():
    provenance = make_provenance()

    assert provenance.model == "llama3.1:latest"
    assert provenance.evaluation_profile == "fast-ci"
    assert provenance.dataset == "smoke-tests"
    assert provenance.dataset_version == "1"
    assert provenance.report_contract == "public-report-v1"
    assert provenance.report_contract_fingerprint == "abc123"


@pytest.mark.parametrize(
    "field_name",
    [
        "run_id",
        "model",
        "evaluation_profile",
        "dataset",
        "dataset_version",
        "report_contract",
        "report_contract_fingerprint",
    ],
)
def test_required_provenance_fields_cannot_be_blank(field_name):
    with pytest.raises(
        ValueError,
        match=f"{field_name} must be a non-empty string",
    ):
        make_provenance(**{field_name: "   "})


def test_provenance_serializes_deterministically():
    provenance = make_provenance()

    assert provenance.to_dict() == {
        "run_id": "run-123",
        "model": "llama3.1:latest",
        "evaluation_profile": "fast-ci",
        "dataset": "smoke-tests",
        "dataset_version": "1",
        "report_contract": "public-report-v1",
        "report_contract_fingerprint": "abc123",
    }


def test_equivalent_provenance_has_equivalent_serialization():
    first = make_provenance()
    second = make_provenance()

    assert first.to_dict() == second.to_dict()


def test_provenance_change_is_observable():
    first = make_provenance(dataset_version="1")
    second = make_provenance(dataset_version="2")

    assert first.to_dict() != second.to_dict()


def test_provenance_is_immutable():
    provenance = make_provenance()

    with pytest.raises(AttributeError):
        provenance.model = "different-model"