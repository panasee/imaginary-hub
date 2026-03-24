from __future__ import annotations

from typing import Any

import pandas as pd

from omnifinan.visualize import StockFigure

from imaginary_hub.indicators.base import TraceSpec, registry, resolve_template
from imaginary_hub.indicators.builtin import register_builtins


MARKET_MAP = {
    "yfinance": "US",
    "finnhub": "US",
    "akshare": "A",
}


def infer_market(provider: str, ticker: str) -> str:
    if provider in MARKET_MAP:
        return MARKET_MAP[provider]
    if ticker.isdigit() and len(ticker) in {5, 6}:
        return "A"
    return "US"


def _add_line_trace(sf: StockFigure, enriched: pd.DataFrame, trace: TraceSpec, params: dict, position: int) -> None:
    column = resolve_template(trace.column_template, params)
    if column not in enriched.columns:
        return
    label = resolve_template(trace.label_template or column, params)
    sf.add_scatter_trace(
        0,
        0,
        label=label,
        position=position,
        y_arr=pd.to_numeric(enriched[column], errors="coerce"),
        plot_spec={
            "line": {
                "color": trace.color or "#60a5fa",
                "width": trace.width,
                "dash": trace.dash,
            },
            "opacity": trace.opacity,
        },
    )


def _add_histogram_trace(sf: StockFigure, enriched: pd.DataFrame, trace: TraceSpec, params: dict, position: int) -> None:
    column = resolve_template(trace.column_template, params)
    if column not in enriched.columns:
        return
    label = resolve_template(trace.label_template or column, params)
    sf.fig.add_bar(
        x=enriched.index,
        y=pd.to_numeric(enriched[column], errors="coerce"),
        name=label,
        marker={"color": trace.color or "#94a3b8"},
        opacity=trace.opacity,
        row=position + 1,
        col=1,
    )


def build_stock_figure(
    df: pd.DataFrame,
    ticker: str,
    provider: str,
    selected_indicators: list[str] | None = None,
    custom_params: dict[str, dict] | None = None,
    width: int = 1400,
    height: int = 1000,
) -> tuple[Any, pd.DataFrame]:
    register_builtins()
    selected_indicators = selected_indicators or []
    custom_params = custom_params or {}

    market = infer_market(provider, ticker)
    oscillator_count = sum(1 for name in selected_indicators if registry.get(name).panel == "oscillator")
    total_rows = max(2, 1 + oscillator_count)

    sf = StockFigure(1, 1, total_rows, width=width, height=height)
    sf.add_candle_trace(0, 0, data_df=df, market=market)

    enriched = registry.apply(sf.data_dfs[0, 0].copy(), selected_indicators, custom_params=custom_params)
    sf.data_dfs[0, 0] = enriched

    oscillator_row = 1
    for name in selected_indicators:
        spec = registry.get(name)
        params = {**spec.default_params, **custom_params.get(name, {})}
        position = 0 if spec.panel == "overlay" else oscillator_row

        for trace in spec.traces:
            if trace.kind == "line":
                _add_line_trace(sf, enriched, trace, params, position=position)
            elif trace.kind == "histogram":
                _add_histogram_trace(sf, enriched, trace, params, position=position)

        if spec.panel == "oscillator":
            oscillator_row += 1

    sf.fig.update_layout(title=f"{ticker} · OmniFinan StockFigure")
    return sf.fig, enriched
