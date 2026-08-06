from __future__ import annotations

from importlib.metadata import entry_points

from src.evaluation_plugins.errors import PluginDiscoveryError
from src.evaluation_plugins.registry import EvaluationEngineRegistry


PLUGIN_ENTRY_POINT_GROUP = "ai_test_lab.evaluation_engines"


def discover_evaluation_plugins(
    registry: EvaluationEngineRegistry,
    *,
    replace: bool = False,
) -> tuple[str, ...]:
    """
    Discover installed external evaluation engine plugins.

    Third-party packages register factories under the entry-point group:

        ai_test_lab.evaluation_engines
    """

    discovered_names: list[str] = []

    installed_entry_points = entry_points()
    plugin_entry_points = installed_entry_points.select(
        group=PLUGIN_ENTRY_POINT_GROUP
    )

    for entry_point in plugin_entry_points:
        try:
            factory = entry_point.load()

            registry.register(
                entry_point.name,
                factory,
                replace=replace,
            )
        except Exception as exc:
            raise PluginDiscoveryError(
                f"Could not load evaluation plugin "
                f"'{entry_point.name}' from '{entry_point.value}'."
            ) from exc

        discovered_names.append(entry_point.name)

    return tuple(sorted(discovered_names))