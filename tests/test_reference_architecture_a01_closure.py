from __future__ import annotations

import ast
from pathlib import Path

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    AQUAGEAR_FROZEN_REFERENCE_INTERFACE_VERSION,
    AQUAGEAR_PROVIDER_NEUTRAL_INTEGRATION_CONTRACT_VERSION,
    AQUAGEAR_REFERENCE_ARCHITECTURE_CONFORMANCE_CONTRACT_VERSION,
    AQUAGEAR_REFERENCE_ARCHITECTURE_CONTRACT_VERSION,
    AQUAGEAR_REFERENCE_ROUND_TRIP_CLIENT_CONTRACT_VERSION,
    REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_VERSION,
    supported_reference_architecture_compatibility_contract,
)
from src.reference_architecture_integration_adapter import (
    REFERENCE_ARCHITECTURE_INTEGRATION_ADAPTER_CONTRACT_VERSION,
)
from src.reference_architecture_request_response_correlation import (
    REFERENCE_ARCHITECTURE_CORRELATION_CONTRACT_VERSION,
)
from src.reference_architecture_request_translation import (
    REFERENCE_ARCHITECTURE_REQUEST_TRANSLATION_CONTRACT_VERSION,
)
from src.reference_architecture_response_translation import (
    REFERENCE_ARCHITECTURE_RESPONSE_TRANSLATION_CONTRACT_VERSION,
)
from src.reference_architecture_round_trip_failure_normalization import (
    REFERENCE_ARCHITECTURE_FAILURE_NORMALIZATION_CONTRACT_VERSION,
)
from src.reference_architecture_round_trip_orchestration import (
    REFERENCE_ARCHITECTURE_ROUND_TRIP_ORCHESTRATION_CONTRACT_VERSION,
)
from src.reference_architecture_round_trip_outcome_projection import (
    REFERENCE_ARCHITECTURE_ROUND_TRIP_OUTCOME_CONTRACT_VERSION,
    execute_public_reference_architecture_round_trip,
)
from src.reference_architecture_round_trip_serialization import (
    REFERENCE_ARCHITECTURE_ROUND_TRIP_SERIALIZATION_FORMAT,
    REFERENCE_ARCHITECTURE_ROUND_TRIP_SERIALIZATION_VERSION,
    decode_reference_architecture_round_trip_outcome,
    encode_reference_architecture_round_trip_outcome,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ARCHITECTURE_MODULES = tuple(
    sorted((PROJECT_ROOT / "src").glob("reference_architecture_*.py"))
)


def compatibility_payload() -> dict[str, object]:
    return serialize_public_contract(
        supported_reference_architecture_compatibility_contract()
    )


def request_identity() -> dict[str, object]:
    return {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "ai-test-lab",
        "operation": "enforce",
    }


def response_payload() -> dict[str, object]:
    return {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "aquagear-reference-app",
        "operation": "enforce",
        "status": "completed",
        "artifact": None,
        "metadata": (),
    }


class RecordingPort:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls = 0

    def integrate(self, request: object) -> dict[str, object]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return response_payload()


def test_frozen_versions_remain_exactly_at_the_a01_baseline() -> None:
    assert {
        REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_INTEGRATION_ADAPTER_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_REQUEST_TRANSLATION_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_RESPONSE_TRANSLATION_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_CORRELATION_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_ROUND_TRIP_ORCHESTRATION_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_FAILURE_NORMALIZATION_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_ROUND_TRIP_OUTCOME_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_ROUND_TRIP_SERIALIZATION_VERSION,
    } == {"1.0"}
    assert {
        AQUAGEAR_FROZEN_REFERENCE_INTERFACE_VERSION,
        AQUAGEAR_REFERENCE_ARCHITECTURE_CONTRACT_VERSION,
        AQUAGEAR_PROVIDER_NEUTRAL_INTEGRATION_CONTRACT_VERSION,
        AQUAGEAR_REFERENCE_ROUND_TRIP_CLIENT_CONTRACT_VERSION,
    } == {"v1"}
    assert AQUAGEAR_REFERENCE_ARCHITECTURE_CONFORMANCE_CONTRACT_VERSION == "1.0"
    assert REFERENCE_ARCHITECTURE_ROUND_TRIP_SERIALIZATION_FORMAT == "json"


def test_complete_success_path_matches_the_frozen_wire_document() -> None:
    compatibility = compatibility_payload()
    identity = request_identity()
    compatibility_before = dict(compatibility)
    identity_before = dict(identity)
    port = RecordingPort()

    outcome = execute_public_reference_architecture_round_trip(
        compatibility, identity, port
    )
    document = encode_reference_architecture_round_trip_outcome(outcome)

    assert document == (
        b'{"contract_name":"ai-test-lab.reference-architecture-round-trip-outcome",'
        b'"failure":null,"outcome_contract_version":"1.0","response":{'
        b'"artifact":null,"contract_version":"v1",'
        b'"correlation_id":"correlation-11","integration_id":"integration-7",'
        b'"metadata":[],"operation":"enforce",'
        b'"source_system":"aquagear-reference-app","status":"completed"},'
        b'"succeeded":true}'
    )
    assert decode_reference_architecture_round_trip_outcome(document) == outcome
    assert port.calls == 1
    assert compatibility == compatibility_before
    assert identity == identity_before


def test_complete_failure_path_is_stable_and_redacts_internal_details() -> None:
    port = RecordingPort(error=RuntimeError("secret-provider-token"))

    outcome = execute_public_reference_architecture_round_trip(
        compatibility_payload(), request_identity(), port
    )
    document = encode_reference_architecture_round_trip_outcome(outcome)

    assert document == (
        b'{"contract_name":"ai-test-lab.reference-architecture-round-trip-outcome",'
        b'"failure":{"code":"provider_invocation_failed",'
        b'"contract_name":"ai-test-lab.reference-architecture-round-trip-failure",'
        b'"correlation_id":"correlation-11","failure_contract_version":"1.0",'
        b'"integration_id":"integration-7",'
        b'"message":"The provider could not complete the integration request.",'
        b'"retryable":true,"stage":"provider_invocation"},'
        b'"outcome_contract_version":"1.0","response":null,"succeeded":false}'
    )
    assert b"secret-provider-token" not in document
    assert decode_reference_architecture_round_trip_outcome(document) == outcome
    assert port.calls == 1


def test_reference_boundary_has_no_aquagear_runtime_or_provider_sdk_imports() -> None:
    forbidden_roots = {
        "anthropic",
        "aquagear",
        "boto3",
        "google",
        "httpx",
        "ollama",
        "openai",
        "reference_app",
        "requests",
    }
    violations: list[str] = []

    for module_path in REFERENCE_ARCHITECTURE_MODULES:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            for name in imported:
                if name.split(".", 1)[0] in forbidden_roots:
                    violations.append(f"{module_path.name}: {name}")

    assert violations == []
