from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from imaginary_hub.config.theme import TV_DARK


OVERLAY_PREFIXES = ("MA_", "EMA_", "BB_MID_", "BB_UP_", "BB_DN_")
OSC_RSI_PREFIX = "RSI_"
MACD_COLS = ("MACD_LINE", "MACD_SIGNAL", "MACD_HIST")


def _has_rsi(df: pd.DataFrame) -> bool:
    return any(col.startswith(OSC_RSI_PREFIX) for col in df.columns)


def _has_macd(df: pd.DataFrame) -> bool:
    return all(col in df.columns for col in MACD_COLS)


def build_figure(df: pd.DataFrame, ticker: str, selected_indicators: list[str] | None = None) -> go.Figure:
    selected_indicators = selected_indicators or []
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=TV_DARK["paper_bgcolor"],
            plot_bgcolor=TV_DARK["plot_bgcolor"],
            font={"color": TV_DARK["font_color"]},
            title=f"{ticker} Price",
            annotations=[{"text": "No data", "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5, "showarrow": False}],
        )
        return fig

    has_rsi = _has_rsi(df)
    has_macd = _has_macd(df)

    row_heights = [0.58, 0.16]
    titles = [f"{ticker} Price", "Volume"]
    if has_rsi:
        row_heights.append(0.13)
        titles.append("RSI")
    if has_macd:
        row_heights.append(0.13)
        titles.append("MACD")

    fig = make_subplots(
        rows=len(row_heights),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=row_heights,
        subplot_titles=titles,
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            increasing_line_color=TV_DARK["up_color"],
            decreasing_line_color=TV_DARK["down_color"],
            name="OHLC",
        ),
        row=1,
        col=1,
    )

    overlay_cols = [c for c in df.columns if c.startswith(OVERLAY_PREFIXES)]
    ma_colors = TV_DARK["ma_colors"]
    for i, col in enumerate(overlay_cols):
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                mode="lines",
                line={"width": 1.4, "color": ma_colors[i % len(ma_colors)]},
                name=col,
            ),
            row=1,
            col=1,
        )

    vol_colors = [TV_DARK["volume_up"] if c >= o else TV_DARK["volume_down"] for c, o in zip(df["close"], df["open"])]
    fig.add_trace(
        go.Bar(x=df.index, y=df["volume"], marker_color=vol_colors, name="Volume"),
        row=2,
        col=1,
    )

    row_idx = 3
    if has_rsi:
        rsi_cols = [c for c in df.columns if c.startswith(OSC_RSI_PREFIX)]
        for col in rsi_cols:
            fig.add_trace(
                go.Scatter(x=df.index, y=df[col], mode="lines", line={"color": "#f59e0b", "width": 1.6}, name=col),
                row=row_idx,
                col=1,
            )
        fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=row_idx, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#22c55e", row=row_idx, col=1)
        fig.update_yaxes(range=[0, 100], row=row_idx, col=1)
        row_idx += 1

    if has_macd:
        fig.add_trace(
            go.Bar(x=df.index, y=df["MACD_HIST"], marker_color="#64748b", name="MACD_HIST"),
            row=row_idx,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df["MACD_LINE"], mode="lines", line={"color": "#60a5fa", "width": 1.5}, name="MACD_LINE"),
            row=row_idx,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df["MACD_SIGNAL"], mode="lines", line={"color": "#f59e0b", "width": 1.3}, name="MACD_SIGNAL"),
            row=row_idx,
            col=1,
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=TV_DARK["paper_bgcolor"],
        plot_bgcolor=TV_DARK["plot_bgcolor"],
        font={"color": TV_DARK["font_color"]},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        margin={"l": 40, "r": 20, "t": 50, "b": 20},
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=TV_DARK["grid_color"], showspikes=True, spikemode="across")
    fig.update_yaxes(showgrid=True, gridcolor=TV_DARK["grid_color"], showspikes=True, spikemode="across")
    return fig
