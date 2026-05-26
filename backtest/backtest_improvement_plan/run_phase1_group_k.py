"""Phase 1 Group K バックテスト（I1 弱点克服フィルター検証）

I1 設定（CAGR 7.72%、Max DD 24.96%、PF 1.297、Sharpe 0.382）の弱点を克服するため、
以下の新規フィルターを単体・複合で検証する:
  - RSI 売られすぎフィルター（rsi_14 <= 40）
  - クオリティスコアフィルター（quality_score >= -0.5）
  - 出来高ブレイクアウトフィルター（volume_ratio >= 1.2）
  - TOPIX 相対強度フィルター（topix_rel_20 >= -0.10）
  - アダプティブ閾値（TOPIX が MA200 +5% 超で threshold を 0.62 に引き上げ）

固定設定（全シナリオ共通）:
  max_utilization : 0.30
  use_ma200_filter: True
  stock_MA_cross  : OFF
  max_positions   : 3
  TOPIX BG        : OFF（weak=1.0 / strong=1.0）
  DD stop         : 12%（dd_timeout=30日）
  stop_loss       : 9%
  max_holding_days: 60日
  trailing_stop_atr: 2.0
  threshold       : 0.58（一部シナリオはアダプティブで 0.62 に切り替わる）
  期間            : 2017-01-01〜2025-12-31

Group K シナリオ:
  K1_i1_ref         : フィルターなし（I1 完全再現）
  K2_rsi_oversold   : RSI <= 40 のみ（売られすぎ確認）
  K3_quality        : quality_score >= -0.5
  K4_volume         : volume_ratio >= 1.2（出来高ブレイクアウト）
  K5_topix_rel      : topix_rel_20 >= -0.10（TOPIX 相対強度）
  K6_adaptive_thr   : アダプティブ閾値（TOPIX MA200 +5% で 0.62）
  K7_rsi_quality    : K2 + K3 複合
  K8_rsi_quality_vol: K2 + K3 + K4 複合（最有力候補）
  K9_adaptive_rsi   : K6 + K2 複合（強気相場でシグナル精度 + 逆張り確認）

Usage:
    python backtest/backtest_improvement_plan/run_phase1_group_k.py
    python backtest/backtest_improvement_plan/run_phase1_group_k.py --workers 4
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
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase1_group_k"

# ---------------------------------------------------------------------------
# 共通パラメータ（全シナリオ固定）
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
    # TOPIX BG は全シナリオで OFF
    "weak_bear": 1.00,
    "strong_bear": 1.00,
    "start": "2017-01-01",
    "end": "2025-12-31",
}

# ---------------------------------------------------------------------------
# Group K シナリオ定義
# ---------------------------------------------------------------------------

_GROUP_K: list[dict] = [
    {
        "name": "K1_i1_ref",
        "group": "K",
        "desc": "I1 完全再現（参照）",
    },
    {
        "name": "K2_rsi_oversold",
        "group": "K",
        "rsi_oversold_max": 40.0,
        "desc": "RSI <= 40 フィルター（売られすぎ確認）",
    },
    {
        "name": "K3_quality",
        "group": "K",
        "quality_score_min": -0.5,
        "desc": "クオリティスコア >= -0.5 フィルター",
    },
    {
        "name": "K4_volume",
        "group": "K",
        "volume_breakout_threshold": 1.2,
        "desc": "出来高ブレイクアウト >= 1.2x フィルター",
    },
    {
        "name": "K5_topix_rel",
        "group": "K",
        "topix_rel_min": -0.10,
        "desc": "TOPIX 20日相対強度 >= -10% フィルター",
    },
    {
        "name": "K6_adaptive_thr",
        "group": "K",
        "adaptive_threshold": True,
        "desc": "アダプティブ閾値（TOPIX MA200 +5% 超で 0.62）",
    },
    {
        "name": "K7_rsi_quality",
        "group": "K",
        "rsi_oversold_max": 40.0,
        "quality_score_min": -0.5,
        "desc": "RSI + クオリティ複合",
    },
    {
        "name": "K8_rsi_quality_vol",
        "group": "K",
        "rsi_oversold_max": 40.0,
        "quality_score_min": -0.5,
        "volume_breakout_threshold": 1.2,
        "desc": "RSI + クオリティ + 出来高 複合（最有力候補）",
    },
    {
        "name": "K9_adaptive_rsi",
        "group": "K",
        "adaptive_threshold": True,
        "rsi_oversold_max": 40.0,
        "desc": "アダプティブ閾値 + RSI 複合",
    },
]

ALL_SCENARIOS: list[dict] = _GROUP_K

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

    # シナリオ固有フィルター
    if scenario.get("rsi_oversold_max") is not None:
        cmd += ["--rsi-oversold-max", str(scenario["rsi_oversold_max"])]
    if scenario.get("quality_score_min") is not None:
        cmd += ["--quality-score-min", str(scenario["quality_score_min"])]
    if scenario.get("volume_breakout_threshold") is not None:
        cmd += ["--volume-breakout-threshold", str(scenario["volume_breakout_threshold"])]
    if scenario.get("topix_rel_min") is not None:
        cmd += ["--topix-rel-min", str(scenario["topix_rel_min"])]
    if scenario.get("adaptive_threshold"):
        cmd.append("--adaptive-threshold")

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
            "rsi_oversold_max": scenario.get("rsi_oversold_max", ""),
            "quality_score_min": scenario.get("quality_score_min", ""),
            "volume_breakout_threshold": scenario.get("volume_breakout_threshold", ""),
            "topix_rel_min": scenario.get("topix_rel_min", ""),
            "adaptive_threshold": scenario.get("adaptive_threshold", False),
            "desc": scenario.get("desc", ""),
            **metrics,
            "error": False,
        }
        results.append(record)

        filters_str = _format_filters(scenario)
        print(
            f"[DONE] {name:<25} {filters_str:<35}"
            f"cagr={_fmt(metrics.get('cagr'), 4)}\t"
            f"sharpe={_fmt(metrics.get('sharpe'), 3)}\t"
            f"dd={_fmt(metrics.get('max_drawdown'), 4)}\t"
            f"trades={metrics.get('total_trades')}",
            flush=True,
        )

    return results


def _format_filters(scenario: dict) -> str:
    parts = []
    if scenario.get("rsi_oversold_max") not in (None, ""):
        parts.append(f"rsi<={float(scenario['rsi_oversold_max']):.0f}")
    if scenario.get("quality_score_min") not in (None, ""):
        parts.append(f"qual>={float(scenario['quality_score_min'])}")
    if scenario.get("volume_breakout_threshold") not in (None, ""):
        parts.append(f"vol>={float(scenario['volume_breakout_threshold'])}")
    if scenario.get("topix_rel_min") not in (None, ""):
        parts.append(f"trel>={float(scenario['topix_rel_min'])}")
    if scenario.get("adaptive_threshold"):
        parts.append("adaptive")
    return " ".join(parts) if parts else "none"


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

CSV_FIELDNAMES = [
    "name",
    "group",
    "rsi_oversold_max",
    "quality_score_min",
    "volume_breakout_threshold",
    "topix_rel_min",
    "adaptive_threshold",
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


def _three_criteria(r: dict) -> bool:
    """Sharpe を除く 3 指標が採用基準を満たすか"""
    try:
        return (
            r.get("cagr") not in (None, "")
            and float(r["cagr"]) > _CAGR_MIN
            and r.get("max_drawdown") not in (None, "")
            and float(r["max_drawdown"]) < _DD_MAX
            and r.get("profit_factor") not in (None, "")
            and float(r["profit_factor"]) > _PF_MIN
        )
    except (ValueError, TypeError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 1 Group K バックテスト（I1 弱点克服フィルター検証）"
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

    print("-" * 120)
    print(f"\n完了: {datetime.now().strftime('%H:%M:%S')}")
    print(f"成功: {len(success)} / {len(scenarios)}, 失敗: {len(failed)}")
    print(f"results_csv={results_csv}")

    if success:
        print("\n--- Group K: I1 弱点克服フィルター検証結果 ---")
        print(
            f"{'name':<25} {'filters':<35}"
            f" {'cagr':>8} {'sharpe':>7} {'max_dd':>8} {'pf':>6} {'trades':>7}  desc"
        )
        print("-" * 120)
        for r in success:
            adopted = _all_criteria(r)
            marker = " ★採択候補" if adopted else ""
            filters_str = _format_filters(r)
            print(
                f"{r['name']:<25}"
                f" {filters_str:<35}"
                f" {_fmt(r.get('cagr'), 4):>8}"
                f" {_fmt(r.get('sharpe'), 3):>7}"
                f" {_fmt(r.get('max_drawdown'), 4):>8}"
                f" {_fmt(r.get('profit_factor'), 3):>6}"
                f" {str(r.get('total_trades', '')):>7}"
                f"  {r.get('desc', '')}{marker}"
            )

        print("\n採択判断:")
        adopted_scenarios = [r for r in success if _all_criteria(r)]
        k1 = next((r for r in success if r["name"] == "K1_i1_ref"), None)
        if adopted_scenarios:
            best = max(adopted_scenarios, key=lambda r: float(r["sharpe"]) if r.get("sharpe") not in (None, "") else 0.0)
            print(
                f"  → {best['name']} が全採用基準（CAGR>{_CAGR_MIN * 100:.0f}%, "
                f"Max DD<{_DD_MAX * 100:.0f}%, PF>{_PF_MIN}, Sharpe>{_SHARPE_MIN}）を達成: 採用"
            )
        else:
            improved_three = [
                r
                for r in success
                if _three_criteria(r)
                and r["name"] != "K1_i1_ref"
                and (k1 is None or (float(r["sharpe"]) if r.get("sharpe") not in (None, "") else 0) >= (float(k1["sharpe"]) if k1.get("sharpe") not in (None, "") else 0))
            ]
            if improved_three:
                best3 = max(improved_three, key=lambda r: float(r["sharpe"]) if r.get("sharpe") not in (None, "") else 0.0)
                print(
                    f"  → Sharpe>{_SHARPE_MIN} 達成なし。{best3['name']} が 3 指標を維持しつつ"
                    f" Sharpe={_fmt(best3.get('sharpe'), 3)} を達成。詳細確認を推奨"
                )
            elif k1 and _three_criteria(k1):
                print(
                    f"  → 全フィルターで Sharpe>{_SHARPE_MIN} 達成なし。"
                    "K1（I1 参照）の 3 指標維持を確認 → I1 設定を継続採用"
                )
            else:
                print(
                    "  → いずれのシナリオも採用基準を満たしていません。別アプローチを検討してください"
                )

    if failed:
        print(f"\n失敗したシナリオ: {[r['name'] for r in failed]}")


if __name__ == "__main__":
    main()
