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

### 2. New TV-like GUI framework

A **TradingView-inspired local dashboard** built with **Dash + Plotly**.

Features:
- input **ticker**
- select **provider / interval / date range**
- render **candlestick + volume**
- render built-in indicators:
  - **MA**
  - **EMA**
  - **Bollinger Bands**
  - **RSI**
  - **MACD**
- extensible **custom indicator registry**
- OmniFinan-backed data adapter

## GUI architecture

- **`src/imaginary_hub/apps/tv_like_app.py`**: Dash app entry
- **`src/imaginary_hub/data/omnifinan_adapter.py`**: OmniFinan OHLCV adapter + normalization
- **`src/imaginary_hub/indicators/base.py`**: indicator registry and extension interface
- **`src/imaginary_hub/indicators/builtin.py`**: built-in indicators
- **`src/imaginary_hub/charts/plotly_tv.py`**: Plotly multi-panel chart builder
- **`src/imaginary_hub/config/theme.py`**: TradingView-like dark palette

## Install / environment

This repo assumes you already use the **`unified`** conda env for OmniFinan work.

Example editable install:

```bash
cd ~/workspace/imaginary-hub
~/miniconda3/envs/unified/bin/python -m pip install -e .
~/miniconda3/envs/unified/bin/python -m pip install -e ~/workspace/omnifinan
```

If OmniFinan is already importable in `unified`, the second line is unnecessary.

## Run the TV-like GUI

### Option A: module run

```bash
cd ~/workspace/imaginary-hub
PYTHONPATH=~/workspace/omnifinan/src:$PYTHONPATH \
~/miniconda3/envs/unified/bin/python -m imaginary_hub.apps.tv_like_app
```

Then open:

- `http://127.0.0.1:8050`

### Option B: console script

```bash
cd ~/workspace/imaginary-hub
PYTHONPATH=~/workspace/omnifinan/src:$PYTHONPATH \
imaginary-hub-tv
```

## Add a custom indicator

Register a new indicator through the registry contract:

```python
from imaginary_hub.indicators.base import register_indicator


def my_indicator(df, params):
    out = df.copy()
    out["MY_ALPHA"] = out["close"].rolling(int(params.get("window", 10))).mean()
    return out

register_indicator(
    name="MyAlpha",
    panel="overlay",
    default_params={"window": 10},
    fn=my_indicator,
)
```

Then add it to the selected indicator list in the GUI or wire it into the app defaults.

## Notes / limitations

- This is a **framework shell**, not a pixel-perfect TradingView clone.
- It is optimized for a **research workstation** flow, not ultra-low-latency real-time charting.
- The app currently exposes a compact **quick-params** control set, not full per-indicator dynamic forms.
- The adapter prefers OmniFinan direct data APIs and keeps the interface deterministic.

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
