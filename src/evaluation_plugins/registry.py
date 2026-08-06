from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.evaluation_plugins.base import (
    EvaluationEngineFactory,
    ExternalEvaluationEngine,
)
from src.evaluation_plugins.errors import (
    InvalidPluginError,
    PluginAlreadyRegisteredError,
    PluginNotFoundError,
)


class EvaluationEngineRegistry:
    """Registers and constructs external evaluation engine plugins."""

    def __init__(self) -> None:
        self._factories: dict[str, EvaluationEngineFactory] = {}

    def register(
        self,
        name: str,
        factory: EvaluationEngineFactory,
        *,
        replace: bool = False,
    ) -> None:
        """Register an engine factory under a normalized name."""

        normalized_name = self._normalize_name(name)

        if normalized_name in self._factories and not replace:
            raise PluginAlreadyRegisteredError(
                f"Evaluation engine plugin "
                f"'{normalized_name}' is already registered."
            )

        if not callable(factory):
            raise InvalidPluginError(
                f"Factory for plugin '{normalized_name}' must be callable."
            )

        self._factories[normalized_name] = factory

    def unregister(self, name: str) -> None:
        """Remove an engine factory from the registry."""

        normalized_name = self._normalize_name(name)

        if normalized_name not in self._factories:
            raise PluginNotFoundError(
                f"Evaluation engine plugin "
                f"'{normalized_name}' is not registered."
            )

        del self._factories[normalized_name]

    def create(
        self,
        name: str,
        config: Mapping[str, Any] | None = None,
    ) -> ExternalEvaluationEngine:
        """Construct a registered evaluation engine."""

        normalized_name = self._normalize_name(name)

        try:
            factory = self._factories[normalized_name]
        except KeyError as exc:
            available = ", ".join(self.names()) or "none"

            raise PluginNotFoundError(
                f"Evaluation engine plugin '{normalized_name}' "
                f"is not registered. Available plugins: {available}."
            ) from exc

        engine = factory(config)

        self._validate_engine(
            expected_name=normalized_name,
            engine=engine,
        )

        return engine

    def contains(self, name: str) -> bool:
        """Return whether an engine name is registered."""

        normalized_name = self._normalize_name(name)
        return normalized_name in self._factories

    def names(self) -> tuple[str, ...]:
        """Return registered engine names in deterministic order."""

        return tuple(sorted(self._factories))

    def __len__(self) -> int:
        return len(self._factories)

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized_name = name.strip().lower()

        if not normalized_name:
            raise ValueError("Plugin name must not be empty.")

        return normalized_name

    @staticmethod
    def _validate_engine(
        *,
        expected_name: str,
        engine: object,
    ) -> None:
        engine_name = getattr(engine, "name", None)
        evaluate = getattr(engine, "evaluate", None)

        if not isinstance(engine_name, str) or not engine_name.strip():
            raise InvalidPluginError(
                f"Plugin '{expected_name}' returned an engine "
                "without a valid name."
            )

        if not callable(evaluate):
            raise InvalidPluginError(
                f"Plugin '{expected_name}' returned an engine "
                "without an evaluate() method."
            )

        if engine_name.strip().lower() != expected_name:
            raise InvalidPluginError(
                f"Plugin was registered as '{expected_name}' "
                f"but created engine '{engine_name}'."
            )