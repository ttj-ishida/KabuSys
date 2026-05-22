"""Phase 1 Bear Guard 閾値グリッドバックテスト（Group E）

TOPIX MA クロスベアガード（Layer 2）の weak_bear / strong_bear を
8段階でグリッドサーチし、どの閾値組み合わせが最良か定量化する。

固定設定: max_positions=3, utilization=0.50, DD stop=12%, 期間 2017〜2025

Group E シナリオ:
  E1_current        : weak=0.50, strong=0.00 （現行 A4 と同じ）
  E2_soften_strong  : weak=0.50, strong=0.25 （強ベア完全停止を緩和）
  E3_soften_weak    : weak=0.75, strong=0.00 （弱ベア縮小を緩和）
  E4_both_soften    : weak=0.75, strong=0.25 （両方を緩和）
  E5_no_hard_stop   : weak=1.00, strong=0.00 （強ベアの完全停止のみ廃止）
  E6_strong_only_soft: weak=1.00, strong=0.25 （強ベア時のみ軽微縮小）
  E7_minimal        : weak=1.00, strong=0.50 （最小限の縮小のみ）
  E8_off            : weak=1.00, strong=1.00 （OFF、A3 と同じ）

Usage:
    python backtest/backtest_improvement_plan/run_phase1_bg_sensitivity.py
    python backtest/backtest_improvement_plan/run_phase1_bg_sensitivity.py --workers 4
"""

from __future__ import annotations

import argparse
import csv
import json
import locale
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

SUBPROCESS_ENCODING = locale.getpreferredencoding(False) or "cp932"
DEFAULT_WORKERS = 5


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "config" / "strategy_config.yaml").exists():
            return candidate
    raise FileNotFoundError("config/strategy_config.yaml が見つかりません")


REPO_ROOT = _find_repo_root()
ENV_PATH = REPO_ROOT / ".env"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest_phase1_bg_sensitivity"

# ---------------------------------------------------------------------------
# 共通パラメータ
# ---------------------------------------------------------------------------

_COM = {
    "cash": 1_000_000,
    "allocation_method": "equal",
    "threshold": 0.58,
    "stop_loss_pct": 0.09,
    "trailing_stop_atr": 2.0,
    "max_holding_days": 60,
    "max_position_pct": 0.22,
    "risk_pct": 0.005,
    "dd_timeout": 30,
    # Group E 固定値
    "max_positions": 3,
    "max_utilization": 0.50,
    "dd_stop": 0.12,
    "start": "2017-01-01",
    "end": "2025-12-31",
}

# ---------------------------------------------------------------------------
# Group E シナリオ定義
# ---------------------------------------------------------------------------

_GROUP_E: list[dict] = [
    {
        "name": "E1_current",
        "group": "E",
        "weak_bear": 0.50,
        "strong_bear": 0.00,
        "desc": "現行 A4（参照）",
    },
    {
        "name": "E2_soften_strong",
        "group": "E",
        "weak_bear": 0.50,
        "strong_bear": 0.25,
        "desc": "強ベア完全停止を緩和",
    },
    {
        "name": "E3_soften_weak",
        "group": "E",
        "weak_bear": 0.75,
        "strong_bear": 0.00,
        "desc": "弱ベア縮小を緩和",
    },
    {
        "name": "E4_both_soften",
        "group": "E",
        "weak_bear": 0.75,
        "strong_bear": 0.25,
        "desc": "両方を緩和",
    },
    {
        "name": "E5_no_hard_stop",
        "group": "E",
        "weak_bear": 1.00,
        "strong_bear": 0.00,
        "desc": "強ベアの完全停止のみ廃止",
    },
    {
        "name": "E6_strong_only_soft",
        "group": "E",
        "weak_bear": 1.00,
        "strong_bear": 0.25,
        "desc": "強ベア時のみ軽微縮小",
    },
    {
        "name": "E7_minimal",
        "group": "E",
        "weak_bear": 1.00,
        "strong_bear": 0.50,
        "desc": "最小限の縮小のみ",
    },
    {
        "name": "E8_off",
        "group": "E",
        "weak_bear": 1.00,
        "strong_bear": 1.00,
        "desc": "OFF（A3 と同じ）参照",
    },
]

