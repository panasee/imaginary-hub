from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
from dash import Dash, Input, Output, State, dcc, html

from imaginary_hub.charts.plotly_tv import build_figure
from imaginary_hub.data.omnifinan_adapter import fetch_price_df
from imaginary_hub.indicators.base import registry
from imaginary_hub.indicators.builtin import register_builtins

DEFAULT_STYLE = {
    "backgroundColor": "#0b1220",
    "color": "#d1d5db",
    "fontFamily": "Inter, Arial, sans-serif",
}

CARD = {
    "background": "#111827",
    "border": "1px solid #243244",
    "borderRadius": "10px",
    "padding": "12px",
    "marginBottom": "12px",
}


def create_app() -> Dash:
    register_builtins()
    app = Dash(__name__)
    indicator_options = [{"label": name, "value": name} for name in registry.names()]

    app.layout = html.Div(
        style={**DEFAULT_STYLE, "minHeight": "100vh", "padding": "16px"},
        children=[
            html.H2("Imaginary Hub · OmniFinan TV-like Workstation"),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "320px 1fr", "gap": "16px"},
                children=[
                    html.Div(
                        style=CARD,
                        children=[
                            html.Label("Ticker"),
                            dcc.Input(id="ticker", type="text", value="AAPL", debounce=True, style={"width": "100%", "marginBottom": "10px"}),
                            html.Label("Provider"),
                            dcc.Dropdown(id="provider", options=[{"label": x, "value": x} for x in ["akshare", "yfinance", "finnhub"]], value="yfinance", clearable=False),
                            html.Br(),
                            html.Label("Interval"),
                            dcc.Dropdown(id="interval", options=[{"label": x, "value": x} for x in ["1d", "1wk", "1mo"]], value="1d", clearable=False),
                            html.Br(),
                            html.Label("Date Range"),
                            dcc.DatePickerRange(
                                id="date-range",
                                start_date=(date.today() - timedelta(days=365)).isoformat(),
                                end_date=date.today().isoformat(),
                                display_format="YYYY-MM-DD",
                                style={"marginBottom": "10px"},
                            ),
                            html.Br(),
                            html.Label("Indicators"),
                            dcc.Dropdown(id="indicators", options=indicator_options, value=["MA", "EMA", "RSI", "MACD"], multi=True),
                            html.Br(),
                            html.Label("Quick Params"),
                            html.Div("MA/EMA/Bollinger window", style={"fontSize": "12px", "marginBottom": "4px"}),
                            dcc.Input(id="window", type="number", value=20, min=2, step=1, style={"width": "100%"}),
                            html.Div("RSI window", style={"fontSize": "12px", "marginTop": "8px", "marginBottom": "4px"}),
                            dcc.Input(id="rsi-window", type="number", value=14, min=2, step=1, style={"width": "100%"}),
                            html.Div("MACD fast / slow / signal", style={"fontSize": "12px", "marginTop": "8px", "marginBottom": "4px"}),
                            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr", "gap": "6px"}, children=[
                                dcc.Input(id="macd-fast", type="number", value=12, min=1, step=1),
                                dcc.Input(id="macd-slow", type="number", value=26, min=2, step=1),
                                dcc.Input(id="macd-signal", type="number", value=9, min=1, step=1),
                            ]),
                            html.Br(),
                            html.Button("Load Chart", id="load-btn", n_clicks=0, style={"width": "100%", "padding": "10px", "background": "#2563eb", "color": "white", "border": "none", "borderRadius": "8px"}),
                            html.Div(id="status", style={"marginTop": "10px", "fontSize": "13px", "color": "#93c5fd"}),
                        ],
                    ),
                    html.Div(
                        children=[
                            html.Div(style=CARD, children=[dcc.Graph(id="price-chart", style={"height": "82vh"})]),
                        ]
                    ),
                ],
            ),
        ],
    )

    @app.callback(
        Output("price-chart", "figure"),
        Output("status", "children"),
        Input("load-btn", "n_clicks"),
        State("ticker", "value"),
        State("provider", "value"),
        State("interval", "value"),
        State("date-range", "start_date"),
        State("date-range", "end_date"),
        State("indicators", "value"),
        State("window", "value"),
        State("rsi-window", "value"),
        State("macd-fast", "value"),
        State("macd-slow", "value"),
        State("macd-signal", "value"),
        prevent_initial_call=False,
    )
    def update_chart(_n, ticker, provider, interval, start_date, end_date, indicators, window, rsi_window, macd_fast, macd_slow, macd_signal):
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return build_figure(pd.DataFrame(), "EMPTY"), "Enter a ticker."

        df = fetch_price_df(ticker=ticker, start_date=start_date, end_date=end_date, interval=interval, provider=provider)
        if df.empty:
            return build_figure(pd.DataFrame(), ticker), f"No data returned for {ticker}."

        custom_params = {
            "MA": {"window": int(window or 20)},
            "EMA": {"window": int(window or 20)},
            "Bollinger": {"window": int(window or 20), "num_std": 2.0},
            "RSI": {"window": int(rsi_window or 14)},
            "MACD": {"fast": int(macd_fast or 12), "slow": int(macd_slow or 26), "signal": int(macd_signal or 9)},
        }
        enriched = registry.apply(df, indicators or [], custom_params=custom_params)
        fig = build_figure(enriched, ticker=ticker, selected_indicators=indicators or [])
        return fig, f"Loaded {ticker} · {provider} · {interval} · {len(enriched)} bars"

    return app


def main() -> None:
    os.environ.setdefault("DASH_DEBUG", "0")
    app = create_app()
    app.run(host="127.0.0.1", port=8050, debug=False)


if __name__ == "__main__":
    main()
