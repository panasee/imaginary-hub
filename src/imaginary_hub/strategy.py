from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .omnifinan_adapter import fetch_financial_metrics, fetch_price_df


def _safe_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        x = float(v)
        if np.isnan(x):
            return None
        return x
    except Exception:
        return None


def _extract_close(prices: pd.DataFrame) -> pd.Series:
    if prices.empty:
        return pd.Series(dtype=float)

    if "close" in prices.columns:
        s = pd.to_numeric(prices["close"], errors="coerce")
    else:
        # Fallback: first numeric column
        numeric_cols = [c for c in prices.columns if pd.api.types.is_numeric_dtype(prices[c])]
        if not numeric_cols:
            return pd.Series(dtype=float)
        s = pd.to_numeric(prices[numeric_cols[0]], errors="coerce")

    if isinstance(prices.index, pd.DatetimeIndex):
        s.index = prices.index
    elif "date" in prices.columns:
        s.index = pd.to_datetime(prices["date"], errors="coerce")
    elif "time" in prices.columns:
        s.index = pd.to_datetime(prices["time"], errors="coerce")

    return s.dropna().sort_index()


def calc_symbol_features(
    ticker: str,
    start_date: str,
    end_date: str,
    provider: str = "akshare",
) -> dict[str, Any]:
    prices = fetch_price_df(ticker=ticker, start_date=start_date, end_date=end_date, provider=provider)
    close = _extract_close(prices)
    if len(close) < 80:
        return {"ticker": ticker, "status": "insufficient_price_history"}

    ret_20 = close.iloc[-1] / close.iloc[-21] - 1 if len(close) >= 21 else None
    ret_60 = close.iloc[-1] / close.iloc[-61] - 1 if len(close) >= 61 else None
    vol_20 = close.pct_change().tail(20).std()

    fm = fetch_financial_metrics(ticker=ticker, end_date=end_date, period="ttm")

    pe = _safe_float(fm.get("price_to_earnings_ratio"))
    pb = _safe_float(fm.get("price_to_book_ratio"))
    roe = _safe_float(fm.get("return_on_equity"))
    rg = _safe_float(fm.get("revenue_growth"))

    return {
        "ticker": ticker,
        "status": "ok",
        "ret_20": _safe_float(ret_20),
        "ret_60": _safe_float(ret_60),
        "vol_20": _safe_float(vol_20),
        "pe": pe,
        "pb": pb,
        "roe": roe,
        "revenue_growth": rg,
        "close": _safe_float(close.iloc[-1]),
    }


def rank_universe(features_df: pd.DataFrame) -> pd.DataFrame:
    df = features_df.copy()
    ok_mask = df["status"].eq("ok")
    df = df.loc[ok_mask].copy()
    if df.empty:
        return df

    # Higher is better: momentum/quality/growth ; Lower is better: valuation/risk
    pe = pd.to_numeric(df.get("pe"), errors="coerce")
    pb = pd.to_numeric(df.get("pb"), errors="coerce")
    vol_20 = pd.to_numeric(df.get("vol_20"), errors="coerce")

    components = {
        "mom": pd.to_numeric(df.get("ret_60"), errors="coerce"),
        "quality": pd.to_numeric(df.get("roe"), errors="coerce"),
        "growth": pd.to_numeric(df.get("revenue_growth"), errors="coerce"),
        "value_pe": -pe,
        "value_pb": -pb,
        "risk": -vol_20,
    }

    score_cols = []
    for name, series in components.items():
        x = pd.to_numeric(series, errors="coerce")
        rank = x.rank(pct=True, na_option="bottom")
        col = f"score_{name}"
        df[col] = rank
        score_cols.append(col)

    df["total_score"] = df[score_cols].mean(axis=1)
    return df.sort_values("total_score", ascending=False).reset_index(drop=True)
