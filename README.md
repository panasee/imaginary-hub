# imaginary-hub

A practical executable quant stock-selection and trading analysis program built on top of `omnifinan`.

## What this repo does

- Uses `omnifinan.unified_api` as the **data/fundamental/macro backend**
- Implements a **strategy layer** (momentum + quality + value + risk ranking)
- Runs a simple **equal-weight portfolio backtest** on selected names
- Exports reproducible artifacts:
  - `features.csv`
  - `ranking.csv`
  - `nav_detail.csv`
  - `portfolio_nav.csv`
  - `report.md`

## Install (local workspace)

```bash
cd ~/workspace/imaginary-hub
python3 -m pip install -e .
# ensure omnifinan is importable too (pick one):
python3 -m pip install -e ~/workspace/omnifinan
# or: export PYTHONPATH=~/workspace/omnifinan/src:$PYTHONPATH
```

## Run

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

## Notes for omnifinan integration

This repo intentionally does **not** re-implement the bottom layer. It directly calls:

- `get_price_df`
- `get_financial_metrics`
- `get_macro_indicators_structured` (adapter ready)

If runtime reveals bottom-layer gaps in `omnifinan`, those should be fixed in `omnifinan` and this repo will consume the improved APIs.
