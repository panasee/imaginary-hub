from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from omnifinan.unified_api import get_price_df
from omnifinan.visualize import StockFigure

UNIVERSE_US_MAG7_AVGO = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "AVGO"]


@dataclass
class ModelConfig:
    start_date: str = "2020-01-01"
    end_date: str = "2025-12-31"
    provider: str = "akshare"
    fee_bps: float = 10.0
    output_dir: Path = Path("outputs/price-action-mag7-avgo")



def build_signal_dataframe(ticker: str, cfg: ModelConfig) -> pd.DataFrame:
    df = get_price_df(
        ticker=ticker,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
        provider=cfg.provider,
    ).copy()

    if df.empty:
        return df

    if not isinstance(df.index, pd.DatetimeIndex):
        if "date" in df.columns:
            df.index = pd.to_datetime(df["date"], errors="coerce")
        elif "time" in df.columns:
            df.index = pd.to_datetime(df["time"], errors="coerce")
    df = df.sort_index()

    # Use omnifinan's built-in candle + indicator logic.
    sf = StockFigure(1, 1, 1, width=1400, height=1000)
    sf.add_candle_trace(0, 0, data_df=df, market="US")
    sf.preset_main_indicators(0, 0)

    # data_dfs[0,0] is enriched with indicator columns and B/S signal columns.
    sig_df = sf.data_dfs[0, 0].copy()
    return sig_df



def backtest_long_only(sig_df: pd.DataFrame, fee_bps: float = 10.0) -> pd.DataFrame:
    if sig_df.empty:
        return pd.DataFrame()

    work = sig_df.copy()
    work["ret"] = pd.to_numeric(work["close"], errors="coerce").pct_change().fillna(0.0)

    buy_signal = work.get("BUY1_SIGNAL", False) | work.get("BUY2_SIGNAL", False)
    sell_signal = work.get("SELL1_SIGNAL", False) | work.get("SELL2_SIGNAL", False)

    position = np.zeros(len(work), dtype=float)
    state = 0.0
    for i in range(len(work)):
        if bool(buy_signal.iloc[i]):
            state = 1.0
        elif bool(sell_signal.iloc[i]):
            state = 0.0
        position[i] = state

    # Signal generated on close of day t, executed for day t+1 return
    work["position"] = pd.Series(position, index=work.index).shift(1).fillna(0.0)

    trade_flag = work["position"].diff().abs().fillna(work["position"].abs())
    fee = trade_flag * (fee_bps / 10000.0)

    work["strategy_ret"] = work["position"] * work["ret"] - fee
    work["buy_and_hold_ret"] = work["ret"]
    work["nav_strategy"] = (1 + work["strategy_ret"]).cumprod()
    work["nav_buy_hold"] = (1 + work["buy_and_hold_ret"]).cumprod()
    work["trade_flag"] = trade_flag
    work["buy_signal"] = buy_signal.astype(int)
    work["sell_signal"] = sell_signal.astype(int)

    return work



def metrics_from_nav(nav: pd.Series) -> dict[str, float]:
    s = nav.dropna()
    if len(s) < 2:
        return {}
    rets = s.pct_change().dropna()
    total_ret = s.iloc[-1] / s.iloc[0] - 1
    ann_ret = (1 + total_ret) ** (252 / max(len(rets), 1)) - 1
    ann_vol = rets.std() * np.sqrt(252)
    sharpe = ann_ret / ann_vol if ann_vol > 1e-12 else np.nan
    dd = s / s.cummax() - 1
    max_dd = dd.min()
    return {
        "total_return": float(total_ret),
        "annualized_return": float(ann_ret),
        "annualized_volatility": float(ann_vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_dd),
        "points": float(len(s)),
    }



def save_chart_with_signals(sig_df: pd.DataFrame, ticker: str, out_html: Path) -> None:
    sf = StockFigure(1, 1, 1, width=1500, height=1000)
    sf.add_candle_trace(0, 0, data_df=sig_df, market="US")
    sf.preset_main_indicators(0, 0)
    sf.fig.update_layout(title=f"{ticker} - Price/Volume Model (with B/S marks)")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    sf.fig.write_html(str(out_html))



