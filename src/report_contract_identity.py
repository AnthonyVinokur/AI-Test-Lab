from __future__ import annotations

from dataclasses import dataclass

from src.report_contract_validator import (
    is_report_schema_version_supported,
)

PUBLIC_REPORT_CONTRACT_NAME = "ai-test-lab.public-report"


@dataclass(frozen=True)
class PublicReportContractIdentity:
    name: str
    schema_version: str


def public_report_contract_identity(
        schema_version: str,
) -> PublicReportContractIdentity:
    if not is_report_schema_version_supported(schema_version):
        raise ValueError(
            f"Unsupported public report schema version: {schema_version}"
        )

    return PublicReportContractIdentity(
        name=PUBLIC_REPORT_CONTRACT_NAME,
        schema_version=schema_version,
    )


