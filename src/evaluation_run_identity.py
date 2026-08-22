from dataclasses import dataclass
from uuid import uuid4

@dataclass(frozen=True)
class EvaluationRunIdentity:
    """Public identity metadata for one evaluation run."""

    run_id: str
    model: str
    evaluation_profile: str
    dataset: str

    def __post_init__(self) -> None:
        for field_name in (
            "run_id",
            "model",
            "evaluation_profile",
            "dataset",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string."
                )

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationRunIdentity:
    """Public identity metadata for one evaluation run."""

    run_id: str
    model: str
    evaluation_profile: str
    dataset: str

    def __post_init__(self) -> None:
        for field_name in (
            "run_id",
            "model",
            "evaluation_profile",
            "dataset",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string."
                )

    def to_public_dict(self) -> dict[str, str]:
        """Return the explicitly supported public representation."""

        return {
            "run_id": self.run_id,
            "model": self.model,
            "evaluation_profile": self.evaluation_profile,
            "dataset": self.dataset,
        }

def create_evaluation_run_identity(
    *,
    model: str,
    evaluation_profile: str,
    dataset: str,
) -> EvaluationRunIdentity:
    """Create a new public identity for an evaluation run."""

    return EvaluationRunIdentity(
        run_id=f"run-{uuid4()}",
        model=model,
        evaluation_profile=evaluation_profile,
        dataset=dataset,
    )
