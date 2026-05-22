"""Phase 1 銘柄単位 MA200 フィルター検証バックテスト（Group H）

Group E・F・G の結果から TOPIX 指数ベアガードの閾値最適化だけでは採択基準に届かないことが
確認された（2026-05-20）。本スクリプトは TOPIX BG を完全 OFF とし、銘柄ごとの 200 日移動
平均フィルターに置き換えた場合の 9 年通算パフォーマンスを定量化する。

Group G・F の知見（util=30% が Max DD 最近接、threshold=0.62 が 2017 年問題を解消）を
組み込んだ複合設定 H5 が採択基準（CAGR>5%, Max DD<25%, PF>1.1）を同時達成できるか検証する。

固定設定（全シナリオ共通）:
  max_positions  : 3
  TOPIX BG       : OFF（weak=1.0 / strong=1.0）
  DD stop        : 12%（dd_timeout=30日）
  stop_loss      : 9%（Group F・G で変更の効果なしと判明）
  期間           : 2017-01-01〜2025-12-31

Group H シナリオ:
  H1_a3_ref               : util=50%, thr=0.58, ma200=OFF  A3 参照（= G1）
  H2_ma200_only           : util=50%, thr=0.58, ma200=ON   MA200 単体の寄与
  H3_util30_ma200         : util=30%, thr=0.58, ma200=ON   G3 知見（Max DD 最近接）+ MA200
  H4_thr62_ma200          : util=50%, thr=0.62, ma200=ON   F5 知見（2017年修正）+ MA200
  H5_util30_thr62_ma200   : util=30%, thr=0.62, ma200=ON   最有力複合設定

読み方:
  H1 → H2: MA200 フィルター単体の効果（CAGR/MDD トレードオフ）
  H2 → H3: util=30% との相乗効果（Max DD を 25% 以下に押し込めるか）
  H2 → H4: threshold=0.62 の 9 年通算効果（2017 年改善 vs 他年トレード数減少）
  H5 : CAGR>5% かつ Max DD<25% の同時達成を狙う最重要シナリオ

採択判断ロジック:
  H5 が採択基準を満たす → H5 設定を Phase 1 採用。Group I は不要
  H5 が未達            → Group I（銘柄 MA25/75 クロス実装）へ進む
  H2 で CAGR < 5%      → MA200 単体フィルターは効果薄。Group I へスキップ

Usage:
    python backtest/backtest_improvement_plan/run_phase1_stock_ma_filter.py
    python backtest/backtest_improvement_plan/run_phase1_stock_ma_filter.py --workers 5
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
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase1_ma200_filter"

# ---------------------------------------------------------------------------
# 共通パラメータ（全シナリオ固定）
# ---------------------------------------------------------------------------

_COM = {
    "cash": 1_000_000,
    "allocation_method": "equal",
    "trailing_stop_atr": 2.0,
    "max_holding_days": 60,
    "max_position_pct": 0.22,
    "risk_pct": 0.005,
    "max_positions": 3,
    "dd_stop": 0.12,
    "dd_timeout": 30,
    "stop_loss_pct": 0.09,
    # TOPIX BG は全シナリオで OFF
    "weak_bear": 1.00,
    "strong_bear": 1.00,
    "start": "2017-01-01",
    "end": "2025-12-31",
}

# ---------------------------------------------------------------------------
# Group H シナリオ定義
# ---------------------------------------------------------------------------

_GROUP_H: list[dict] = [
    {
        "name": "H1_a3_ref",
        "group": "H",
        "max_utilization": 0.50,
        "threshold": 0.58,
        "use_ma200_filter": False,
        "desc": "A3 参照（= G1。MA200 なし）",
    },
    {
        "name": "H2_ma200_only",
        "group": "H",
        "max_utilization": 0.50,
        "threshold": 0.58,
        "use_ma200_filter": True,
        "desc": "MA200 フィルター単体の寄与",
    },
    {
        "name": "H3_util30_ma200",
        "group": "H",
        "max_utilization": 0.30,
        "threshold": 0.58,
        "use_ma200_filter": True,
        "desc": "util=30%（G3 知見）+ MA200",
    },
    {
        "name": "H4_thr62_ma200",
        "group": "H",
        "max_utilization": 0.50,
        "threshold": 0.62,
        "use_ma200_filter": True,
        "desc": "threshold=0.62（F5 知見・2017年修正）+ MA200",
    },
    {
        "name": "H5_util30_thr62_ma200",
        "group": "H",
        "max_utilization": 0.30,
        "threshold": 0.62,
        "use_ma200_filter": True,
        "desc": "util=30% + threshold=0.62 + MA200（最有力複合）",
    },
]

ALL_SCENARIOS: list[dict] = _GROUP_H

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
        str(scenario["max_utilization"]),
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
        str(scenario["threshold"]),
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
    if scenario.get("use_ma200_filter"):
        cmd.append("--ma200-filter")
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
            "max_utilization": scenario["max_utilization"],
            "threshold": scenario["threshold"],
            "use_ma200_filter": scenario["use_ma200_filter"],
            "desc": scenario.get("desc", ""),
            **metrics,
            "error": False,
        }
        results.append(record)

        print(
            f"[DONE] {name}\t"
            f"util={scenario['max_utilization']:.2f} "
            f"thr={scenario['threshold']:.2f} "
            f"ma200={scenario['use_ma200_filter']}\t"
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
    "max_utilization",
    "threshold",
    "use_ma200_filter",
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
        description="Phase 1 銘柄単位 MA200 フィルター検証バックテスト（Group H）"
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
    print("-" * 100)

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

    print("-" * 100)
    print(f"\n完了: {datetime.now().strftime('%H:%M:%S')}")
    print(f"成功: {len(success)} / {len(scenarios)}, 失敗: {len(failed)}")
    print(f"results_csv={results_csv}")

    if success:
        print("\n--- Group H: 銘柄単位 MA200 フィルター結果 ---")
        print(
            f"{'name':<28} {'util':>5} {'thr':>5} {'ma200':>6}"
            f" {'cagr':>8} {'sharpe':>7} {'max_dd':>8} {'pf':>6} {'trades':>7}  desc"
        )
        print("-" * 100)
        for r in success:
            cagr_val = r.get("cagr")
            dd_val = r.get("max_drawdown")
            pf_val = r.get("profit_factor")
            adopted = (
                cagr_val is not None
                and cagr_val > 0.05
                and dd_val is not None
                and dd_val < 0.25
                and pf_val is not None
                and pf_val > 1.1
            )
            marker = " ★採択候補" if adopted else ""
            print(
                f"{r['name']:<28}"
                f" {_fmt(r.get('max_utilization'), 2):>5}"
                f" {_fmt(r.get('threshold'), 2):>5}"
                f" {str(r.get('use_ma200_filter', '')):>6}"
                f" {_fmt(r.get('cagr'), 4):>8}"
                f" {_fmt(r.get('sharpe'), 3):>7}"
                f" {_fmt(r.get('max_drawdown'), 4):>8}"
                f" {_fmt(r.get('profit_factor'), 3):>6}"
                f" {str(r.get('total_trades', '')):>7}"
                f"  {r.get('desc', '')}{marker}"
            )

        print("\n採択基準: CAGR>5%, Sharpe>0.5, Max DD<25%, PF>1.1")
        adopted_list = [
            r
            for r in success
            if (r.get("cagr") or 0) > 0.05
            and (r.get("max_drawdown") or 1) < 0.25
            and (r.get("profit_factor") or 0) > 1.1
        ]
        if adopted_list:
            print(f"★ 採択基準（CAGR/Max DD/PF）通過: {[r['name'] for r in adopted_list]}")
            print("  → Sharpe > 0.5 も確認して Phase 1 採用を検討してください")
        else:
            print("★ 採択基準（CAGR>5% かつ Max DD<25% かつ PF>1.1）を満たすシナリオなし")
            print("  → Group I（銘柄単位 MA25/75 クロス実装）への移行を検討してください")

    if failed:
        print("\n--- 失敗シナリオ ---")
        for r in failed:
            print(f"  {r['name']}")


if __name__ == "__main__":
    main()
