"""Phase 2 Group Y — TOPIX 騰落率ベースのレジーム検知強化検証 (Issue #392)

Issue #388 分析より、2021〜2023 年の 3 年連続マイナスの一因が「レジーム変化
（横ばい・小幅下落相場）への非適合」であることが判明した。全 IS/OOS 分割で
OOS がマイナスという事実が示すように、IS（2017-2020）と OOS（2021-2023）で
市場環境が大きく異なる。

本スクリプトでは TOPIX の N 日騰落率が閾値を下回る日に BUY を全件抑制する
新パラメータ（topix_return_bear_period / topix_return_bear_threshold）を検証する。
この機能は既存の MA クロスベアガード（MA75 < MA200 → size_multiplier=0）より
短期の下落に素早く反応できる点が特徴。

ベース: V1_score（score_drop_atr_gate=1.0 + U1_t4設定）
シナリオ:
  Y0_ref    : V1 のみ（Group V 採択設定、レジームフィルターなし）
  Y1_20d_m3 : V1 + TOPIX 20日騰落率 < -3% → BUY 抑制
  Y2_20d_m5 : V1 + TOPIX 20日騰落率 < -5% → BUY 抑制
  Y3_10d_m3 : V1 + TOPIX 10日騰落率 < -3% → BUY 抑制（短期反応）
  Y4_ma_bear: V1 + MA クロスベアガード（weak=0.5, strong=0.0）← 既存機能との比較

Phase 2 採択基準:
  CAGR  > 8%
  Sharpe > 0.5
  MaxDD  < 25%
  PF     > 1.1

Usage:
    python backtest/backtest_improvement_plan/run_phase2_group_y.py
    python backtest/backtest_improvement_plan/run_phase2_group_y.py --workers 4
"""

from __future__ import annotations

import argparse
import csv
import json
import os
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
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase2_group_y"

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
    "topix_vol_low_threshold": 0.12,
    "adaptive_threshold_hi": 0.62,
    "dynamic_trailing_stop": True,
    "trail_profit_gate_atr": 1.5,
    "trail_stage2_mult": 1.8,
    "trail_stage3_mult": 1.5,
    "quality_score_min": -0.30,
    "score_drop_atr_gate": 1.0,  # V1 採択済み
    "start": "2017-01-01",
    "end": "2025-12-31",
}

# V1_score（Group V 採択）の参照値
_IS_CAGR = 0.1380
_IS_SHARPE = 0.631
_IS_MAX_DD = 0.2376
_IS_PF = 1.591

_CAGR_MIN = 0.08
_SHARPE_MIN = 0.5
_DD_MAX = 0.25
_PF_MIN = 1.1

_SCENARIOS: list[dict] = [
    {
        "name": "Y0_ref",
        "group": "Y",
        "topix_return_bear_period": None,
        "topix_return_bear_threshold": None,
        "topix_size_multiplier_weak_bear": None,
        "topix_size_multiplier_strong_bear": None,
        "desc": "V1_score 参照（レジームフィルターなし）",
        "is_reference": True,
    },
    {
        "name": "Y1_20d_m3",
        "group": "Y",
        "topix_return_bear_period": 20,
        "topix_return_bear_threshold": -0.03,
        "topix_size_multiplier_weak_bear": None,
        "topix_size_multiplier_strong_bear": None,
        "desc": "V1 + TOPIX 20日騰落率 < -3% → BUY 抑制",
        "is_reference": False,
    },
    {
        "name": "Y2_20d_m5",
        "group": "Y",
        "topix_return_bear_period": 20,
        "topix_return_bear_threshold": -0.05,
        "topix_size_multiplier_weak_bear": None,
        "topix_size_multiplier_strong_bear": None,
        "desc": "V1 + TOPIX 20日騰落率 < -5% → BUY 抑制",
        "is_reference": False,
    },
    {
        "name": "Y3_10d_m3",
        "group": "Y",
        "topix_return_bear_period": 10,
        "topix_return_bear_threshold": -0.03,
        "topix_size_multiplier_weak_bear": None,
        "topix_size_multiplier_strong_bear": None,
        "desc": "V1 + TOPIX 10日騰落率 < -3% → BUY 抑制（短期反応）",
        "is_reference": False,
    },
    {
        "name": "Y4_ma_bear",
        "group": "Y",
        "topix_return_bear_period": None,
        "topix_return_bear_threshold": None,
        "topix_size_multiplier_weak_bear": 0.5,
        "topix_size_multiplier_strong_bear": 0.0,
        "desc": "V1 + MA クロスベアガード（weak=0.5, strong=0.0）",
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
        str(com["weak_bear"] if scenario.get("topix_size_multiplier_weak_bear") is None
            else scenario["topix_size_multiplier_weak_bear"]),
        "--topix-size-multiplier-strong-bear",
        str(com["strong_bear"] if scenario.get("topix_size_multiplier_strong_bear") is None
            else scenario["topix_size_multiplier_strong_bear"]),
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
        "--output-format",
        "all",
        "--output-dir",
        str(output_dir),
    ]
    if scenario.get("topix_return_bear_period") is not None:
        cmd += ["--topix-return-bear-period", str(scenario["topix_return_bear_period"])]
    if scenario.get("topix_return_bear_threshold") is not None:
        cmd += ["--topix-return-bear-threshold", str(scenario["topix_return_bear_threshold"])]
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
                print(
                    f"[ERROR] {name}: exit {completed.returncode}",
                    file=sys.stderr,
                    flush=True,
                )
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
            "topix_return_bear_period": scenario.get("topix_return_bear_period"),
            "topix_return_bear_threshold": scenario.get("topix_return_bear_threshold"),
            "topix_size_multiplier_weak_bear": scenario.get("topix_size_multiplier_weak_bear"),
            "topix_size_multiplier_strong_bear": scenario.get("topix_size_multiplier_strong_bear"),
            "desc": scenario.get("desc", ""),
            "is_reference": scenario.get("is_reference", False),
            **{k: v for k, v in metrics.items()},
            "error": False,
        }
        results.append(record)
        print(
            f"[DONE] {name:<14}"
            f"  cagr={_pct(metrics.get('cagr')):>8}"
            f"  sharpe={_fmt(metrics.get('sharpe'), 3):>6}"
            f"  dd={_pct(metrics.get('max_drawdown')):>8}"
            f"  pf={_fmt(metrics.get('profit_factor'), 3):>6}"
            f"  trades={metrics.get('total_trades')}",
            flush=True,
        )
    return results


