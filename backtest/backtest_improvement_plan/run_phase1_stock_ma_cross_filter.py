"""Phase 1 銘柄単位 MA25/MA75 クロスフィルター検証バックテスト（Group I）

Group H の検証結果から:
  - H5（最有力複合設定）が採択基準（CAGR>5%, Max DD<25%, PF>1.1）を未達成
  - H3（util=30% + MA200）が Max DD 最近接（25.35%）で Group I のベースラインとなる
  - MA200 バイナリフィルター単独（H2）は CAGR を大幅に悪化させるため不採用

本スクリプトは MA200 バイナリフィルターを **銘柄単位の MA25/MA75 クロス判定（段階的縮小）** に
置き換えた場合の効果を検証する。

固定設定（全シナリオ共通）:
  max_positions  : 3
  TOPIX BG       : OFF（weak=1.0 / strong=1.0）
  DD stop        : 12%（dd_timeout=30日）
  stop_loss      : 9%
  threshold      : 0.58
  期間           : 2017-01-01〜2025-12-31

Group I シナリオ:
  I1_h3_ref           : util=30%, MA200=ON,  stock_MA_cross=OFF  H3 参照（Group H 最有力設定）
  I2_h1_ref           : util=50%, MA200=OFF, stock_MA_cross=OFF  A3/H1 参照（フィルターなし）
  I3_stock_ma_only    : util=30%, MA200=OFF, stock_MA_cross=ON   MA200 → MA25/75 クロスに置換
  I4_h3_plus_stock_ma : util=30%, MA200=ON,  stock_MA_cross=ON   H3 に MA25/75 クロスを追加（二重フィルター）

読み方:
  I1 → I3: MA200 バイナリを MA25/75 クロスに置き換えた場合の効果差分
  I1 → I4: H3 に MA25/75 クロスを追加した場合の効果差分（過剰絞り込みのリスクに注意）
  I2 → I3: フィルターなし vs 銘柄 MA クロス単体の純粋な効果

採択判断ロジック:
  I3 が CAGR>5% かつ Max DD<25% → I3 設定を Phase 1 採用
  I3 が Max DD<25% 未達          → I4（二重フィルター）を確認
  I4 でも未達                    → 銘柄 MA クロスフィルターは限界。別アプローチを検討

Usage:
    python backtest/backtest_improvement_plan/run_phase1_stock_ma_cross_filter.py
    python backtest/backtest_improvement_plan/run_phase1_stock_ma_cross_filter.py --workers 4
"""

from __future__ import annotations

import argparse
import csv
import json
import locale
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

SUBPROCESS_ENCODING = locale.getpreferredencoding(False) or "cp932"
DEFAULT_WORKERS = 4


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "config" / "strategy_config.yaml").exists():
            return candidate
    raise FileNotFoundError("config/strategy_config.yaml が見つかりません")


REPO_ROOT = _find_repo_root()
ENV_PATH = REPO_ROOT / ".env"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest" / "backtest_phase1_stock_ma_cross"

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
    "threshold": 0.58,
    # TOPIX BG は全シナリオで OFF
    "weak_bear": 1.00,
    "strong_bear": 1.00,
    "start": "2017-01-01",
    "end": "2025-12-31",
    # 弱ベア時の縮小係数（stock_MA_cross=ON のとき有効）
    "stock_ma_weak_bear_multiplier": 0.5,
}

# ---------------------------------------------------------------------------
# Group I シナリオ定義
# ---------------------------------------------------------------------------

_GROUP_I: list[dict] = [
    {
        "name": "I1_h3_ref",
        "group": "I",
        "max_utilization": 0.30,
        "use_ma200_filter": True,
        "use_stock_ma_cross_filter": False,
        "desc": "H3 参照（util=30% + MA200、Group H 最有力設定）",
    },
    {
        "name": "I2_h1_ref",
        "group": "I",
        "max_utilization": 0.50,
        "use_ma200_filter": False,
        "use_stock_ma_cross_filter": False,
        "desc": "A3/H1 参照（フィルターなし、ベースライン）",
    },
    {
        "name": "I3_stock_ma_only",
        "group": "I",
        "max_utilization": 0.30,
        "use_ma200_filter": False,
        "use_stock_ma_cross_filter": True,
        "desc": "MA200 を外し MA25/75 クロスのみに置換",
    },
    {
        "name": "I4_h3_plus_stock_ma",
        "group": "I",
        "max_utilization": 0.30,
        "use_ma200_filter": True,
        "use_stock_ma_cross_filter": True,
        "desc": "H3 に MA25/75 クロスを追加（二重フィルター）",
    },
]