ALL_SCENARIOS: list[dict] = _GROUP_E

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
        str(scenario["weak_bear"]),
        "--topix-size-multiplier-strong-bear",
        str(scenario["strong_bear"]),
        "--portfolio-drawdown-stop",
        str(_COM["dd_stop"]),
        "--portfolio-drawdown-stop-timeout",
        str(_COM["dd_timeout"]),
        "--output-format",
        "all",
        "--output-dir",
        str(output_dir),
    ]
    return cmd


def _read_summary(report_dir: Path) -> dict:
    summaries = list(report_dir.glob("*/summary.json"))
    if not summaries:
        raise FileNotFoundError(f"summary.json が見つかりません: {report_dir}")
    data = json.loads(summaries[0].read_text(encoding="utf-8"))
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

        completed = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding=SUBPROCESS_ENCODING,
            errors="replace",
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
            "weak_bear": scenario["weak_bear"],
            "strong_bear": scenario["strong_bear"],
            "desc": scenario.get("desc", ""),
            **metrics,
            "error": False,
        }
        results.append(record)

        print(
            f"[DONE] {name}\t"
            f"weak={scenario['weak_bear']:.2f} strong={scenario['strong_bear']:.2f}\t"
            f"cagr={_fmt(metrics.get('cagr'), 4)}\t"
            f"sharpe={_fmt(metrics.get('sharpe'), 3)}\t"
            f"dd={_fmt(metrics.get('max_drawdown'), 4)}\t"
            f"trades={metrics.get('total_trades')}",
            flush=True,
        )

    return results


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

CSV_FIELDNAMES = [
    "name",
    "group",
    "weak_bear",
    "strong_bear",
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
        description="Phase 1 Bear Guard 閾値グリッドバックテスト（Group E）"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"並列ワーカー数（デフォルト: {DEFAULT_WORKERS}）",
    )
    args = parser.parse_args()

    scenarios = ALL_SCENARIOS
    n_workers = min(args.workers, len(scenarios))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ARTIFACTS_ROOT / stamp
    output_dir.mkdir(parents=True, exist_ok=True)

    source_db = _get_db_path()
    snapshots_dir = output_dir / "_snapshots"
    snapshots_dir.mkdir()

    print(f"output_dir={output_dir}")
    print(f"scenarios={len(scenarios)}, workers={n_workers}")
    print(f"source_db={source_db}")
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
    print("-" * 80)

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(_run_batch, ba): i for i, ba in enumerate(batch_args)}
        for future in as_completed(futures):
            worker_idx = futures[future]
            try:
                batch_results = future.result()
                all_results.extend(batch_results)
            except Exception as exc:
                print(f"[ERROR] worker {worker_idx} で例外: {exc}", file=sys.stderr)

    all_results.sort(key=lambda r: r.get("name", ""))

    success = [r for r in all_results if not r.get("error")]
    failed = [r for r in all_results if r.get("error")]

    with results_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(success)

    with results_jsonl.open("w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("-" * 80)
    print(f"\n完了: {datetime.now().strftime('%H:%M:%S')}")
    print(f"成功: {len(success)} / {len(scenarios)}, 失敗: {len(failed)}")
    print(f"results_csv={results_csv}")

    if success:
        print("\n--- Group E: Bear Guard 閾値グリッド結果 ---")
        print(
            f"{'name':<24} {'weak':>6} {'strong':>7} {'cagr':>8} {'sharpe':>7} {'max_dd':>8} {'pf':>6} {'trades':>7}"
        )
        print("-" * 80)
        for r in success:
            print(
                f"{r['name']:<24}"
                f" {r.get('weak_bear', ''):>6.2f}"
                f" {r.get('strong_bear', ''):>7.2f}"
                f" {_fmt(r.get('cagr'), 4):>8}"
                f" {_fmt(r.get('sharpe'), 3):>7}"
                f" {_fmt(r.get('max_drawdown'), 4):>8}"
                f" {_fmt(r.get('profit_factor'), 3):>6}"
                f" {str(r.get('total_trades', '')):>7}"
            )

    if failed:
        print("\n--- 失敗シナリオ ---")
        for r in failed:
            print(f"  {r['name']}")


if __name__ == "__main__":
    main()
