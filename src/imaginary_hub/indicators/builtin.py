from __future__ import annotations

import numpy as np
import pandas as pd

from .base import IndicatorParam, TraceSpec, register_indicator, registry


def _ensure_close(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["close"], errors="coerce")


def _ensure_high(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["high"], errors="coerce")


def _ensure_low(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["low"], errors="coerce")


def ma(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    out = df.copy()
    window = int(params.get("window", 20))
    out[f"MA_{window}"] = _ensure_close(out).rolling(window).mean()
    return out


def ema(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    out = df.copy()
    window = int(params.get("window", 20))
    out[f"EMA_{window}"] = _ensure_close(out).ewm(span=window, adjust=False).mean()
    return out


def bollinger(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    out = df.copy()
    window = int(params.get("window", 20))
    num_std = float(params.get("num_std", 2.0))
    close = _ensure_close(out)
    mid = close.rolling(window).mean()
    std = close.rolling(window).std(ddof=0)
    out[f"BB_MID_{window}"] = mid
    out[f"BB_UP_{window}"] = mid + num_std * std
    out[f"BB_DN_{window}"] = mid - num_std * std
    return out


def rsi(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    out = df.copy()
    window = int(params.get("window", 14))
    close = _ensure_close(out)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out[f"RSI_{window}"] = (100 - 100 / (1 + rs)).fillna(50)
    return out


def macd(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    out = df.copy()
    close = _ensure_close(out)
    fast = int(params.get("fast", 12))
    slow = int(params.get("slow", 26))
    signal = int(params.get("signal", 9))
    macd_line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    out[f"MACD_LINE_{fast}_{slow}_{signal}"] = macd_line
    out[f"MACD_SIGNAL_{fast}_{slow}_{signal}"] = signal_line
    out[f"MACD_HIST_{fast}_{slow}_{signal}"] = hist
    return out


def ma_cross_signal(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    out = df.copy()
    fast = int(params.get("fast", 10))
    slow = int(params.get("slow", 30))
    close = _ensure_close(out)
    fast_ma = close.rolling(fast).mean()
    slow_ma = close.rolling(slow).mean()
    spread = fast_ma - slow_ma
    prev_spread = spread.shift(1)

    out[f"XOVER_FAST_{fast}_{slow}"] = fast_ma
    out[f"XOVER_SLOW_{fast}_{slow}"] = slow_ma
    out[f"XOVER_BUY_{fast}_{slow}"] = ((spread > 0) & (prev_spread <= 0)).fillna(False).astype(int)
    out[f"XOVER_SELL_{fast}_{slow}"] = ((spread < 0) & (prev_spread >= 0)).fillna(False).astype(int)
    return out


def breakout_signal(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    out = df.copy()
    window = int(params.get("window", 20))
    close = _ensure_close(out)
    high = _ensure_high(out)
    low = _ensure_low(out)
    rolling_high = high.shift(1).rolling(window).max()
    rolling_low = low.shift(1).rolling(window).min()
    out[f"BREAKOUT_HIGH_{window}"] = rolling_high
    out[f"BREAKOUT_LOW_{window}"] = rolling_low
    out[f"BREAKOUT_BUY_{window}"] = ((close > rolling_high) & rolling_high.notna()).fillna(False).astype(int)
    out[f"BREAKOUT_SELL_{window}"] = ((close < rolling_low) & rolling_low.notna()).fillna(False).astype(int)
    return out


def register_builtins() -> None:
    existing = set(registry.names())
    specs = [
        (
            "MA",
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
            ma,
        ),
        (
            "EMA",
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
            ema,
        ),
        (
            "Bollinger",
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
            bollinger,
        ),
        (
            "RSI",
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
            rsi,
        ),
        (
            "MACD",
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
            macd,
        ),
        (
            "MA Cross Signal",
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
            ma_cross_signal,
        ),
        (
            "Breakout Signal",
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
            breakout_signal,
        ),
    ]
    for name, panel, default_params, params_schema, traces, fn in specs:
        if name not in existing:
            register_indicator(name, panel, default_params, fn, params_schema=params_schema, traces=traces)
