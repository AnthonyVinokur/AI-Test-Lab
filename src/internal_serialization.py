from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from src.public_contract import PublicContractModel


class InternalSerializationError(TypeError):
    """Raised when public-contract data enters the internal serializer."""


def serialize_internal_model(
    value: BaseModel,
    *,
    mode: Literal["python", "json"] = "python",
) -> dict[str, Any]:
    """Serialize an internal Pydantic model for internal-only processing."""

    if isinstance(value, PublicContractModel):
        raise InternalSerializationError(
            "Public-contract models must use serialize_public_contract()."
        )

    return value.model_dump(mode=mode)