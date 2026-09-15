from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from src.reference_architecture_evidence_lifecycle_authority import (
    LifecycleAuthorityGrant,
    verify_lifecycle_authority,
)
from src.reference_architecture_evidence_lifecycle_contract import LifecycleEvent, LifecycleEventType, lifecycle_identifier
from src.reference_architecture_evidence_lifecycle_serialization import expected_event_digest


@dataclass(frozen=True, slots=True)
class LifecycleEventProof:
    key_id: str
    signature_base64: str
    algorithm: str = "ed25519"

    def __post_init__(self) -> None:
        lifecycle_identifier(self.key_id, "key_id")
        if self.algorithm != "ed25519":
            raise ValueError("proof algorithm is unsupported.")
        try:
            decoded = base64.b64decode(self.signature_base64, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError("signature_base64 is invalid.") from error
        if len(decoded) != 64 or base64.b64encode(decoded).decode("ascii") != self.signature_base64:
            raise ValueError("signature_base64 must be canonical Ed25519 signature bytes.")


@dataclass(frozen=True, slots=True)
class AuthenticatedLifecycleEvent:
    event: LifecycleEvent
    proof: LifecycleEventProof


class LifecycleChainError(ValueError):
    pass


AuthorityResolver = Callable[[str], LifecycleAuthorityGrant | None]
SignatureVerifier = Callable[[LifecycleEvent, LifecycleEventProof], bool]


def verify_lifecycle_chain(
    history: Sequence[AuthenticatedLifecycleEvent],
    *,
    authority_resolver: AuthorityResolver,
    signature_verifier: SignatureVerifier,
) -> tuple[LifecycleEvent, ...]:
    """Verify one complete, append-only history; never repair or ignore bad events."""

    if not history:
        raise LifecycleChainError("Lifecycle history is unavailable.")
    verified: list[LifecycleEvent] = []
    identities: tuple[str, str, str, str] | None = None
    seen: set[str] = set()
    try:
        for index, authenticated in enumerate(history):
            if not isinstance(authenticated, AuthenticatedLifecycleEvent):
                raise ValueError
            event, proof = authenticated.event, authenticated.proof
            if event.event_digest in seen or event.event_digest != expected_event_digest(event):
                raise ValueError
            expected_previous = None if index == 0 else verified[-1].event_digest
            if event.previous_event_id != expected_previous:
                raise ValueError
            if index == 0 and event.event_type is not LifecycleEventType.ISSUED:
                raise ValueError
            if index and event.effective_at < verified[-1].effective_at:
                raise ValueError
            current_identity = (
                event.receipt_id,
                event.release_manifest_digest,
                event.evidence_package_id,
                event.environment,
            )
            identities = identities or current_identity
            if current_identity != identities:
                raise ValueError
            grant = authority_resolver(event.authority_id)
            if grant is None or proof.key_id != grant.key_id:
                raise ValueError
            verify_lifecycle_authority(event, grant)
            if not signature_verifier(event, proof):
                raise ValueError
            verified.append(event)
            seen.add(event.event_digest)
    except Exception as error:
        raise LifecycleChainError("Lifecycle history could not be verified.") from error
    return tuple(verified)


class InMemoryLifecycleStore:
    """Small append-only reference store; persistence is deliberately outside this sprint."""

    def __init__(self) -> None:
        self._histories: dict[str, tuple[AuthenticatedLifecycleEvent, ...]] = {}

    def history(self, receipt_id: str) -> tuple[AuthenticatedLifecycleEvent, ...]:
        return self._histories.get(receipt_id, ())

    def append(self, value: AuthenticatedLifecycleEvent) -> None:
        event = value.event
        existing = self._histories.get(event.receipt_id, ())
        expected_previous = existing[-1].event.event_digest if existing else None
        if event.previous_event_id != expected_previous or (existing and event.effective_at < existing[-1].event.effective_at):
            raise LifecycleChainError("Lifecycle event cannot be appended.")
        self._histories[event.receipt_id] = (*existing, value)


def histories_are_consistent(left: Sequence[LifecycleEvent], right: Sequence[LifecycleEvent]) -> bool:
    """Two histories are consistent only when their shared portion is identical."""

    shared = min(len(left), len(right))
    return all(left[index].event_digest == right[index].event_digest for index in range(shared))
