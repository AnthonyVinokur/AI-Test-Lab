"""Evaluation profile configuration API."""

from src.evaluation_config.errors import (
    EvaluationConfigError,
    EvaluationConfigFileError,
    EvaluationConfigValidationError,
)
from src.evaluation_config.loader import load_evaluation_profile
from src.evaluation_config.models import (
    EngineConfig,
    EvaluationProfile,
    MetricConfig,
    QualityGateConfig,
)
from src.evaluation_config.validator import validate_registered_engines
from src.evaluation_config.pipeline_builder import (
    create_pipeline_from_profile,
)

__all__ = [
    "EngineConfig",
    "EvaluationConfigError",
    "EvaluationConfigFileError",
    "EvaluationConfigValidationError",
    "EvaluationProfile",
    "MetricConfig",
    "QualityGateConfig",
    "load_evaluation_profile",
    "validate_registered_engines",
    "create_pipeline_from_profile",
]