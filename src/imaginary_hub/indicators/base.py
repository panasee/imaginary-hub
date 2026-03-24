from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd


IndicatorFn = Callable[[pd.DataFrame, dict], pd.DataFrame]


@dataclass(frozen=True)
class IndicatorSpec:
    name: str
    panel: str = "overlay"  # overlay | oscillator
    default_params: dict = field(default_factory=dict)
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

    def apply(self, df: pd.DataFrame, selected: list[str], custom_params: dict[str, dict] | None = None) -> pd.DataFrame:
        custom_params = custom_params or {}
        out = df.copy()
        for name in selected:
            spec = self.get(name)
            params = {**spec.default_params, **custom_params.get(name, {})}
            out = spec.fn(out, params)
        return out


registry = IndicatorRegistry()


def register_indicator(name: str, panel: str, default_params: dict, fn: IndicatorFn) -> None:
    registry.register(IndicatorSpec(name=name, panel=panel, default_params=default_params, fn=fn))
