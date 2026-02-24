# Workspace Repo Analysis (2026-02-24)

> Scope baseline: `~/workspace`
> Constraint applied: `pyomnix` / `omnifinan` treated as read-only; analysis only.

## 1) Repo Inventory (git repos under `~/workspace`)

- `imaginary-hub` (project repo, writable)
- `omnifinan` (key finance library, read-only)
- `pyomnix` (base utility/workflow library, read-only)
- `awesome-quant`
- `akshare`
- `aktools`
- `akquant`
- `FinRL`
- `qlib`
- `quant`

---

## 2) Key Findings: `omnifinan` (重点)

## 2.1 Architecture snapshot

- Package root: `src/omnifinan`
- Major modules:
  - `unified_api.py`: core unified data/fundamental/macro API
  - `data/unified_service.py`: cache + incremental refresh service layer
  - `data/providers/*`: provider abstraction (akshare / finnhub / yfinance / sec_edgar)
  - `core/workflow.py`: LangGraph-driven hedge-fund workflow orchestration
  - `agents/*`: analyst nodes/edges/graph components
  - `backtester.py`: strategy backtesting loop with long/short + margin handling
  - `presentation/cli.py`, `presentation/api.py`: CLI + Flask API entrypoints

## 2.2 Highest-value reusable APIs

From `unified_api.py` (public functions):

- `get_prices(...)` / `get_price_df(...)`
  - Multi-market symbol normalization + market detection
  - Daily + intraday intervals (`1d`, `1m`, `3m`, `5m`, `15m`, `30m`, `60m`)
  - Holiday filtering + data column normalization + volume/amount auto-completion
  - Optional provider switching (`akshare`, `finnhub`, `yfinance`)

- `get_macro_indicators(...)` + `get_macro_indicators_structured(...)`
  - Built-in source policy and robust normalization pipeline
  - Macro dimensions mapped into growth / inflation / liquidity / credit / market_feedback
  - Useful for downstream signal-engineering directly

- `get_financial_metrics(...)`
  - Cross-market financial metric extraction with fallback logic
  - Notes: some TODO/log messages indicate partially evolving sockets

- `search_line_items(...)`, `get_market_cap(...)`, `get_company_news(...)`, `get_insider_trades(...)`
  - Broad fundamental/news coverage with varying completeness by market/provider

## 2.3 Important design strengths

- Clear **provider abstraction** (`DataProvider`) + factory pattern.
- Strong **service-layer caching** (`UnifiedDataService`) including:
  - dataset cache,
  - stale-series detection for macro,
  - partial refresh/merge logic,
  - history snapshots (`macro_indicators_history`).
- Workflow integration already done for LLM multi-agent portfolio decisions.
- Backtester has practical mechanics (long/short, margin, realized PnL, drawdown/sharpe/sortino).

## 2.4 Risks / caveats to keep in mind

- Some functions contain TODO markers and comments indicating partial coverage for certain markets.
- `unified_api.py` is very large (single-file complexity); integration should call APIs, avoid deep edits.
- Coverage/quality may vary by upstream data source availability.

---

## 3) `pyomnix` Summary (supporting base layer)

## 3.1 Useful components for this project

- `pyomnix.data_process.DataManipulator`
  - Data load/merge helpers
  - 2D/3D plotting helpers
  - live plot / Dash-serving utilities
  - candlestick update helpers

- `pyomnix.agents.graphs`
  - Ready-made LangGraph builders:
    - chat graph with summarization
    - tool-agent graph
    - self-correction graph
  - Includes `GraphSession` wrapper for state/history/export and streaming

- `pyomnix.utils.plot`
  - plotting presets + helper utilities

## 3.2 Role in our quant stack

- `omnifinan` should be the primary finance-domain engine.
- `pyomnix` should be used as infra support for:
  - data manipulation,
  - visualization,
  - generic graph/session orchestration patterns.

---

## 4) `imaginary-hub` current state

- Currently minimal scaffold (`README.md`, `LICENSE`), no implementation yet.
- Best next step: make this the orchestration/integration layer that calls `omnifinan` + `pyomnix` directly.

---

## 5) Recommended integration blueprint (no reinvention)

## 5.1 Proposed structure in `imaginary-hub`

```text
imaginary-hub/
  src/imaginary_hub/
    data/
      market.py        # thin wrappers over omnifinan.get_prices/get_price_df
      macro.py         # wrappers over get_macro_indicators_structured
      fundamentals.py  # wrappers over get_financial_metrics/search_line_items
    signals/
      macro_regime.py
      valuation.py
      technical.py
      risk.py
    strategies/
      baseline_rotation.py
      event_driven.py
    pipeline/
      runner.py
      report.py
    config/
      defaults.yaml
  notebooks/
  tests/
  docs/
```

## 5.2 Integration principles

1. Call `omnifinan` first; avoid rebuilding market-data plumbing.
2. Keep wrappers thin and typed at project boundary.
3. Add project-specific logic only in `signals/strategies/pipeline`.
4. If `omnifinan` lacks a feature, copy minimal needed module into `imaginary-hub` and adapt there.

---

## 6) Suggested immediate next tasks

1. Create `imaginary-hub` package skeleton + pyproject + basic CLI.
2. Implement three thin adapters first:
   - `fetch_price_df()`
   - `fetch_macro_structured()`
   - `fetch_financial_metrics()`
3. Build one baseline strategy using these adapters.
4. Add smoke tests with 1-2 tickers and short date window.
5. Produce first reproducible report artifact (CSV + markdown summary).

---

## 7) Rules applied during this analysis

- No modification to `pyomnix` / `omnifinan`.
- No push performed to non-`imaginary-hub` repos.
- Analysis artifact saved in `imaginary-hub/docs/` for future reference.
