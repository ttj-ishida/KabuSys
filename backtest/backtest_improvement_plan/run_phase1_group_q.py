"""Phase 1 Group Q バックテスト（Stage2/Stage3 グリッドサーチ）

Group P で最優秀となった P2_n1b_o2（施策A ON + Stage2=1.8×ATR, Stage3=1.5×ATR）を
出発点に、多段階トレーリングストップの ATR 乗数組み合わせを系統的に探索する。

固定設定（全シナリオ共通・P2 設定継承）:
  allocation_method    : equal
  max_positions        : 3
  max_utilization      : 0.30
  use_ma200_filter     : True
  max_holding_days     : 60日
  trailing_stop_atr    : 2.0（Stage 1 デフォルト）
  threshold            : 0.58
  stop_loss            : 9%
  dd_stop              : 12%
  adaptive_vol_regime  : True（施策A ON 固定）
  topix_vol_window     : 20
  topix_vol_low_thr    : 0.12
  adaptive_threshold_hi: 0.62
  trail_profit_gate_atr: 1.5（Stage2 発動ゲート固定）
  Stage 2 開始         : 6 日目（固定）
  Stage 3 開始         : 21 日目（固定）
  期間                 : 2017-01-01〜2025-12-31

グリッド（Stage3 < Stage2 の制約付き）:
  Stage2 mult : 1.4, 1.6, 1.8, 2.0, 2.2
  Stage3 mult : 1.0, 1.2, 1.5

シナリオ一覧:
  Q0_p2_ref   Stage2=1.8, Stage3=1.5  P2 完全再現（参照）
  Q1_s14_s10  Stage2=1.4, Stage3=1.0  最積極タイト化
  Q2_s14_s12  Stage2=1.4, Stage3=1.2
  Q3_s16_s10  Stage2=1.6, Stage3=1.0
  Q4_s16_s12  Stage2=1.6, Stage3=1.2
  Q5_s18_s10  Stage2=1.8, Stage3=1.0
  Q6_s18_s12  Stage2=1.8, Stage3=1.2
  Q7_s20_s10  Stage2=2.0, Stage3=1.0
  Q8_s20_s12  Stage2=2.0, Stage3=1.2
  Q9_s20_s15  Stage2=2.0, Stage3=1.5
  Q10_s22_s10 Stage2=2.2, Stage3=1.0
  Q11_s22_s12 Stage2=2.2, Stage3=1.2
  Q12_s22_s15 Stage2=2.2, Stage3=1.5  最控えめタイト化

採択基準:
  いずれかのシナリオで Sharpe > 0.5 かつ MaxDD < 25%, CAGR > 5%, PF > 1.1
    → 当該設定を Phase 1 最終採用（P2 から更新）
  Q0（P2）を上回る Sharpe が存在（0.428 < Sharpe ≤ 0.5）
    → 最良シナリオを Phase 1 改良版として採用
  全シナリオ Sharpe ≤ 0.428
    → P2 設定を Phase 1 最終採用として確定

Usage:
    python backtest/backtest_improvement_plan/run_phase1_group_q.py
    python backtest/backtest_improvement_plan/run_phase1_group_q.py --workers 4
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "config" / "strategy_config.yaml").exists():
            return candidate
    raise FileNotFoundError("config/strategy_config.yaml が見つかりません")


REPO_ROOT = _find_repo_root()
ENV_PATH = REPO_ROOT / ".env"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase1_group_q"

# ---------------------------------------------------------------------------
# 共通パラメータ（全シナリオ固定・P2 設定継承）
# ---------------------------------------------------------------------------

_COM = {
    "cash": 1_000_000,
    "allocation_method": "equal",
    "max_positions": 3,
    "max_position_pct": 0.22,
    "risk_pct": 0.005,
    "max_utilization": 0.30,
    "use_ma200_filter": True,
    "stop_loss_pct": 0.09,
    "max_holding_days": 60,
    "trailing_stop_atr": 2.0,
    "threshold": 0.58,
    "dd_stop": 0.12,
    "dd_timeout": 30,
    "weak_bear": 1.00,
    "strong_bear": 1.00,
    # 施策A 固定（N1b 準拠）
    "adaptive_vol_regime": True,
    "topix_vol_window": 20,
    "topix_vol_low_threshold": 0.12,
    "adaptive_threshold_hi": 0.62,
    # 施策B 固定パラメータ
    "dynamic_trailing_stop": True,
    "trail_profit_gate_atr": 1.5,
    "start": "2017-01-01",
    "end": "2025-12-31",
}

# ---------------------------------------------------------------------------
# Group Q シナリオ定義（Stage2 × Stage3 グリッド）
# ---------------------------------------------------------------------------


def _scenario(name: str, s2: float, s3: float, desc: str) -> dict:
    return {
        "name": name,
        "group": "Q",
        "trail_stage2_mult": s2,
        "trail_stage3_mult": s3,
        "desc": desc,
    }


_GROUP_Q: list[dict] = [
    _scenario("Q0_p2_ref", 1.8, 1.5, "P2 完全再現（参照ベースライン）Stage2=1.8×, Stage3=1.5×"),
    _scenario("Q1_s14_s10", 1.4, 1.0, "Stage2=1.4×, Stage3=1.0× 最も積極的なタイト化"),
    _scenario("Q2_s14_s12", 1.4, 1.2, "Stage2=1.4×, Stage3=1.2×"),
    _scenario("Q3_s16_s10", 1.6, 1.0, "Stage2=1.6×, Stage3=1.0×"),
    _scenario("Q4_s16_s12", 1.6, 1.2, "Stage2=1.6×, Stage3=1.2× 両段階中タイト"),
    _scenario("Q5_s18_s10", 1.8, 1.0, "Stage2=1.8×, Stage3=1.0× Stage3 のみ締める"),
    _scenario("Q6_s18_s12", 1.8, 1.2, "Stage2=1.8×, Stage3=1.2× Stage3 を P2 より締める"),
    _scenario("Q7_s20_s10", 2.0, 1.0, "Stage2=2.0×, Stage3=1.0×"),
    _scenario("Q8_s20_s12", 2.0, 1.2, "Stage2=2.0×, Stage3=1.2×"),
    _scenario("Q9_s20_s15", 2.0, 1.5, "Stage2=2.0×, Stage3=1.5× Stage2 のみ緩める"),
    _scenario("Q10_s22_s10", 2.2, 1.0, "Stage2=2.2×, Stage3=1.0×"),
    _scenario("Q11_s22_s12", 2.2, 1.2, "Stage2=2.2×, Stage3=1.2×"),
    _scenario("Q12_s22_s15", 2.2, 1.5, "Stage2=2.2×, Stage3=1.5× 最も控えめなタイト化"),
]

ALL_SCENARIOS: list[dict] = _GROUP_Q

# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------


def _load_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        result[key.strip()] = val.strip()
    return result


def _get_db_path() -> Path:
    env = _load_env(ENV_PATH)
    db_path = Path(env.get("DUCKDB_PATH", "data/kabusys.duckdb"))
    if not db_path.is_absolute():
        db_path = REPO_ROOT / db_path
    return db_path


def _build_command(db_path: Path, scenario: dict, output_dir: Path) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "kabusys.backtest.run",
        "--db",
        str(db_path),
        "--start",
        _COM["start"],
        "--end",
        _COM["end"],
        "--cash",
        str(_COM["cash"]),
        "--allocation-method",
        _COM["allocation_method"],
        "--max-positions",
        str(_COM["max_positions"]),
        "--max-position-pct",
        str(_COM["max_position_pct"]),
        "--max-utilization",
        str(_COM["max_utilization"]),
        "--risk-pct",
        str(_COM["risk_pct"]),
        "--stop-loss-pct",
        str(_COM["stop_loss_pct"]),
        "--min-holding-days",
        "5",
        "--max-holding-days",
        str(_COM["max_holding_days"]),
        "--trailing-stop-atr",
        str(_COM["trailing_stop_atr"]),
        "--threshold",
        str(_COM["threshold"]),
        "--topix-size-multiplier-weak-bear",
        str(_COM["weak_bear"]),
        "--topix-size-multiplier-strong-bear",
        str(_COM["strong_bear"]),
        "--portfolio-drawdown-stop",
        str(_COM["dd_stop"]),
        "--portfolio-drawdown-stop-timeout",
        str(_COM["dd_timeout"]),
        "--topix-vol-window",
        str(_COM["topix_vol_window"]),
        "--topix-vol-low-threshold",
        str(_COM["topix_vol_low_threshold"]),
        "--adaptive-threshold-hi",
        str(_COM["adaptive_threshold_hi"]),
        "--trail-profit-gate-atr",
        str(_COM["trail_profit_gate_atr"]),
        "--trail-stage2-mult",
        str(scenario["trail_stage2_mult"]),
        "--trail-stage3-mult",
        str(scenario["trail_stage3_mult"]),
        "--output-format",
        "all",
        "--output-dir",
        str(output_dir),
    ]
    if _COM.get("use_ma200_filter"):
        cmd.append("--ma200-filter")
    if _COM.get("adaptive_vol_regime"):
        cmd.append("--adaptive-threshold-vol-regime")
    if _COM.get("dynamic_trailing_stop"):
        cmd.append("--dynamic-trailing-stop")
    return cmd


def _read_summary(report_dir: Path) -> dict:
    summaries = list(report_dir.glob("*/summary.json"))
    if not summaries:
        raise FileNotFoundError(f"summary.json が見つかりません: {report_dir}")
    latest = max(summaries, key=lambda p: p.stat().st_mtime)
    data = json.loads(latest.read_text(encoding="utf-8"))
    headline = data.get("headline", {})
    trades = data.get("trades", {})
    meta = data.get("meta", {})
    return {
        "run_id": meta.get("run_id", ""),
        "created_at": meta.get("generated_at", ""),
        "cagr": headline.get("cagr"),
        "sharpe": headline.get("sharpe_ratio"),
        "max_drawdown": headline.get("max_drawdown"),
        "calmar_ratio": headline.get("calmar_ratio"),
        "annual_volatility": headline.get("annual_volatility"),
        "win_rate": trades.get("win_rate"),
        "payoff_ratio": trades.get("payoff_ratio"),
        "profit_factor": trades.get("profit_factor"),
        "avg_holding_days": trades.get("avg_holding_days"),
        "total_trades": trades.get("total_trades"),
    }


def _fmt(value: object, digits: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


# ---------------------------------------------------------------------------
# ワーカー関数（Windows spawn 対応のためトップレベルに配置）
# ---------------------------------------------------------------------------


def _run_batch(args: tuple) -> list[dict]:
    snapshot_db, scenario_batch, output_dir_str, repo_root_str = args
    output_dir = Path(output_dir_str)
    repo_root = Path(repo_root_str)
    results: list[dict] = []

    for scenario in scenario_batch:
        name = scenario["name"]
        scenario_dir = output_dir / name
        scenario_dir.mkdir(parents=True, exist_ok=True)
        report_dir = scenario_dir / "report"

        cmd = _build_command(Path(snapshot_db), scenario, report_dir)

        env = os.environ.copy()
        src_path = str(repo_root / "src")
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [src_path, existing]))
        env["PYTHONIOENCODING"] = "utf-8"

        completed = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        (scenario_dir / "stdout.log").write_text(completed.stdout or "", encoding="utf-8")
        (scenario_dir / "stderr.log").write_text(completed.stderr or "", encoding="utf-8")

        if completed.returncode != 0:
            results.append(
                {
                    "name": name,
                    "group": "Q",
                    "error": f"exit={completed.returncode}",
                }
            )
            continue

        try:
            summary = _read_summary(report_dir)
        except FileNotFoundError as e:
            results.append({"name": name, "group": "Q", "error": str(e)})
            continue

        results.append(
            {
                "name": name,
                "group": "Q",
                "trail_stage2_mult": scenario["trail_stage2_mult"],
                "trail_stage3_mult": scenario["trail_stage3_mult"],
                "trail_profit_gate_atr": _COM["trail_profit_gate_atr"],
                "desc": scenario.get("desc", ""),
                **summary,
            }
        )
        print(
            f"  {name:<16}"
            f" s2={scenario['trail_stage2_mult']:.1f}"
            f" s3={scenario['trail_stage3_mult']:.1f}"
            f" CAGR={_fmt(summary.get('cagr'))}"
            f" Sharpe={_fmt(summary.get('sharpe'))}"
            f" MaxDD={_fmt(summary.get('max_drawdown'))}"
            f" Calmar={_fmt(summary.get('calmar_ratio'))}"
            f" Trades={summary.get('total_trades')}",
            flush=True,
        )

    return results


CSV_FIELDNAMES = [
    "name",
    "group",
    "trail_stage2_mult",
    "trail_stage3_mult",
    "trail_profit_gate_atr",
    "desc",
    "run_id",
    "created_at",
    "cagr",
    "sharpe",
    "max_drawdown",
    "calmar_ratio",
    "annual_volatility",
    "win_rate",
    "payoff_ratio",
    "profit_factor",
    "avg_holding_days",
    "total_trades",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 1 Group Q バックテスト（Stage2/Stage3 グリッドサーチ）"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="並列ワーカー数（デフォルト: 2）",
    )
    args = parser.parse_args()

    db_path = _get_db_path()
    if not db_path.exists():
        print(f"[ERROR] DB が見つかりません: {db_path}", file=sys.stderr)
        sys.exit(1)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ARTIFACTS_ROOT / stamp
    output_dir.mkdir(parents=True, exist_ok=True)

    scenarios = ALL_SCENARIOS
    n_workers = min(args.workers, len(scenarios))

    # ワーカーごとに DuckDB スナップショットを作成（排他ロック競合を回避）
    snapshots_dir = output_dir / "_snapshots"
    snapshots_dir.mkdir()
    snapshot_paths: list[str] = []
    for i in range(n_workers):
        snap = snapshots_dir / f"worker_{i:02d}.duckdb"
        shutil.copy2(str(db_path), str(snap))
        snapshot_paths.append(str(snap))

    batches: list[list[dict]] = [[] for _ in range(n_workers)]
    for idx, scenario in enumerate(scenarios):
        batches[idx % n_workers].append(scenario)

    batch_args = [
        (snapshot_paths[i], batches[i], str(output_dir), str(REPO_ROOT)) for i in range(n_workers)
    ]

    print(f"Group Q: {len(scenarios)} シナリオを {n_workers} ワーカーで実行")
    print(f"出力先: {output_dir}")
    print("固定: 施策A ON（vol<12%, hi=0.62）, 施策B ON, gate=1.5×ATR")
    print("-" * 100)

    all_results: list[dict] = []

    try:
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = {executor.submit(_run_batch, ba): i for i, ba in enumerate(batch_args)}
            for future in as_completed(futures):
                try:
                    all_results.extend(future.result())
                except Exception as exc:
                    print(f"[ERROR] バッチ実行エラー: {exc}", file=sys.stderr)
    finally:
        try:
            shutil.rmtree(snapshots_dir)
        except Exception as e:
            print(f"[WARN] スナップショット削除失敗: {e}", file=sys.stderr)

    # シナリオ定義順に並び替え
    all_results.sort(
        key=lambda r: next(
            (i for i, s in enumerate(scenarios) if s["name"] == r["name"]),
            999,
        )
    )

    csv_path = output_dir / "results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_results)

    # 結果サマリー表示
    print("\n" + "=" * 100)
    print(
        f"{'シナリオ':<16} {'s2':>5} {'s3':>5}"
        f" {'CAGR':>9} {'Sharpe':>8} {'MaxDD':>8} {'Calmar':>8} {'PF':>7} {'Trades':>7}"
    )
    print("-" * 100)
    for r in all_results:
        if "error" in r:
            print(f"  {r['name']:<16} ERROR: {r['error']}")
            continue
        print(
            f"  {r['name']:<16}"
            f" {r.get('trail_stage2_mult') or '':>5}"
            f" {r.get('trail_stage3_mult') or '':>5}"
            f" {_fmt(r.get('cagr')):>9}"
            f" {_fmt(r.get('sharpe')):>8}"
            f" {_fmt(r.get('max_drawdown')):>8}"
            f" {_fmt(r.get('calmar_ratio')):>8}"
            f" {_fmt(r.get('profit_factor')):>7}"
            f" {str(r.get('total_trades') or ''):>7}"
        )
    print("=" * 100)
    print(f"\nCSV: {csv_path}")

    valid = [r for r in all_results if "error" not in r and r.get("sharpe") is not None]
    if not valid:
        print("[WARN] 有効なシナリオがありません", file=sys.stderr)
        return

    best = max(valid, key=lambda r: r["sharpe"])
    p2_sharpe = 0.428  # P2_n1b_o2 の参照値

    print(f"\n最良シナリオ: {best['name']}")
    print(f"  Stage2={best.get('trail_stage2_mult')}×  Stage3={best.get('trail_stage3_mult')}×")
    print(
        f"  Sharpe={_fmt(best['sharpe'])}  CAGR={_fmt(best.get('cagr'))}  MaxDD={_fmt(best.get('max_drawdown'))}"
    )

    sharpe = best["sharpe"]
    if sharpe > 0.5:
        print("→ 採択基準 Sharpe > 0.5 達成: 当該設定を Phase 1 最終採用（P2 から更新）")
    elif sharpe > p2_sharpe:
        print(f"→ Q0（P2参照: {p2_sharpe}）を上回る改善: 最良シナリオを Phase 1 改良版として採用")
    else:
        print(f"→ 全シナリオ Sharpe ≤ {p2_sharpe}（Q0 以下）: Stage2/Stage3 グリッドでは改善不可")
        print("   P2 設定（Stage2=1.8×, Stage3=1.5×）を Phase 1 最終採用として確定")

    # Sharpe TOP3 を表示
    top3 = sorted(valid, key=lambda r: r["sharpe"], reverse=True)[:3]
    print("\n--- Sharpe 上位3 ---")
    for rank, r in enumerate(top3, 1):
        print(
            f"  #{rank} {r['name']:<16}"
            f" s2={r.get('trail_stage2_mult')} s3={r.get('trail_stage3_mult')}"
            f" Sharpe={_fmt(r['sharpe'])} MaxDD={_fmt(r.get('max_drawdown'))} CAGR={_fmt(r.get('cagr'))}"
        )


if __name__ == "__main__":
    main()
