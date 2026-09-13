from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import StringConstraints, ValidationError

from src.public_contract import PublicContractModel


REFERENCE_ARCHITECTURE_RESPONSE_TRANSLATION_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-response-translation"
)
REFERENCE_ARCHITECTURE_RESPONSE_TRANSLATION_CONTRACT_VERSION = "1.0"
SUPPORTED_PROVIDER_NEUTRAL_INTEGRATION_CONTRACT_VERSION = "v1"

NonEmptyString = Annotated[str, StringConstraints(strict=True, min_length=1)]


class ProviderNeutralIntegrationOperationV1(str, Enum):
    SUBMIT = "submit"
    ENFORCE = "enforce"
    RETURN = "return"


class ProviderNeutralIntegrationStatusV1(str, Enum):
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class ProviderNeutralIntegrationMetadataV1(PublicContractModel):
    key: NonEmptyString
    value: str


class ProviderNeutralIntegrationArtifactV1(PublicContractModel):
    artifact_id: NonEmptyString
    artifact_type: NonEmptyString
    content_type: NonEmptyString
    payload_base64: NonEmptyString
    schema_version: NonEmptyString | None = None


class ProviderNeutralIntegrationResponseV1(PublicContractModel):
    contract_version: Literal["v1"]
    integration_id: NonEmptyString
    correlation_id: NonEmptyString
    source_system: NonEmptyString
    operation: ProviderNeutralIntegrationOperationV1
    status: ProviderNeutralIntegrationStatusV1
    artifact: ProviderNeutralIntegrationArtifactV1 | None = None
    metadata: tuple[ProviderNeutralIntegrationMetadataV1, ...] = ()


class ReferenceArchitectureResponseTranslationResultV1(PublicContractModel):
    contract_name: Literal[
        "ai-test-lab.reference-architecture-response-translation"
    ] = REFERENCE_ARCHITECTURE_RESPONSE_TRANSLATION_CONTRACT_NAME
    translation_contract_version: Literal["1.0"] = (
        REFERENCE_ARCHITECTURE_RESPONSE_TRANSLATION_CONTRACT_VERSION
    )
    response: ProviderNeutralIntegrationResponseV1


class ReferenceArchitectureResponseTranslationError(ValueError):
    """Raised when a provider response cannot enter the public v1 contract."""


_RESPONSE_FIELDS = frozenset(
    {
        "contract_version",
        "integration_id",
        "correlation_id",
        "source_system",
        "operation",
        "status",
        "artifact",
        "metadata",
    }
)
_ARTIFACT_FIELDS = frozenset(
    {
        "artifact_id",
        "artifact_type",
        "content_type",
        "payload",
        "schema_version",
    }
)
_METADATA_FIELDS = frozenset({"key", "value"})


def _copy_exact_mapping(
    value: object,
    *,
    fields: frozenset[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ReferenceArchitectureResponseTranslationError(
            f"{label} must be a mapping."
        )
    copied = dict(value)
    if set(copied) != fields:
        raise ReferenceArchitectureResponseTranslationError(
            f"{label} does not match the frozen public schema."
        )
    return copied


def _translate_artifact(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    artifact = _copy_exact_mapping(
        value, fields=_ARTIFACT_FIELDS, label="Response artifact"
    )
    payload = artifact.pop("payload")
    if not isinstance(payload, bytes) or not payload:
        raise ReferenceArchitectureResponseTranslationError(
            "Response artifact payload must be non-empty bytes."
        )
    artifact["payload_base64"] = base64.b64encode(payload).decode("ascii")
    return artifact


def _translate_metadata(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ReferenceArchitectureResponseTranslationError(
            "Response metadata must be a sequence."
        )
    translated: list[dict[str, Any]] = []
    keys: set[str] = set()
    for item in value:
        entry = _copy_exact_mapping(
            item, fields=_METADATA_FIELDS, label="Response metadata entry"
        )
        key = entry.get("key")
        if isinstance(key, str) and key in keys:
            raise ReferenceArchitectureResponseTranslationError(
                "Response metadata keys must be unique."
            )
        if isinstance(key, str):
            keys.add(key)
        translated.append(entry)
    return tuple(translated)


def translate_reference_architecture_response(
    payload: Mapping[str, Any],
) -> ReferenceArchitectureResponseTranslationResultV1:
    """Translate one untrusted Aquagear A.40 v1 response into a public DTO."""

    response = _copy_exact_mapping(
        payload, fields=_RESPONSE_FIELDS, label="Provider-neutral response"
    )
    response["artifact"] = _translate_artifact(response["artifact"])
    response["metadata"] = _translate_metadata(response["metadata"])

    try:
        response["operation"] = ProviderNeutralIntegrationOperationV1(
            response["operation"]
        )
        response["status"] = ProviderNeutralIntegrationStatusV1(
            response["status"]
        )
        validated = ProviderNeutralIntegrationResponseV1.model_validate(response)
    except (TypeError, ValueError, ValidationError) as exc:
        raise ReferenceArchitectureResponseTranslationError(
            "Provider-neutral response does not match the frozen v1 schema."
        ) from exc

    return ReferenceArchitectureResponseTranslationResultV1(response=validated)
