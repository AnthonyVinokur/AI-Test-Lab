class EvaluationPluginError(Exception):
    """Base exception for evaluation plugin failures."""


class PluginAlreadyRegisteredError(EvaluationPluginError):
    """Raised when an engine name is registered more than once."""


class PluginNotFoundError(EvaluationPluginError):
    """Raised when a requested engine is not registered."""


class InvalidPluginError(EvaluationPluginError):
    """Raised when a plugin does not satisfy the engine contract."""


class PluginDiscoveryError(EvaluationPluginError):
    """Raised when an installed plugin cannot be discovered or loaded."""