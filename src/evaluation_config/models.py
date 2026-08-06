"""Typed models for evaluation profile configuration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MetricConfig(BaseModel):
    """Configuration for one external evaluation metric."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    enabled: bool = True
    options: dict[str, Any] = Field(default_factory=dict)


class EngineConfig(BaseModel):
    """Configuration for one evaluation engine plugin."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    enabled: bool = True
    metrics: list[MetricConfig] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_unique_metrics(self) -> "EngineConfig":
        metric_names = [
            metric.name.casefold()
            for metric in self.metrics
            if metric.enabled
        ]

        if len(metric_names) != len(set(metric_names)):
            raise ValueError(
                f"Engine '{self.name}' contains duplicate metric names."
            )

        return self


class QualityGateConfig(BaseModel):
    """Configuration controlling aggregate evaluation acceptance."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    minimum_score: float = Field(default=0.70, ge=0.0, le=1.0)
    fail_on_engine_error: bool = True
    require_all_engines: bool = False


class EvaluationProfile(BaseModel):
    """Complete evaluation configuration profile."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    version: str = Field(default="1.0", min_length=1)
    description: str | None = None
    engines: list[EngineConfig] = Field(min_length=1)
    quality_gate: QualityGateConfig = Field(
        default_factory=QualityGateConfig
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_unique_engines(self) -> "EvaluationProfile":
        enabled_engine_names = [
            engine.name.casefold()
            for engine in self.engines
            if engine.enabled
        ]

        if not enabled_engine_names:
            raise ValueError(
                "Evaluation profile must enable at least one engine."
            )

        if len(enabled_engine_names) != len(set(enabled_engine_names)):
            raise ValueError(
                "Evaluation profile contains duplicate engine names."
            )

        return self