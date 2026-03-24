from __future__ import annotations

from typing import Any

import pandas as pd

from omnifinan.visualize import StockFigure

from imaginary_hub.indicators.base import registry
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
    sf = StockFigure(1, 1, 2, width=width, height=height)
    sf.add_candle_trace(0, 0, data_df=df, market=market)

    enriched = registry.apply(sf.data_dfs[0, 0].copy(), selected_indicators, custom_params=custom_params)
    sf.data_dfs[0, 0] = enriched

    overlay_colors = [
        "#60a5fa",
        "#f59e0b",
        "#34d399",
        "#f472b6",
        "#a78bfa",
        "#f87171",
    ]

    overlay_idx = 0
    oscillator_slot = 1

    for name in selected_indicators:
        spec = registry.get(name)
        params = {**spec.default_params, **custom_params.get(name, {})}

        if name == "MA":
            col = f"MA_{int(params['window'])}"
            if col in enriched.columns:
                sf.add_scatter_trace(
                    0,
                    0,
                    label=col,
                    position=0,
                    y_arr=pd.to_numeric(enriched[col], errors="coerce"),
                    plot_spec={"line": {"color": overlay_colors[overlay_idx % len(overlay_colors)], "width": 1.6}},
                )
                overlay_idx += 1
        elif name == "EMA":
            col = f"EMA_{int(params['window'])}"
            if col in enriched.columns:
                sf.add_scatter_trace(
                    0,
                    0,
                    label=col,
                    position=0,
                    y_arr=pd.to_numeric(enriched[col], errors="coerce"),
                    plot_spec={"line": {"color": overlay_colors[overlay_idx % len(overlay_colors)], "width": 1.6, "dash": "dot"}},
                )
                overlay_idx += 1
        elif name == "Bollinger":
            window = int(params["window"])
            for col, dash in [
                (f"BB_MID_{window}", "solid"),
                (f"BB_UP_{window}", "dash"),
                (f"BB_DN_{window}", "dash"),
            ]:
                if col in enriched.columns:
                    sf.add_scatter_trace(
                        0,
                        0,
                        label=col,
                        position=0,
                        y_arr=pd.to_numeric(enriched[col], errors="coerce"),
                        plot_spec={"line": {"color": overlay_colors[overlay_idx % len(overlay_colors)], "width": 1.3, "dash": dash}},
                    )
            overlay_idx += 1
        elif name == "RSI":
            col = f"RSI_{int(params['window'])}"
            if col in enriched.columns:
                sf.add_scatter_trace(
                    0,
                    0,
                    label=col,
                    position=oscillator_slot,
                    y_arr=pd.to_numeric(enriched[col], errors="coerce"),
                    plot_spec={"line": {"color": "#f59e0b", "width": 1.8}},
                )
        elif name == "MACD":
            for col, color in [
                ("MACD_LINE", "#60a5fa"),
                ("MACD_SIGNAL", "#f59e0b"),
            ]:
                if col in enriched.columns:
                    sf.add_scatter_trace(
                        0,
                        0,
                        label=col,
                        position=oscillator_slot + 1,
                        y_arr=pd.to_numeric(enriched[col], errors="coerce"),
                        plot_spec={"line": {"color": color, "width": 1.6}},
                    )

    sf.fig.update_layout(title=f"{ticker} · OmniFinan StockFigure")
    return sf.fig, enriched
