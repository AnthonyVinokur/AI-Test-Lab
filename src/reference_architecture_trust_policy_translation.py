from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from src.reference_architecture_trust_policy_contract import (
    REFERENCE_ARCHITECTURE_TRUST_POLICY_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_TRUST_POLICY_CONTRACT_VERSION,
    ReferenceArchitectureTrustedKeyStatus,
    ReferenceArchitectureTrustedKeyV1,
    ReferenceArchitectureTrustedSignerV1,
    ReferenceArchitectureTrustPolicyV1,
)


class ReferenceArchitectureTrustPolicyTranslationError(ValueError):
    """Raised when untrusted policy data cannot enter the internal contract."""


_TOP_FIELDS = {"contract_name", "contract_version", "policy_id", "policy_version", "trusted_signers", "permitted_algorithms", "permitted_key_types"}
_SIGNER_FIELDS = {"signer_id", "keys"}
_KEY_FIELDS = {"key_id", "public_key_base64", "algorithm", "key_type", "activated_at", "expires_at", "status", "permitted_purposes", "permitted_environments"}


def _exact_mapping(value: object, fields: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ReferenceArchitectureTrustPolicyTranslationError(f"{name} must contain exactly the frozen schema fields.")
    return value


def _strings(value: object, name: str) -> frozenset[str]:
    if type(value) is not list or not value or any(type(item) is not str for item in value):
        raise ReferenceArchitectureTrustPolicyTranslationError(f"{name} must be a non-empty string array.")
    if len(value) != len(set(value)):
        raise ReferenceArchitectureTrustPolicyTranslationError(f"{name} cannot contain duplicates.")
    return frozenset(value)


def _timestamp(value: object, name: str, *, optional: bool = False) -> datetime | None:
    if optional and value is None:
        return None
    if type(value) is not str or not value.endswith("Z"):
        raise ReferenceArchitectureTrustPolicyTranslationError(f"{name} must be a canonical UTC timestamp.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ReferenceArchitectureTrustPolicyTranslationError(f"{name} must be a valid UTC timestamp.") from exc
    if parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != value:
        raise ReferenceArchitectureTrustPolicyTranslationError(f"{name} must use second-precision canonical UTC form.")
    return parsed


def translate_untrusted_reference_architecture_trust_policy(payload: Mapping[str, Any]) -> ReferenceArchitectureTrustPolicyV1:
    """Copy untrusted JSON-shaped policy data into immutable internal values."""
    try:
        root = _exact_mapping(payload, _TOP_FIELDS, "policy")
        if root["contract_name"] != REFERENCE_ARCHITECTURE_TRUST_POLICY_CONTRACT_NAME or root["contract_version"] != REFERENCE_ARCHITECTURE_TRUST_POLICY_CONTRACT_VERSION:
            raise ReferenceArchitectureTrustPolicyTranslationError("The trust-policy contract identity is unsupported.")
        raw_signers = root["trusted_signers"]
        if type(raw_signers) is not list or not raw_signers:
            raise ReferenceArchitectureTrustPolicyTranslationError("trusted_signers must be a non-empty array.")
        signers: list[ReferenceArchitectureTrustedSignerV1] = []
        for raw_signer in raw_signers:
            signer = _exact_mapping(raw_signer, _SIGNER_FIELDS, "trusted signer")
            raw_keys = signer["keys"]
            if type(raw_keys) is not list or not raw_keys:
                raise ReferenceArchitectureTrustPolicyTranslationError("keys must be a non-empty array.")
            keys: list[ReferenceArchitectureTrustedKeyV1] = []
            for raw_key in raw_keys:
                key = _exact_mapping(raw_key, _KEY_FIELDS, "trusted key")
                try:
                    public_key = base64.b64decode(key["public_key_base64"], validate=True)
                except (TypeError, ValueError, binascii.Error) as exc:
                    raise ReferenceArchitectureTrustPolicyTranslationError("public_key_base64 must be canonical base64.") from exc
                if base64.b64encode(public_key).decode("ascii") != key["public_key_base64"]:
                    raise ReferenceArchitectureTrustPolicyTranslationError("public_key_base64 must be canonical base64.")
                keys.append(ReferenceArchitectureTrustedKeyV1(
                    key_id=key["key_id"], public_key=public_key, algorithm=key["algorithm"], key_type=key["key_type"],
                    activated_at=_timestamp(key["activated_at"], "activated_at"), expires_at=_timestamp(key["expires_at"], "expires_at", optional=True),
                    status=ReferenceArchitectureTrustedKeyStatus(key["status"]), permitted_purposes=_strings(key["permitted_purposes"], "permitted_purposes"),
                    permitted_environments=_strings(key["permitted_environments"], "permitted_environments"),
                ))
            signers.append(ReferenceArchitectureTrustedSignerV1(signer_id=signer["signer_id"], keys=tuple(keys)))
        return ReferenceArchitectureTrustPolicyV1(
            policy_id=root["policy_id"], policy_version=root["policy_version"], trusted_signers=tuple(signers),
            permitted_algorithms=_strings(root["permitted_algorithms"], "permitted_algorithms"),
            permitted_key_types=_strings(root["permitted_key_types"], "permitted_key_types"),
        )
    except ReferenceArchitectureTrustPolicyTranslationError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ReferenceArchitectureTrustPolicyTranslationError("The trust policy is malformed or ambiguous.") from exc


__all__ = ["ReferenceArchitectureTrustPolicyTranslationError", "translate_untrusted_reference_architecture_trust_policy"]
