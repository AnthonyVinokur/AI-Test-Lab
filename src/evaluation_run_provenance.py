from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationRunProvenance:
    run_id: str
    model: str
    evaluation_profile: str
    dataset: str
    dataset_version: str
    report_contract: str
    report_contract_fingerprint: str

    def __post_init__(self) -> None:
        required_fields = {
            "run_id": self.run_id,
            "model": self.model,
            "evaluation_profile": self.evaluation_profile,
            "dataset": self.dataset,
            "dataset_version": self.dataset_version,
            "report_contract": self.report_contract,
            "report_contract_fingerprint": self.report_contract_fingerprint,
        }

        for field_name, value in required_fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

    def to_dict(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "model": self.model,
            "evaluation_profile": self.evaluation_profile,
            "dataset": self.dataset,
            "dataset_version": self.dataset_version,
            "report_contract": self.report_contract,
            "report_contract_fingerprint": self.report_contract_fingerprint,
        }
