"""Phase 1 A3設定 Max DD 改善バックテスト（Group G）

A3 設定（CAGR +9.05%、Profit Factor 1.23）の強みを維持しながら
Max Drawdown 40.3% を採択基準 25% 未満に引き下げるための感度分析。

固定設定: Bear Guard=OFF（weak=1.0/strong=1.0）, 期間 2017〜2025

Group G シナリオ:
  G1_a3_ref      : A3 参照 (pos=3, util=0.50, dd=12%, sl=9%, thr=0.58)
  G2_util40      : 利用率を 40% に下げる
  G3_util30      : 利用率を 30% に下げる
  G4_dd_08       : DD ストップを 8% に厳格化
  G5_dd_10       : DD ストップを 10% に厳格化
  G6_pos2        : ポジション数を 2 に減らす
  G7_stoploss7   : ストップロスを 7% に絞る
  G8_threshold62 : BUY 閾値を 0.62 に上げる（選球眼）
  G9_combined    : 複合（util=0.40, dd=10%, sl=7%, thr=0.62）

読み方:
  各パラメータ変更が CAGR と Max DD にどう影響するかのトレードオフを確認。
  CAGR > 5% かつ Max DD < 25% を両立する設定を探す。

Usage:
    python backtest/backtest_improvement_plan/run_phase1_a3_maxdd.py
    python backtest/backtest_improvement_plan/run_phase1_a3_maxdd.py --workers 5
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
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest_phase1_a3_maxdd"

# ---------------------------------------------------------------------------
# 共通パラメータ（Bear Guard は全シナリオで OFF 固定）
# ---------------------------------------------------------------------------

_COM = {
    "cash": 1_000_000,
    "allocation_method": "equal",
    "trailing_stop_atr": 2.0,
    "max_holding_days": 60,
    "max_position_pct": 0.22,
    "risk_pct": 0.005,
    "dd_timeout": 30,
    "start": "2017-01-01",
    "end": "2025-12-31",
    # Bear Guard は全シナリオで OFF
    "weak_bear": 1.00,
    "strong_bear": 1.00,
}

# ---------------------------------------------------------------------------
# Group G シナリオ定義
# ---------------------------------------------------------------------------

_GROUP_G: list[dict] = [
    {
        "name": "G1_a3_ref",
        "group": "G",
        "max_positions": 3,
        "max_utilization": 0.50,
        "dd_stop": 0.12,
        "stop_loss_pct": 0.09,
        "threshold": 0.58,
        "desc": "A3 参照",
    },
    {
        "name": "G2_util40",
        "group": "G",
        "max_positions": 3,
        "max_utilization": 0.40,
        "dd_stop": 0.12,
        "stop_loss_pct": 0.09,
        "threshold": 0.58,
        "desc": "利用率 40%",
    },
    {
        "name": "G3_util30",
        "group": "G",
        "max_positions": 3,
        "max_utilization": 0.30,
        "dd_stop": 0.12,
        "stop_loss_pct": 0.09,
        "threshold": 0.58,
        "desc": "利用率 30%",
    },
    {
        "name": "G4_dd_08",
        "group": "G",
        "max_positions": 3,
        "max_utilization": 0.50,
        "dd_stop": 0.08,
        "stop_loss_pct": 0.09,
        "threshold": 0.58,
        "desc": "DD ストップ 8%",
    },
    {
        "name": "G5_dd_10",
        "group": "G",
        "max_positions": 3,
        "max_utilization": 0.50,
        "dd_stop": 0.10,
        "stop_loss_pct": 0.09,
        "threshold": 0.58,
        "desc": "DD ストップ 10%",
    },
    {
        "name": "G6_pos2",
        "group": "G",
        "max_positions": 2,
        "max_utilization": 0.50,
        "dd_stop": 0.12,
        "stop_loss_pct": 0.09,
        "threshold": 0.58,
        "desc": "ポジション数 2",
    },
    {
        "name": "G7_stoploss7",
        "group": "G",
        "max_positions": 3,
        "max_utilization": 0.50,
        "dd_stop": 0.12,
        "stop_loss_pct": 0.07,
        "threshold": 0.58,
        "desc": "ストップロス 7%",
    },
    {
        "name": "G8_threshold62",
        "group": "G",
        "max_positions": 3,
        "max_utilization": 0.50,
        "dd_stop": 0.12,
        "stop_loss_pct": 0.09,
        "threshold": 0.62,
        "desc": "閾値 0.62（選球眼向上）",
    },
    {
        "name": "G9_combined",
        "group": "G",
        "max_positions": 3,
        "max_utilization": 0.40,
        "dd_stop": 0.10,
        "stop_loss_pct": 0.07,
        "threshold": 0.62,
        "desc": "複合（util=0.40, dd=10%, sl=7%, thr=0.62）",
    },
]

ALL_SCENARIOS: list[dict] = _GROUP_G

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
        str(scenario["max_positions"]),
        "--max-position-pct",
        str(_COM["max_position_pct"]),
        "--max-utilization",
        str(scenario["max_utilization"]),
        "--risk-pct",
        str(_COM["risk_pct"]),
        "--stop-loss-pct",
        str(scenario["stop_loss_pct"]),
        "--min-holding-days",
        "5",
        "--max-holding-days",
        str(_COM["max_holding_days"]),
        "--trailing-stop-atr",
        str(_COM["trailing_stop_atr"]),
        "--threshold",
        str(scenario["threshold"]),
        "--topix-size-multiplier-weak-bear",
        str(_COM["weak_bear"]),
        "--topix-size-multiplier-strong-bear",
        str(_COM["strong_bear"]),
        "--portfolio-drawdown-stop",
        str(scenario["dd_stop"]),
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
            "max_positions": scenario["max_positions"],
            "max_utilization": scenario["max_utilization"],
            "dd_stop": scenario["dd_stop"],
            "stop_loss_pct": scenario["stop_loss_pct"],
            "threshold": scenario["threshold"],
            "desc": scenario.get("desc", ""),
            **metrics,
            "error": False,
        }
        results.append(record)

        print(
            f"[DONE] {name}\t"
            f"util={scenario['max_utilization']:.2f} dd={scenario['dd_stop']:.2f} "
            f"sl={scenario['stop_loss_pct']:.2f} thr={scenario['threshold']:.2f}\t"
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
    "max_positions",
    "max_utilization",
    "dd_stop",
    "stop_loss_pct",
    "threshold",
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
        description="Phase 1 A3設定 Max DD 改善バックテスト（Group G）"
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
    print("-" * 90)

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

    print("-" * 90)
    print(f"\n完了: {datetime.now().strftime('%H:%M:%S')}")
    print(f"成功: {len(success)} / {len(scenarios)}, 失敗: {len(failed)}")
    print(f"results_csv={results_csv}")

    if success:
        print("\n--- Group G: A3設定 Max DD 改善結果 ---")
        print(
            f"{'name':<20} {'pos':>4} {'util':>5} {'dd':>5} {'sl':>5} {'thr':>5}"
            f" {'cagr':>8} {'sharpe':>7} {'max_dd':>8} {'pf':>6} {'trades':>7}  desc"
        )
        print("-" * 105)
        for r in success:
            print(
                f"{r['name']:<20}"
                f" {r.get('max_positions', ''):>4}"
                f" {_fmt(r.get('max_utilization'), 2):>5}"
                f" {_fmt(r.get('dd_stop'), 2):>5}"
                f" {_fmt(r.get('stop_loss_pct'), 2):>5}"
                f" {_fmt(r.get('threshold'), 2):>5}"
                f" {_fmt(r.get('cagr'), 4):>8}"
                f" {_fmt(r.get('sharpe'), 3):>7}"
                f" {_fmt(r.get('max_drawdown'), 4):>8}"
                f" {_fmt(r.get('profit_factor'), 3):>6}"
                f" {str(r.get('total_trades', '')):>7}"
                f"  {r.get('desc', '')}"
            )

    if failed:
        print("\n--- 失敗シナリオ ---")
        for r in failed:
            print(f"  {r['name']}")


if __name__ == "__main__":
    main()
