from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .strategy import calc_symbol_features, rank_universe


@dataclass
class RunConfig:
    universe: list[str]
    start_date: str
    end_date: str
    top_n: int
    provider: str
    out_dir: Path


def backtest_equal_weight(
    tickers: list[str],
    start_date: str,
    end_date: str,
    provider: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    from .omnifinan_adapter import fetch_price_df

    curves = {}
    for t in tickers:
        df = fetch_price_df(t, start_date=start_date, end_date=end_date, provider=provider)
        if df.empty or "close" not in df.columns:
            continue
        px = pd.to_numeric(df["close"], errors="coerce").dropna()
        if len(px) < 2:
            continue
        if isinstance(df.index, pd.DatetimeIndex):
            px.index = df.index[: len(px)]
        px = px.sort_index()
        curves[t] = px / px.iloc[0]

    if not curves:
        return pd.DataFrame(), pd.DataFrame()

    nav = pd.concat(curves, axis=1).ffill().dropna(how="all")
    port = nav.mean(axis=1).to_frame("portfolio_nav")
    return nav, port


def summarize_performance(port: pd.DataFrame) -> dict:
    if port.empty:
        return {"status": "no_portfolio_curve"}

    s = port["portfolio_nav"].dropna()
    if len(s) < 2:
        return {"status": "insufficient_points"}

    rets = s.pct_change().dropna()
    total_ret = s.iloc[-1] / s.iloc[0] - 1
    ann_ret = (1 + total_ret) ** (252 / max(len(rets), 1)) - 1
    ann_vol = rets.std() * (252**0.5)
    sharpe = ann_ret / ann_vol if ann_vol and ann_vol > 1e-12 else None
    dd = s / s.cummax() - 1
    max_dd = dd.min()

    return {
        "status": "ok",
        "points": int(len(s)),
        "total_return": float(total_ret),
        "annualized_return": float(ann_ret),
        "annualized_volatility": float(ann_vol),
        "sharpe": None if sharpe is None else float(sharpe),
        "max_drawdown": float(max_dd),
    }


def build_report(cfg: RunConfig) -> int:
    cfg.out_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        calc_symbol_features(
            ticker=t,
            start_date=cfg.start_date,
            end_date=cfg.end_date,
            provider=cfg.provider,
        )
        for t in cfg.universe
    ]
    features = pd.DataFrame(rows)
    ranked = rank_universe(features)

    features.to_csv(cfg.out_dir / "features.csv", index=False)
    ranked.to_csv(cfg.out_dir / "ranking.csv", index=False)

    selected = ranked.head(cfg.top_n)["ticker"].tolist() if not ranked.empty else []

    nav_detail, port = backtest_equal_weight(
        tickers=selected,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
        provider=cfg.provider,
    )
    if not nav_detail.empty:
        nav_detail.to_csv(cfg.out_dir / "nav_detail.csv")
    if not port.empty:
        port.to_csv(cfg.out_dir / "portfolio_nav.csv")

    perf = summarize_performance(port)

    report_md = [
        "# Quant Analysis Report",
        "",
        f"- Universe size: {len(cfg.universe)}",
        f"- Start date: {cfg.start_date}",
        f"- End date: {cfg.end_date}",
        f"- Provider: {cfg.provider}",
        f"- Top N selected: {cfg.top_n}",
        f"- Selected tickers: {', '.join(selected) if selected else 'None'}",
        "",
        "## Performance Summary",
    ]
    for k, v in perf.items():
        report_md.append(f"- {k}: {v}")

    (cfg.out_dir / "report.md").write_text("\n".join(report_md), encoding="utf-8")

    print(f"Done. Artifacts in: {cfg.out_dir}")
    print(f"Selected: {selected}")
    print(f"Performance: {perf}")
    return 0


def parse_args() -> RunConfig:
    p = argparse.ArgumentParser(description="Run quant stock selection + simple backtest via omnifinan")
    p.add_argument("--universe", type=str, required=True, help="Comma separated tickers, e.g. AAPL,MSFT,GOOGL")
    p.add_argument("--start-date", type=str, required=True)
    p.add_argument("--end-date", type=str, required=True)
    p.add_argument("--top-n", type=int, default=5)
    p.add_argument("--provider", type=str, default="akshare", choices=["akshare", "finnhub", "yfinance"])
    p.add_argument("--out-dir", type=str, default="outputs/latest")
    args = p.parse_args()

    universe = [x.strip() for x in args.universe.split(",") if x.strip()]
    return RunConfig(
        universe=universe,
        start_date=args.start_date,
        end_date=args.end_date,
        top_n=args.top_n,
        provider=args.provider,
        out_dir=Path(args.out_dir),
    )


def main() -> int:
    cfg = parse_args()
    return build_report(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
