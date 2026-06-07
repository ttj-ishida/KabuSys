"""Phase 2 — W1_08 OOS ウォークフォワード検証 (Issue #396)

W1_08（V1 + entry_3d_max_abs_return=0.08）は IS 2017-2025 で全採択基準を達成したが、
9年間すべてがサンプル内であり OOS 検証が未実施。本スクリプトで過剰適合リスクを定量化する。

検証設計:
  IS 期間  : 2017-01-01 〜 2021-12-31 (5 年)
  OOS 期間 : 2022-01-01 〜 2025-12-31 (4 年)

シナリオ:
  W1_full  : 2017-01-01〜2025-12-31  IS 再現確認（参照）
  W1_IS    : 2017-01-01〜2021-12-31  IS のみ（5年）
  W1_OOS   : 2022-01-01〜2025-12-31  メイン OOS（4年）★採択判断対象
  WF_2017  : 2017 年単年
  WF_2018  : 2018 年単年
  WF_2019  : 2019 年単年
  WF_2020  : 2020 年単年
  WF_2021  : 2021 年単年
  WF_2022  : 2022 年単年
  WF_2023  : 2023 年単年
  WF_2024  : 2024 年単年
  WF_2025  : 2025 年単年

OOS 採択基準（W1_OOS）:
  CAGR        > 0%
  MaxDD       < 25%
  Sharpe      >= 0.40
  PF          >= 1.0
  IS/OOS Sharpe 乖離 <= 0.30

Usage:
    python backtest/backtest_improvement_plan/run_phase2_oos_w1.py
    python backtest/backtest_improvement_plan/run_phase2_oos_w1.py --workers 4
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
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase2_oos_w1"

# W1_08 固定パラメータ
_COM = {
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
    "topix_vol_low_threshold": 0.12,
    "adaptive_threshold_hi": 0.62,
    "dynamic_trailing_stop": True,
    "trail_profit_gate_atr": 1.5,
    "trail_stage2_mult": 1.8,
    "trail_stage3_mult": 1.5,
    "quality_score_min": -0.30,
    "score_drop_atr_gate": 1.0,
    "entry_3d_max_abs_return": 0.08,
}

# W1_08 IS（2017-2025）参照値
_IS_CAGR = 0.1438
_IS_SHARPE = 0.674
_IS_MAX_DD = 0.1843
_IS_PF = 1.793

# OOS 採択基準
_OOS_CAGR_MIN = 0.0
_OOS_DD_MAX = 0.25
_OOS_SHARPE_MIN = 0.40
_OOS_PF_MIN = 1.0
_OOS_SHARPE_DIVERGENCE_MAX = 0.30

_SCENARIOS: list[dict] = [
    {
        "name": "W1_full",
        "group": "IS",
        "start": "2017-01-01",
        "end": "2025-12-31",
        "desc": "IS 全期間再現確認（参照）",
        "is_reference": True,
    },
    {
        "name": "W1_IS",
        "group": "IS",
        "start": "2017-01-01",
        "end": "2021-12-31",
        "desc": "IS のみ（5年）",
        "is_reference": False,
    },
    {
        "name": "W1_OOS",
        "group": "OOS",
        "start": "2022-01-01",
        "end": "2025-12-31",
        "desc": "メイン OOS（4年）★採択判断対象",
        "is_reference": False,
    },
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
    com = _COM
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
        "--ma200-filter",
        "--quality-score-min",
        str(com["quality_score_min"]),
        "--score-drop-atr-gate",
        str(com["score_drop_atr_gate"]),
        "--entry-3d-max-abs-return",
        str(com["entry_3d_max_abs_return"]),
        "--output-format",
        "all",
        "--output-dir",
        str(output_dir),
    ]
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
        (scenario_dir / "command.txt").write_text(" ".join(map(str, cmd)), encoding="utf-8")

        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(repo_root / "src"), env.get("PYTHONPATH", "")])
        )
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
                    f"[ERROR] {name}: exit {completed.returncode}\n"
                    + "\n".join(f"  {line}" for line in tail),
                    file=sys.stderr,
                    flush=True,
                )
            except Exception:
                print(f"[ERROR] {name}: exit {completed.returncode}", file=sys.stderr, flush=True)
            results.append({"name": name, "group": scenario["group"], "error": True})
            continue

        try:
            metrics = _read_summary(report_dir)
        except Exception as exc:
            print(f"[ERROR] {name}: summary 読み込み失敗: {exc}", file=sys.stderr, flush=True)
            results.append({"name": name, "group": scenario["group"], "error": True})
            continue

        record = {
            "name": name,
            "group": scenario["group"],
            "start": scenario["start"],
            "end": scenario["end"],
            "desc": scenario.get("desc", ""),
            "is_reference": scenario.get("is_reference", False),
            **metrics,
            "error": False,
        }
        results.append(record)
        print(
            f"[DONE] {name:<12}  {scenario['start']}~{scenario['end']}"
            f"  cagr={_pct(metrics.get('cagr')):>8}"
            f"  sharpe={_fmt(metrics.get('sharpe'), 3):>6}"
            f"  dd={_pct(metrics.get('max_drawdown')):>7}"
            f"  pf={_fmt(metrics.get('profit_factor'), 3):>6}"
            f"  trades={metrics.get('total_trades')}",
            flush=True,
        )
    return results


CSV_FIELDNAMES = [
    "name",
    "group",
    "start",
    "end",
    "desc",
    "is_reference",
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


def _oos_pass(r: dict, is_sharpe: float) -> bool:
    cagr_ok = (r.get("cagr") or -1) > _OOS_CAGR_MIN
    dd_ok = (r.get("max_drawdown") or 1) < _OOS_DD_MAX
    sharpe = r.get("sharpe")
    sharpe_ok = sharpe is not None and sharpe >= _OOS_SHARPE_MIN
    pf_ok = (r.get("profit_factor") or 0) >= _OOS_PF_MIN
    div_ok = sharpe is not None and abs(is_sharpe - sharpe) <= _OOS_SHARPE_DIVERGENCE_MAX
    return cagr_ok and dd_ok and sharpe_ok and pf_ok and div_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 W1_08 OOS Walk-Forward (Issue #396)")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--keep-snapshots", action="store_true", default=False)
    parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="WF 含む任意シナリオ失敗で exit 1（デフォルトは致命シナリオのみ）",
    )
    args = parser.parse_args()
    _cpu = os.cpu_count() or DEFAULT_WORKERS
    workers = min(args.workers or DEFAULT_WORKERS, _cpu, len(_SCENARIOS))

    source_db = _get_db_path()
    if not source_db.exists():
        sys.exit(f"[ERROR] DuckDB が見つかりません: {source_db}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ARTIFACTS_ROOT / ts
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "scenarios.json").write_text(
        json.dumps(_SCENARIOS, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "config.json").write_text(
        json.dumps(_COM, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[INFO] W1_08 OOS 検証開始  workers={workers}  出力={output_dir}")
    print(
        f"[INFO] W1_08 IS(2017-2025): CAGR={_IS_CAGR:.2%}  Sharpe={_IS_SHARPE}  "
        f"MaxDD={_IS_MAX_DD:.2%}  PF={_IS_PF}"
    )
    print(
        f"[INFO] OOS 採択基準: CAGR>{_OOS_CAGR_MIN:.0%}  Sharpe≥{_OOS_SHARPE_MIN}  "
        f"MaxDD<{_OOS_DD_MAX:.0%}  PF≥{_OOS_PF_MIN}  Sharpe乖離≤{_OOS_SHARPE_DIVERGENCE_MAX}"
    )

    snapshots_dir = output_dir / "_snapshots"
    snapshots_dir.mkdir(exist_ok=True)
    snapshot_paths = []
    for i in range(workers):
        snap = snapshots_dir / f"worker_{i:02d}.duckdb"
        shutil.copy2(str(source_db), str(snap))
        snapshot_paths.append(str(snap))

    batches = [_SCENARIOS[i::workers] for i in range(workers)]
    batch_args = [
        (snapshot_paths[i], batches[i], str(output_dir), str(REPO_ROOT))
        for i, b in enumerate(batches)
        if b
    ]

    all_results: list[dict] = []
    try:
        if workers == 1:
            for ba in batch_args:
                all_results.extend(_run_batch(ba))
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_run_batch, ba): ba for ba in batch_args}
                for fut in as_completed(futures):
                    try:
                        all_results.extend(fut.result())
                    except Exception:
                        traceback.print_exc()
    finally:
        if not args.keep_snapshots:
            try:
                shutil.rmtree(snapshots_dir)
            except Exception as e:
                print(f"[WARN] スナップショット削除失敗: {e}", file=sys.stderr)

    order = {s["name"]: i for i, s in enumerate(_SCENARIOS)}
    all_results.sort(key=lambda r: order.get(r.get("name", ""), 999))

    success = [r for r in all_results if not r.get("error")]
    failed = [r for r in all_results if r.get("error")]

    csv_path = output_dir / "results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(success)

    # --- IS Sharpe 比較対象の決定: W1_IS(2017-2021) > W1_full > 定数 ---
    is_ref = next((r for r in success if r.get("name") == "W1_IS"), None)
    full_ref = next((r for r in success if r.get("is_reference")), None)
    if is_ref and is_ref.get("sharpe") is not None:
        actual_is_sharpe = is_ref["sharpe"]
        is_sharpe_src = "W1_IS"
        is_sharpe_period = f"{is_ref['start']}~{is_ref['end']}"
    elif full_ref and full_ref.get("sharpe") is not None:
        actual_is_sharpe = full_ref["sharpe"]
        is_sharpe_src = "W1_full"
        is_sharpe_period = f"{full_ref['start']}~{full_ref['end']}"
    else:
        actual_is_sharpe = _IS_SHARPE
        is_sharpe_src = "fallback"
        is_sharpe_period = "2017-2025 (const)"

    print(f"\n{'=' * 100}")
    print("【W1_08 OOS ウォークフォワード検証結果】")
    if full_ref:
        print(
            f"  IS 参照（{full_ref['start']}~{full_ref['end']}）: "
            f"CAGR {_pct(full_ref.get('cagr'))}  Sharpe {_fmt(full_ref.get('sharpe'), 3)}  "
            f"MaxDD {_pct(full_ref.get('max_drawdown'))}  PF {_fmt(full_ref.get('profit_factor'), 3)}"
        )
    else:
        print(
            f"  IS 参照（2017-2025, const）: CAGR {_IS_CAGR:.2%}  Sharpe {_IS_SHARPE:.3f}  "
            f"MaxDD {_IS_MAX_DD:.2%}  PF {_IS_PF:.3f}"
        )
    print(
        f"  Sharpe 乖離比較対象: {is_sharpe_src} ({is_sharpe_period}) = {_fmt(actual_is_sharpe, 3)}"
    )
    print(f"{'=' * 100}")

    # IS / OOS 期間比較
    period_group = [r for r in success if r["group"] in ("IS", "OOS")]
    if period_group:
        print(f"\n--- IS / OOS 期間比較  ※Sharpe 乖離は vs {is_sharpe_src}({is_sharpe_period}) ---")
        print(
            f"  {'シナリオ':<12} {'期間':<24} {'CAGR':>8} {'Sharpe':>7} {'MaxDD':>8} "
            f"{'PF':>6} {'Trades':>7}  {'Sharpe乖離':>10}  判定"
        )
        print("  " + "-" * 96)
        for r in period_group:
            sharpe = r.get("sharpe")
            div = abs(actual_is_sharpe - sharpe) if sharpe is not None else None
            div_str = _fmt(div, 3) if div is not None else "NA"
            mark = (
                "[GO]"
                if (r["group"] == "OOS" and _oos_pass(r, actual_is_sharpe))
                else ("ref" if r.get("is_reference") else "")
            )
            print(
                f"  {r['name']:<12} {r['start']}~{r['end']}"
                f"  {_pct(r.get('cagr')):>8}"
                f"  {_fmt(r.get('sharpe'), 3):>7}"
                f"  {_pct(r.get('max_drawdown')):>8}"
                f"  {_fmt(r.get('profit_factor'), 3):>6}"
                f"  {str(r.get('total_trades', '')):>7}"
                f"  {div_str:>10}"
                f"  {mark}"
            )

    # ウォークフォワード年次
    wf_group = [r for r in success if r["group"] == "WF"]
    if wf_group:
        print("\n--- ウォークフォワード年次成績 ---")
        print(f"  {'年':>6} {'CAGR':>8} {'Sharpe':>7} {'MaxDD':>8} {'PF':>6} {'Trades':>7}  概況")
        print("  " + "-" * 72)
        profitable = 0
        for r in wf_group:
            year = r["start"][:4]
            cagr = r.get("cagr")
            if cagr is not None and cagr > 0:
                profitable += 1
            print(
                f"  {year:>6}  {_pct(cagr):>8}"
                f"  {_fmt(r.get('sharpe'), 3):>7}"
                f"  {_pct(r.get('max_drawdown')):>8}"
                f"  {_fmt(r.get('profit_factor'), 3):>6}"
                f"  {str(r.get('total_trades', '')):>7}"
                f"  {r.get('desc', '')}"
            )
        print(f"\n  プラス年: {profitable} / {len(wf_group)} 年（IS={_IS_CAGR:.2%} 参照）")

    # 採択判断
    print(f"\n{'=' * 100}")
    print("【採択判断】W1_OOS（2022-2025）")
    oos_main = next((r for r in success if r["name"] == "W1_OOS"), None)
    decision: dict = {}

    if oos_main is None:
        print("  [WARNING] W1_OOS が未取得のため採択判定不可")
        decision = {
            "verdict": "UNKNOWN",
            "reason": "W1_OOS not available",
            "is_sharpe_source": is_sharpe_src,
            "is_sharpe_period": is_sharpe_period,
        }
    else:
        oos_sharpe = oos_main.get("sharpe")
        oos_cagr = oos_main.get("cagr")
        oos_dd = oos_main.get("max_drawdown")
        oos_pf = oos_main.get("profit_factor")
        div = abs(actual_is_sharpe - oos_sharpe) if oos_sharpe is not None else None

        cagr_ok = (oos_cagr or -1) > _OOS_CAGR_MIN
        dd_ok = (oos_dd or 1) < _OOS_DD_MAX
        sharpe_ok = oos_sharpe is not None and oos_sharpe >= _OOS_SHARPE_MIN
        pf_ok = (oos_pf or 0) >= _OOS_PF_MIN
        div_ok = div is not None and div <= _OOS_SHARPE_DIVERGENCE_MAX
        passed = cagr_ok and dd_ok and sharpe_ok and pf_ok and div_ok

        print(
            f"  Sharpe 乖離比較: vs {is_sharpe_src}({is_sharpe_period}) IS Sharpe={_fmt(actual_is_sharpe, 3)}"
        )
        print()
        print(
            f"  CAGR > {_OOS_CAGR_MIN:.0%}             : {'[OK]' if cagr_ok else '[NG]'} {_pct(oos_cagr)}"
        )
        print(
            f"  MaxDD < {_OOS_DD_MAX:.0%}           : {'[OK]' if dd_ok else '[NG]'} {_pct(oos_dd)}"
        )
        print(
            f"  Sharpe >= {_OOS_SHARPE_MIN}         : {'[OK]' if sharpe_ok else '[NG]'} {_fmt(oos_sharpe, 3)}"
        )
        print(
            f"  PF >= {_OOS_PF_MIN}                 : {'[OK]' if pf_ok else '[NG]'} {_fmt(oos_pf, 3)}"
        )
        print(
            f"  Sharpe 乖離 <= {_OOS_SHARPE_DIVERGENCE_MAX}"
            f"    : {'[OK]' if div_ok else '[NG]'} {_fmt(div, 3) if div is not None else 'NA'}"
        )
        print()
        if passed:
            print("  → OOS 基準クリア: W1_08 本番投入 Go（Issue #397, #398 へ）")
        else:
            print("  → OOS 基準未達: パラメータ再設計が必要（IS 過剰適合の可能性）")

        decision = {
            "verdict": "GO" if passed else "NG",
            "oos_cagr": oos_cagr,
            "oos_max_drawdown": oos_dd,
            "oos_sharpe": oos_sharpe,
            "oos_profit_factor": oos_pf,
            "is_sharpe": actual_is_sharpe,
            "is_sharpe_source": is_sharpe_src,
            "is_sharpe_period": is_sharpe_period,
            "sharpe_divergence": div,
            "cagr_ok": cagr_ok,
            "dd_ok": dd_ok,
            "sharpe_ok": sharpe_ok,
            "pf_ok": pf_ok,
            "divergence_ok": div_ok,
        }

    (output_dir / "decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"{'=' * 100}")
    print(f"出力: {output_dir}")

    if failed:
        failed_names = {r["name"] for r in failed}
        critical = {"W1_full", "W1_IS", "W1_OOS"}
        critical_failed = sorted(failed_names & critical)
        wf_failed = sorted(failed_names - critical)

        if critical_failed:
            print(f"[ERROR] 致命的な失敗シナリオ: {critical_failed}", file=sys.stderr)
            sys.exit(1)
        elif args.strict and wf_failed:
            print(f"[ERROR] 失敗シナリオ（--strict）: {wf_failed}", file=sys.stderr)
            sys.exit(1)
        else:
            print(
                f"[WARN] 一部 WF シナリオ失敗（採択判断には影響なし）: {wf_failed}", file=sys.stderr
            )


if __name__ == "__main__":
    main()
