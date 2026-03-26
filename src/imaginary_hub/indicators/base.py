from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import pandas as pd


IndicatorFn = Callable[[pd.DataFrame, dict], pd.DataFrame]
ParamType = Literal["int", "float", "bool", "select", "text"]
TraceKind = Literal["line", "histogram", "marker"]
TracePanel = Literal["overlay", "oscillator"]
MarkerAnchor = Literal["close", "open", "high", "low", "column", "zero"]


@dataclass(frozen=True)
class IndicatorParam:
    key: str
    label: str
    type: ParamType
    default: Any
    min: int | float | None = None
    max: int | float | None = None
    step: int | float | None = None
    options: list[Any] = field(default_factory=list)
    help: str | None = None


@dataclass(frozen=True)
class TraceSpec:
    kind: TraceKind
    column_template: str
    panel: TracePanel = "overlay"
    label_template: str | None = None
    color: str | None = None
    width: float = 1.6
    dash: str = "solid"
    opacity: float = 1.0
    fill_to_next_y: bool = False
    marker_symbol: str = "circle"
    marker_size: int = 9
    anchor: MarkerAnchor = "close"
    y_column_template: str | None = None
    y_offset_ratio: float = 0.0
    truthy_only: bool = True
    text_template: str | None = None


@dataclass(frozen=True)
class IndicatorSpec:
    name: str
    method_name: str
    panel: str = "overlay"
    default_params: dict = field(default_factory=dict)
    params_schema: list[IndicatorParam] = field(default_factory=list)
    fn: IndicatorFn | None = None
    traces: list[TraceSpec] = field(default_factory=list)


class IndicatorRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, IndicatorSpec] = {}

    def register(self, spec: IndicatorSpec) -> None:
        if spec.fn is None:
            raise ValueError(f"Indicator {spec.name} has no callable fn")
        self._specs[spec.name] = spec

    def get(self, name: str) -> IndicatorSpec:
        if name not in self._specs:
            raise KeyError(f"Unknown indicator: {name}")
        return self._specs[name]

    def names(self) -> list[str]:
        return list(self._specs.keys())

    def specs(self) -> dict[str, IndicatorSpec]:
        return dict(self._specs)

    def build_params(self, selected: list[str], overrides: dict[str, dict] | None = None) -> dict[str, dict]:
        overrides = overrides or {}
        built: dict[str, dict] = {}
        for name in selected:
            spec = self.get(name)
            built[name] = {**spec.default_params, **overrides.get(name, {})}
        return built


registry = IndicatorRegistry()


def resolve_template(template: str, params: dict) -> str:
    return template.format(**params)


def register_indicator(
    name: str,
    method_name: str,
    panel: str,
    default_params: dict,
    fn: IndicatorFn,
    params_schema: list[IndicatorParam] | None = None,
    traces: list[TraceSpec] | None = None,
) -> None:
    registry.register(
        IndicatorSpec(
            name=name,
            method_name=method_name,
            panel=panel,
            default_params=default_params,
            params_schema=params_schema or [],
            fn=fn,
            traces=traces or [],
        )
    )
