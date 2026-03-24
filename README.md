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
- select **provider / interval / date range**
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
- **`src/imaginary_hub/indicators/builtin.py`**: built-in example indicators
- **`src/imaginary_hub/charts/omnifinan_stock_figure.py`**: OmniFinan `StockFigure` adapter for GUI rendering
- **`src/imaginary_hub/charts/plotly_tv.py`**: legacy fallback renderer, no longer the preferred path
- **`src/imaginary_hub/config/theme.py`**: TradingView-like dark palette

## Indicator design

The indicator system is now **schema-driven**, so the GUI does not hardcode MA/RSI/MACD-specific inputs, while the actual chart rendering is delegated to **OmniFinan `StockFigure`**.

Each indicator can declare:
- **name**
- **panel**
- **default params**
- **parameter schema**
- **calculation function**

This makes it straightforward to replace built-in indicators with your own research indicators later.

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

Register a new indicator through the registry contract:

```python
from imaginary_hub.indicators.base import IndicatorParam, register_indicator


def my_indicator(df, params):
    out = df.copy()
    window = int(params.get("window", 10))
    out["MY_ALPHA"] = out["close"].rolling(window).mean()
    return out

register_indicator(
    name="MyAlpha",
    panel="overlay",
    default_params={"window": 10},
    params_schema=[
        IndicatorParam(key="window", label="Window", type="int", default=10, min=1, max=300, step=1),
    ],
    fn=my_indicator,
)
```

The Streamlit sidebar will render parameter widgets from the schema, and the selected outputs are then drawn through the OmniFinan chart object.

## Notes / limitations

- This is a **framework shell**, not a pixel-perfect TradingView clone.
- It is optimized for a **research workstation** flow, not ultra-low-latency real-time charting.
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
