from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from imaginary_hub.charts.omnifinan_stock_figure import build_stock_figure
from imaginary_hub.data.omnifinan_adapter import fetch_price_df
from imaginary_hub.indicators.base import IndicatorParam, registry
from imaginary_hub.indicators.builtin import register_builtins


st.set_page_config(page_title="Imaginary Hub TV-like", layout="wide")
register_builtins()


@st.cache_data(show_spinner=False)
def load_price_df(ticker: str, start_date: str, end_date: str, interval: str, provider: str) -> pd.DataFrame:
    return fetch_price_df(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
        provider=provider,
    )


def render_param_widget(indicator_name: str, param: IndicatorParam, current_value):
    key = f"{indicator_name}__{param.key}"
    if param.type == "int":
        return st.number_input(
            param.label,
            min_value=int(param.min) if param.min is not None else None,
            max_value=int(param.max) if param.max is not None else None,
            value=int(current_value),
            step=int(param.step or 1),
            key=key,
            help=param.help,
        )
    if param.type == "float":
        return st.number_input(
            param.label,
            min_value=float(param.min) if param.min is not None else None,
            max_value=float(param.max) if param.max is not None else None,
            value=float(current_value),
            step=float(param.step or 0.1),
            key=key,
            help=param.help,
        )
    if param.type == "bool":
        return st.checkbox(param.label, value=bool(current_value), key=key, help=param.help)
    if param.type == "select":
        options = param.options or []
        idx = options.index(current_value) if current_value in options else 0
        return st.selectbox(param.label, options=options, index=idx, key=key, help=param.help)
    return st.text_input(param.label, value=str(current_value), key=key, help=param.help)


def build_indicator_params(selected: list[str]) -> dict[str, dict]:
    params_map: dict[str, dict] = {}
    for name in selected:
        spec = registry.get(name)
        with st.sidebar.expander(f"{name} Parameters", expanded=False):
            params = dict(spec.default_params)
            if not spec.params_schema:
                st.caption("No schema defined for this indicator yet.")
            for param in spec.params_schema:
                params[param.key] = render_param_widget(name, param, params.get(param.key, param.default))
            params_map[name] = params
    return params_map


def main() -> None:
    st.title("Imaginary Hub · OmniFinan TV-like Workstation")
    st.caption("Rendering now uses OmniFinan StockFigure first, with Streamlit only as the GUI shell.")

    with st.sidebar:
        st.subheader("Market")
        ticker = st.text_input("Ticker", value="AAPL").strip().upper()
        provider = st.selectbox("Provider", options=["yfinance", "akshare", "finnhub"], index=0)
        interval = st.selectbox("Interval", options=["1d", "1wk", "1mo"], index=0)
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=365))
        end_date = st.date_input("End Date", value=date.today())

        st.subheader("Indicators")
        indicator_names = registry.names()
        selected = st.multiselect(
            "Select indicators",
            options=indicator_names,
            default=[x for x in ["MA", "EMA", "RSI", "MACD"] if x in indicator_names],
        )

    custom_params = build_indicator_params(selected)

    if not ticker:
        st.warning("Please enter a ticker.")
        st.stop()

    with st.spinner(f"Loading {ticker}..."):
        df = load_price_df(
            ticker=ticker,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            interval=interval,
            provider=provider,
        )

    if df.empty:
        st.error(f"No data returned for {ticker}.")
        st.stop()

    fig, enriched = build_stock_figure(
        df=df,
        ticker=ticker,
        provider=provider,
        selected_indicators=selected,
        custom_params=custom_params,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ticker", ticker)
    c2.metric("Bars", len(enriched))
    c3.metric("Last Close", f"{enriched['close'].iloc[-1]:.2f}")
    c4.metric("Date Range", f"{enriched.index.min().date()} → {enriched.index.max().date()}")

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Data Preview", expanded=False):
        st.dataframe(enriched.tail(50), use_container_width=True)

    with st.expander("Indicator Config Snapshot", expanded=False):
        st.json(custom_params)


if __name__ == "__main__":
    main()
