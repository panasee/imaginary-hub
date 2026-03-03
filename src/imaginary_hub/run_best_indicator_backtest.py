from __future__ import annotations

import itertools
import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Literal

import numpy as np
import pandas as pd

from omnifinan.unified_api import get_price_df
from omnifinan.visualize import StockFigure


Asset = Literal["SPY", "QQQ", "BTC-USD", "ETH-USD"]


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for the 2-year single-asset backtests."""

    end_date: str = date.today().isoformat()
    lookback_days: int = 365 * 2
    provider: str = "yfinance"
    interval: str = "1d"
    fee_bps: float = 5.0
    output_dir: Path = Path("outputs/best-indicators-2y")

    @property
    def start_date(self) -> str:
        end = date.fromisoformat(self.end_date)
        start = end - timedelta(days=self.lookback_days)
        return start.isoformat()


@dataclass(frozen=True)
class StrategyResult:
    name: str
    params: dict[str, float]
    metrics: dict[str, float]
    bt: pd.DataFrame


def _ensure_omnix_path() -> None:
    """Ensure OMNIX_PATH exists to avoid omnifinan prompt-loader warnings."""

    if os.environ.get("OMNIX_PATH"):
        return
    # Keep runtime artifacts outside repos; user can override.
    os.environ["OMNIX_PATH"] = "/home/dongkai-claw/.omnix"


def fetch_ohlcv(asset: Asset, cfg: BacktestConfig) -> pd.DataFrame:
    """Fetch OHLCV data using omnifinan's unified API.

    Args:
        asset: Symbol, e.g. SPY/QQQ/BTC-USD/ETH-USD.
        cfg: Backtest configuration.

    Returns:
        DataFrame indexed by datetime with columns: open/high/low/close/volume.
    """

    df = get_price_df(
        ticker=asset,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
        interval=cfg.interval,
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
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna(subset=["close"])


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    roll_up = up.ewm(alpha=1 / window, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / window, adjust=False).mean()
    rs = roll_up / roll_down.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def add_strategy_signals(df: pd.DataFrame, name: str, params: dict[str, float]) -> pd.DataFrame:
    """Attach buy/sell signals to a price dataframe.

    Signals are long/flat:
    - BUY  -> enter/hold long
    - SELL -> exit to cash

    Returns:
        Copy of df with boolean columns: buy_signal, sell_signal, plus indicator columns.
    """

    work = df.copy()
    close = work["close"]

    if name == "ma_cross":
        fast = int(params["fast"])
        slow = int(params["slow"])
        work["ma_fast"] = close.rolling(fast).mean()
        work["ma_slow"] = close.rolling(slow).mean()
        cross_up = (work["ma_fast"] > work["ma_slow"]) & (
            work["ma_fast"].shift(1) <= work["ma_slow"].shift(1)
        )
        cross_dn = (work["ma_fast"] < work["ma_slow"]) & (
            work["ma_fast"].shift(1) >= work["ma_slow"].shift(1)
        )
        work["buy_signal"] = cross_up
        work["sell_signal"] = cross_dn
        return work

    if name == "donchian_breakout":
        n = int(params["n"])
        work["donchian_high"] = work["high"].rolling(n).max()
        work["donchian_low"] = work["low"].rolling(n).min()
        buy = close > work["donchian_high"].shift(1)
        sell = close < work["donchian_low"].shift(1)
        work["buy_signal"] = buy
        work["sell_signal"] = sell
        return work

    if name == "bollinger_mr":
        n = int(params["n"])
        k = float(params["k"])
        mid = close.rolling(n).mean()
        std = close.rolling(n).std(ddof=0)
        work["bb_mid"] = mid
        work["bb_up"] = mid + k * std
        work["bb_dn"] = mid - k * std
        # Mean reversion: buy when below lower band; exit when back above mid.
        work["buy_signal"] = close < work["bb_dn"]
        work["sell_signal"] = close > work["bb_mid"]
        return work

    if name == "rsi_mr":
        n = int(params["n"])
        lo = float(params["lo"])
        hi = float(params["hi"])
        work["rsi"] = _rsi(close, n)
        work["buy_signal"] = work["rsi"] < lo
        work["sell_signal"] = work["rsi"] > hi
        return work

    raise ValueError(f"Unknown strategy: {name}")


def backtest_long_flat(sig_df: pd.DataFrame, fee_bps: float) -> pd.DataFrame:
    """Simple long/flat backtest (signal at t -> position for t+1)."""

    if sig_df.empty:
        return pd.DataFrame()

    work = sig_df.copy()
    work["ret"] = work["close"].pct_change().fillna(0.0)

    buy = work["buy_signal"].fillna(False).astype(bool)
    sell = work["sell_signal"].fillna(False).astype(bool)

    pos = np.zeros(len(work), dtype=float)
    state = 0.0
    for i in range(len(work)):
        if bool(buy.iloc[i]):
            state = 1.0
        if bool(sell.iloc[i]):
            state = 0.0
        pos[i] = state

    work["position"] = pd.Series(pos, index=work.index).shift(1).fillna(0.0)
    trade_flag = work["position"].diff().abs().fillna(work["position"].abs())
    fee = trade_flag * (fee_bps / 10000.0)

    work["strategy_ret"] = work["position"] * work["ret"] - fee
    work["nav"] = (1 + work["strategy_ret"]).cumprod()

    dd = work["nav"] / work["nav"].cummax() - 1
    work["drawdown"] = dd

    return work


def metrics_from_nav(nav: pd.Series) -> dict[str, float]:
    s = nav.dropna()
    if len(s) < 10:
        return {}

    rets = s.pct_change().dropna()
    total_ret = s.iloc[-1] / s.iloc[0] - 1
    ann_ret = (1 + total_ret) ** (252 / max(len(rets), 1)) - 1
    ann_vol = rets.std() * np.sqrt(252)
    sharpe = ann_ret / ann_vol if ann_vol > 1e-12 else np.nan
    max_dd = (s / s.cummax() - 1).min()

    return {
        "total_return": float(total_ret),
        "annualized_return": float(ann_ret),
        "annualized_volatility": float(ann_vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_dd),
        "bars": float(len(s)),
    }


def plot_with_signals(
    sig_df: pd.DataFrame,
    asset: Asset,
    title: str,
    out_html: Path,
    market: str,
) -> None:
    sf = StockFigure(1, 1, 2, width=1500, height=1100)
    sf.add_candle_trace(0, 0, data_df=sig_df, market=market)
    sf.add_volume_trace(0, 0)

    # Overlay some common indicator columns if present.
    overlay_cols = [
        "ma_fast",
        "ma_slow",
        "donchian_high",
        "donchian_low",
        "bb_mid",
        "bb_up",
        "bb_dn",
    ]
    for c in overlay_cols:
        if c in sig_df.columns:
            sf.add_scatter_trace(0, 0, label=c, position=0, y_arr=sig_df[c].astype(float))

    # RSI in subpanel if present.
    if "rsi" in sig_df.columns:
        sf.add_scatter_trace(0, 0, label="rsi", position=1, y_arr=sig_df["rsi"].astype(float))

    buy_idx = sig_df.index[sig_df["buy_signal"].fillna(False).astype(bool)]
    sell_idx = sig_df.index[sig_df["sell_signal"].fillna(False).astype(bool)]

    sf.add_marker_trace(
        0,
        0,
        label="BUY",
        position=0,
        x_arr=list(buy_idx),
        y_arr=list(sig_df.loc[buy_idx, "low"] * 0.995),
        marker={"symbol": "triangle-up", "color": "#1f9d55"},
    )
    sf.add_marker_trace(
        0,
        0,
        label="SELL",
        position=0,
        x_arr=list(sell_idx),
        y_arr=list(sig_df.loc[sell_idx, "high"] * 1.005),
        marker={"symbol": "triangle-down", "color": "#dc2626"},
    )

    sf.fig.update_layout(title=f"{asset} | {title}")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    sf.fig.write_html(str(out_html))


def _grid_candidates() -> list[tuple[str, dict[str, float]]]:
    candidates: list[tuple[str, dict[str, float]]] = []

    for fast, slow in [(5, 20), (10, 50), (20, 100)]:
        candidates.append(("ma_cross", {"fast": fast, "slow": slow}))

    for n in [20, 55]:
        candidates.append(("donchian_breakout", {"n": n}))

    for n, k in [(20, 2.0), (20, 2.5)]:
        candidates.append(("bollinger_mr", {"n": n, "k": k}))

    for n, lo, hi in [(14, 30, 70), (21, 35, 65)]:
        candidates.append(("rsi_mr", {"n": n, "lo": lo, "hi": hi}))

    return candidates


def evaluate_strategies(asset: Asset, df: pd.DataFrame, cfg: BacktestConfig) -> list[StrategyResult]:
    results: list[StrategyResult] = []
    for name, params in _grid_candidates():
        try:
            sig = add_strategy_signals(df, name=name, params=params)
            bt = backtest_long_flat(sig, fee_bps=cfg.fee_bps)
            m = metrics_from_nav(bt["nav"])
            if not m:
                continue
            results.append(StrategyResult(name=f"{name}", params=params, metrics=m, bt=bt))
        except Exception:
            continue
    return results


def pick_best(results: list[StrategyResult]) -> StrategyResult | None:
    if not results:
        return None

    # Primary: Sharpe; Secondary: max drawdown (less negative is better).
    def key(r: StrategyResult) -> tuple[float, float]:
        return (
            float(r.metrics.get("sharpe", -np.inf)),
            float(r.metrics.get("max_drawdown", -np.inf)),
        )

    return sorted(results, key=key, reverse=True)[0]


def run(cfg: BacktestConfig) -> int:
    _ensure_omnix_path()
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    assets: list[Asset] = ["SPY", "QQQ", "BTC-USD", "ETH-USD"]
    summary_rows: list[dict[str, object]] = []

    for a in assets:
        df = fetch_ohlcv(a, cfg)
        if df.empty:
            summary_rows.append({"asset": a, "status": "no_data"})
            continue

        results = evaluate_strategies(a, df, cfg)
        best = pick_best(results)
        if best is None:
            summary_rows.append({"asset": a, "status": "no_valid_strategy"})
            continue

        bt = best.bt
        bt.to_csv(cfg.output_dir / f"{a}_best_backtest.csv")

        market = "US" if a in {"SPY", "QQQ"} else "NA"
        title = f"best={best.name} params={best.params} sharpe={best.metrics.get('sharpe'):.2f}"
        plot_with_signals(
            bt,
            asset=a,
            title=title,
            out_html=cfg.output_dir / "charts" / f"{a}_best.html",
            market=market,
        )

        summary_rows.append(
            {
                "asset": a,
                "best_strategy": best.name,
                "params": best.params,
                **best.metrics,
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(cfg.output_dir / "summary.csv", index=False)

    report = [
        "# Best Indicator Backtest (2y)",
        "",
        f"Date range: {cfg.start_date} -> {cfg.end_date}",
        f"Provider: {cfg.provider}",
        f"Fee: {cfg.fee_bps} bps per position change",
        "",
        "Artifacts:",
        "- summary.csv",
        "- *_best_backtest.csv",
        "- charts/*_best.html",
    ]
    (cfg.output_dir / "report.md").write_text("\n".join(report), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(run(BacktestConfig()))
