from __future__ import annotations

from typing import Literal

from src.public_contract import PublicContractModel


class EvaluationRunRegressionResultV1(PublicContractModel):
    """Public contract for one regression enforcement result."""

    enforcement: Literal["allow", "block"]
    exit_code: int
