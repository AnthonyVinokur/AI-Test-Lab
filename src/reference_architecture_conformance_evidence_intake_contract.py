from __future__ import annotations

import math
import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Literal

from pydantic import (
    Field,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
)

from src.public_contract import PublicContractModel


REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTAKE_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-conformance-evidence-intake"
)
REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTAKE_CONTRACT_VERSION = "1.0"

AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_SCHEMA = (
    "aquagear.reference-architecture-conformance-evidence"
)
AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_VERSION = "1"
AQUAGEAR_CONFORMANCE_EVIDENCE_SCHEMA_VERSION = "1.0"
AQUAGEAR_FROZEN_ARCHITECTURE_VERSION = "v1"

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class ReferenceArchitectureConformanceEvidenceV1(PublicContractModel):
    """Strict public shape of the evidence inside Aquagear's frozen export.

    ``evaluation`` is deliberately an opaque JSON object. This contract checks
    only that it is deterministic JSON data; later A.02 slices own digest and
    semantic verification.
    """

    schema_version: Literal["1.0"]
    architecture_version: Literal["v1"]
    evaluation: Mapping[str, Any]
    evaluation_sha256: str
    evidence_sha256: str

    @field_validator("evaluation_sha256", "evidence_sha256")
    @classmethod
    def validate_sha256_identity(cls, value: str) -> str:
        if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("SHA-256 identities must be 64 lowercase hex characters.")
        return value

    @model_validator(mode="after")
    def freeze_evaluation(self) -> "ReferenceArchitectureConformanceEvidenceV1":
        frozen = _freeze_json_object(self.evaluation, path="evaluation")
        object.__setattr__(self, "evaluation", frozen)
        return self

    @field_serializer("evaluation")
    def serialize_evaluation(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _thaw_json_object(value)


class ReferenceArchitectureConformanceEvidenceIntakeV1(PublicContractModel):
    """Frozen ATL-A.02.01 contract matching the Aquagear A.43.4 envelope."""

    export_schema: Literal[
        "aquagear.reference-architecture-conformance-evidence"
    ] = Field(alias="schema")
    version: Literal["1"]
    evidence: ReferenceArchitectureConformanceEvidenceV1

    @model_serializer(mode="plain")
    def serialize_envelope(self) -> dict[str, Any]:
        return {
            "schema": self.export_schema,
            "version": self.version,
            "evidence": self.evidence,
        }


def supported_reference_architecture_conformance_evidence_intake_contract(
    *,
    evaluation: Mapping[str, Any],
    evaluation_sha256: str,
    evidence_sha256: str,
) -> ReferenceArchitectureConformanceEvidenceIntakeV1:
    """Build the single Aquagear conformance-evidence shape ATL accepts."""

    return ReferenceArchitectureConformanceEvidenceIntakeV1(
        schema=AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_SCHEMA,
        version=AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_VERSION,
        evidence=ReferenceArchitectureConformanceEvidenceV1(
            schema_version=AQUAGEAR_CONFORMANCE_EVIDENCE_SCHEMA_VERSION,
            architecture_version=AQUAGEAR_FROZEN_ARCHITECTURE_VERSION,
            evaluation=evaluation,
            evaluation_sha256=evaluation_sha256,
            evidence_sha256=evidence_sha256,
        )
    )


def _freeze_json_object(
    value: Mapping[str, Any], *, path: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be a JSON object.")
    return MappingProxyType(
        {
            key: _freeze_json_value(item, path=f"{path}.{key}")
            for key, item in value.items()
            if _validate_json_key(key, path=path)
        }
    )


def _validate_json_key(key: object, *, path: str) -> bool:
    if type(key) is not str:
        raise ValueError(f"{path} must use string keys.")
    return True


def _freeze_json_value(value: Any, *, path: str) -> Any:
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} must not contain a non-finite number.")
        return value
    if isinstance(value, Mapping):
        return _freeze_json_object(value, path=path)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    raise ValueError(f"{path} contains a non-JSON value.")


def _thaw_json_object(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _thaw_json_value(item) for key, item in value.items()}


def _thaw_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _thaw_json_object(value)
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


__all__ = [
    "AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_SCHEMA",
    "AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_VERSION",
    "AQUAGEAR_CONFORMANCE_EVIDENCE_SCHEMA_VERSION",
    "AQUAGEAR_FROZEN_ARCHITECTURE_VERSION",
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTAKE_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTAKE_CONTRACT_VERSION",
    "ReferenceArchitectureConformanceEvidenceIntakeV1",
    "ReferenceArchitectureConformanceEvidenceV1",
    "supported_reference_architecture_conformance_evidence_intake_contract",
]
