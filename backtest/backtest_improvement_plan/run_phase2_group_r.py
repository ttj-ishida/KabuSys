"""Phase 2 Group R — ポジション数・utilization グリッドサーチ (Issue #375)

P2_n1b_o2 の設定を固定し、max_positions と max_utilization を変化させることで
2018 年への収益集中（OOS 検証で判明した構造問題）を分散によって解消できるか検証する。

追加実装ゼロ。パラメータ変更のみ。

IS 参照値（P2_n1b_o2、Phase1_Backtest_Strategy.md Section 46）:
  CAGR 8.31%、Sharpe 0.428、MaxDD 19.10%、PF 1.321

シナリオ:
  R0_p2_ref : max_pos=3,  util=30%  P2 参照（Phase 1 最終採用）
  R1        : max_pos=5,  util=40%  銘柄数+2・投下率+10pt
  R2        : max_pos=5,  util=50%  銘柄数+2・投下率+20pt
  R3        : max_pos=7,  util=40%  銘柄数+4・投下率+10pt（分散重視）
  R4        : max_pos=7,  util=50%  銘柄数+4・投下率+20pt
  R5        : max_pos=7,  util=60%  銘柄数+4・投下率+30pt（積極）
  R6        : max_pos=10, util=50%  最大分散（Phase 2 上限候補）

Phase 2 採択基準:
  CAGR  > 8%    (Phase 1 実績 8.31% を維持)
  Sharpe > 0.5  (Phase 2 主目標)
  MaxDD  < 25%  (Phase 1 採択基準と同一)
  PF     > 1.1

Usage:
    python backtest/backtest_improvement_plan/run_phase2_group_r.py
    python backtest/backtest_improvement_plan/run_phase2_group_r.py --workers 4
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

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

DEFAULT_WORKERS = 4


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "config" / "strategy_config.yaml").exists():
            return candidate
    raise FileNotFoundError("config/strategy_config.yaml が見つかりません")


REPO_ROOT = _find_repo_root()
ENV_PATH = REPO_ROOT / ".env"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase2_group_r"

# ---------------------------------------------------------------------------
# P2_n1b_o2 固定パラメータ（max_positions / max_utilization 以外）
# ---------------------------------------------------------------------------

_COM_BASE = {
    "cash": 1_000_000,
    "allocation_method": "equal",
    "max_position_pct": 0.22,
    "risk_pct": 0.005,
    "use_ma200_filter": True,
    "stop_loss_pct": 0.09,
    "min_holding_days": 5,
    "max_holding_days": 60,
    "trailing_stop_atr": 2.0,
    "threshold": 0.58,
    # Bear Guard OFF
    "weak_bear": 1.00,
    "strong_bear": 1.00,
    # DD Stop
    "dd_stop": 0.12,
    "dd_timeout": 30,
    # 施策A: 動的シグナル閾値
    "adaptive_threshold_vol_regime": True,
    "topix_vol_window": 20,
    "topix_vol_low_threshold": 0.12,
    "adaptive_threshold_hi": 0.62,
    # 施策B: 多段階トレーリングストップ
    "dynamic_trailing_stop": True,
    "trail_profit_gate_atr": 1.5,
    "trail_stage2_mult": 1.8,
    "trail_stage3_mult": 1.5,
    # 期間固定
    "start": "2017-01-01",
    "end": "2025-12-31",
}

# IS 参照値（Phase 1 Section 46）
_IS_CAGR = 0.0831
_IS_SHARPE = 0.428
_IS_MAX_DD = 0.1910
_IS_PF = 1.321

# Phase 2 採択基準
_CAGR_MIN = 0.08
_SHARPE_MIN = 0.5
_DD_MAX = 0.25
_PF_MIN = 1.1

# ---------------------------------------------------------------------------
# シナリオ定義（max_positions / max_utilization のみ変動）
# ---------------------------------------------------------------------------

_SCENARIOS: list[dict] = [
    {
        "name": "R0_p2_ref",
        "group": "R",
        "max_positions": 3,
        "max_utilization": 0.30,
        "desc": "P2 参照（Phase 1 最終採用）",
        "is_reference": True,
    },
    {
        "name": "R1",
        "group": "R",
        "max_positions": 5,
        "max_utilization": 0.40,
        "desc": "銘柄数+2・投下率+10pt（1銘柄 8.0%）",
        "is_reference": False,
    },
    {
        "name": "R2",
        "group": "R",
        "max_positions": 5,
        "max_utilization": 0.50,
        "desc": "銘柄数+2・投下率+20pt（1銘柄 10.0%）",
        "is_reference": False,
    },
    {
        "name": "R3",
        "group": "R",
        "max_positions": 7,
        "max_utilization": 0.40,
        "desc": "銘柄数+4・投下率+10pt（1銘柄 5.7%）",
        "is_reference": False,
    },
    {
        "name": "R4",
        "group": "R",
        "max_positions": 7,
        "max_utilization": 0.50,
        "desc": "銘柄数+4・投下率+20pt（1銘柄 7.1%）",
        "is_reference": False,
    },
    {
        "name": "R5",
        "group": "R",
        "max_positions": 7,
        "max_utilization": 0.60,
        "desc": "銘柄数+4・投下率+30pt（1銘柄 8.6%、積極）",
        "is_reference": False,
    },
    {
        "name": "R6",
        "group": "R",
        "max_positions": 10,
        "max_utilization": 0.50,
        "desc": "最大分散（1銘柄 5.0%、Phase 2 上限候補）",
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
        str(scenario["max_positions"]),
        "--max-position-pct",
        str(com["max_position_pct"]),
        "--max-utilization",
        str(scenario["max_utilization"]),
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
        str(com["topix_vol_low_threshold"]),
        "--adaptive-threshold-hi",
        str(com["adaptive_threshold_hi"]),
        "--dynamic-trailing-stop",
        "--trail-profit-gate-atr",
        str(com["trail_profit_gate_atr"]),
        "--trail-stage2-mult",
        str(com["trail_stage2_mult"]),
        "--trail-stage3-mult",
        str(com["trail_stage3_mult"]),
        "--output-format",
        "all",
        "--output-dir",
        str(output_dir),
    ]
    if com.get("use_ma200_filter"):
        cmd.append("--ma200-filter")
    return cmd


def _read_summary(report_dir: Path) -> dict:
    # サブディレクトリ配下を優先、なければ直下もフォールバック
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
        "created_at": meta.get("generated_at", ""),
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
            completed = subprocess.run(
                cmd,
                cwd=str(repo_root),
                stdout=fo,
                stderr=fe,
                env=env,
            )

        if completed.returncode != 0:
            # CI デバッグ支援: stderr の末尾 10 行をエコー
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
                    f"[ERROR] {name}: exit code {completed.returncode}", file=sys.stderr, flush=True
                )
            results.append({"name": name, "group": scenario["group"], "error": True})
            continue

        try:
            metrics = _read_summary(report_dir)
        except Exception as exc:
            print(f"[ERROR] {name}: summary.json 読み込み失敗 — {exc}", file=sys.stderr, flush=True)
            results.append({"name": name, "group": scenario["group"], "error": True})
            continue

        record = {
            "name": name,
            "group": scenario["group"],
            "max_positions": scenario["max_positions"],
            "max_utilization": scenario["max_utilization"],
            "alloc_per_pos_pct": scenario["max_utilization"] / scenario["max_positions"] * 100,
            "desc": scenario.get("desc", ""),
            "is_reference": scenario.get("is_reference", False),
            **{k: v for k, v in metrics.items()},
            "error": False,
        }
        results.append(record)

        print(
            f"[DONE] {name:<14}"
            f"  pos={scenario['max_positions']:>2}  util={scenario['max_utilization']:.0%}"
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
    "max_positions",
    "max_utilization",
    "alloc_per_pos_pct",
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


def _meets_three(r: dict) -> bool:
    """Sharpe を除く 3 指標"""
    return (
        (r.get("cagr") or 0) > _CAGR_MIN
        and (r.get("max_drawdown") or 1) < _DD_MAX
        and (r.get("profit_factor") or 0) > _PF_MIN
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 2 Group R — ポジション数・utilization グリッドサーチ"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="並列ワーカー数（デフォルト: CPU コア数とシナリオ数の小さい方）",
    )
    parser.add_argument(
        "--keep-snapshots",
        action="store_true",
        default=False,
        help="実行後もDBスナップショットを削除せず保持する",
    )
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
        f"IS 参照    = CAGR {_IS_CAGR:.2%}  Sharpe {_IS_SHARPE:.3f}  MaxDD {_IS_MAX_DD:.2%}  PF {_IS_PF:.3f}"
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
    print("-" * 110)

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

    with results_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(success)

    with results_jsonl.open("w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("-" * 110)
    print(f"\n完了: {datetime.now().strftime('%H:%M:%S')}")
    print(f"成功: {len(success)} / {len(scenarios)}, 失敗: {len(failed)}")
    print(f"results_csv   = {results_csv}")
    print(f"results_jsonl = {results_jsonl}")

    if not success:
        if failed:
            sys.exit(1)
        return

    # -----------------------------------------------------------------------
    # 結果表示
    # -----------------------------------------------------------------------

    ref = next((r for r in success if r.get("is_reference")), None)

    print("\n" + "=" * 120)
    print("【Group R 結果】P2_n1b_o2 固定 / max_positions・max_utilization 変動（2017-2025）")
    print(
        f"  IS 参照（R0）: CAGR {_IS_CAGR:.2%}  Sharpe {_IS_SHARPE:.3f}"
        f"  MaxDD {_IS_MAX_DD:.2%}  PF {_IS_PF:.3f}"
    )
    print("=" * 120)
    print(
        f"  {'シナリオ':<14} {'pos':>4} {'util':>6} {'配分%':>7}"
        f"  {'CAGR':>8} {'Sharpe':>7} {'MaxDD':>8} {'Calmar':>7}"
        f"  {'PF':>6} {'Trades':>7}  採択"
    )
    print("  " + "-" * 110)

    for r in success:
        all_ok = _meets_all(r)
        three_ok = _meets_three(r)
        marker = " [ALL]" if all_ok else (" [3/4]" if three_ok else "")
        ref_sharpe = ref["sharpe"] if ref and ref.get("sharpe") else 0
        better_than_ref = (r.get("sharpe") or 0) > ref_sharpe and r["name"] != "R0_p2_ref"
        if better_than_ref and not all_ok:
            marker = " [>R0]"
        print(
            f"  {r['name']:<14}"
            f"  {r.get('max_positions', ''):>4}"
            f"  {r.get('max_utilization', 0):.0%}".rjust(7)
            + f"  {r.get('alloc_per_pos_pct', 0):.1f}%".rjust(7)
            + f"  {_pct(r.get('cagr')):>8}"
            f"  {_fmt(r.get('sharpe'), 3):>7}"
            f"  {_pct(r.get('max_drawdown')):>8}"
            f"  {_fmt(r.get('calmar'), 3):>7}"
            f"  {_fmt(r.get('profit_factor'), 3):>6}"
            f"  {str(r.get('total_trades', '')):>7}"
            f"{marker}"
        )

    # --- 採択判断 ---
    print("\n" + "=" * 120)
    print("【採択判断】")
    adopted = [r for r in success if _meets_all(r)]
    improved = [
        r
        for r in success
        if (r.get("sharpe") or 0) > (ref["sharpe"] if ref else 0) and r["name"] != "R0_p2_ref"
    ]

    decision: dict = {}
    if adopted:
        best = max(adopted, key=lambda r: r.get("sharpe") or 0)
        print(f"  全採択基準達成: {[r['name'] for r in adopted]}")
        print(
            f"  → 最良設定 {best['name']} を Phase 2 採用候補として選択（Section 49 のベースとする）"
        )
        decision = {
            "verdict": "ADOPTED",
            "best_scenario": best["name"],
            "adopted_scenarios": [r["name"] for r in adopted],
            "best_cagr": best.get("cagr"),
            "best_sharpe": best.get("sharpe"),
            "best_max_drawdown": best.get("max_drawdown"),
            "best_profit_factor": best.get("profit_factor"),
        }
    elif improved:
        best = max(improved, key=lambda r: r.get("sharpe") or 0)
        print(f"  Sharpe が R0 を上回るシナリオ: {[r['name'] for r in improved]}")
        print(
            f"  → {best['name']} を Phase 2 ベースとして採用（Sharpe 0.5 未達は Group S に委ねる）"
        )
        decision = {
            "verdict": "IMPROVED",
            "best_scenario": best["name"],
            "improved_scenarios": [r["name"] for r in improved],
            "best_cagr": best.get("cagr"),
            "best_sharpe": best.get("sharpe"),
            "best_max_drawdown": best.get("max_drawdown"),
            "best_profit_factor": best.get("profit_factor"),
        }
    else:
        print("  全シナリオで R0（P2 参照）以下")
        print("  → ポジション数拡大では構造改善不可。Phase 3 課題として保留")
        decision = {"verdict": "NO_IMPROVEMENT", "reason": "All scenarios <= R0"}

    (output_dir / "decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("=" * 120)
    print(f"decision.json = {output_dir / 'decision.json'}")

    if failed:
        print(f"\n失敗したシナリオ: {[r['name'] for r in failed]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