CSV_FIELDNAMES = [
    "name",
    "group",
    "topix_return_bear_period",
    "topix_return_bear_threshold",
    "topix_size_multiplier_weak_bear",
    "topix_size_multiplier_strong_bear",
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
        description="Phase 2 Group Y — TOPIX 騰落率ベースのレジーム検知強化検証"
    )
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()
    workers = args.workers or DEFAULT_WORKERS

    db_path = _get_db_path()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ARTIFACTS_ROOT / ts
    output_dir.mkdir(parents=True, exist_ok=True)

    scenarios_path = output_dir / "scenarios.json"
    scenarios_path.write_text(
        json.dumps(_SCENARIOS, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[INFO] Group Y バックテスト開始  workers={workers}  出力={output_dir}")
    print(
        f"[INFO] ベース(V1_score): CAGR={_IS_CAGR:.2%}  Sharpe={_IS_SHARPE}  MaxDD={_IS_MAX_DD:.2%}"
    )

    n = len(_SCENARIOS)
    batches = [_SCENARIOS[i::workers] for i in range(workers)]
    batch_args = [(str(db_path), b, str(output_dir), str(REPO_ROOT)) for b in batches if b]

    all_results: list[dict] = []
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

    all_results.sort(
        key=lambda r: (
            _SCENARIOS.index(next(s for s in _SCENARIOS if s["name"] == r["name"]))
            if not r.get("error")
            else 999
        )
    )

    csv_path = output_dir / "results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(r for r in all_results if not r.get("error"))

    ok = [r for r in all_results if not r.get("error") and _meets_all(r)]
    ref = next((r for r in all_results if r.get("is_reference")), None)
    best = max(ok, key=lambda r: r.get("sharpe") or 0) if ok else None

    verdict = (
        "ADOPTED"
        if ok
        else (
            "IMPROVED"
            if any((r.get("sharpe") or 0) > _IS_SHARPE for r in all_results if not r.get("error"))
            else "NO_IMPROVEMENT"
        )
    )

    decision = {
        "verdict": verdict,
        "best_scenario": best["name"] if best else None,
        "adopted_scenarios": [r["name"] for r in ok],
        "reference_scenario": ref["name"] if ref else None,
        "best_cagr": best["cagr"] if best else None,
        "best_sharpe": best["sharpe"] if best else None,
        "best_max_drawdown": best["max_drawdown"] if best else None,
        "best_profit_factor": best["profit_factor"] if best else None,
    }
    (output_dir / "decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n{'=' * 65}")
    print(f"結果サマリ  verdict={verdict}  ({n} シナリオ中 {len(ok)} 件採択基準達成)")
    print(f"{'=' * 65}")
    header = f"{'シナリオ':<16}  {'CAGR':>8}  {'Sharpe':>7}  {'MaxDD':>7}  {'PF':>6}  {'Trades':>7}"
    print(header)
    print("-" * 60)
    for r in all_results:
        if r.get("error"):
            print(f"  {r['name']:<14}  ERROR")
            continue
        mark = " *" if _meets_all(r) else ("  ref" if r.get("is_reference") else "")
        print(
            f"  {r['name']:<14}"
            f"  {_pct(r.get('cagr')):>8}"
            f"  {_fmt(r.get('sharpe'), 3):>7}"
            f"  {_pct(r.get('max_drawdown')):>7}"
            f"  {_fmt(r.get('profit_factor'), 3):>6}"
            f"  {r.get('total_trades') or 'NA':>7}"
            f"{mark}"
        )
    print(f"\n出力: {output_dir}")


if __name__ == "__main__":
    main()
