from __future__ import annotations

import numpy as np
import pandas as pd

from .base import IndicatorParam, register_indicator, registry


def _ensure_close(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["close"], errors="coerce")


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
    out["MACD_LINE"] = macd_line
    out["MACD_SIGNAL"] = signal_line
    out["MACD_HIST"] = hist
    return out


def register_builtins() -> None:
    existing = set(registry.names())
    specs = [
        (
            "MA",
            "overlay",
            {"window": 20},
            [IndicatorParam(key="window", label="Window", type="int", default=20, min=1, max=400, step=1)],
            ma,
        ),
        (
            "EMA",
            "overlay",
            {"window": 20},
            [IndicatorParam(key="window", label="Window", type="int", default=20, min=1, max=400, step=1)],
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
            bollinger,
        ),
        (
            "RSI",
            "oscillator",
            {"window": 14},
            [IndicatorParam(key="window", label="Window", type="int", default=14, min=1, max=200, step=1)],
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
            macd,
        ),
    ]
    for name, panel, default_params, params_schema, fn in specs:
        if name not in existing:
            register_indicator(name, panel, default_params, fn, params_schema=params_schema)
