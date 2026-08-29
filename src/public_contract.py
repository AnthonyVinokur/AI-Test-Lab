from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class PublicContractModel(BaseModel):
    """Base class for data explicitly approved for public exposure."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class PublicContractExposureError(TypeError):
    """Raised when non-public data is sent through the public serializer."""


def serialize_public_contract(
    value: PublicContractModel,
) -> dict[str, Any]:
    """Serialize only explicitly approved public-contract models."""

    if not isinstance(value, PublicContractModel):
        raise PublicContractExposureError(
            "Only explicit public-contract models may be serialized."
        )

    return value.model_dump(mode="json")
