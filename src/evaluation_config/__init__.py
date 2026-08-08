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

from src.evaluation_config.validator import (
    validate_registered_engines,
    validate_supported_metrics,
)

from src.evaluation_config.pipeline_builder import (
    create_pipeline_from_profile,
)
from src.evaluation_config.catalog import list_profiles

__all__ = [
    "EngineConfig",
    "EvaluationConfigError",
    "EvaluationConfigFileError",
    "EvaluationConfigValidationError",
    "EvaluationProfile",
    "MetricConfig",
    "QualityGateConfig",
    "list_profiles",
    "load_evaluation_profile",
    "validate_registered_engines",
    "validate_supported_metrics",
    "create_pipeline_from_profile",
]