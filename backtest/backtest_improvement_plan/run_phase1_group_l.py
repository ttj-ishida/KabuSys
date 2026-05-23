"""Phase 1 Group L バックテスト（動的 Utilization: ボラティリティターゲティング）

I1 設定（CAGR 7.72%、Max DD 24.96%、PF 1.297、Sharpe 0.382）のベース上で、
ポートフォリオ実現ボラティリティに基づき max_utilization を動的調整し、
年次リターンのばらつき（主に 2018 年の +64%）を緩和して Sharpe を改善する。

固定設定（全シナリオ共通・I1 と同一）:
  max_utilization : 0.30
  use_ma200_filter: True
  threshold       : 0.58
  max_holding_days: 60 日
  trailing_stop_atr: 2.0
  stop_loss_pct   : 0.09
  dd_stop         : 12%（dd_timeout=30 日）
  期間            : 2017-01-01〜2025-12-31

Group L シナリオ:
  L0_i1_ref : vol_target なし（I1 完全再現・参照用）
  L1        : vol_target=10%, vol_floor=10%
  L2        : vol_target=10%, vol_floor=15%
  L3        : vol_target=15%, vol_floor=10%
  L4        : vol_target=15%, vol_floor=15%
  L5        : vol_target=20%, vol_floor=10%
  L6        : vol_target=20%, vol_floor=15%

Usage:
    python backtest/backtest_improvement_plan/run_phase1_group_l.py
    python backtest/backtest_improvement_plan/run_phase1_group_l.py --workers 4
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
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase1_group_l"

# ---------------------------------------------------------------------------
# 共通パラメータ（全シナリオ固定・I1 と同一）
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
# Group L シナリオ定義
# ---------------------------------------------------------------------------

_GROUP_L: list[dict] = [
    {
        "name": "L0_i1_ref",
        "group": "L",
        "vol_target": None,
        "vol_floor": None,
        "desc": "I1 完全再現（参照・動的 util なし）",
    },
    {
        "name": "L1",
        "group": "L",
        "vol_target": 0.10,
        "vol_floor": 0.10,
        "desc": "vol_target=10%, vol_floor=10%（最積極的縮小）",
    },
    {
        "name": "L2",
        "group": "L",
        "vol_target": 0.10,
        "vol_floor": 0.15,
        "desc": "vol_target=10%, vol_floor=15%",
    },
    {
        "name": "L3",
        "group": "L",
        "vol_target": 0.15,
        "vol_floor": 0.10,
        "desc": "vol_target=15%, vol_floor=10%（中程度の縮小）",
    },
    {
        "name": "L4",
        "group": "L",
        "vol_target": 0.15,
        "vol_floor": 0.15,
        "desc": "vol_target=15%, vol_floor=15%",
    },
    {
        "name": "L5",
        "group": "L",
        "vol_target": 0.20,
        "vol_floor": 0.10,
        "desc": "vol_target=20%, vol_floor=10%（穏やかな縮小）",
    },
    {
        "name": "L6",
        "group": "L",
        "vol_target": 0.20,
        "vol_floor": 0.15,
        "desc": "vol_target=20%, vol_floor=15%（最保守的調整）",
    },
]

ALL_SCENARIOS: list[dict] = _GROUP_L

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
        "--output-format",
        "all",
        "--output-dir",
        str(output_dir),
    ]
    if _COM.get("use_ma200_filter"):
        cmd.append("--ma200-filter")

    if scenario.get("vol_target") is not None:
        cmd += ["--vol-target", str(scenario["vol_target"])]
        cmd += ["--vol-floor", str(scenario["vol_floor"])]

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


def _format_vol(scenario: dict) -> str:
    if scenario.get("vol_target") is None:
        return "fixed"
    return f"tgt={scenario['vol_target']:.0%} fl={scenario['vol_floor']:.0%}"


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
            "vol_target": scenario.get("vol_target", ""),
            "vol_floor": scenario.get("vol_floor", ""),
            "desc": scenario.get("desc", ""),
            **metrics,
            "error": False,
        }
        results.append(record)

        vol_str = _format_vol(scenario)
        print(
            f"[DONE] {name:<12} {vol_str:<22}"
            f"cagr={_fmt(metrics.get('cagr'), 4)}\t"
            f"sharpe={_fmt(metrics.get('sharpe'), 3)}\t"
            f"dd={_fmt(metrics.get('max_drawdown'), 4)}\t"
            f"trades={metrics.get('total_trades')}",
            flush=True,
        )

    return results


# ---------------------------------------------------------------------------
# 採択判断
# ---------------------------------------------------------------------------

_CAGR_MIN = 0.05
_DD_MAX = 0.25
_PF_MIN = 1.1
_SHARPE_MIN = 0.5


def _all_criteria(r: dict) -> bool:
    try:
        return (
            r.get("cagr") not in (None, "")
            and float(r["cagr"]) > _CAGR_MIN
            and r.get("max_drawdown") not in (None, "")
            and float(r["max_drawdown"]) < _DD_MAX
            and r.get("profit_factor") not in (None, "")
            and float(r["profit_factor"]) > _PF_MIN
            and r.get("sharpe") not in (None, "")
            and float(r["sharpe"]) > _SHARPE_MIN
        )
    except (ValueError, TypeError):
        return False


def _print_annual_comparison(output_dir: Path, l0: dict, best: dict) -> None:
    """L0 と最良シナリオの年次リターンを summary.json から取得して比較表出力"""

    def load_annual(scenario_name: str) -> dict[int, float]:
        candidates = list(output_dir.glob(f"{scenario_name}/report/*/summary.json"))
        if not candidates:
            return {}
        path = max(candidates, key=lambda p: p.stat().st_mtime)
        data = json.loads(path.read_text(encoding="utf-8"))
        by_year: dict[int, list[float]] = {}
        for m in data.get("performance", {}).get("monthly_returns", []):
            yr = m["year"]
            by_year.setdefault(yr, []).append(float(m["return_pct"]))
        annual: dict[int, float] = {}
        for yr, months in by_year.items():
            r = 1.0
            for m in months:
                r *= 1.0 + m / 100.0
            annual[yr] = (r - 1.0) * 100.0
        return annual

    l0_annual = load_annual(l0["name"])
    best_annual = load_annual(best["name"])

    if not l0_annual or not best_annual:
        return

    years = sorted(set(l0_annual) | set(best_annual))
    print(f"\n--- 年次リターン比較: {l0['name']} vs {best['name']} ---")
    print(f"{'年':>6}  {'L0_i1_ref':>12}  {best['name']:>12}  {'差':>8}")
    print("-" * 46)
    for yr in years:
        v0 = l0_annual.get(yr, 0.0)
        vb = best_annual.get(yr, 0.0)
        diff = vb - v0
        print(f"{yr:>6}  {v0:>11.2f}%  {vb:>11.2f}%  {diff:>+7.2f}%")


# ---------------------------------------------------------------------------
# CSV フィールド定義
# ---------------------------------------------------------------------------

CSV_FIELDNAMES = [
    "name",
    "group",
    "vol_target",
    "vol_floor",
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

# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 1 Group L バックテスト（動的 Utilization: ボラティリティターゲティング）"
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
        print("\n--- Group L: 動的 Utilization 検証結果 ---")
        print(
            f"{'name':<12} {'vol_setting':<22}"
            f" {'cagr':>8} {'sharpe':>7} {'max_dd':>8} {'pf':>6} {'trades':>7}  desc"
        )
        print("-" * 100)
        for r in success:
            adopted = _all_criteria(r)
            marker = " ★採択候補" if adopted else ""
            vol_str = (
                "fixed"
                if r.get("vol_target") in (None, "")
                else f"tgt={float(r['vol_target']):.0%} fl={float(r['vol_floor']):.0%}"
            )
            print(
                f"{r['name']:<12}"
                f" {vol_str:<22}"
                f" {_fmt(r.get('cagr'), 4):>8}"
                f" {_fmt(r.get('sharpe'), 3):>7}"
                f" {_fmt(r.get('max_drawdown'), 4):>8}"
                f" {_fmt(r.get('profit_factor'), 3):>6}"
                f" {str(r.get('total_trades', '')):>7}"
                f"  {r.get('desc', '')}{marker}"
            )

        # 採択判断
        print("\n採択判断:")
        i1_sharpe = 0.382
        adopted_all = [r for r in success if _all_criteria(r)]
        l0 = next((r for r in success if r["name"] == "L0_i1_ref"), None)
        non_l0 = [r for r in success if r["name"] != "L0_i1_ref" and not r.get("error")]

        if adopted_all:
            best = max(
                adopted_all,
                key=lambda r: float(r["sharpe"]) if r.get("sharpe") not in (None, "") else 0.0,
            )
            print(
                f"  → {best['name']} が全採用基準（CAGR>5%, MaxDD<25%, PF>1.1, Sharpe>0.5）を達成: Phase 1 改良版として採用"
            )
            if l0:
                _print_annual_comparison(output_dir, l0, best)
        else:
            improved = [
                r
                for r in non_l0
                if r.get("sharpe") not in (None, "")
                and float(r["sharpe"]) > i1_sharpe
            ]
            if improved:
                best = max(improved, key=lambda r: float(r["sharpe"]))
                print(
                    f"  → Sharpe>0.5 達成なし。{best['name']} が I1（{i1_sharpe}）を上回る"
                    f" Sharpe={_fmt(best.get('sharpe'), 3)} を達成。Phase 2 設計の参考として記録 → I1 継続採用"
                )
                if l0:
                    _print_annual_comparison(output_dir, l0, best)
            else:
                print(
                    "  → 全シナリオで Sharpe が I1（0.382）以下。動的 utilization の効果なし。"
                    " Group M（シグナル強度ベースサイジング）へ進む"
                )

    if failed:
        print(f"\n失敗したシナリオ: {[r['name'] for r in failed]}")


if __name__ == "__main__":
    main()
