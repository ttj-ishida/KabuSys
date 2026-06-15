"""Phase 2 — W1_08 収益集中リスク定量評価 (Issue #397)

W1_08（IS 2017-2025: CAGR 14.4%, Sharpe 0.674）は 2018 年（+49.4%）・
2024 年（+52.6%）の 2 年で収益の大半を生成している。本スクリプトでは
その依存度とリスクを定量化する。

検証内容:
  1. 2018・2024 除外シミュレーション
     - 7 年間の CAGR・MaxDD を計算
  2. 最大連続マイナス年シミュレーション
     - 実績の最悪年（-6.3%）を n 年連続で仮定した場合の資産毀損
     - dd_stop=12% が何回発動するか
  3. 年次リターン分布分析
     - 平均・中央値・標準偏差・歪度など

Usage:
    python backtest/backtest_improvement_plan/analyze_phase2_concentration_risk.py
    python backtest/backtest_improvement_plan/analyze_phase2_concentration_risk.py --out-dir artifacts/backtest/custom
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# W1_08 バックテスト年次データ（Phase2_Backtest_Strategy.md Section 12.5.4）
# ---------------------------------------------------------------------------

# (年, 年次リターン(%), 年内最大DD(%), 月次データ)
# 月次は文書から判明している最大月のみ記録
W1_08_ANNUAL = [
    {"year": 2017, "return_pct": 5.7, "intra_dd_pct": 9.4},
    {"year": 2018, "return_pct": 49.4, "intra_dd_pct": 9.5},  # 9月 +59.2%
    {"year": 2019, "return_pct": 4.8, "intra_dd_pct": 4.4},
    {"year": 2020, "return_pct": 5.0, "intra_dd_pct": 9.6},
    {"year": 2021, "return_pct": 10.0, "intra_dd_pct": 9.8},
    {"year": 2022, "return_pct": -6.3, "intra_dd_pct": 8.4},
    {"year": 2023, "return_pct": 0.4, "intra_dd_pct": 6.7},
    {"year": 2024, "return_pct": 52.6, "intra_dd_pct": 14.4},  # 12月 +33.1%
    {"year": 2025, "return_pct": 14.1, "intra_dd_pct": 17.9},
]

# IS 参照値
IS_CAGR = 14.4
IS_SHARPE = 0.674
IS_MAXDD = 18.4

# dd_stop 閾値（年内最大 DD がこれを超えたら年内取引停止）
DD_STOP_THRESHOLD = 12.0


# ---------------------------------------------------------------------------
# 計算ヘルパー
# ---------------------------------------------------------------------------


def _compound_returns(returns: list[float], initial: float = 1.0) -> list[float]:
    """年次リターン列を資産残高列に変換する（初期値=1.0）。"""
    values = [initial]
    for r in returns:
        values.append(values[-1] * (1 + r / 100))
    return values


def _cagr(values: list[float], n_years: int) -> float:
    """年率リターンを計算する。"""
    if n_years == 0 or values[0] == 0:
        return 0.0
    return ((values[-1] / values[0]) ** (1 / n_years) - 1) * 100


def _max_drawdown(values: list[float]) -> float:
    """資産残高列から最大ドローダウン(%)を計算する。"""
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _stats(returns: list[float]) -> dict[str, float]:
    """年次リターン列の基本統計を返す。"""
    n = len(returns)
    if n == 0:
        return {}
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / n
    std = variance**0.5
    sorted_r = sorted(returns)
    median = sorted_r[n // 2] if n % 2 == 1 else (sorted_r[n // 2 - 1] + sorted_r[n // 2]) / 2
    skew = sum((r - mean) ** 3 for r in returns) / n / (std**3) if std > 0 else 0.0
    return {
        "count": n,
        "mean": mean,
        "median": median,
        "std": std,
        "min": min(returns),
        "max": max(returns),
        "skewness": skew,
        "positive_years": sum(1 for r in returns if r > 0),
        "negative_years": sum(1 for r in returns if r < 0),
    }


# ---------------------------------------------------------------------------
# 分析関数
# ---------------------------------------------------------------------------


def analyze_full(records: list[dict]) -> dict:
    """9 年全期間分析。"""
    returns = [r["return_pct"] for r in records]
    values = _compound_returns(returns)
    cagr = _cagr(values, len(returns))
    max_dd = _max_drawdown(values)
    total_return = (values[-1] / values[0] - 1) * 100
    return {
        "label": "W1_08 全期間（2017-2025）",
        "years": len(returns),
        "returns": returns,
        "values": values,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "total_return": total_return,
    }


def analyze_excluding_2018_2024(records: list[dict]) -> dict:
    """2018・2024 を除いた 7 年間の分析。"""
    filtered = [r for r in records if r["year"] not in (2018, 2024)]
    returns = [r["return_pct"] for r in filtered]
    years = [r["year"] for r in filtered]
    values = _compound_returns(returns)
    cagr = _cagr(values, len(returns))
    max_dd = _max_drawdown(values)
    total_return = (values[-1] / values[0] - 1) * 100
    return {
        "label": "2018・2024 除外（7年）",
        "excluded_years": [2018, 2024],
        "years": years,
        "n_years": len(returns),
        "returns": returns,
        "values": values,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "total_return": total_return,
    }


def analyze_concentration(records: list[dict]) -> dict:
    """2018・2024 の収益寄与率を計算する。"""
    values_all = _compound_returns([r["return_pct"] for r in records])
    total_gain = values_all[-1] - values_all[0]

    contributions = []
    for rec in records:
        r = rec["return_pct"] / 100
        # 各年の絶対寄与 = 前年末資産 × 当年リターン
        idx = next(i for i, x in enumerate(records) if x["year"] == rec["year"])
        v_before = values_all[idx]
        abs_contribution = v_before * r
        pct_of_total = abs_contribution / total_gain * 100 if total_gain > 0 else 0.0
        contributions.append(
            {
                "year": rec["year"],
                "return_pct": rec["return_pct"],
                "value_before": v_before,
                "abs_contribution": abs_contribution,
                "pct_of_total_gain": pct_of_total,
            }
        )

    top2_contribution = sum(
        c["pct_of_total_gain"] for c in contributions if c["year"] in (2018, 2024)
    )
    return {
        "total_gain_factor": total_gain,
        "contributions": contributions,
        "2018_2024_contribution_pct": top2_contribution,
        "other_7years_contribution_pct": 100 - top2_contribution,
    }


def analyze_consecutive_losses(records: list[dict], n_consecutive: int = 3) -> dict:
    """実績最悪年リターンを n 年連続で仮定した最悪ケースシミュレーション。"""
    worst_year_return = min(r["return_pct"] for r in records)
    worst_year = next(r["year"] for r in records if r["return_pct"] == worst_year_return)

    simulations = []
    # 実績の連続マイナス年（もし複数あれば）
    actual_loss_years = [(r["year"], r["return_pct"]) for r in records if r["return_pct"] < 0]

    for n in range(1, n_consecutive + 1):
        scenario_returns = [worst_year_return] * n
        values = _compound_returns(scenario_returns)
        capital_loss = (values[-1] / values[0] - 1) * 100
        simulations.append(
            {
                "n_years": n,
                "assumed_annual_return_pct": worst_year_return,
                "capital_loss_pct": capital_loss,
                "final_value_from_1000": values[-1] * 1000,
            }
        )

    return {
        "worst_single_year": {"year": worst_year, "return_pct": worst_year_return},
        "actual_negative_years": actual_loss_years,
        "consecutive_loss_simulations": simulations,
    }


def analyze_dd_stop(records: list[dict], threshold: float = DD_STOP_THRESHOLD) -> dict:
    """dd_stop 発動年を特定する。"""
    triggered = []
    not_triggered = []
    for rec in records:
        if rec["intra_dd_pct"] > threshold:
            triggered.append(
                {
                    "year": rec["year"],
                    "intra_dd_pct": rec["intra_dd_pct"],
                    "annual_return_pct": rec["return_pct"],
                }
            )
        else:
            not_triggered.append(
                {
                    "year": rec["year"],
                    "intra_dd_pct": rec["intra_dd_pct"],
                    "annual_return_pct": rec["return_pct"],
                }
            )
    return {
        "threshold_pct": threshold,
        "triggered_count": len(triggered),
        "not_triggered_count": len(not_triggered),
        "triggered_years": triggered,
        "not_triggered_years": not_triggered,
    }


def analyze_distribution(records: list[dict]) -> dict:
    """年次リターン分布統計。"""
    returns = [r["return_pct"] for r in records]
    st = _stats(returns)
    return {
        "per_year": [{"year": r["year"], "return_pct": r["return_pct"]} for r in records],
        "stats": st,
    }


# ---------------------------------------------------------------------------
# レポート出力
# ---------------------------------------------------------------------------


def _fmt(v: float, decimals: int = 1) -> str:
    return f"{v:+.{decimals}f}%" if isinstance(v, float) else str(v)


def build_report(
    full: dict,
    excl: dict,
    conc: dict,
    consec: dict,
    dd_stop: dict,
    dist: dict,
) -> str:
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("Phase 2 - W1_08 収益集中リスク定量評価 (Issue #397)")
    lines.append(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    # --- 1. 基準値 ---
    lines.append("\n【全期間成績（IS 参照）】")
    lines.append(f"  期間       : 2017-2025 ({full['years']} 年)")
    lines.append(f"  CAGR       : {IS_CAGR:.1f}% (計算値: {full['cagr']:.1f}%)")
    lines.append(f"  MaxDD      : {IS_MAXDD:.1f}% (計算値: {full['max_drawdown']:.1f}%)")
    lines.append(f"  総収益率   : {full['total_return']:+.1f}%")
    lines.append(f"  Sharpe     : {IS_SHARPE:.3f}")

    # --- 2. 年次収益集中 ---
    lines.append("\n【収益集中度分析】")
    lines.append(
        f"  2018・2024 の寄与率: {conc['2018_2024_contribution_pct']:.1f}% "
        f"/ 残り 7 年: {conc['other_7years_contribution_pct']:.1f}%"
    )
    lines.append("")
    lines.append(f"  {'年':>4} | {'年次リターン':>12} | {'絶対寄与':>10} | {'総利益寄与%':>10}")
    lines.append(f"  {'-' * 4}-+-{'-' * 12}-+-{'-' * 10}-+-{'-' * 10}")
    for c in conc["contributions"]:
        lines.append(
            f"  {c['year']:>4} | {c['return_pct']:>+11.1f}% | "
            f"{c['abs_contribution']:>+9.3f}x | {c['pct_of_total_gain']:>9.1f}%"
        )

    # --- 3. 2018・2024 除外シミュレーション ---
    lines.append("\n【2018・2024 除外シミュレーション（7 年）】")
    lines.append(f"  対象年     : {excl['years']}")
    lines.append(f"  CAGR       : {excl['cagr']:+.1f}%")
    lines.append(f"  MaxDD      : {excl['max_drawdown']:.1f}%")
    lines.append(f"  総収益率   : {excl['total_return']:+.1f}%")
    lines.append(
        f"  → 大相場 2 年を除くと年率 {excl['cagr']:+.1f}% に低下"
        f"（全期間比 {excl['cagr'] - IS_CAGR:.1f}pt）"
    )

    # --- 4. 連続マイナス年シミュレーション ---
    worst = consec["worst_single_year"]
    lines.append("\n【最悪年連続シミュレーション】")
    lines.append(f"  実績最悪年リターン: {worst['year']} 年 {worst['return_pct']:+.1f}%")
    neg_years = consec["actual_negative_years"]
    lines.append(
        f"  実績マイナス年    : {len(neg_years)} 年 ({', '.join(str(y) for y, _ in neg_years)})"
    )
    lines.append("")
    lines.append(
        f"  {'連続年数':>6} | {'年次仮定':>10} | {'資本毀損':>10} | {'最終資産(1000万→)':>18}"
    )
    lines.append(f"  {'-' * 6}-+-{'-' * 10}-+-{'-' * 10}-+-{'-' * 18}")
    for s in consec["consecutive_loss_simulations"]:
        lines.append(
            f"  {s['n_years']:>6} 年 | "
            f"{s['assumed_annual_return_pct']:>+9.1f}% | "
            f"{s['capital_loss_pct']:>+9.1f}% | "
            f"{s['final_value_from_1000']:>16.0f} 万円"
        )

    # --- 5. dd_stop 発動分析 ---
    dd = dd_stop
    lines.append(f"\n【dd_stop={dd['threshold_pct']:.0f}% 発動分析】")
    lines.append(f"  発動回数   : {dd['triggered_count']} / {len(W1_08_ANNUAL)} 年")
    if dd["triggered_years"]:
        lines.append("  発動年     :")
        for t in dd["triggered_years"]:
            lines.append(
                f"    {t['year']} 年: 年内最大DD={t['intra_dd_pct']:.1f}% > "
                f"{dd['threshold_pct']:.0f}%（年次リターン={t['annual_return_pct']:+.1f}%）"
            )
    else:
        lines.append("  発動なし")

    # --- 6. 分布統計 ---
    st = dist["stats"]
    lines.append("\n【年次リターン分布統計（2017-2025）】")
    lines.append(f"  平均       : {st['mean']:+.2f}%")
    lines.append(f"  中央値     : {st['median']:+.2f}%")
    lines.append(f"  標準偏差   : {st['std']:.2f}%")
    lines.append(f"  最小       : {st['min']:+.2f}%")
    lines.append(f"  最大       : {st['max']:+.2f}%")
    lines.append(f"  歪度       : {st['skewness']:+.3f}（正 = 高リターン年の外れ値あり）")
    lines.append(f"  プラス年   : {st['positive_years']} / {st['count']} 年")
    lines.append(f"  マイナス年 : {st['negative_years']} / {st['count']} 年")

    # --- 7. 採用判断への影響 ---
    lines.append("\n【本番投入リスク開示（採用判断への影響）】")
    lines.append(
        f"  大相場なし 7 年 CAGR: {excl['cagr']:+.1f}%  "
        f"({'プラス' if excl['cagr'] > 0 else 'マイナス'})"
    )
    consec_3 = next(s for s in consec["consecutive_loss_simulations"] if s["n_years"] == 3)
    lines.append(f"  3 年連続最悪ケース  : 資本毀損 {consec_3['capital_loss_pct']:.1f}%")
    lines.append(
        f"  dd_stop 発動頻度    : {dd['triggered_count']} / {len(W1_08_ANNUAL)} 年"
        f" ({dd['triggered_count'] / len(W1_08_ANNUAL) * 100:.0f}%)"
    )
    lines.append("")
    lines.append("  ■ 2018・2024 の 2 大相場依存は構造的リスク。")
    lines.append(
        f"    大相場なし 7 年 CAGR が {excl['cagr']:+.1f}% であることを踏まえ、本番運用時は"
    )
    lines.append("    「3〜5 年単位での実績評価」「大相場待機期間の資産毀損許容設定」が必要。")
    lines.append("=" * 70)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV 出力
# ---------------------------------------------------------------------------


def save_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    if not rows:
        return
    fieldnames = fieldnames or list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 2 W1_08 収益集中リスク定量評価 (Issue #397)",
    )
    parser.add_argument(
        "--out-dir",
        metavar="DIR",
        default=None,
        help="出力ディレクトリ（省略時: artifacts/backtest/backtest_phase2_concentration_risk/{timestamp}）",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = (
            repo_root / "artifacts" / "backtest" / "backtest_phase2_concentration_risk" / timestamp
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    records = W1_08_ANNUAL

    # --- 分析実行 ---
    full = analyze_full(records)
    excl = analyze_excluding_2018_2024(records)
    conc = analyze_concentration(records)
    consec = analyze_consecutive_losses(records, n_consecutive=3)
    dd_stop_result = analyze_dd_stop(records, threshold=DD_STOP_THRESHOLD)
    dist = analyze_distribution(records)

    # --- レポート出力 ---
    report = build_report(full, excl, conc, consec, dd_stop_result, dist)
    print(report)

    report_path = out_dir / "report.txt"
    report_path.write_text(report, encoding="utf-8")

    # --- CSV 出力 ---
    # 年次リターン一覧
    save_csv(
        out_dir / "annual_returns.csv",
        [
            {
                "year": r["year"],
                "return_pct": r["return_pct"],
                "intra_dd_pct": r["intra_dd_pct"],
            }
            for r in records
        ],
    )

    # 資産推移（全期間）
    full_values = full["values"]
    save_csv(
        out_dir / "portfolio_value_full.csv",
        [{"label": "full", "year_end": 2016 + i, "value": v} for i, v in enumerate(full_values)],
    )

    # 資産推移（2018・2024 除外）
    excl_values = excl["values"]
    save_csv(
        out_dir / "portfolio_value_excl_2018_2024.csv",
        [
            {"label": "excl_2018_2024", "year_end": yr, "value": v}
            for yr, v in zip([2016] + excl["years"], excl_values)
        ],
    )

    # 収益集中度
    save_csv(
        out_dir / "concentration.csv",
        conc["contributions"],
    )

    # 連続マイナス年シミュレーション
    save_csv(
        out_dir / "consecutive_loss_simulation.csv",
        consec["consecutive_loss_simulations"],
    )

    # dd_stop 発動一覧
    save_csv(
        out_dir / "dd_stop_analysis.csv",
        dd_stop_result["triggered_years"] + dd_stop_result["not_triggered_years"],
        fieldnames=["year", "intra_dd_pct", "annual_return_pct"],
    )

    # summary.json
    summary = {
        "generated_at": datetime.now().isoformat(),
        "issue": "#397",
        "w1_08_is_cagr": IS_CAGR,
        "w1_08_is_sharpe": IS_SHARPE,
        "w1_08_is_maxdd": IS_MAXDD,
        "excl_2018_2024_cagr": round(excl["cagr"], 2),
        "excl_2018_2024_maxdd": round(excl["max_drawdown"], 2),
        "excl_2018_2024_total_return": round(excl["total_return"], 2),
        "concentration_2018_2024_pct": round(conc["2018_2024_contribution_pct"], 1),
        "worst_year": consec["worst_single_year"],
        "consecutive_3y_capital_loss_pct": round(
            next(s for s in consec["consecutive_loss_simulations"] if s["n_years"] == 3)[
                "capital_loss_pct"
            ],
            2,
        ),
        "dd_stop_triggered_count": dd_stop_result["triggered_count"],
        "dd_stop_threshold_pct": DD_STOP_THRESHOLD,
        "dd_stop_triggered_years": [t["year"] for t in dd_stop_result["triggered_years"]],
        "annual_return_stats": {
            k: round(v, 3) if isinstance(v, float) else v for k, v in dist["stats"].items()
        },
        "out_dir": str(out_dir),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n[OK] 出力先: {out_dir}")
    print("  report.txt                        : テキストレポート")
    print("  summary.json                      : 集計 JSON")
    print("  annual_returns.csv                : W1_08 年次リターン")
    print("  portfolio_value_full.csv          : 資産推移（全期間）")
    print("  portfolio_value_excl_2018_2024.csv: 資産推移（2018・2024 除外）")
    print("  concentration.csv                 : 収益集中度")
    print("  consecutive_loss_simulation.csv   : 連続マイナス年シミュレーション")
    print("  dd_stop_analysis.csv              : dd_stop 発動分析")


if __name__ == "__main__":
    main()
