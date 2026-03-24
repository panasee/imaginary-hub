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


def _resolve_column(enriched: pd.DataFrame, trace: TraceSpec, params: dict) -> str | None:
    column = resolve_template(trace.column_template, params)
    return column if column in enriched.columns else None


def _resolve_y_values(enriched: pd.DataFrame, trace: TraceSpec, params: dict) -> pd.Series:
    if trace.anchor == "zero":
        return pd.Series(0.0, index=enriched.index)
    if trace.anchor == "column" and trace.y_column_template:
        y_column = resolve_template(trace.y_column_template, params)
        if y_column in enriched.columns:
            return pd.to_numeric(enriched[y_column], errors="coerce")
    source_col = {
        "close": "close",
        "open": "open",
        "high": "high",
        "low": "low",
    }.get(trace.anchor, "close")
    base = pd.to_numeric(enriched[source_col], errors="coerce")
    if trace.y_offset_ratio:
        span = (pd.to_numeric(enriched["high"], errors="coerce") - pd.to_numeric(enriched["low"], errors="coerce")).abs()
        base = base + span.fillna(0) * trace.y_offset_ratio
    return base


def _add_line_trace(sf: StockFigure, enriched: pd.DataFrame, trace: TraceSpec, params: dict, position: int) -> None:
    column = _resolve_column(enriched, trace, params)
    if not column:
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
    column = _resolve_column(enriched, trace, params)
    if not column:
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


def _add_marker_trace(sf: StockFigure, enriched: pd.DataFrame, trace: TraceSpec, params: dict, position: int) -> None:
    column = _resolve_column(enriched, trace, params)
    if not column:
        return

    events = pd.to_numeric(enriched[column], errors="coerce")
    if trace.truthy_only:
        mask = events.fillna(0) != 0
    else:
        mask = events.notna()
    if not mask.any():
        return

    label = resolve_template(trace.label_template or column, params)
    y_values = _resolve_y_values(enriched, trace, params)
    marker_df = pd.DataFrame({
        "x": enriched.index,
        "y": y_values,
        "event": events,
    }).loc[mask]

    text = None
    if trace.text_template:
        text = [resolve_template(trace.text_template, params) for _ in range(len(marker_df))]

    sf.fig.add_scatter(
        x=marker_df["x"],
        y=marker_df["y"],
        mode="markers+text" if text else "markers",
        name=label,
        marker={
            "symbol": trace.marker_symbol,
            "size": trace.marker_size,
            "color": trace.color or "#22c55e",
            "opacity": trace.opacity,
        },
        text=text,
        textposition="top center" if position == 0 else "middle right",
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
            elif trace.kind == "marker":
                _add_marker_trace(sf, enriched, trace, params, position=position)

        if spec.panel == "oscillator":
            oscillator_row += 1

    sf.fig.update_layout(title=f"{ticker} · OmniFinan StockFigure")
    return sf.fig, enriched
