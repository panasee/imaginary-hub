# Price-Volume Quant Backtest Report

Universe: MAG7 + AVGO
Date range: 2020-01-01 -> 2025-12-31
Provider: akshare
Fee: 10.0 bps per position change

## Model
- Pure price-volume model (no financial factors).
- Signal source: `omnifinan.visualize.StockFigure.preset_main_indicators`.
- Buy signal: `BUY1_SIGNAL or BUY2_SIGNAL`.
- Sell signal: `SELL1_SIGNAL or SELL2_SIGNAL`.
- Execution: signal at t, take position for t+1 return.

## Portfolio Metrics (Equal-weight)
- strategy_total_return: 0.059671134115130364
- strategy_annualized_return: 0.009738935616687483
- strategy_annualized_volatility: 0.26924013387794216
- strategy_sharpe: 0.036171931266021994
- strategy_max_drawdown: -0.522047153245736
- strategy_points: 1508.0
- benchmark_total_return: 0.3437492538793361
- benchmark_annualized_return: 0.05064822093623689
- benchmark_annualized_volatility: 0.4297950901891867
- benchmark_sharpe: 0.11784271643015422
- benchmark_max_drawdown: -0.70850840867976
- benchmark_points: 1508.0

## Artifacts
- metrics_by_symbol.csv
- portfolio_nav.csv
- charts/*.html