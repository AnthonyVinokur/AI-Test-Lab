""""Load evaluation profiles from YAML or JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from src.evaluation_config.catalog import resolve_profile_path, list_profiles
from src.evaluation_config.errors import (
    EvaluationConfigFileError,
    EvaluationConfigValidationError,
)
from src.evaluation_config.models import EvaluationProfile


SUPPORTED_PROFILE_EXTENSIONS = {".yaml", ".yml", ".json"}


def load_evaluation_profile(
    path: str | Path,
) -> EvaluationProfile:
    """Load and validate an evaluation profile.

    Args:
        path: YAML or JSON profile path.

    Returns:
        A validated EvaluationProfile.

    Raises:
        EvaluationConfigFileError:
            The file is missing, unsupported, unreadable, or malformed.
        EvaluationConfigValidationError:
            The parsed profile violates the expected schema.
    """

    profile_path = resolve_profile_path(path)

    if not profile_path.exists():
        available_profiles = list_profiles()

        if Path(path).suffix:
            raise EvaluationConfigFileError(
                f"Evaluation profile does not exist: {profile_path}"
            )

        available_text = "\n".join(
            f"  {profile_name}"
            for profile_name in available_profiles
        )

        raise EvaluationConfigFileError(
            f"Unknown evaluation profile '{path}'.\n\n"
            f"Available built-in profiles:\n"
            f"{available_text}\n\n"
            "You may also provide a path to a YAML or JSON profile."
        )

    if not profile_path.is_file():
        raise EvaluationConfigFileError(
            f"Evaluation profile path is not a file: {profile_path}"
        )

    suffix = profile_path.suffix.casefold()

    if suffix not in SUPPORTED_PROFILE_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_PROFILE_EXTENSIONS))
        raise EvaluationConfigFileError(
            f"Unsupported evaluation profile format '{suffix}'. "
            f"Supported formats: {supported}."
        )

    try:
        content = profile_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EvaluationConfigFileError(
            f"Unable to read evaluation profile "
            f"'{profile_path}': {exc}"
        ) from exc

    try:
        raw_profile = _parse_profile(content, suffix)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise EvaluationConfigFileError(
            f"Malformed evaluation profile "
            f"'{profile_path}': {exc}"
        ) from exc

    if not isinstance(raw_profile, dict):
        raise EvaluationConfigValidationError(
            "Evaluation profile root must be an object."
        )

    try:
        return EvaluationProfile.model_validate(raw_profile)
    except ValidationError as exc:
        raise EvaluationConfigValidationError(
            f"Invalid evaluation profile "
            f"'{profile_path}':\n{exc}"
        ) from exc


def _parse_profile(
    content: str,
    suffix: str,
) -> dict[str, Any] | Any:
    if suffix == ".json":
        return json.loads(content)

    return yaml.safe_load(content)