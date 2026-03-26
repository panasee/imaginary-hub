# imaginary-hub

A practical executable quant stock-selection and trading analysis program built on top of **OmniFinan**.

## What this repo now includes

### 1. Existing quant research scripts

- Uses `omnifinan.unified_api` as the **data/fundamental/macro backend**
- Implements a **strategy layer** (momentum + quality + value + risk ranking)
- Runs a simple **equal-weight portfolio backtest** on selected names
- Exports reproducible artifacts:
  - `features.csv`
  - `ranking.csv`
  - `nav_detail.csv`
  - `portfolio_nav.csv`
  - `report.md`

### 2. TV-like GUI framework

A **TradingView-inspired local dashboard** built around **Streamlit** as GUI shell, with **OmniFinan StockFigure** as the preferred chart engine and **OmniFinan** as the backend.

Features:
- input **ticker**
- select **interval / date range / price-axis scale**
- use built-in **yfinance** as the internal price source
- render **candlestick + volume** via **OmniFinan `StockFigure`**
- render built-in indicators:
  - **MA**
  - **EMA**
  - **Bollinger Bands**
  - **RSI**
  - **MACD**
- **dynamic indicator parameter controls** generated from schema
- extensible **custom indicator registry**
- OmniFinan-backed data adapter

A Dash version is still kept as a backup entry point, but the **Streamlit app is now the main workstation path**.

## GUI architecture

- **`src/imaginary_hub/apps/tv_like_streamlit.py`**: main Streamlit app entry
- **`src/imaginary_hub/apps/tv_like_app.py`**: legacy/backup Dash entry
- **`src/imaginary_hub/data/omnifinan_adapter.py`**: OmniFinan OHLCV adapter + normalization
- **`src/imaginary_hub/indicators/base.py`**: indicator registry + parameter schema contract
- **`src/imaginary_hub/indicators/builtin.py`**: built-in example indicators + metadata registration
- **`src/imaginary_hub/indicators/engine.py`**: class-based indicator compute engine; each indicator method returns only newly computed columns
- **`src/imaginary_hub/charts/omnifinan_stock_figure.py`**: OmniFinan `StockFigure` adapter for GUI rendering
- **`src/imaginary_hub/charts/plotly_tv.py`**: legacy fallback renderer, no longer the preferred path
- **`src/imaginary_hub/config/theme.py`**: TradingView-like dark palette

## Indicator design

The indicator system is now **schema-driven**, so the GUI does not hardcode MA/RSI/MACD-specific inputs, while the actual chart rendering is delegated to **OmniFinan `StockFigure`**.

Each indicator can declare:
- **name**
- **method name**
- **panel**
- **default params**
- **parameter schema**
- **trace schema**

The compute path is now split cleanly:

```text
indicator = class method compute + UI schema + trace schema
```

Concretely:
- **`Indicators.some_indicator(df, ...) -> DataFrame`** computes only the extra columns for that indicator
- **`register_indicator(...)`** binds the display name to the method name, params schema, and trace schema
- the chart builder computes all selected indicators, concatenates the returned DataFrames by index, and then renders from the trace specs

Supported trace kinds currently include:
- **line**
- **histogram**
- **marker**

That means a new indicator no longer requires editing the chart builder just to tell the GUI which columns to draw, including signal markers such as **buy/sell points**, **crossovers**, and other event annotations.

## Install / environment

This repo assumes you already use the **`unified`** conda env for OmniFinan work.

Example editable install:

```bash
cd ~/workspace/imaginary-hub
~/miniconda3/envs/unified/bin/python -m pip install -e .
~/miniconda3/envs/unified/bin/python -m pip install -e ~/workspace/omnifinan
```

If OmniFinan is already importable in `unified`, the second line is unnecessary.

## Run the main Streamlit workstation

### Option A: direct streamlit command

```bash
cd ~/workspace/imaginary-hub
PYTHONPATH=~/workspace/omnifinan/src:$PYTHONPATH \
~/miniconda3/envs/unified/bin/streamlit run src/imaginary_hub/apps/tv_like_streamlit.py
```

