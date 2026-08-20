from __future__ import annotations

_REPORT_CAPABILITIES = {
    "1.0": (
        "report",
        "summary",
        "decision",
        "assessment",
    ),
}


def report_capabilities(schema_version: str) -> tuple[str, ...]:
    """Return public capabilities available for a report schema version."""

    return _REPORT_CAPABILITIES.get(schema_version, ())


def report_supports_capability(
        schema_version: str,
        capability: str,
) -> bool:
    """Return whether a public report version supports a capability."""

    return capability in report_capabilities(schema_version)


def capability_schema_versions() -> tuple[str, ...]:
    """Return schema versions that publish public capability metadata."""

    return tuple(_REPORT_CAPABILITIES)
