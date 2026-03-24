from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

import pandas as pd


UI_TO_PROVIDER_INTERVAL = {
    "15min": "15m",
    "30min": "30m",
    "1h": "60m",
    "2h": "120m",
    "4h": "240m",
    "1d": "1d",
    "1w": "1wk",
    "1m": "1mo",
}


PRICE_ALIASES = {
    "open": ["open", "Open"],
    "high": ["high", "High"],
    "low": ["low", "Low"],
    "close": ["close", "Close", "adj_close", "Adj Close"],
    "volume": ["volume", "Volume"],
}


def _to_dict(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return obj
    return dict(vars(obj))


def _first_present(df: pd.DataFrame, names: list[str]) -> str | None:
    for name in names:
        if name in df.columns:
            return name
    return None


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        if "date" in out.columns:
            out.index = pd.to_datetime(out["date"], errors="coerce")
        elif "time" in out.columns:
            out.index = pd.to_datetime(out["time"], errors="coerce")

    out = out.sort_index()
    rename_map = {}
    for canonical, aliases in PRICE_ALIASES.items():
        found = _first_present(out, aliases)
        if found is not None:
            rename_map[found] = canonical
    out = out.rename(columns=rename_map)

    for col in ["open", "high", "low", "close", "volume"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = pd.NA

    out = out[["open", "high", "low", "close", "volume"]]
    out = out[~out.index.duplicated(keep="last")]
    return out.dropna(subset=["close"])


def map_interval(interval: str, provider: str) -> str:
    normalized = interval.strip().lower()
    mapped = UI_TO_PROVIDER_INTERVAL.get(normalized, normalized)

    if provider == "akshare":
        akshare_map = {
            "15m": "15m",
            "30m": "30m",
            "60m": "60m",
            "120m": "120m",
            "240m": "240m",
            "1d": "1d",
            "1wk": "1w",
            "1mo": "1m",
        }
        return akshare_map.get(mapped, mapped)

    return mapped


def fetch_price_df(
    ticker: str,
    start_date: str,
    end_date: str,
    interval: str = "1d",
    provider: str = "akshare",
) -> pd.DataFrame:
    from omnifinan.unified_api import get_price_df

    provider_interval = map_interval(interval, provider)
    df = get_price_df(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        interval=provider_interval,
        provider=provider,
    )
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    return normalize_ohlcv(df)


def fetch_financial_metrics(
    ticker: str,
    end_date: str | None = None,
    period: str = "ttm",
) -> dict[str, Any]:
    from omnifinan.unified_api import get_financial_metrics

    metrics = get_financial_metrics(ticker=ticker, end_date=end_date, period=period, limit=1)
    if not metrics:
        return {}
    return _to_dict(metrics[0])
