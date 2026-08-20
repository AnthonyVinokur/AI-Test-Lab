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
def supports_schema_version(schema_version: str) -> bool:
    """Return whether a public report schema version is supported."""

    if not isinstance(schema_version, str):
        raise ValueError(
            "Public report schema_version must be a string."
        )

    return schema_version in capability_schema_versions()


def supports_report_schema(
        report: dict[str, object],
) -> bool:
    """Return whether a public report uses a supported schema version."""

    schema_version = report.get("schema_version")

    if not isinstance(schema_version, str):
        raise ValueError(
            "Public report schema_version must be a string."
        )

    return supports_schema_version(schema_version)



def supports_capability(
        report: dict[str, object],
        capability: str,
) -> bool:
    """Return whether a public report supports a public capability."""

    schema_version = report.get("schema_version")

    if not isinstance(schema_version, str):
        raise ValueError(
            "Public report schema_version must be a string."
        )

    if not isinstance(capability, str):
        raise ValueError(
            "Public report capability must be a string."
        )

    return report_supports_capability(
        schema_version,
        capability,
    )
