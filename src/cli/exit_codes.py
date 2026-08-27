from __future__ import annotations

from enum import IntEnum


class CliExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    INPUT_ERROR = 2
    INFRASTRUCTURE_ERROR = 3