def run(cfg: ModelConfig) -> int:
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    per_symbol_metrics: list[dict] = []
    strategy_curves = {}
    benchmark_curves = {}

    for ticker in UNIVERSE_US_MAG7_AVGO:
        sig_df = build_signal_dataframe(ticker, cfg)
        if sig_df.empty:
            continue

        bt = backtest_long_only(sig_df, fee_bps=cfg.fee_bps)
        if bt.empty:
            continue

        bt.to_csv(cfg.output_dir / f"{ticker}_backtest.csv")
        save_chart_with_signals(sig_df, ticker, cfg.output_dir / "charts" / f"{ticker}.html")

        m_strategy = metrics_from_nav(bt["nav_strategy"])
        m_bh = metrics_from_nav(bt["nav_buy_hold"])

        per_symbol_metrics.append(
            {
                "ticker": ticker,
                "n_bars": len(bt),
                "n_trades": int(bt["trade_flag"].sum()),
                "strategy_total_return": m_strategy.get("total_return", np.nan),
                "strategy_sharpe": m_strategy.get("sharpe", np.nan),
                "strategy_max_drawdown": m_strategy.get("max_drawdown", np.nan),
                "bh_total_return": m_bh.get("total_return", np.nan),
                "bh_sharpe": m_bh.get("sharpe", np.nan),
                "bh_max_drawdown": m_bh.get("max_drawdown", np.nan),
            }
        )

        strategy_curves[ticker] = bt["nav_strategy"]
        benchmark_curves[ticker] = bt["nav_buy_hold"]

    if not strategy_curves:
        print("No valid symbols for backtest.")
        return 1

    strategy_panel = pd.concat(strategy_curves, axis=1).sort_index().ffill().dropna(how="all")
    benchmark_panel = pd.concat(benchmark_curves, axis=1).sort_index().ffill().dropna(how="all")

    portfolio = pd.DataFrame(index=strategy_panel.index)
    portfolio["strategy_nav_eqw"] = strategy_panel.mean(axis=1)
    portfolio["benchmark_nav_eqw"] = benchmark_panel.mean(axis=1)

    portfolio.to_csv(cfg.output_dir / "portfolio_nav.csv")
    strategy_panel.to_csv(cfg.output_dir / "strategy_nav_by_symbol.csv")
    benchmark_panel.to_csv(cfg.output_dir / "benchmark_nav_by_symbol.csv")

    metrics_df = pd.DataFrame(per_symbol_metrics).sort_values("strategy_total_return", ascending=False)
    metrics_df.to_csv(cfg.output_dir / "metrics_by_symbol.csv", index=False)

    p_strategy = metrics_from_nav(portfolio["strategy_nav_eqw"])
    p_bh = metrics_from_nav(portfolio["benchmark_nav_eqw"])

    report_lines = [
        "# Price-Volume Quant Backtest Report",
        "",
        "Universe: MAG7 + AVGO",
        f"Date range: {cfg.start_date} -> {cfg.end_date}",
        f"Provider: {cfg.provider}",
        f"Fee: {cfg.fee_bps} bps per position change",
        "",
        "## Model",
        "- Pure price-volume model (no financial factors).",
        "- Signal source: `omnifinan.visualize.StockFigure.preset_main_indicators`.",
        "- Buy signal: `BUY1_SIGNAL or BUY2_SIGNAL`.",
        "- Sell signal: `SELL1_SIGNAL or SELL2_SIGNAL`.",
        "- Execution: signal at t, take position for t+1 return.",
        "",
        "## Portfolio Metrics (Equal-weight)",
    ]
    for k, v in p_strategy.items():
        report_lines.append(f"- strategy_{k}: {v}")
    for k, v in p_bh.items():
        report_lines.append(f"- benchmark_{k}: {v}")

    report_lines += ["", "## Artifacts", "- metrics_by_symbol.csv", "- portfolio_nav.csv", "- charts/*.html"]

    (cfg.output_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Done. Output dir: {cfg.output_dir}")
    print("Portfolio strategy metrics:", p_strategy)
    print("Portfolio benchmark metrics:", p_bh)
    return 0


if __name__ == "__main__":
    cfg = ModelConfig()
    raise SystemExit(run(cfg))
