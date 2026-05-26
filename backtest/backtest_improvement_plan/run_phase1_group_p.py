"""Phase 1 Group P バックテスト（Step 3: 施策A + 施策B 複合検証）

施策A（ボラティリティレジーム連動 動的シグナル閾値）と
施策B（多段階・時間減衰型トレーリングストップ）の複合効果を検証する。

単体では Sharpe 0.5 未達（施策A: 0.420、施策B: 0.379）だった両施策の
組み合わせが相乗効果を生むかどうかを確認する。

固定設定（全シナリオ共通）:
  allocation_method: equal
  max_positions   : 3
  max_utilization : 0.30
  use_ma200_filter: True
  max_holding_days: 60日
  trailing_stop_atr: 2.0（Stage 1 デフォルト）
  threshold       : 0.58
  stop_loss       : 9%
  dd_stop         : 12%
  topix_vol_window: 20
  trail_profit_gate_atr: 1.5（施策B 固定）
  Stage 2 開始    : 6 日目（固定）
  Stage 3 開始    : 21 日目（固定）
  期間            : 2017-01-01〜2025-12-31

Group P シナリオ:
  P0_i1_ref   : 施策A OFF, 施策B OFF（I1 完全再現・参照）
  P1_n1b      : 施策A ON（vol<12%, hi=0.62）, 施策B OFF
  P2_n1b_o2   : 施策A ON（vol<12%, hi=0.62）+ 施策B O2（s2=1.8, s3=1.5）
  P3_n1b_o1   : 施策A ON（vol<12%, hi=0.62）+ 施策B O1（s2=1.5, s3=1.0）

採択基準:
  Sharpe > 0.5                   : 採用
  0.382 < Sharpe <= 0.5          : 参考値として記録、I1 継続採用
  全シナリオ Sharpe <= 0.382     : A+B 複合効果なし → I1 を Phase 1 最終戦略として確定

Usage:
    python backtest/backtest_improvement_plan/run_phase1_group_p.py
    python backtest/backtest_improvement_plan/run_phase1_group_p.py --workers 4
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
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase1_group_p"

# ---------------------------------------------------------------------------
# 共通パラメータ（全シナリオ固定）
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
    "topix_vol_window": 20,
    "trail_profit_gate_atr": 1.5,
    "start": "2017-01-01",
    "end": "2025-12-31",
}

# ---------------------------------------------------------------------------
# Group P シナリオ定義
# ---------------------------------------------------------------------------

_GROUP_P: list[dict] = [
    {
        "name": "P0_i1_ref",
        "group": "P",
        "adaptive_vol_regime": False,
        "topix_vol_low_threshold": 0.12,
        "adaptive_threshold_hi": 0.62,
        "dynamic_trailing_stop": False,
        "trail_stage2_mult": 1.8,
        "trail_stage3_mult": 1.5,
        "desc": "I1 完全再現（参照・ベースライン）",
    },
    {
        "name": "P1_n1b",
        "group": "P",
        "adaptive_vol_regime": True,
        "topix_vol_low_threshold": 0.12,
        "adaptive_threshold_hi": 0.62,
        "dynamic_trailing_stop": False,
        "trail_stage2_mult": 1.8,
        "trail_stage3_mult": 1.5,
        "desc": "施策A のみ: vol<12% で閾値 0.62（N1b 再現）",
    },
    {
        "name": "P2_n1b_o2",
        "group": "P",
        "adaptive_vol_regime": True,
        "topix_vol_low_threshold": 0.12,
        "adaptive_threshold_hi": 0.62,
        "dynamic_trailing_stop": True,
        "trail_stage2_mult": 1.8,
        "trail_stage3_mult": 1.5,
        "desc": "施策A+B 複合（控えめ）: N1b + Stage2=1.8×ATR, Stage3=1.5×ATR",
    },
    {
        "name": "P3_n1b_o1",
        "group": "P",
        "adaptive_vol_regime": True,
        "topix_vol_low_threshold": 0.12,
        "adaptive_threshold_hi": 0.62,
        "dynamic_trailing_stop": True,
        "trail_stage2_mult": 1.5,
        "trail_stage3_mult": 1.0,
        "desc": "施策A+B 複合（積極）: N1b + Stage2=1.5×ATR, Stage3=1.0×ATR",
    },
]

ALL_SCENARIOS: list[dict] = _GROUP_P

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
        str(scenario["topix_vol_low_threshold"]),
        "--adaptive-threshold-hi",
        str(scenario["adaptive_threshold_hi"]),
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
    if scenario.get("adaptive_vol_regime"):
        cmd.append("--adaptive-threshold-vol-regime")
    if scenario.get("dynamic_trailing_stop"):
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
        "win_rate": trades.get("win_rate"),
        "payoff_ratio": trades.get("payoff_ratio"),
        "profit_factor": trades.get("profit_factor"),
        "avg_holding_days": trades.get("avg_holding_days"),
        "total_trades": trades.get("total_trades"),
    }


def _fmt(value: object, digits: int = 6) -> str:
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
                    "group": scenario.get("group", "P"),
                    "error": f"exit={completed.returncode}",
                }
            )
            continue

        try:
            summary = _read_summary(report_dir)
        except FileNotFoundError as e:
            results.append({"name": name, "group": scenario.get("group", "P"), "error": str(e)})
            continue

        results.append(
            {
                "name": name,
                "group": scenario.get("group", "P"),
                "adaptive_vol_regime": scenario.get("adaptive_vol_regime", False),
                "topix_vol_low_threshold": scenario.get("topix_vol_low_threshold"),
                "adaptive_threshold_hi": scenario.get("adaptive_threshold_hi"),
                "dynamic_trailing_stop": scenario.get("dynamic_trailing_stop", False),
                "trail_stage2_mult": scenario.get("trail_stage2_mult"),
                "trail_stage3_mult": scenario.get("trail_stage3_mult"),
                "trail_profit_gate_atr": _COM["trail_profit_gate_atr"],
                "desc": scenario.get("desc", ""),
                **summary,
            }
        )
        print(
            f"  {name:<20}"
            f" A={str(scenario.get('adaptive_vol_regime', False)):<6}"
            f" B={str(scenario.get('dynamic_trailing_stop', False)):<6}"
            f" vol_thr={scenario.get('topix_vol_low_threshold')}"
            f" s2={scenario.get('trail_stage2_mult')}"
            f" s3={scenario.get('trail_stage3_mult')}"
            f" CAGR={_fmt(summary.get('cagr'), 4)}"
            f" Sharpe={_fmt(summary.get('sharpe'), 4)}"
            f" MaxDD={_fmt(summary.get('max_drawdown'), 4)}"
            f" Trades={summary.get('total_trades')}",
            flush=True,
        )

    return results


CSV_FIELDNAMES = [
    "name",
    "group",
    "adaptive_vol_regime",
    "topix_vol_low_threshold",
    "adaptive_threshold_hi",
    "dynamic_trailing_stop",
    "trail_stage2_mult",
    "trail_stage3_mult",
    "trail_profit_gate_atr",
    "desc",
    "run_id",
    "created_at",
    "cagr",
    "sharpe",
    "max_drawdown",
    "win_rate",
    "payoff_ratio",
    "profit_factor",
    "avg_holding_days",
    "total_trades",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 1 Group P バックテスト（Step 3: 施策A+B 複合）"
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

    print(f"Group P: {len(scenarios)} シナリオを {n_workers} ワーカーで実行")
    print(f"出力先: {output_dir}")
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

    print("\n" + "=" * 100)
    print(
        f"{'シナリオ':<20} {'A':>5} {'B':>5} {'vol_thr':>8} {'s2':>5} {'s3':>5}"
        f" {'CAGR':>9} {'Sharpe':>8} {'MaxDD':>8} {'PF':>7} {'Trades':>7}"
    )
    print("-" * 100)
    for r in all_results:
        if "error" in r:
            print(f"  {r['name']:<20} ERROR: {r['error']}")
            continue
        print(
            f"  {r['name']:<20}"
            f" {str(r.get('adaptive_vol_regime', ''))!s:>5}"
            f" {str(r.get('dynamic_trailing_stop', ''))!s:>5}"
            f" {str(r.get('topix_vol_low_threshold') or ''):>8}"
            f" {r.get('trail_stage2_mult') or '':>5}"
            f" {r.get('trail_stage3_mult') or '':>5}"
            f" {_fmt(r.get('cagr'), 4):>9}"
            f" {_fmt(r.get('sharpe'), 4):>8}"
            f" {_fmt(r.get('max_drawdown'), 4):>8}"
            f" {_fmt(r.get('profit_factor'), 4):>7}"
            f" {str(r.get('total_trades') or ''):>7}"
        )
    print("=" * 100)
    print(f"\nCSV: {csv_path}")

    valid = [r for r in all_results if "error" not in r and r.get("sharpe") is not None]
    best = max(valid, key=lambda r: r["sharpe"], default=None)
    if best:
        sharpe = best["sharpe"]
        print(f"\n最良シナリオ: {best['name']}  Sharpe={_fmt(sharpe, 4)}")
        if sharpe > 0.5:
            print("→ 採択基準 Sharpe > 0.5 達成: 施策A+B 複合採用")
        elif sharpe > 0.382:
            print(
                "→ I1 超え（Sharpe > 0.382）だが 0.5 未達: 参考記録・I1 を Phase 1 最終戦略として確定"
            )
        else:
            print(
                "→ 全シナリオ Sharpe ≤ 0.382: A+B 複合効果なし → I1 を Phase 1 最終戦略として確定"
            )


if __name__ == "__main__":
    main()