ALL_SCENARIOS: list[dict] = _GROUP_I

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
    if scenario.get("use_ma200_filter"):
        cmd.append("--ma200-filter")
    if scenario.get("use_stock_ma_cross_filter"):
        cmd.extend(
            [
                "--stock-ma-cross-filter",
                "--stock-ma-cross-weak-bear-multiplier",
                str(_COM["stock_ma_weak_bear_multiplier"]),
            ]
        )
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

        env = os.environ.copy()
        src_path = str(repo_root / "src")
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [src_path, existing]))

        completed = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding=SUBPROCESS_ENCODING,
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
            "max_utilization": scenario["max_utilization"],
            "use_ma200_filter": scenario["use_ma200_filter"],
            "use_stock_ma_cross_filter": scenario["use_stock_ma_cross_filter"],
            "desc": scenario.get("desc", ""),
            **metrics,
            "error": False,
        }
        results.append(record)

        print(
            f"[DONE] {name}\t"
            f"util={scenario['max_utilization']:.2f} "
            f"ma200={scenario['use_ma200_filter']} "
            f"stock_ma={scenario['use_stock_ma_cross_filter']}\t"
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
    "use_ma200_filter",
    "use_stock_ma_cross_filter",
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
        description="Phase 1 銘柄単位 MA25/MA75 クロスフィルター検証バックテスト（Group I）"
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
    print("-" * 110)

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

    print("-" * 110)
    print(f"\n完了: {datetime.now().strftime('%H:%M:%S')}")
    print(f"成功: {len(success)} / {len(scenarios)}, 失敗: {len(failed)}")
    print(f"results_csv={results_csv}")

    if success:
        print("\n--- Group I: 銘柄単位 MA25/MA75 クロスフィルター結果 ---")
        print(
            f"{'name':<28} {'util':>5} {'ma200':>6} {'stk_ma':>7}"
            f" {'cagr':>8} {'sharpe':>7} {'max_dd':>8} {'pf':>6} {'trades':>7}  desc"
        )
        print("-" * 110)
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
                f" {str(r.get('use_ma200_filter', '')):>6}"
                f" {str(r.get('use_stock_ma_cross_filter', '')):>7}"
                f" {_fmt(r.get('cagr'), 4):>8}"
                f" {_fmt(r.get('sharpe'), 3):>7}"
                f" {_fmt(r.get('max_drawdown'), 4):>8}"
                f" {_fmt(r.get('profit_factor'), 3):>6}"
                f" {str(r.get('total_trades', '')):>7}"
                f"  {r.get('desc', '')}{marker}"
            )

        print("\n採択判断:")
        i3 = next((r for r in success if r["name"] == "I3_stock_ma_only"), None)
        i4 = next((r for r in success if r["name"] == "I4_h3_plus_stock_ma"), None)

        if i3:
            cagr_ok = i3.get("cagr") is not None and i3["cagr"] > 0.05
            dd_ok = i3.get("max_drawdown") is not None and i3["max_drawdown"] < 0.25
            if cagr_ok and dd_ok:
                print("  → I3 が CAGR>5% かつ Max DD<25% を達成: I3 設定を Phase 1 採用")
            elif dd_ok:
                print("  → I3 は Max DD<25% を達成したが CAGR 未達")
                if i4:
                    i4_cagr_ok = i4.get("cagr") is not None and i4["cagr"] > 0.05
                    i4_dd_ok = i4.get("max_drawdown") is not None and i4["max_drawdown"] < 0.25
                    if i4_cagr_ok and i4_dd_ok:
                        print("  → I4 が採択基準を達成: I4 設定を Phase 1 採用")
                    else:
                        print("  → I4 も未達。別アプローチを検討")
            else:
                print("  → I3 が Max DD<25% 未達")
                if i4:
                    i4_dd_ok = i4.get("max_drawdown") is not None and i4["max_drawdown"] < 0.25
                    if i4_dd_ok:
                        print("  → I4 は Max DD<25% を達成: I4 設定を確認")
                    else:
                        print("  → I4 も未達。銘柄 MA クロスフィルターは限界。別アプローチを検討")

    if failed:
        print(f"\n失敗したシナリオ: {[r['name'] for r in failed]}")


if __name__ == "__main__":
    main()
