"""Phase 2 事前検証 — P2_n1b_o2 の OOS（アウトオブサンプル）検証 (Issue #374)

P2_n1b_o2（Phase 1 最終採用設定）を固定し、異なる期間で実行することで
過剰適合リスクを定量化する。Phase 2 移行の Go/No-Go 判断材料として使用する。

シナリオ:
  OOS_full       : 2017-01-01〜2025-12-31  P2 参照値の再現確認
  OOS_2022_2025  : 2022-01-01〜2025-12-31  直近 4 年の OOS 成績
  OOS_2023_2025  : 2023-01-01〜2025-12-31  最新 3 年の OOS 成績
  WF_2017        : 2017-01-01〜2017-12-31  ウォークフォワード: 2017年
  WF_2018        : 2018-01-01〜2018-12-31  ウォークフォワード: 2018年
  WF_2019        : 2019-01-01〜2019-12-31  ウォークフォワード: 2019年
  WF_2020        : 2020-01-01〜2020-12-31  ウォークフォワード: 2020年
  WF_2021        : 2021-01-01〜2021-12-31  ウォークフォワード: 2021年
  WF_2022        : 2022-01-01〜2022-12-31  ウォークフォワード: 2022年
  WF_2023        : 2023-01-01〜2023-12-31  ウォークフォワード: 2023年
  WF_2024        : 2024-01-01〜2024-12-31  ウォークフォワード: 2024年
  WF_2025        : 2025-01-01〜2025-12-31  ウォークフォワード: 2025年

採択基準（OOS）:
  OOS CAGR      > 5%
  OOS Max DD    < 25%
  IS/OOS Sharpe 乖離 < 0.15

Usage:
    python backtest/backtest_improvement_plan/run_phase2_oos.py
    python backtest/backtest_improvement_plan/run_phase2_oos.py --workers 4
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
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase2_oos"

# ---------------------------------------------------------------------------
# P2_n1b_o2 固定パラメータ（全シナリオ共通）
# ---------------------------------------------------------------------------

_COM = {
    "cash": 1_000_000,
    "allocation_method": "equal",
    "max_position_pct": 0.22,
    "risk_pct": 0.005,
    "max_positions": 3,
    "max_utilization": 0.30,
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
}

# IS 参照値（Phase 1 Section 46 より）
_IS_CAGR = 0.0831
_IS_SHARPE = 0.428
_IS_MAX_DD = 0.1910
_IS_PF = 1.321

# ---------------------------------------------------------------------------
# シナリオ定義
# ---------------------------------------------------------------------------

_SCENARIOS: list[dict] = [
    # --- 期間比較 ---
    {
        "name": "OOS_full",
        "group": "OOS",
        "start": "2017-01-01",
        "end": "2025-12-31",
        "desc": "P2 参照値の再現確認（IS+OOS 統合）",
        "is_reference": True,
    },
    {
        "name": "OOS_2022_2025",
        "group": "OOS",
        "start": "2022-01-01",
        "end": "2025-12-31",
        "desc": "直近 4 年 OOS",
        "is_reference": False,
    },
    {
        "name": "OOS_2023_2025",
        "group": "OOS",
        "start": "2023-01-01",
        "end": "2025-12-31",
        "desc": "最新 3 年 OOS",
        "is_reference": False,
    },
    # --- ウォークフォワード（年次）---
    {
        "name": "WF_2017",
        "group": "WF",
        "start": "2017-01-01",
        "end": "2017-12-31",
        "desc": "強気 +19%",
        "is_reference": False,
    },
    {
        "name": "WF_2018",
        "group": "WF",
        "start": "2018-01-01",
        "end": "2018-12-31",
        "desc": "調整 ±0%",
        "is_reference": False,
    },
    {
        "name": "WF_2019",
        "group": "WF",
        "start": "2019-01-01",
        "end": "2019-12-31",
        "desc": "回復 +18%",
        "is_reference": False,
    },
    {
        "name": "WF_2020",
        "group": "WF",
        "start": "2020-01-01",
        "end": "2020-12-31",
        "desc": "V字 +16%（COVID）",
        "is_reference": False,
    },
    {
        "name": "WF_2021",
        "group": "WF",
        "start": "2021-01-01",
        "end": "2021-12-31",
        "desc": "横ばい +5%",
        "is_reference": False,
    },
    {
        "name": "WF_2022",
        "group": "WF",
        "start": "2022-01-01",
        "end": "2022-12-31",
        "desc": "弱気 -9%",
        "is_reference": False,
    },
    {
        "name": "WF_2023",
        "group": "WF",
        "start": "2023-01-01",
        "end": "2023-12-31",
        "desc": "強気 +28%",
        "is_reference": False,
    },
    {
        "name": "WF_2024",
        "group": "WF",
        "start": "2024-01-01",
        "end": "2024-12-31",
        "desc": "強気 +19%（8月急落）",
        "is_reference": False,
    },
    {
        "name": "WF_2025",
        "group": "WF",
        "start": "2025-01-01",
        "end": "2025-12-31",
        "desc": "混乱（関税ショック）",
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
        scenario["start"],
        "--end",
        scenario["end"],
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
        str(_COM["min_holding_days"]),
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
        # 施策A
        "--adaptive-threshold-vol-regime",
        "--topix-vol-window",
        str(_COM["topix_vol_window"]),
        "--topix-vol-low-threshold",
        str(_COM["topix_vol_low_threshold"]),
        "--adaptive-threshold-hi",
        str(_COM["adaptive_threshold_hi"]),
        # 施策B
        "--dynamic-trailing-stop",
        "--trail-profit-gate-atr",
        str(_COM["trail_profit_gate_atr"]),
        "--trail-stage2-mult",
        str(_COM["trail_stage2_mult"]),
        "--trail-stage3-mult",
        str(_COM["trail_stage3_mult"]),
        "--output-format",
        "all",
        "--output-dir",
        str(output_dir),
    ]
    if _COM.get("use_ma200_filter"):
        cmd.append("--ma200-filter")
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
    annual = data.get("annual_returns", {})
    return {
        "run_id": meta.get("run_id", ""),
        "created_at": meta.get("generated_at", ""),
        "cagr": headline.get("cagr"),
        "sharpe": headline.get("sharpe_ratio"),
        "max_drawdown": headline.get("max_drawdown"),
        "calmar": headline.get("calmar_ratio"),
        "win_rate": trades.get("win_rate"),
        "payoff_ratio": trades.get("payoff_ratio"),
        "profit_factor": trades.get("profit_factor"),
        "avg_holding_days": trades.get("avg_holding_days"),
        "total_trades": trades.get("total_trades"),
        "final_value": headline.get("final_portfolio_value"),
        "annual_returns": annual,
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
            print(f"[ERROR] {name}: exit code {completed.returncode}", file=sys.stderr, flush=True)
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
            "start": scenario["start"],
            "end": scenario["end"],
            "desc": scenario.get("desc", ""),
            "is_reference": scenario.get("is_reference", False),
            **{k: v for k, v in metrics.items() if k != "annual_returns"},
            "error": False,
        }
        results.append(record)

        print(
            f"[DONE] {name:<18}  {scenario['start']}~{scenario['end']}"
            f"  cagr={_fmt(metrics.get('cagr'))}"
            f"  sharpe={_fmt(metrics.get('sharpe'), 3)}"
            f"  dd={_fmt(metrics.get('max_drawdown'))}"
            f"  pf={_fmt(metrics.get('profit_factor'), 3)}"
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
    "start",
    "end",
    "desc",
    "cagr",
    "sharpe",
    "max_drawdown",
    "calmar",
    "win_rate",
    "payoff_ratio",
    "profit_factor",
    "avg_holding_days",
    "total_trades",
    "final_value",
]

# OOS 採択基準
_OOS_CAGR_MIN = 0.05
_OOS_DD_MAX = 0.25
_OOS_SHARPE_DIVERGENCE_MAX = 0.15  # IS と OOS の Sharpe 乖離許容上限


def _oos_pass(r: dict, is_sharpe: float) -> bool:
    """OOS 採択基準を満たすか"""
    cagr_ok = r.get("cagr") is not None and r["cagr"] > _OOS_CAGR_MIN
    dd_ok = r.get("max_drawdown") is not None and r["max_drawdown"] < _OOS_DD_MAX
    oos_sharpe = r.get("sharpe")
    div_ok = oos_sharpe is not None and abs(is_sharpe - oos_sharpe) < _OOS_SHARPE_DIVERGENCE_MAX
    return cagr_ok and dd_ok and div_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 事前検証 — P2_n1b_o2 OOS 検証")
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"並列ワーカー数（デフォルト: {DEFAULT_WORKERS}）",
    )
    parser.add_argument(
        "--keep-snapshots",
        action="store_true",
        default=False,
        help="実行後もDBスナップショットを削除せず保持する",
    )
    args = parser.parse_args()

    scenarios = _SCENARIOS
    n_workers = min(args.workers, len(scenarios))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ARTIFACTS_ROOT / stamp
    output_dir.mkdir(parents=True, exist_ok=True)

    source_db = _get_db_path()
    if not source_db.exists():
        sys.exit(f"[ERROR] DuckDB が見つかりません: {source_db}")

    snapshots_dir = output_dir / "_snapshots"
    snapshots_dir.mkdir()

    print(f"output_dir  = {output_dir}")
    print(f"scenarios   = {len(scenarios)}, workers = {n_workers}")
    print(f"source_db   = {source_db}")
    print(
        f"P2 IS 参照  = CAGR {_IS_CAGR:.2%}  Sharpe {_IS_SHARPE:.3f}  MaxDD {_IS_MAX_DD:.2%}  PF {_IS_PF:.3f}"
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

    # 定義順にソート
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
    print(f"results_csv = {results_csv}")

    if not success:
        return

    # -----------------------------------------------------------------------
    # 結果表示
    # -----------------------------------------------------------------------

    ref = next((r for r in success if r.get("is_reference")), None)
    actual_is_sharpe = ref["sharpe"] if ref and ref.get("sharpe") is not None else _IS_SHARPE

    print("\n" + "=" * 110)
    print("【OOS 検証結果】P2_n1b_o2 固定")
    print(
        f"  IS 参照（2017-2025）: CAGR {_IS_CAGR:.2%}  Sharpe {_IS_SHARPE:.3f}  MaxDD {_IS_MAX_DD:.2%}  PF {_IS_PF:.3f}"
    )
    print("=" * 110)

    # --- OOS 期間比較 ---
    oos_group = [r for r in success if r["group"] == "OOS"]
    if oos_group:
        print("\n--- OOS 期間比較 ---")
        print(
            f"  {'シナリオ':<20} {'期間':<24} {'CAGR':>8} {'Sharpe':>7} {'MaxDD':>8} {'PF':>6} {'Trades':>7}  {'Sharpe乖離':>10}  基準"
        )
        print("  " + "-" * 100)
        for r in oos_group:
            oos_sharpe = r.get("sharpe")
            divergence = abs(actual_is_sharpe - oos_sharpe) if oos_sharpe is not None else None
            div_str = _fmt(divergence, 3) if divergence is not None else "NA"
            passed = _oos_pass(r, actual_is_sharpe)
            mark = "[GO]" if passed else "[NG]"
            print(
                f"  {r['name']:<20} {r['start']}~{r['end']}"
                f"  {_fmt(r.get('cagr')):>8}"
                f"  {_fmt(r.get('sharpe'), 3):>7}"
                f"  {_fmt(r.get('max_drawdown')):>8}"
                f"  {_fmt(r.get('profit_factor'), 3):>6}"
                f"  {str(r.get('total_trades', '')):>7}"
                f"  {div_str:>10}"
                f"  {mark}"
            )

    # --- ウォークフォワード年次 ---
    wf_group = [r for r in success if r["group"] == "WF"]
    if wf_group:
        print("\n--- ウォークフォワード年次成績 ---")
        print(f"  {'年':>6} {'CAGR':>8} {'Sharpe':>7} {'MaxDD':>8} {'PF':>6} {'Trades':>7}  概況")
        print("  " + "-" * 70)
        profitable = 0
        for r in wf_group:
            year = r["start"][:4]
            desc = r.get("desc", "")
            cagr = r.get("cagr")
            mark = "+" if cagr is not None and cagr > 0 else "-"
            if cagr is not None and cagr > 0:
                profitable += 1
            print(
                f"  {year:>6}  {_fmt(cagr):>8}"
                f"  {_fmt(r.get('sharpe'), 3):>7}"
                f"  {_fmt(r.get('max_drawdown')):>8}"
                f"  {_fmt(r.get('profit_factor'), 3):>6}"
                f"  {str(r.get('total_trades', '')):>7}"
                f"  {mark}  {desc}"
            )
        print(f"\n  プラス年: {profitable} / {len(wf_group)} 年")

    # --- 採択判断 ---
    print("\n" + "=" * 110)
    print("【採択判断】")
    oos_main = next((r for r in oos_group if r["name"] == "OOS_2022_2025"), None)
    if oos_main:
        passed = _oos_pass(oos_main, actual_is_sharpe)
        oos_sharpe = oos_main.get("sharpe")
        div = abs(actual_is_sharpe - oos_sharpe) if oos_sharpe is not None else None
        print("  OOS_2022_2025:")
        cagr_ok = (oos_main.get("cagr") or 0) > _OOS_CAGR_MIN
        dd_ok = (oos_main.get("max_drawdown") or 1) < _OOS_DD_MAX
        div_ok = div is not None and div < _OOS_SHARPE_DIVERGENCE_MAX
        print(
            f"    CAGR > 5%              : {'[OK]' if cagr_ok else '[NG]'} {_fmt(oos_main.get('cagr'))}"
        )
        print(
            f"    MaxDD < 25%            : {'[OK]' if dd_ok else '[NG]'} {_fmt(oos_main.get('max_drawdown'))}"
        )
        print(
            f"    Sharpe 乖離 < 0.15     : {'[OK]' if div_ok else '[NG]'} {_fmt(div, 3) if div is not None else 'NA'}"
        )
        print()
        if passed:
            print("  → OOS 基準クリア: Phase 2 設定探索 Go（#375 Group R へ）")
        else:
            print("  → OOS 基準未達: P2 設定を OOS データで再調整してから #375 へ")
    print("=" * 110)

    if failed:
        print(f"\n失敗したシナリオ: {[r['name'] for r in failed]}")


if __name__ == "__main__":
    main()
