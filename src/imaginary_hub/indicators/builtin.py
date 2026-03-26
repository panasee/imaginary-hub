from __future__ import annotations

from .base import IndicatorParam, TraceSpec, register_indicator, registry
from .engine import Indicators


def _wrap(method_name: str):
    def _fn(df: pd.DataFrame, params: dict) -> pd.DataFrame:
        method = getattr(Indicators, method_name)
        return method(df, **params)

    return _fn


def register_builtins() -> None:
    existing = set(registry.names())
    specs = [
        (
            "MA",
            "ma",
            "overlay",
            {"window": 20},
            [IndicatorParam(key="window", label="Window", type="int", default=20, min=1, max=400, step=1)],
            [
                TraceSpec(
                    kind="line",
                    panel="overlay",
                    column_template="MA_{window}",
                    label_template="MA {window}",
                    color="#60a5fa",
                    width=1.6,
                )
            ],
            _wrap("ma"),
        ),
        (
            "EMA",
            "ema",
            "overlay",
            {"window": 20},
            [IndicatorParam(key="window", label="Window", type="int", default=20, min=1, max=400, step=1)],
            [
                TraceSpec(
                    kind="line",
                    panel="overlay",
                    column_template="EMA_{window}",
                    label_template="EMA {window}",
                    color="#f59e0b",
                    width=1.6,
                    dash="dot",
                )
            ],
            _wrap("ema"),
        ),
        (
            "Bollinger",
            "bollinger",
            "overlay",
            {"window": 20, "num_std": 2.0},
            [
                IndicatorParam(key="window", label="Window", type="int", default=20, min=1, max=400, step=1),
                IndicatorParam(key="num_std", label="Std Dev", type="float", default=2.0, min=0.1, max=10.0, step=0.1),
            ],
            [
                TraceSpec(
                    kind="line",
                    panel="overlay",
                    column_template="BB_MID_{window}",
                    label_template="BB Mid {window}",
                    color="#34d399",
                    width=1.3,
                ),
                TraceSpec(
                    kind="line",
                    panel="overlay",
                    column_template="BB_UP_{window}",
                    label_template="BB Up {window}",
                    color="#34d399",
                    width=1.1,
                    dash="dash",
                    opacity=0.8,
                ),
                TraceSpec(
                    kind="line",
                    panel="overlay",
                    column_template="BB_DN_{window}",
                    label_template="BB Dn {window}",
                    color="#34d399",
                    width=1.1,
                    dash="dash",
                    opacity=0.8,
                ),
            ],
            _wrap("bollinger"),
        ),
        (
            "RSI",
            "rsi",
            "oscillator",
            {"window": 14},
            [IndicatorParam(key="window", label="Window", type="int", default=14, min=1, max=200, step=1)],
            [
                TraceSpec(
                    kind="line",
                    panel="oscillator",
                    column_template="RSI_{window}",
                    label_template="RSI {window}",
                    color="#a78bfa",
                    width=1.8,
                )
            ],
            _wrap("rsi"),
        ),
        (
            "MACD",
            "macd",
            "oscillator",
            {"fast": 12, "slow": 26, "signal": 9},
            [
                IndicatorParam(key="fast", label="Fast", type="int", default=12, min=1, max=200, step=1),
                IndicatorParam(key="slow", label="Slow", type="int", default=26, min=2, max=400, step=1),
                IndicatorParam(key="signal", label="Signal", type="int", default=9, min=1, max=200, step=1),
            ],
            [
                TraceSpec(
                    kind="line",
                    panel="oscillator",
                    column_template="MACD_LINE_{fast}_{slow}_{signal}",
                    label_template="MACD Line {fast}/{slow}/{signal}",
                    color="#60a5fa",
                    width=1.6,
                ),
                TraceSpec(
                    kind="line",
                    panel="oscillator",
                    column_template="MACD_SIGNAL_{fast}_{slow}_{signal}",
                    label_template="MACD Signal {fast}/{slow}/{signal}",
                    color="#f59e0b",
                    width=1.6,
                ),
                TraceSpec(
                    kind="histogram",
                    panel="oscillator",
                    column_template="MACD_HIST_{fast}_{slow}_{signal}",
                    label_template="MACD Hist {fast}/{slow}/{signal}",
                    color="#94a3b8",
                    width=1.0,
                    opacity=0.5,
                ),
            ],
            _wrap("macd"),
        ),
        (
            "MA Cross Signal",
            "ma_cross_signal",
            "overlay",
            {"fast": 10, "slow": 30},
            [
                IndicatorParam(key="fast", label="Fast MA", type="int", default=10, min=1, max=200, step=1),
                IndicatorParam(key="slow", label="Slow MA", type="int", default=30, min=2, max=400, step=1),
            ],
            [
                TraceSpec(
                    kind="line",
                    panel="overlay",
                    column_template="XOVER_FAST_{fast}_{slow}",
                    label_template="Fast MA {fast}",
                    color="#38bdf8",
                    width=1.3,
                ),
                TraceSpec(
                    kind="line",
                    panel="overlay",
                    column_template="XOVER_SLOW_{fast}_{slow}",
                    label_template="Slow MA {slow}",
                    color="#f97316",
                    width=1.3,
                ),
                TraceSpec(
                    kind="marker",
                    panel="overlay",
                    column_template="XOVER_BUY_{fast}_{slow}",
                    label_template="MA Cross Buy {fast}/{slow}",
                    color="#22c55e",
                    marker_symbol="triangle-up",
                    marker_size=12,
                    anchor="low",
                    y_offset_ratio=-0.015,
                    text_template="BUY {fast}/{slow}",
                ),
                TraceSpec(
                    kind="marker",
                    panel="overlay",
                    column_template="XOVER_SELL_{fast}_{slow}",
                    label_template="MA Cross Sell {fast}/{slow}",
                    color="#ef4444",
                    marker_symbol="triangle-down",
                    marker_size=12,
                    anchor="high",
                    y_offset_ratio=0.015,
                    text_template="SELL {fast}/{slow}",
                ),
            ],
            _wrap("ma_cross_signal"),
        ),
        (
            "Breakout Signal",
            "breakout_signal",
            "overlay",
            {"window": 20},
            [IndicatorParam(key="window", label="Lookback", type="int", default=20, min=2, max=300, step=1)],
            [
                TraceSpec(
                    kind="line",
                    panel="overlay",
                    column_template="BREAKOUT_HIGH_{window}",
                    label_template="Breakout High {window}",
                    color="#14b8a6",
                    width=1.1,
                    dash="dot",
                    opacity=0.75,
                ),
                TraceSpec(
                    kind="line",
                    panel="overlay",
                    column_template="BREAKOUT_LOW_{window}",
                    label_template="Breakout Low {window}",
                    color="#f43f5e",
                    width=1.1,
                    dash="dot",
                    opacity=0.75,
                ),
                TraceSpec(
                    kind="marker",
                    panel="overlay",
                    column_template="BREAKOUT_BUY_{window}",
                    label_template="Breakout Buy {window}",
                    color="#10b981",
                    marker_symbol="star",
                    marker_size=13,
                    anchor="high",
                    y_offset_ratio=0.02,
                    text_template="BO↑ {window}",
                ),
                TraceSpec(
                    kind="marker",
                    panel="overlay",
                    column_template="BREAKOUT_SELL_{window}",
                    label_template="Breakout Sell {window}",
                    color="#e11d48",
                    marker_symbol="x",
                    marker_size=11,
                    anchor="low",
                    y_offset_ratio=-0.02,
                    text_template="BO↓ {window}",
                ),
            ],
            _wrap("breakout_signal"),
        ),
    ]
    for name, method_name, panel, default_params, params_schema, traces, fn in specs:
        if name not in existing:
            register_indicator(name, method_name, panel, default_params, fn, params_schema=params_schema, traces=traces)
