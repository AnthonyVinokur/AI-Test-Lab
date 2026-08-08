class DeepEvalIntegrationError(Exception):
    """Base exception for DeepEval integration failures."""


class DeepEvalDependencyError(DeepEvalIntegrationError):
    """Raised when the optional DeepEval dependency is unavailable."""


class UnsupportedDeepEvalMetricError(DeepEvalIntegrationError):
    """Raised when an unsupported DeepEval metric is requested."""


class DeepEvalExecutionError(DeepEvalIntegrationError):
    """Raised when DeepEval cannot complete an evaluation."""