Then open:

- `http://127.0.0.1:8501`

### Option B: console script wrapper

```bash
cd ~/workspace/imaginary-hub
PYTHONPATH=~/workspace/omnifinan/src:$PYTHONPATH \
imaginary-hub-tv-streamlit
```

## Run the backup Dash version

```bash
cd ~/workspace/imaginary-hub
PYTHONPATH=~/workspace/omnifinan/src:$PYTHONPATH \
~/miniconda3/envs/unified/bin/python -m imaginary_hub.apps.tv_like_app
```

Then open:

- `http://127.0.0.1:8050`

## Add a custom indicator

Add a new method to **`src/imaginary_hub/indicators/engine.py`** and then register its metadata in **`src/imaginary_hub/indicators/builtin.py`**.

### Step 1: implement the compute method

```python
import pandas as pd


class Indicators:
    @staticmethod
    def my_alpha(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        close = pd.to_numeric(df["close"], errors="coerce")
        out[f"MY_ALPHA_{window}"] = close.rolling(window).mean()
        out[f"MY_ALPHA_BUY_{window}"] = (close > out[f"MY_ALPHA_{window}"]).fillna(False).astype(int)
        return out
```

Rules:
- the first argument must be **`df`**
- extra parameter names and counts are **fully user-definable**
- the method must return a **DataFrame** indexed like the input
- return only the new indicator columns, not a full OHLCV copy

### Step 2: register the indicator metadata

```python
from imaginary_hub.indicators.base import IndicatorParam, TraceSpec, register_indicator
from imaginary_hub.indicators.builtin import _wrap

register_indicator(
    name="MyAlpha",
    method_name="my_alpha",
    panel="overlay",
    default_params={"window": 10},
    params_schema=[
        IndicatorParam(key="window", label="Window", type="int", default=10, min=1, max=300, step=1),
    ],
    traces=[
        TraceSpec(
            kind="line",
            panel="overlay",
            column_template="MY_ALPHA_{window}",
            label_template="MyAlpha {window}",
            color="#22c55e",
            width=1.8,
        ),
        TraceSpec(
            kind="marker",
            panel="overlay",
            column_template="MY_ALPHA_BUY_{window}",
            label_template="MyAlpha Buy {window}",
            color="#10b981",
            marker_symbol="triangle-up",
            marker_size=11,
            anchor="low",
            y_offset_ratio=-0.015,
            text_template="BUY {window}",
        ),
    ],
    fn=_wrap("my_alpha"),
)
```

Parameter names must stay consistent across three places:
- the method signature in **`engine.py`**
- **`default_params`** / **`params_schema`**
- any placeholders used by **`column_template`**, **`label_template`**, and **`text_template`**

The Streamlit sidebar renders parameter widgets from the schema, then the app computes all selected indicator DataFrames, concatenates them by index, and renders the declared traces through the OmniFinan chart object.

## Notes / limitations

- This is a **framework shell**, not a pixel-perfect TradingView clone.
- It is optimized for a **research workstation** flow, not ultra-low-latency real-time charting.
- The GUI now uses a built-in **yfinance-only** price path internally; provider switching is intentionally hidden from the UI.
- **2h / 4h / 1w / 1m** are built from local resampling of lower/base intervals.
- **Log** price scale is applied only to the main price axis; if price data contains **<= 0**, the app warns and falls back to **linear**.
- Built-in indicators are best treated as **examples/bootstrap defaults**, not the long-term center of the system.
- The next natural step is letting users register and manage fully custom indicators more directly.

## Existing quant CLI

```bash
cd ~/workspace/imaginary-hub
PYTHONPATH=~/workspace/omnifinan/src:$PYTHONPATH \
python3 -m imaginary_hub.run_quant \
  --universe AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA \
  --start-date 2024-01-01 \
  --end-date 2025-12-31 \
  --top-n 3 \
  --provider akshare \
  --out-dir outputs/us-tech-demo
```
