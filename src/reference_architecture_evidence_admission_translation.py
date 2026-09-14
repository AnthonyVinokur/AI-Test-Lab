from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from src.reference_architecture_authenticated_provenance_outcome import (
    ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
)
from src.reference_architecture_conformance_evidence_binding_outcome import (
    ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
)
from src.reference_architecture_evidence_admission_contract import (
    REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_VERSION,
    ReferenceArchitectureEvidenceAdmissionPolicyV1,
    ReferenceArchitectureEvidenceAdmissionRequestV1,
    ReferenceArchitectureReplayStatus,
)
from src.reference_architecture_trusted_evidence_outcome import (
    ReferenceArchitectureTrustedEvidenceOutcomeV1,
)


class ReferenceArchitectureEvidenceAdmissionTranslationError(ValueError):
    """Raised before malformed untrusted data can reach admission policy logic."""


_REQUEST_FIELDS = {
    "contract_name", "contract_version", "evidence_id", "evidence_sha256",
    "evidence_type", "producer_id", "purpose", "target_environment",
    "workflow_id", "run_id", "created_at", "not_before", "expires_at",
    "evaluated_at", "replay_status",
}
_POLICY_FIELDS = {
    "policy_id", "policy_version", "supported_evidence_types",
    "authorized_producers", "allowed_producer_evidence_types",
    "acceptable_contract_versions", "allowed_purposes", "allowed_environments",
    "permitted_workflows", "maximum_evidence_age_seconds",
}


def _exact_mapping(value: object, fields: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ReferenceArchitectureEvidenceAdmissionTranslationError(
            f"{name} must contain exactly the frozen schema fields."
        )
    return value


def _strings(value: object, name: str) -> frozenset[str]:
    if type(value) is not list or not value or any(type(item) is not str for item in value):
        raise ReferenceArchitectureEvidenceAdmissionTranslationError(
            f"{name} must be a non-empty string array."
        )
    if len(value) != len(set(value)):
        raise ReferenceArchitectureEvidenceAdmissionTranslationError(f"{name} cannot contain duplicates.")
    return frozenset(value)


def _timestamp(value: object, name: str) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ReferenceArchitectureEvidenceAdmissionTranslationError(
            f"{name} must be a canonical UTC timestamp."
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ReferenceArchitectureEvidenceAdmissionTranslationError(
            f"{name} must be a valid UTC timestamp."
        ) from exc
    if parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != value:
        raise ReferenceArchitectureEvidenceAdmissionTranslationError(
            f"{name} must use second-precision canonical UTC form."
        )
    return parsed


def translate_untrusted_reference_architecture_admission_policy(
    payload: Mapping[str, Any],
) -> ReferenceArchitectureEvidenceAdmissionPolicyV1:
    try:
        root = _exact_mapping(payload, _POLICY_FIELDS, "admission policy")
        combinations = root["allowed_producer_evidence_types"]
        if type(combinations) is not list or not combinations:
            raise ReferenceArchitectureEvidenceAdmissionTranslationError(
                "allowed_producer_evidence_types must be a non-empty pair array."
            )
        pairs: list[tuple[str, str]] = []
        for combination in combinations:
            if type(combination) is not list or len(combination) != 2 or any(type(item) is not str for item in combination):
                raise ReferenceArchitectureEvidenceAdmissionTranslationError(
                    "Each producer/evidence combination must be a two-string array."
                )
            pairs.append((combination[0], combination[1]))
        if len(pairs) != len(set(pairs)):
            raise ReferenceArchitectureEvidenceAdmissionTranslationError(
                "Producer/evidence combinations cannot contain duplicates."
            )
        age = root["maximum_evidence_age_seconds"]
        if type(age) is not int or age <= 0:
            raise ReferenceArchitectureEvidenceAdmissionTranslationError(
                "maximum_evidence_age_seconds must be a positive integer."
            )
        return ReferenceArchitectureEvidenceAdmissionPolicyV1(
            policy_id=root["policy_id"], policy_version=root["policy_version"],
            supported_evidence_types=_strings(root["supported_evidence_types"], "supported_evidence_types"),
            authorized_producers=_strings(root["authorized_producers"], "authorized_producers"),
            allowed_producer_evidence_types=frozenset(pairs),
            acceptable_contract_versions=_strings(root["acceptable_contract_versions"], "acceptable_contract_versions"),
            allowed_purposes=_strings(root["allowed_purposes"], "allowed_purposes"),
            allowed_environments=_strings(root["allowed_environments"], "allowed_environments"),
            permitted_workflows=_strings(root["permitted_workflows"], "permitted_workflows"),
            maximum_evidence_age=timedelta(seconds=age),
        )
    except ReferenceArchitectureEvidenceAdmissionTranslationError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ReferenceArchitectureEvidenceAdmissionTranslationError(
            "The admission policy is malformed or ambiguous."
        ) from exc


def translate_untrusted_reference_architecture_evidence_admission_request(
    payload: Mapping[str, Any],
    *,
    integrity_result: ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
    authenticated_provenance_result: ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
    trust_result: ReferenceArchitectureTrustedEvidenceOutcomeV1,
    policy: ReferenceArchitectureEvidenceAdmissionPolicyV1,
) -> ReferenceArchitectureEvidenceAdmissionRequestV1:
    try:
        root = _exact_mapping(payload, _REQUEST_FIELDS, "admission request")
        if root["contract_name"] != REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_NAME:
            raise ReferenceArchitectureEvidenceAdmissionTranslationError("The admission contract name is unsupported.")
        if root["contract_version"] != REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_VERSION:
            raise ReferenceArchitectureEvidenceAdmissionTranslationError("The admission contract version is unsupported.")
        return ReferenceArchitectureEvidenceAdmissionRequestV1(
            evidence_id=root["evidence_id"], evidence_sha256=root["evidence_sha256"],
            evidence_type=root["evidence_type"], producer_id=root["producer_id"],
            contract_version=root["contract_version"], purpose=root["purpose"],
            target_environment=root["target_environment"], workflow_id=root["workflow_id"],
            run_id=root["run_id"], created_at=_timestamp(root["created_at"], "created_at"),
            not_before=_timestamp(root["not_before"], "not_before"),
            expires_at=_timestamp(root["expires_at"], "expires_at"),
            evaluated_at=_timestamp(root["evaluated_at"], "evaluated_at"),
            replay_status=ReferenceArchitectureReplayStatus(root["replay_status"]),
            integrity_result=integrity_result,
            authenticated_provenance_result=authenticated_provenance_result,
            trust_result=trust_result, policy=policy,
        )
    except ReferenceArchitectureEvidenceAdmissionTranslationError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ReferenceArchitectureEvidenceAdmissionTranslationError(
            "The admission request is malformed or ambiguous."
        ) from exc


__all__ = [
    "ReferenceArchitectureEvidenceAdmissionTranslationError",
    "translate_untrusted_reference_architecture_admission_policy",
    "translate_untrusted_reference_architecture_evidence_admission_request",
]
