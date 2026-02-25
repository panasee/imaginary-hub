from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

import pandas as pd


def _to_dict(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return obj
    return dict(vars(obj))


def fetch_price_df(
    ticker: str,
    start_date: str,
    end_date: str,
    interval: str = "1d",
    provider: str = "akshare",
):
    from omnifinan.unified_api import get_price_df

    df = get_price_df(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
        provider=provider,
    )
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    return df.copy()


def fetch_financial_metrics(
    ticker: str,
    end_date: str | None = None,
    period: str = "ttm",
):
    from omnifinan.unified_api import get_financial_metrics

    metrics = get_financial_metrics(ticker=ticker, end_date=end_date, period=period, limit=1)
    if not metrics:
        return {}
    return _to_dict(metrics[0])


def fetch_macro_structured(start_date: str | None = None, end_date: str | None = None):
    from omnifinan.unified_api import get_macro_indicators_structured

    return get_macro_indicators_structured(start_date=start_date, end_date=end_date)
