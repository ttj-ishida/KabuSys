"""Phase 2 Group U — market_calendar 修正後 S2+T4 複合検証 (Issue #382)

2020-10-01 market_calendar 修正後に、クオリティフィルター（T4）・S2 適応閾値・
両者の複合（U3）を独立・組み合わせで検証する。

IS 参照値（R3、Phase2_Backtest_Strategy.md Section 48）:
  CAGR 9.01%、Sharpe 0.445、MaxDD 26.87%、PF 1.402

シナリオ:
  U0_ref  : R3 ベースライン（フィルターなし・2 値施策A）
  U1_t4   : クオリティフィルター単体（quality_score >= -0.30）
  U2_s2   : S2 適応閾値単体（3 値レジーム）
  U3_s2t4 : S2 + クオリティ複合（最終候補）

Phase 2 採択基準:
  CAGR  > 8%
  Sharpe > 0.5  (Phase 2 主目標)
  MaxDD  < 25%
  PF     > 1.1

Usage:
    python backtest/backtest_improvement_plan/run_phase2_group_u.py
    python backtest/backtest_improvement_plan/run_phase2_group_u.py --workers 4
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

DEFAULT_WORKERS = 4


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "config" / "strategy_config.yaml").exists():
            return candidate
    raise FileNotFoundError("config/strategy_config.yaml が見つかりません")


REPO_ROOT = _find_repo_root()
ENV_PATH = REPO_ROOT / ".env"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase2_group_u"

# ---------------------------------------------------------------------------
# R3 ベース固定パラメータ（adaptive threshold / quality 以外）
# ---------------------------------------------------------------------------

_COM_BASE = {
    "cash": 1_000_000,
    "allocation_method": "equal",
    "max_position_pct": 0.22,
    "risk_pct": 0.005,
    "max_positions": 7,
    "max_utilization": 0.40,
    "use_ma200_filter": True,
    "stop_loss_pct": 0.09,
    "min_holding_days": 5,
    "max_holding_days": 60,
    "trailing_stop_atr": 2.0,
    "threshold": 0.58,
    "weak_bear": 1.00,
    "strong_bear": 1.00,
    "dd_stop": 0.12,
    "dd_timeout": 30,
    "topix_vol_window": 20,
    "dynamic_trailing_stop": True,
    "trail_profit_gate_atr": 1.5,
    "trail_stage2_mult": 1.8,
    "trail_stage3_mult": 1.5,
    "start": "2017-01-01",
    "end": "2025-12-31",
}

_IS_CAGR = 0.0901
_IS_SHARPE = 0.445
_IS_MAX_DD = 0.2687
_IS_PF = 1.402

_CAGR_MIN = 0.08
_SHARPE_MIN = 0.5
_DD_MAX = 0.25
_PF_MIN = 1.1

# ---------------------------------------------------------------------------
# シナリオ定義
# ---------------------------------------------------------------------------

_SCENARIOS: list[dict] = [
    {
        "name": "U0_ref",
        "group": "U",
        "topix_vol_low_threshold": 0.12,
        "topix_vol_high_threshold": None,
        "adaptive_threshold_hi": 0.62,
        "adaptive_threshold_lo": None,
        "quality_score_min": None,
        "desc": "R3 ベースライン（修正後）",
        "is_reference": True,
    },
    {
        "name": "U1_t4",
        "group": "U",
        "topix_vol_low_threshold": 0.12,
        "topix_vol_high_threshold": None,
        "adaptive_threshold_hi": 0.62,
        "adaptive_threshold_lo": None,
        "quality_score_min": -0.30,
        "desc": "クオリティフィルター単体（T4 修正版）",
        "is_reference": False,
    },
    {
        "name": "U2_s2",
        "group": "U",
        "topix_vol_low_threshold": 0.10,
        "topix_vol_high_threshold": 0.20,
        "adaptive_threshold_hi": 0.63,
        "adaptive_threshold_lo": 0.55,
        "quality_score_min": None,
        "desc": "S2 適応閾値単体（3 値レジーム）",
        "is_reference": False,
    },
    {
        "name": "U3_s2t4",
        "group": "U",
        "topix_vol_low_threshold": 0.10,
        "topix_vol_high_threshold": 0.20,
        "adaptive_threshold_hi": 0.63,
        "adaptive_threshold_lo": 0.55,
        "quality_score_min": -0.30,
        "desc": "S2 + クオリティ複合（最終候補）",
        "is_reference": False,
    },
]

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
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        result[key.strip()] = val
    return result


def _get_db_path() -> Path:
    env = _load_env(ENV_PATH)
    db_path = Path(env.get("DUCKDB_PATH", "data/kabusys.duckdb"))
    if not db_path.is_absolute():
        db_path = REPO_ROOT / db_path
    return db_path


def _build_command(db_path: Path, scenario: dict, output_dir: Path) -> list[str]:
    com = _COM_BASE
    cmd = [
        sys.executable,
        "-m",
        "kabusys.backtest.run",
        "--db",
        str(db_path),
        "--start",
        com["start"],
        "--end",
        com["end"],
        "--cash",
        str(com["cash"]),
        "--allocation-method",
        com["allocation_method"],
        "--max-positions",
        str(com["max_positions"]),
        "--max-position-pct",
        str(com["max_position_pct"]),
        "--max-utilization",
        str(com["max_utilization"]),
        "--risk-pct",
        str(com["risk_pct"]),
        "--stop-loss-pct",
        str(com["stop_loss_pct"]),
        "--min-holding-days",
        str(com["min_holding_days"]),
        "--max-holding-days",
        str(com["max_holding_days"]),
        "--trailing-stop-atr",
        str(com["trailing_stop_atr"]),
        "--threshold",
        str(com["threshold"]),
        "--topix-size-multiplier-weak-bear",
        str(com["weak_bear"]),
        "--topix-size-multiplier-strong-bear",
        str(com["strong_bear"]),
        "--portfolio-drawdown-stop",
        str(com["dd_stop"]),
        "--portfolio-drawdown-stop-timeout",
        str(com["dd_timeout"]),
        "--adaptive-threshold-vol-regime",
        "--topix-vol-window",
        str(com["topix_vol_window"]),
        "--topix-vol-low-threshold",
        str(scenario["topix_vol_low_threshold"]),
        "--adaptive-threshold-hi",
        str(scenario["adaptive_threshold_hi"]),
        "--dynamic-trailing-stop",
        "--trail-profit-gate-atr",
        str(com["trail_profit_gate_atr"]),
        "--trail-stage2-mult",
        str(com["trail_stage2_mult"]),
        "--trail-stage3-mult",
        str(com["trail_stage3_mult"]),
        "--ma200-filter",
        "--output-format",
        "all",
        "--output-dir",
        str(output_dir),
    ]
    if scenario.get("topix_vol_high_threshold") is not None:
        cmd += ["--topix-vol-high-threshold", str(scenario["topix_vol_high_threshold"])]
    if scenario.get("adaptive_threshold_lo") is not None:
        cmd += ["--adaptive-threshold-lo", str(scenario["adaptive_threshold_lo"])]
    if scenario.get("quality_score_min") is not None:
        cmd += ["--quality-score-min", str(scenario["quality_score_min"])]
    return cmd


def _read_summary(report_dir: Path) -> dict:
    summaries = list(report_dir.glob("*/summary.json"))
    if not summaries:
        direct = report_dir / "summary.json"
        if direct.exists():
            summaries = [direct]
    if not summaries:
        raise FileNotFoundError(f"summary.json が見つかりません: {report_dir}")
    latest = max(summaries, key=lambda p: p.stat().st_mtime)
    data = json.loads(latest.read_text(encoding="utf-8"))
    headline = data.get("headline", {})
    trades = data.get("trades", {})
    meta = data.get("meta", {})
    return {
        "run_id": meta.get("run_id", ""),
        "cagr": headline.get("cagr"),
        "sharpe": headline.get("sharpe_ratio"),
        "max_drawdown": headline.get("max_drawdown"),
        "calmar": headline.get("calmar_ratio"),
        "annual_volatility": headline.get("annual_volatility"),
        "win_rate": trades.get("win_rate"),
        "payoff_ratio": trades.get("payoff_ratio"),
        "profit_factor": trades.get("profit_factor"),
        "avg_holding_days": trades.get("avg_holding_days"),
        "total_trades": trades.get("total_trades"),
        "final_value": headline.get("final_portfolio_value"),
    }


def _fmt(value: object, digits: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _pct(v: object) -> str:
    if v is None:
        return "NA"
    return f"{float(v) * 100:.2f}%"


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

        stdout_path = scenario_dir / "stdout.log"
        stderr_path = scenario_dir / "stderr.log"
        with (
            stdout_path.open("w", encoding="utf-8", errors="replace") as fo,
            stderr_path.open("w", encoding="utf-8", errors="replace") as fe,
        ):
            completed = subprocess.run(cmd, cwd=str(repo_root), stdout=fo, stderr=fe, env=env)

        if completed.returncode != 0:
            try:
                tail = stderr_path.read_text(encoding="utf-8", errors="replace").splitlines()[-10:]
                print(
                    f"[ERROR] {name}: exit code {completed.returncode}\n"
                    + "\n".join(f"  {line}" for line in tail),
                    file=sys.stderr,
                    flush=True,
                )
            except Exception:
                print(
                    f"[ERROR] {name}: exit code {completed.returncode}",
                    file=sys.stderr,
                    flush=True,
                )
            results.append({"name": name, "group": scenario["group"], "error": True})
            continue

        try:
            metrics = _read_summary(report_dir)
        except Exception as exc:
            print(
                f"[ERROR] {name}: summary.json 読み込み失敗: {exc}",
                file=sys.stderr,
                flush=True,
            )
            results.append({"name": name, "group": scenario["group"], "error": True})
            continue

        record = {
            "name": name,
            "group": scenario["group"],
            "topix_vol_low_threshold": scenario.get("topix_vol_low_threshold"),
            "topix_vol_high_threshold": scenario.get("topix_vol_high_threshold"),
            "adaptive_threshold_hi": scenario.get("adaptive_threshold_hi"),
            "adaptive_threshold_lo": scenario.get("adaptive_threshold_lo"),
            "quality_score_min": scenario.get("quality_score_min"),
            "desc": scenario.get("desc", ""),
            "is_reference": scenario.get("is_reference", False),
            **{k: v for k, v in metrics.items()},
            "error": False,
        }
        results.append(record)

        print(
            f"[DONE] {name:<12}"
            f"  qual={'-' if scenario.get('quality_score_min') is None else str(scenario.get('quality_score_min')):>5}"
            f"  vol_hi={'-' if scenario.get('topix_vol_high_threshold') is None else str(scenario.get('topix_vol_high_threshold')):>5}"
            f"  cagr={_pct(metrics.get('cagr')):>8}"
            f"  sharpe={_fmt(metrics.get('sharpe'), 3):>6}"
            f"  dd={_pct(metrics.get('max_drawdown')):>8}"
            f"  pf={_fmt(metrics.get('profit_factor'), 3):>6}"
            f"  trades={metrics.get('total_trades')}",
            flush=True,
        )

    return results


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

CSV_FIELDNAMES = [
    "name",
    "group",
    "topix_vol_low_threshold",
    "topix_vol_high_threshold",
    "adaptive_threshold_hi",
    "adaptive_threshold_lo",
    "quality_score_min",
    "desc",
    "cagr",
    "sharpe",
    "max_drawdown",
    "calmar",
    "annual_volatility",
    "win_rate",
    "payoff_ratio",
    "profit_factor",
    "avg_holding_days",
    "total_trades",
    "final_value",
]


def _meets_all(r: dict) -> bool:
    return (
        (r.get("cagr") or 0) > _CAGR_MIN
        and (r.get("sharpe") or 0) > _SHARPE_MIN
        and (r.get("max_drawdown") or 1) < _DD_MAX
        and (r.get("profit_factor") or 0) > _PF_MIN
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 2 Group U — market_calendar 修正後 S2+T4 複合検証"
    )
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--keep-snapshots", action="store_true", default=False)
    args = parser.parse_args()

    scenarios = _SCENARIOS
    n_workers = max(1, min(args.workers or os.cpu_count() or DEFAULT_WORKERS, len(scenarios)))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ARTIFACTS_ROOT / stamp
    output_dir.mkdir(parents=True, exist_ok=True)

    source_db = _get_db_path()
    if not source_db.exists():
        sys.exit(f"[ERROR] DuckDB が見つかりません: {source_db}")

    snapshots_dir = output_dir / "_snapshots"
    snapshots_dir.mkdir(exist_ok=True)

    print(f"output_dir = {output_dir}")
    print(f"scenarios  = {len(scenarios)}, workers = {n_workers}")
    print(f"source_db  = {source_db}")
    print(
        f"IS 参照（R3）= CAGR {_IS_CAGR:.2%}  Sharpe {_IS_SHARPE:.3f}"
        f"  MaxDD {_IS_MAX_DD:.2%}  PF {_IS_PF:.3f}"
    )
    print(
        f"Phase 2 採択基準: CAGR>{_CAGR_MIN:.0%}  Sharpe>{_SHARPE_MIN}  MaxDD<{_DD_MAX:.0%}  PF>{_PF_MIN}"
    )
    print("DBスナップショットを作成中...")

    snapshot_paths = []
    for i in range(n_workers):
        snap = snapshots_dir / f"worker_{i:02d}.duckdb"
        shutil.copy2(str(source_db), str(snap))
        snapshot_paths.append(str(snap))
        print(f"  snapshot[{i}] = {snap.name}")

    batches: list[list[dict]] = [[] for _ in range(n_workers)]
    for idx, scenario in enumerate(scenarios):
        batches[idx % n_workers].append(scenario)

    batch_args = [
        (snapshot_paths[i], batches[i], str(output_dir), str(REPO_ROOT)) for i in range(n_workers)
    ]

    (output_dir / "scenarios.json").write_text(
        json.dumps(scenarios, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "config_base.json").write_text(
        json.dumps(_COM_BASE, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    results_csv = output_dir / "results.csv"
    results_jsonl = output_dir / "results.jsonl"

    all_results: list[dict] = []
    print(f"\n並列実行開始: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 120)

    try:
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = {executor.submit(_run_batch, ba): i for i, ba in enumerate(batch_args)}
            for future in as_completed(futures):
                worker_idx = futures[future]
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                except Exception as exc:
                    print(f"[ERROR] worker {worker_idx} で例外: {exc}", file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
    finally:
        if not args.keep_snapshots:
            try:
                shutil.rmtree(snapshots_dir)
            except Exception as e:
                print(f"[WARN] スナップショット削除失敗: {e}", file=sys.stderr)

    order = {s["name"]: i for i, s in enumerate(scenarios)}
    all_results.sort(key=lambda r: order.get(r.get("name", ""), 999))

    success = [r for r in all_results if not r.get("error")]
    failed = [r for r in all_results if r.get("error")]

    if not any(r.get("name") == "U0_ref" for r in success):
        print("[ERROR] 参照シナリオ U0_ref が失敗しました。採択判断を中断します。", file=sys.stderr)
        sys.exit(1)

    with results_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(success)

    with results_jsonl.open("w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("-" * 120)
    print(f"\n完了: {datetime.now().strftime('%H:%M:%S')}")
    print(f"成功: {len(success)} / {len(scenarios)}, 失敗: {len(failed)}")
    print(f"results_csv   = {results_csv}")
    print(f"results_jsonl = {results_jsonl}")

    if not success:
        if failed:
            sys.exit(1)
        return

    ref = next((r for r in success if r.get("is_reference")), None)

    print("\n" + "=" * 130)
    print("【Group U 結果】R3 固定 / 施策A × クオリティフィルター（2017-2025）")
    print(
        f"  IS 参照（R3）: CAGR {_IS_CAGR:.2%}  Sharpe {_IS_SHARPE:.3f}"
        f"  MaxDD {_IS_MAX_DD:.2%}  PF {_IS_PF:.3f}"
    )
    print("=" * 130)
    print(
        f"  {'シナリオ':<12}  {'vol_hi':>6}  {'thr_lo':>6}  {'quality':>7}"
        f"  {'CAGR':>8}  {'Sharpe':>7}  {'MaxDD':>8}  {'Calmar':>7}"
        f"  {'PF':>6}  {'Trades':>7}  採択"
    )
    print("  " + "-" * 115)

    for r in success:
        all_ok = _meets_all(r)
        ref_sharpe = ref["sharpe"] if ref and ref.get("sharpe") else 0
        better = (r.get("sharpe") or 0) > ref_sharpe and r["name"] != "U0_ref"
        marker = " [ALL]" if all_ok else (" [>U0]" if better else "")
        print(
            f"  {r['name']:<12}"
            f"  {'-' if r.get('topix_vol_high_threshold') is None else str(r.get('topix_vol_high_threshold')):>6}"
            f"  {'-' if r.get('adaptive_threshold_lo') is None else str(r.get('adaptive_threshold_lo')):>6}"
            f"  {'-' if r.get('quality_score_min') is None else str(r.get('quality_score_min')):>7}"
            f"  {_pct(r.get('cagr')):>8}"
            f"  {_fmt(r.get('sharpe'), 3):>7}"
            f"  {_pct(r.get('max_drawdown')):>8}"
            f"  {_fmt(r.get('calmar'), 3):>7}"
            f"  {_fmt(r.get('profit_factor'), 3):>6}"
            f"  {str(r.get('total_trades', '')):>7}"
            f"{marker}"
        )

    print("\n" + "=" * 130)
    print("【採択判断】")
    adopted = [r for r in success if _meets_all(r)]
    improved = [
        r
        for r in success
        if (r.get("sharpe") or 0) > (ref["sharpe"] if ref else 0) and r["name"] != "U0_ref"
    ]

    decision: dict = {}
    if adopted:
        best = max(adopted, key=lambda r: r.get("sharpe") or 0)
        print(f"  全採択基準達成: {[r['name'] for r in adopted]}")
        print(
            f"  → 最良設定 {best['name']} を Phase 2 最終採用（Phase2_Backtest_Strategy.md Section 51 に記録）"
        )
        decision = {
            "verdict": "ADOPTED",
            "best_scenario": best["name"],
            "adopted_scenarios": [r["name"] for r in adopted],
            "best_cagr": best.get("cagr"),
            "best_sharpe": best.get("sharpe"),
            "best_max_drawdown": best.get("max_drawdown"),
            "best_profit_factor": best.get("profit_factor"),
            "best_win_rate": best.get("win_rate"),
            "best_total_trades": best.get("total_trades"),
        }
    elif improved:
        best = max(improved, key=lambda r: r.get("sharpe") or 0)
        print(f"  Sharpe が U0 を上回るシナリオ: {[r['name'] for r in improved]}")
        print(f"  → {best['name']} を Phase 2 ベースとして採用")
        decision = {
            "verdict": "IMPROVED",
            "best_scenario": best["name"],
            "improved_scenarios": [r["name"] for r in improved],
            "best_cagr": best.get("cagr"),
            "best_sharpe": best.get("sharpe"),
            "best_max_drawdown": best.get("max_drawdown"),
            "best_profit_factor": best.get("profit_factor"),
            "best_win_rate": best.get("win_rate"),
            "best_total_trades": best.get("total_trades"),
        }
    else:
        print("  全シナリオで U0 以下 → 複合フィルターは改善効果なし")
        decision = {"verdict": "NO_IMPROVEMENT", "reason": "All scenarios <= U0"}

    (output_dir / "decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("=" * 130)
    print(f"decision.json = {output_dir / 'decision.json'}")

    if failed:
        print(f"\n失敗したシナリオ: {[r['name'] for r in failed]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
