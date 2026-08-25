from __future__ import annotations

from src.evaluation_run_identity import EvaluationRunIdentity
from src.evaluation_run_provenance import EvaluationRunProvenance
from src.report_contract_fingerprint import (
    public_report_contract_fingerprint,
)
from src.report_contract_identity import (
    public_report_contract_identity,
)


def construct_candidate_evaluation_run_provenance(
    *,
    identity: EvaluationRunIdentity,
    dataset_version: str,
    report_schema_version: str,
) -> EvaluationRunProvenance:
    """Construct validated provenance for the current candidate run."""

    if not isinstance(identity, EvaluationRunIdentity):
        raise TypeError(
            "identity must be an EvaluationRunIdentity"
        )

    contract = public_report_contract_identity(
        report_schema_version
    )
    fingerprint = public_report_contract_fingerprint(
        report_schema_version
    )

    return EvaluationRunProvenance(
        run_id=identity.run_id,
        model=identity.model,
        evaluation_profile=identity.evaluation_profile,
        dataset=identity.dataset,
        dataset_version=dataset_version,
        report_contract=contract.name,
        report_contract_fingerprint=fingerprint,
    )
