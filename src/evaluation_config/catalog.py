"""Built-in evaluation profile catalog."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIRECTORY = PROJECT_ROOT / "configs" / "evaluation"


def list_profiles() -> list[str]:
    """Return available built-in evaluation profile names."""

    return sorted(
        path.stem
        for path in PROFILE_DIRECTORY.glob("*.yaml")
        if path.is_file()
    )


def profile_exists(name: str) -> bool:
    """Return True when a built-in profile exists."""

    return (
        (PROFILE_DIRECTORY / f"{name}.yaml").is_file()
        or (PROFILE_DIRECTORY / f"{name}.yml").is_file()
        or (PROFILE_DIRECTORY / f"{name}.json").is_file()
    )


def resolve_profile_path(
    profile: str | Path,
) -> Path:
    """Resolve a profile name or explicit file path.

    Explicit paths take precedence. If the supplied value does not
    identify an existing file, the built-in evaluation profile catalog
    is searched.
    """

    requested = Path(profile)

    if requested.is_file():
        return requested

    # If the caller explicitly supplied an extension/path, preserve it.
    if requested.suffix:
        return requested

    for suffix in (".yaml", ".yml", ".json"):
        candidate = PROFILE_DIRECTORY / f"{requested.name}{suffix}"

        if candidate.is_file():
            return candidate

    return requested