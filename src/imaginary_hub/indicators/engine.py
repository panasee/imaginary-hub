from __future__ import annotations

import numpy as np
import pandas as pd


class Indicators:
    @staticmethod
    def _close(df: pd.DataFrame) -> pd.Series:
        return pd.to_numeric(df["close"], errors="coerce")

    @staticmethod
    def _high(df: pd.DataFrame) -> pd.Series:
        return pd.to_numeric(df["high"], errors="coerce")

    @staticmethod
    def _low(df: pd.DataFrame) -> pd.Series:
        return pd.to_numeric(df["low"], errors="coerce")

    @staticmethod
    def ma(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        out[f"MA_{window}"] = Indicators._close(df).rolling(window).mean()
        return out

    @staticmethod
    def ema(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        out[f"EMA_{window}"] = Indicators._close(df).ewm(span=window, adjust=False).mean()
        return out

    @staticmethod
    def bollinger(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        close = Indicators._close(df)
        mid = close.rolling(window).mean()
        std = close.rolling(window).std(ddof=0)
        out[f"BB_MID_{window}"] = mid
        out[f"BB_UP_{window}"] = mid + num_std * std
        out[f"BB_DN_{window}"] = mid - num_std * std
        return out

    @staticmethod
    def rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        close = Indicators._close(df)
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        out[f"RSI_{window}"] = (100 - 100 / (1 + rs)).fillna(50)
        return out

    @staticmethod
    def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        close = Indicators._close(df)
        macd_line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        hist = macd_line - signal_line
        out[f"MACD_LINE_{fast}_{slow}_{signal}"] = macd_line
        out[f"MACD_SIGNAL_{fast}_{slow}_{signal}"] = signal_line
        out[f"MACD_HIST_{fast}_{slow}_{signal}"] = hist
        return out

    @staticmethod
    def ma_cross_signal(df: pd.DataFrame, fast: int = 10, slow: int = 30) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        close = Indicators._close(df)
        fast_ma = close.rolling(fast).mean()
        slow_ma = close.rolling(slow).mean()
        spread = fast_ma - slow_ma
        prev_spread = spread.shift(1)
        out[f"XOVER_FAST_{fast}_{slow}"] = fast_ma
        out[f"XOVER_SLOW_{fast}_{slow}"] = slow_ma
        out[f"XOVER_BUY_{fast}_{slow}"] = ((spread > 0) & (prev_spread <= 0)).fillna(False).astype(int)
        out[f"XOVER_SELL_{fast}_{slow}"] = ((spread < 0) & (prev_spread >= 0)).fillna(False).astype(int)
        return out

    @staticmethod
    def breakout_signal(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        close = Indicators._close(df)
        high = Indicators._high(df)
        low = Indicators._low(df)
        rolling_high = high.shift(1).rolling(window).max()
        rolling_low = low.shift(1).rolling(window).min()
        out[f"BREAKOUT_HIGH_{window}"] = rolling_high
        out[f"BREAKOUT_LOW_{window}"] = rolling_low
        out[f"BREAKOUT_BUY_{window}"] = ((close > rolling_high) & rolling_high.notna()).fillna(False).astype(int)
        out[f"BREAKOUT_SELL_{window}"] = ((close < rolling_low) & rolling_low.notna()).fillna(False).astype(int)
        return out


def compute_indicators(
    df: pd.DataFrame,
    requests: list[dict[str, object]],
) -> pd.DataFrame:
    parts: list[pd.DataFrame] = [df.copy()]
    for request in requests:
        name = str(request.get("name"))
        params = dict(request.get("params", {}) or {})
        fn = getattr(Indicators, name)
        result = fn(df, **params)
        if not isinstance(result, pd.DataFrame):
            raise TypeError(f"Indicator {name} must return a DataFrame")
        parts.append(result)
    out = pd.concat(parts, axis=1)
    out = out.loc[:, ~out.columns.duplicated(keep="last")]
    return out
