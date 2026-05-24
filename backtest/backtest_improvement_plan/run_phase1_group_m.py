"""Phase 1 Group M バックテスト（シグナル強度ベースサイジング検証）

I1 設定（CAGR 7.72%、Max DD 24.96%、PF 1.297、Sharpe 0.382）の Sharpe 改善を目的として、
allocation_method（equal/score）と max_positions（2/3）の組み合わせを検証する。

固定設定（全シナリオ共通）:
  max_utilization : 0.30
  use_ma200_filter: True
  max_holding_days: 60日
  trailing_stop_atr: 2.0
  threshold       : 0.58
  stop_loss       : 9%
  dd_stop         : 12%
  期間            : 2017-01-01〜2025-12-31

Group M シナリオ:
  M0_i1_ref    : equal / max_positions=3  (I1 完全再現・参照)
  M1_score     : score / max_positions=3  (スコア重み付けの純粋効果)
  M2_equal_pos2: equal / max_positions=2  (銘柄集中の純粋効果)
  M3_score_pos2: score / max_positions=2  (スコア重み × 集中の相乗効果)

Usage:
    python backtest/backtest_improvement_plan/run_phase1_group_m.py
    python backtest/backtest_improvement_plan/run_phase1_group_m.py --workers 4
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
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase1_group_m"

# ---------------------------------------------------------------------------
# 共通パラメータ（全シナリオ固定）
# ---------------------------------------------------------------------------

_COM = {
    "cash": 1_000_000,
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
    "start": "2017-01-01",
    "end": "2025-12-31",
}

# ---------------------------------------------------------------------------
# Group M シナリオ定義
# ---------------------------------------------------------------------------

_GROUP_M: list[dict] = [
    {
        "name": "M0_i1_ref",
        "group": "M",
        "allocation_method": "equal",
        "max_positions": 3,
        "desc": "I1 完全再現（参照・ベースライン）",
    },
    {
        "name": "M1_score",
        "group": "M",
        "allocation_method": "score",
        "max_positions": 3,
        "desc": "スコア重み付けの効果を分離",
    },
    {
        "name": "M2_equal_pos2",
        "group": "M",
        "allocation_method": "equal",
        "max_positions": 2,
        "desc": "銘柄集中（max_positions=2）の効果を分離",
    },
    {
        "name": "M3_score_pos2",
        "group": "M",
        "allocation_method": "score",
        "max_positions": 2,
        "desc": "スコア重み × 集中の相乗効果",
    },
]

ALL_SCENARIOS: list[dict] = _GROUP_M

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
        scenario["allocation_method"],
        "--max-positions",
        str(scenario["max_positions"]),
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
            "allocation_method": scenario["allocation_method"],
            "max_positions": scenario["max_positions"],
            "desc": scenario.get("desc", ""),
            **metrics,
            "error": False,
        }
        results.append(record)

        print(
            f"[DONE] {name:<20} alloc={scenario['allocation_method']:<6} pos={scenario['max_positions']}"
            f"  cagr={_fmt(metrics.get('cagr'), 4)}"
            f"  sharpe={_fmt(metrics.get('sharpe'), 3)}"
            f"  dd={_fmt(metrics.get('max_drawdown'), 4)}"
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
    "allocation_method",
    "max_positions",
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

_I1_SHARPE = 0.382
_SHARPE_TARGET = 0.5
_CAGR_MIN = 0.05
_DD_MAX = 0.25
_PF_MIN = 1.1


def _get_sharpe(r: dict) -> float:
    try:
        return float(r["sharpe"]) if r.get("sharpe") not in (None, "") else 0.0
    except (ValueError, TypeError):
        return 0.0


def _all_criteria(r: dict) -> bool:
    try:
        return (
            r.get("cagr") not in (None, "")
            and float(r["cagr"]) > _CAGR_MIN
            and r.get("max_drawdown") not in (None, "")
            and float(r["max_drawdown"]) < _DD_MAX
            and r.get("profit_factor") not in (None, "")
            and float(r["profit_factor"]) > _PF_MIN
            and _get_sharpe(r) > _SHARPE_TARGET
        )
    except (ValueError, TypeError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 1 Group M バックテスト（シグナル強度ベースサイジング検証）"
    )
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
        help="実行後もDBスナップショットを削除せず保持する（デフォルト: 削除）",
    )
    args = parser.parse_args()

    scenarios = ALL_SCENARIOS
    n_workers = min(args.workers, len(scenarios))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ARTIFACTS_ROOT / stamp
    output_dir.mkdir(parents=True, exist_ok=True)

    source_db = _get_db_path()
    if not source_db.exists():
        sys.exit(
            f"[ERROR] DuckDB が見つかりません: {source_db}. .env の DUCKDB_PATH を確認してください"
        )
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
    print("-" * 100)

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

    print("-" * 100)
    print(f"\n完了: {datetime.now().strftime('%H:%M:%S')}")
    print(f"成功: {len(success)} / {len(scenarios)}, 失敗: {len(failed)}")
    print(f"results_csv={results_csv}")

    if success:
        print("\n--- Group M: シグナル強度ベースサイジング検証結果 ---")
        print(
            f"{'name':<20} {'alloc':<7} {'pos':>4}"
            f"  {'cagr':>8} {'sharpe':>7} {'max_dd':>8} {'pf':>6} {'trades':>7}  desc"
        )
        print("-" * 100)
        for r in success:
            adopted = _all_criteria(r)
            marker = " ★採択候補" if adopted else ""
            print(
                f"{r['name']:<20}"
                f" {r.get('allocation_method', ''):<7}"
                f" {str(r.get('max_positions', '')):>4}"
                f"  {_fmt(r.get('cagr'), 4):>8}"
                f"  {_fmt(r.get('sharpe'), 3):>7}"
                f"  {_fmt(r.get('max_drawdown'), 4):>8}"
                f"  {_fmt(r.get('profit_factor'), 3):>6}"
                f"  {str(r.get('total_trades', '')):>7}"
                f"  {r.get('desc', '')}{marker}"
            )

        print("\n採択判断:")
        adopted_scenarios = [r for r in success if _all_criteria(r)]
        if adopted_scenarios:
            best = max(adopted_scenarios, key=_get_sharpe)
            print(
                f"  → {best['name']} が全採用基準（Sharpe>{_SHARPE_TARGET}, "
                f"CAGR>{_CAGR_MIN * 100:.0f}%, MaxDD<{_DD_MAX * 100:.0f}%, PF>{_PF_MIN}）を達成: 採用"
            )
        else:
            improved = [
                r for r in success if r["name"] != "M0_i1_ref" and _get_sharpe(r) > _I1_SHARPE
            ]
            if improved:
                best_imp = max(improved, key=_get_sharpe)
                print(
                    f"  → Sharpe>{_SHARPE_TARGET} 達成なし。"
                    f"{best_imp['name']} が I1 を上回る Sharpe={_fmt(best_imp.get('sharpe'), 3)} を達成。"
                    "Phase 2 設計の参考として記録 → I1 継続採用"
                )
            else:
                print(
                    f"  → 全シナリオで Sharpe ≤ {_I1_SHARPE}（I1 以下）。"
                    "スコア重み付け・銘柄集中いずれも効果なし → Group N へ進む"
                )

    if failed:
        print(f"\n失敗したシナリオ: {[r['name'] for r in failed]}")


if __name__ == "__main__":
    main()
