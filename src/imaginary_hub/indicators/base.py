from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import pandas as pd


IndicatorFn = Callable[[pd.DataFrame, dict], pd.DataFrame]
ParamType = Literal["int", "float", "bool", "select", "text"]


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
class IndicatorSpec:
    name: str
    panel: str = "overlay"  # overlay | oscillator | separate
    default_params: dict = field(default_factory=dict)
    params_schema: list[IndicatorParam] = field(default_factory=list)
    fn: IndicatorFn | None = None


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

    def apply(self, df: pd.DataFrame, selected: list[str], custom_params: dict[str, dict] | None = None) -> pd.DataFrame:
        out = df.copy()
        params_map = self.build_params(selected, overrides=custom_params)
        for name in selected:
            spec = self.get(name)
            out = spec.fn(out, params_map[name])
        return out


registry = IndicatorRegistry()


def register_indicator(
    name: str,
    panel: str,
    default_params: dict,
    fn: IndicatorFn,
    params_schema: list[IndicatorParam] | None = None,
) -> None:
    registry.register(
        IndicatorSpec(
            name=name,
            panel=panel,
            default_params=default_params,
            params_schema=params_schema or [],
            fn=fn,
        )
    )
