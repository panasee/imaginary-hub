from __future__ import annotations

import numpy as np
import pandas as pd


class Indicators:
    @staticmethod
    def _close(df: pd.DataFrame) -> pd.Series:
        return pd.to_numeric(df["close"], errors="coerce")

    @staticmethod
    def _open(df: pd.DataFrame) -> pd.Series:
        return pd.to_numeric(df["open"], errors="coerce")

    @staticmethod
    def _high(df: pd.DataFrame) -> pd.Series:
        return pd.to_numeric(df["high"], errors="coerce")

    @staticmethod
    def _low(df: pd.DataFrame) -> pd.Series:
        return pd.to_numeric(df["low"], errors="coerce")

    @staticmethod
    def _ref(series: pd.Series, periods: int = 1) -> pd.Series:
        return series.shift(periods)

    @staticmethod
    def _ma(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).mean()

    @staticmethod
    def _ema(series: pd.Series, window: int) -> pd.Series:
        return series.ewm(span=window, adjust=False).mean()

    @staticmethod
    def _wma(series: pd.Series, window: int) -> pd.Series:
        weights = np.arange(1, window + 1, dtype=float)
        return series.rolling(window).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

    @staticmethod
    def _hhv(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).max()

    @staticmethod
    def _llv(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).min()

    @staticmethod
    def _cross(a: pd.Series, b: pd.Series) -> pd.Series:
        a = pd.to_numeric(a, errors="coerce")
        b = pd.to_numeric(b, errors="coerce")
        return ((a > b) & (a.shift(1) <= b.shift(1))).fillna(False).astype(int)

    @staticmethod
    def _dma(x: pd.Series, a: pd.Series) -> pd.Series:
        x = pd.to_numeric(x, errors="coerce")
        a = pd.to_numeric(a, errors="coerce").clip(lower=0)
        out = pd.Series(np.nan, index=x.index, dtype=float)
        prev = np.nan
        for idx in x.index:
            xv = x.loc[idx]
            av = a.loc[idx]
            if pd.isna(xv) or pd.isna(av):
                out.loc[idx] = prev
                continue
            if pd.isna(prev):
                prev = xv
            else:
                prev = av * xv + (1 - av) * prev
            out.loc[idx] = prev
        return out

    @staticmethod
    def ma(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        out[f"MA_{window}"] = Indicators._ma(Indicators._close(df), window)
        return out

    @staticmethod
    def ema(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        out[f"EMA_{window}"] = Indicators._ema(Indicators._close(df), window)
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

    @staticmethod
    def futu_reference_channel(df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        close = Indicators._close(df)
        high = Indicators._high(df)
        low = Indicators._low(df)
        open_ = Indicators._open(df)

        avg = (3 * close + high + low + open_) / 6
        refer = avg
        ma_close_21 = Indicators._ma(close, 21)
        dma_alpha = ((2 * close + high + low) / 4 - ma_close_21).abs() / ma_close_21.replace(0, np.nan)
        dyn = Indicators._dma(close, dma_alpha)

        ma10 = Indicators._ema(refer, 10)
        ma5 = Indicators._ema(refer, 5)
        ma200 = Indicators._ma(refer, 200)
        wma8 = Indicators._wma(refer, 8)
        highp_wma = (
            Indicators._hhv(wma8, 2) + Indicators._hhv(wma8, 4) + Indicators._hhv(wma8, 8)
        ) / 3
        lowp_wma = (
            Indicators._llv(wma8, 2) + Indicators._llv(wma8, 4) + Indicators._llv(wma8, 8)
        ) / 3
        stop_fall = ((Indicators._ref(lowp_wma, 1) == Indicators._ref(wma8, 1)) & (wma8 > lowp_wma)).fillna(False).astype(int)

        high_smth = Indicators._ema(Indicators._wma(high, 20), 70)
        low_smth = Indicators._ema(Indicators._wma(low, 20), 70)
        width = high_smth - low_smth
        top_long = high_smth + width * 2
        bot_long = low_smth - width * 2

        numerator_high = sum((13 - i) * Indicators._ref(high, i) for i in range(13))
        numerator_low = sum((13 - i) * Indicators._ref(low, i) for i in range(13))
        high_smth2 = numerator_high / (14 * 6 + 7)
        low_smth2 = numerator_low / (14 * 6 + 7)
        width2 = high_smth2 - low_smth2
        top_short = high_smth2 + width2
        bot_short = low_smth2 - width2

        positive = ((bot_short >= bot_long) & (top_short >= top_long)).fillna(False).astype(int)
        negative = ((top_short <= top_long) & (bot_short <= bot_long)).fillna(False).astype(int)
        neutral = ((bot_short >= bot_long) & (top_short <= top_long)).fillna(False).astype(int)
        mid = (high_smth2 + low_smth2) / 2

        buy1 = (Indicators._cross(bot_short, low) & positive.astype(bool)).astype(int)
        careful = (Indicators._cross(high, top_short) & positive.astype(bool) & (~neutral.astype(bool))).astype(int)
        sell1 = (Indicators._cross(high, top_short) & negative.astype(bool)).astype(int)
        careful2 = (Indicators._cross(bot_short, low) & negative.astype(bool) & (~neutral.astype(bool))).astype(int)
        buy2 = (Indicators._cross(bot_short, low) & neutral.astype(bool)).astype(int)
        sell2 = (Indicators._cross(high, top_short) & neutral.astype(bool)).astype(int)

        signal_b = ((buy1 == 1) | (buy2 == 1)).astype(int)
        signal_s = ((sell1 == 1) | (sell2 == 1)).astype(int)

        out["FUTU_DYN"] = dyn
        out["FUTU_AVG"] = avg
        out["FUTU_REFER"] = refer
        out["FUTU_MA10"] = ma10
        out["FUTU_MA5"] = ma5
        out["FUTU_MA200"] = ma200
        out["FUTU_WMA8"] = wma8
        out["FUTU_HIGHP_WMA"] = highp_wma
        out["FUTU_LOWP_WMA"] = lowp_wma
        out["FUTU_STOP_FALL"] = stop_fall
        out["FUTU_HIGH_SMTH"] = high_smth
        out["FUTU_LOW_SMTH"] = low_smth
        out["FUTU_TOP_LONG"] = top_long
        out["FUTU_BOT_LONG"] = bot_long
        out["FUTU_HIGH_SMTH2"] = high_smth2
        out["FUTU_LOW_SMTH2"] = low_smth2
        out["FUTU_TOP_SHORT"] = top_short
        out["FUTU_BOT_SHORT"] = bot_short
        out["FUTU_POSITIVE"] = positive
        out["FUTU_NEGATIVE"] = negative
        out["FUTU_NEUTRAL"] = neutral
        out["FUTU_MID"] = mid
        out["FUTU_BUY1"] = buy1
        out["FUTU_CAREFUL"] = careful
        out["FUTU_SELL1"] = sell1
        out["FUTU_CAREFUL2"] = careful2
        out["FUTU_BUY2"] = buy2
        out["FUTU_SELL2"] = sell2
        out["FUTU_SIGNAL_B"] = signal_b
        out["FUTU_SIGNAL_S"] = signal_s
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
