"""Exceptions raised while loading evaluation profiles."""


class EvaluationConfigError(ValueError):
    """Base exception for evaluation profile failures."""


class EvaluationConfigFileError(EvaluationConfigError):
    """Raised when an evaluation profile cannot be read or parsed."""


class EvaluationConfigValidationError(EvaluationConfigError):
    """Raised when an evaluation profile has invalid content."""