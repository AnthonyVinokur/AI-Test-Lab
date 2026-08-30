import pytest
from pydantic import BaseModel

from src.internal_serialization import (
    InternalSerializationError,
    serialize_internal_model,
)
from src.public_contract import PublicContractModel


class InternalExample(BaseModel):
    name: str


class PublicExample(PublicContractModel):
    name: str


def test_internal_model_can_be_serialized() -> None:
    result = serialize_internal_model(
        InternalExample(name="internal")
    )

    assert result == {
        "name": "internal",
    }


def test_internal_model_supports_json_mode() -> None:
    result = serialize_internal_model(
        InternalExample(name="internal"),
        mode="json",
    )

    assert result == {
        "name": "internal",
    }


def test_public_contract_cannot_use_internal_serializer() -> None:
    with pytest.raises(
        InternalSerializationError,
        match="Public-contract models must use",
    ):
        serialize_internal_model(
            PublicExample(name="public")
        )
