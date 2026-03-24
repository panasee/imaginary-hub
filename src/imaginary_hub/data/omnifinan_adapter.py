from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

import pandas as pd


INTERNAL_PRICE_PROVIDER = "yfinance"
SUPPORTED_INTERVALS = ["15min", "30min", "1h", "2h", "4h", "1d", "1w", "1m"]
MAX_LOOKBACK_DAYS = {
    "15min": 30,
    "30min": 30,
    "1h": 730,
    "2h": 730,
    "4h": 730,
    "1d": 3650,
    "1w": 3650,
    "1m": 3650,
}
UI_TO_BASE_INTERVAL = {
    "15min": "15m",
    "30min": "30m",
    "1h": "60m",
    "2h": "60m",
    "4h": "60m",
    "1d": "1d",
    "1w": "1d",
    "1m": "1d",
}
RESAMPLE_RULES = {
    "15min": None,
    "30min": None,
    "1h": None,
    "2h": "2h",
    "4h": "4h",
    "1d": None,
    "1w": "1W",
    "1m": "MS",
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
    out.index = pd.to_datetime(out.index, errors="coerce")
    out = out[~out.index.isna()]
    return out.dropna(subset=["close"]) 


def _resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df.empty:
        return df

    work = df.copy().sort_index()
    agg_map = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    label = "left" if rule in {"1W", "MS"} else "right"
    closed = "left" if rule in {"1W", "MS"} else "right"
    resampled = work.resample(rule, label=label, closed=closed).agg(agg_map)
    resampled = resampled.dropna(subset=["open", "high", "low", "close"])
    return resampled


def _maybe_trim_partial_period(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    if df.empty:
        return df
    if interval not in {"1w", "1m"}:
        return df

    now = pd.Timestamp.now(tz=df.index.tz) if df.index.tz is not None else pd.Timestamp.now()
    last_ts = df.index.max()
    if pd.isna(last_ts):
        return df

    if interval == "1w":
        current_period = now.to_period("W")
        last_period = last_ts.to_period("W")
    else:
        current_period = now.to_period("M")
        last_period = last_ts.to_period("M")

    if last_period == current_period and len(df) > 1:
        return df.iloc[:-1]
    return df


def resolve_fetch_plan(interval: str) -> tuple[str, str | None]:
    normalized = interval.strip()
    if normalized not in SUPPORTED_INTERVALS:
        raise ValueError(f"Unsupported interval: {interval}")
    return UI_TO_BASE_INTERVAL[normalized], RESAMPLE_RULES[normalized]


def clamp_date_range(start_date: str, end_date: str, interval: str) -> tuple[str, str]:
    start_ts = pd.to_datetime(start_date, errors="coerce")
    end_ts = pd.to_datetime(end_date, errors="coerce")
    if pd.isna(end_ts):
        end_ts = pd.Timestamp.now().normalize()
    if pd.isna(start_ts):
        start_ts = end_ts - pd.Timedelta(days=365)

    max_days = MAX_LOOKBACK_DAYS.get(interval, 3650)
    min_start = end_ts - pd.Timedelta(days=max_days)
    effective_start = max(start_ts, min_start)
    return effective_start.strftime("%Y-%m-%d"), end_ts.strftime("%Y-%m-%d")


def fetch_price_df(
    ticker: str,
    start_date: str,
    end_date: str,
    interval: str = "1d",
    provider: str | None = None,
) -> pd.DataFrame:
    from omnifinan.unified_api import get_price_df

    actual_provider = provider or INTERNAL_PRICE_PROVIDER
    base_interval, resample_rule = resolve_fetch_plan(interval)
    effective_start_date, effective_end_date = clamp_date_range(start_date, end_date, interval)

    df = get_price_df(
        ticker=ticker,
        start_date=effective_start_date,
        end_date=effective_end_date,
        interval=base_interval,
        provider=actual_provider,
    )
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()

    normalized = normalize_ohlcv(df)
    if normalized.empty:
        return normalized

    if resample_rule:
        normalized = _resample_ohlcv(normalized, resample_rule)
        normalized = _maybe_trim_partial_period(normalized, interval)

    return normalized


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
