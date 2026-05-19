"""10m バックテスト改善スイート v2

v1 で判明した課題（2025年通年マイナス）に対し、以下の方向性で探索する。
  1. ストップ収縮   : stop_loss 9% → 6%, trail_atr 2.0 → 1.5, max_holding 60 → 30-40日
  2. equal 配分     : 1m スイートで equal が好成績のため 10m でも検証
  3. 閾値引き下げ   : threshold 0.58 → 0.55 で分散を増やす
  4. スロット集中   : 4-5 スロットに絞り 1 銘柄あたりの重みを上げる
"""

from __future__ import annotations

import csv
import json
import locale
import re
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import duckdb
import yaml


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "config" / "strategy_config.yaml").exists():
            return candidate
    raise FileNotFoundError("Could not locate repo root containing config/strategy_config.yaml")


REPO_ROOT = _find_repo_root()
ENV_PATH = REPO_ROOT / ".env"
STRATEGY_CONFIG_PATH = REPO_ROOT / "config" / "strategy_config.yaml"
RISK_CONFIG_PATH = REPO_ROOT / "config" / "risk_config.yaml"
RUN_ID_PATTERN = re.compile(r"run_id:\s*([0-9a-fA-F-]+)|run_id=([0-9a-fA-F-]+)")
SUBPROCESS_ENCODING = locale.getpreferredencoding(False) or "cp932"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest_improvement_10m_v2"


SCENARIOS = [
    # ── ベースライン（v1 との比較用） ──────────────────────────────────────────
    {
        "name": "10m_base",
        "cash": 10_000_000,
        "allocation_method": "risk_based",
        "max_positions": 7,
        "max_position_pct": 0.10,
        "max_utilization": 0.70,
        "risk_pct": 0.005,
        "stop_loss_pct": 0.09,
        "threshold": 0.58,
        "topix_size_multiplier_weak_bear": 0.50,
        "trailing_stop_atr_mult": 2.0,
        "max_holding_days": 60,
    },
    # ── ストップ収縮：損切りを早めてドローダウン抑制 ─────────────────────────
    {
        "name": "10m_tighter_stop",
        "cash": 10_000_000,
        "allocation_method": "risk_based",
        "max_positions": 7,
        "max_position_pct": 0.10,
        "max_utilization": 0.70,
        "risk_pct": 0.005,
        "stop_loss_pct": 0.06,
        "threshold": 0.58,
        "topix_size_multiplier_weak_bear": 0.50,
        "trailing_stop_atr_mult": 1.5,
        "max_holding_days": 40,
    },
    # ── 高速エグジット：短期回転で含み損を引きずらない ───────────────────────
    {
        "name": "10m_fast_exit",
        "cash": 10_000_000,
        "allocation_method": "risk_based",
        "max_positions": 7,
        "max_position_pct": 0.10,
        "max_utilization": 0.70,
        "risk_pct": 0.005,
        "stop_loss_pct": 0.06,
        "threshold": 0.58,
        "topix_size_multiplier_weak_bear": 0.50,
        "trailing_stop_atr_mult": 1.5,
        "max_holding_days": 30,
    },
    # ── equal 配分 + 閾値引き下げ：分散と銘柄数のバランスを探る ─────────────
    {
        "name": "10m_equal_lower_thr",
        "cash": 10_000_000,
        "allocation_method": "equal",
        "max_positions": 6,
        "max_position_pct": 0.15,
        "max_utilization": 0.75,
        "risk_pct": 0.005,
        "stop_loss_pct": 0.07,
        "threshold": 0.55,
        "topix_size_multiplier_weak_bear": 0.50,
        "trailing_stop_atr_mult": 2.0,
        "max_holding_days": 60,
    },
    # ── equal 集中 5slots：質重視で 1 銘柄あたりの重みを上げる ──────────────
    {
        "name": "10m_concentrate_5slots",
        "cash": 10_000_000,
        "allocation_method": "equal",
        "max_positions": 5,
        "max_position_pct": 0.18,
        "max_utilization": 0.80,
        "risk_pct": 0.005,
        "stop_loss_pct": 0.07,
        "threshold": 0.60,
        "topix_size_multiplier_weak_bear": 0.50,
        "trailing_stop_atr_mult": 1.5,
        "max_holding_days": 40,
    },
    # ── equal 4slots：1m で最良だった設定を 10m に適用 ───────────────────────
    {
        "name": "10m_equal_4slots",
        "cash": 10_000_000,
        "allocation_method": "equal",
        "max_positions": 4,
        "max_position_pct": 0.22,
        "max_utilization": 0.80,
        "risk_pct": 0.005,
        "stop_loss_pct": 0.07,
        "threshold": 0.58,
        "topix_size_multiplier_weak_bear": 0.50,
        "trailing_stop_atr_mult": 2.0,
        "max_holding_days": 60,
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
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _save_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _build_base_context() -> dict[str, object]:
    env = _load_env(ENV_PATH)
    strategy_config = _load_yaml(STRATEGY_CONFIG_PATH)
    risk_config = _load_yaml(RISK_CONFIG_PATH)

    db_path = Path(env.get("DUCKDB_PATH", "data/kabusys.duckdb"))
    if not db_path.is_absolute():
        db_path = REPO_ROOT / db_path

    return {
        "db_path": db_path,
        "strategy_config": strategy_config,
        "risk_config": risk_config,
    }


def _build_strategy_config(base: dict, scenario: dict[str, object]) -> dict:
    strategy_config = deepcopy(base)
    strategy_section = strategy_config.setdefault("strategy", {})
    sector_section = strategy_config.setdefault("sector", {})
    regime_section = strategy_config.setdefault("regime", {})
    portfolio_section = strategy_config.setdefault("portfolio", {})

    strategy_section["threshold"] = scenario.get("threshold", 0.58)
    strategy_section["gap_up_threshold"] = 0.07
    strategy_section["gap_down_threshold"] = -0.05
    strategy_section["rsi_overbought_threshold"] = 65.0
    strategy_section["stop_loss_rate"] = -0.08
    strategy_section["min_holding_days"] = 5
    strategy_section["max_holding_days"] = scenario.get("max_holding_days", 60)
    strategy_section["trailing_stop_atr_mult"] = scenario.get("trailing_stop_atr_mult", 2.0)
    strategy_section["reentry_cooldown_days"] = 5

    sector_section["boost"] = 0.05
    sector_section["quartile"] = 0.30

    regime_section["topix_size_multiplier_weak_bear"] = scenario.get(
        "topix_size_multiplier_weak_bear", 0.50
    )
    regime_section["topix_size_multiplier_strong_bear"] = scenario.get(
        "topix_size_multiplier_strong_bear", 0.00
    )

    portfolio_section["max_positions"] = scenario.get("max_positions", 7)
    return strategy_config


def _build_risk_config(base: dict, scenario: dict[str, object]) -> dict:
    risk_config = deepcopy(base)
    risk_section = risk_config.setdefault("risk", {})
    risk_section["max_position_pct"] = scenario.get("max_position_pct", 0.10)
    risk_section["max_utilization"] = scenario.get("max_utilization", 0.70)
    return risk_config


def _build_backtest_params(scenario: dict[str, object]) -> dict[str, object]:
    return {
        "start": "2025-01-01",
        "end": "2025-12-31",
        "cash": scenario["cash"],
        "allocation_method": scenario.get("allocation_method", "risk_based"),
        "max_positions": scenario.get("max_positions", 7),
        "max_position_pct": scenario.get("max_position_pct", 0.10),
        "max_utilization": scenario.get("max_utilization", 0.70),
        "risk_pct": scenario.get("risk_pct", 0.005),
        "stop_loss_pct": scenario.get("stop_loss_pct", 0.09),
        "min_holding_days": 5,
        "max_holding_days": scenario.get("max_holding_days", 60),
        "trailing_stop_atr": scenario.get("trailing_stop_atr_mult", 2.0),
        "threshold": scenario.get("threshold", 0.58),
        "topix_size_multiplier_weak_bear": scenario.get("topix_size_multiplier_weak_bear", 0.50),
        "topix_size_multiplier_strong_bear": scenario.get(
            "topix_size_multiplier_strong_bear", 0.00
        ),
    }


def _build_command(db_path: Path, params: dict[str, object], output_dir: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "kabusys.backtest.run",
        "--db",
        str(db_path),
        "--start",
        str(params["start"]),
        "--end",
        str(params["end"]),
        "--cash",
        str(params["cash"]),
        "--allocation-method",
        str(params["allocation_method"]),
        "--max-position-pct",
        str(params["max_position_pct"]),
        "--max-utilization",
        str(params["max_utilization"]),
        "--max-positions",
        str(params["max_positions"]),
        "--risk-pct",
        str(params["risk_pct"]),
        "--stop-loss-pct",
        str(params["stop_loss_pct"]),
        "--min-holding-days",
        str(params["min_holding_days"]),
        "--max-holding-days",
        str(params["max_holding_days"]),
        "--trailing-stop-atr",
        str(params["trailing_stop_atr"]),
        "--threshold",
        str(params["threshold"]),
        "--topix-size-multiplier-weak-bear",
        str(params["topix_size_multiplier_weak_bear"]),
        "--topix-size-multiplier-strong-bear",
        str(params.get("topix_size_multiplier_strong_bear", 0.0)),
        "--output-format",
        "all",
        "--output-dir",
        str(output_dir),
    ]


def _extract_run_id(output: str) -> str:
    match = RUN_ID_PATTERN.search(output)
    if not match:
        raise RuntimeError("run_id could not be found in backtest output.")
    return match.group(1) or match.group(2)


def _fetch_metrics(conn: duckdb.DuckDBPyConnection, run_id: str) -> dict[str, object]:
    row = conn.execute(
        """
        SELECT
            created_at,
            cagr,
            sharpe,
            max_drawdown,
            win_rate,
            payoff_ratio,
            profit_factor,
            avg_holding_days,
            total_trades
        FROM backtest_runs
        WHERE run_id = ?
        """,
        [run_id],
    ).fetchone()
    if row is None:
        raise RuntimeError(f"backtest_runs does not contain run_id={run_id}.")
    return {
        "created_at": str(row[0]),
        "cagr": row[1],
        "sharpe": row[2],
        "max_drawdown": row[3],
        "win_rate": row[4],
        "payoff_ratio": row[5],
        "profit_factor": row[6],
        "avg_holding_days": row[7],
        "total_trades": row[8],
    }


def _export_trades_csv(conn: duckdb.DuckDBPyConnection, run_id: str, out_path: Path) -> None:
    rows = conn.execute(
        """
        SELECT
            trade_seq,
            date,
            code,
            side,
            shares,
            price,
            commission,
            realized_pnl
        FROM backtest_trades
        WHERE run_id = ?
        ORDER BY trade_seq
        """,
        [run_id],
    ).fetchall()
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["trade_seq", "date", "code", "side", "shares", "price", "commission", "realized_pnl"]
        )
        writer.writerows(rows)


def _format_metric(value: object, digits: int = 6) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _make_output_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ARTIFACTS_ROOT / stamp
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _make_db_snapshot(source_db_path: Path, output_dir: Path) -> Path:
    snapshot_path = output_dir / "kabusys_snapshot.duckdb"
    shutil.copy2(str(source_db_path), str(snapshot_path))
    return snapshot_path


def main() -> None:
    context = _build_base_context()
    output_dir = _make_output_dir()
    db_path = _make_db_snapshot(context["db_path"], output_dir)
    log_jsonl_path = output_dir / "results.jsonl"
    log_csv_path = output_dir / "results.csv"

    (output_dir / "scenarios.json").write_text(
        json.dumps(SCENARIOS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    original_strategy_text = STRATEGY_CONFIG_PATH.read_text(encoding="utf-8")
    original_risk_text = RISK_CONFIG_PATH.read_text(encoding="utf-8")

    fieldnames = [
        "name",
        "run_id",
        "created_at",
        "cash",
        "allocation_method",
        "threshold",
        "topix_size_multiplier_weak_bear",
        "topix_size_multiplier_strong_bear",
        "trailing_stop_atr",
        "rsi_overbought_threshold",
        "max_positions",
        "max_position_pct",
        "max_utilization",
        "risk_pct",
        "stop_loss_pct",
        "max_holding_days",
        "cagr",
        "sharpe",
        "max_drawdown",
        "win_rate",
        "payoff_ratio",
        "profit_factor",
        "avg_holding_days",
        "total_trades",
        "trades_csv",
    ]

    print(f"output_dir={output_dir}")
    print(
        "scenario\trun_id\tthreshold\tstop%\ttrail_atr\tmax_hold\talloc\tslots"
        "\tcagr\tsharpe\tmax_dd\tpf\ttrades"
    )

    with (
        log_jsonl_path.open("w", encoding="utf-8") as jsonl_file,
        log_csv_path.open("w", newline="", encoding="utf-8") as csv_file,
    ):
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        try:
            for scenario in SCENARIOS:
                strategy_config = _build_strategy_config(context["strategy_config"], scenario)
                risk_config = _build_risk_config(context["risk_config"], scenario)
                _save_yaml(STRATEGY_CONFIG_PATH, strategy_config)
                _save_yaml(RISK_CONFIG_PATH, risk_config)

                scenario_slug = str(scenario["name"])
                scenario_dir = output_dir / scenario_slug
                scenario_dir.mkdir(parents=True, exist_ok=True)

                params = _build_backtest_params(scenario)
                (scenario_dir / "strategy_config.yaml").write_text(
                    yaml.dump(
                        strategy_config,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False,
                    ),
                    encoding="utf-8",
                )
                (scenario_dir / "risk_config.yaml").write_text(
                    yaml.dump(
                        risk_config,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False,
                    ),
                    encoding="utf-8",
                )
                (scenario_dir / "effective_backtest_params.json").write_text(
                    json.dumps(params, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                report_base_dir = scenario_dir / "report"
                cmd = _build_command(db_path, params, report_base_dir)
                print(f"\n=== running: {scenario_slug} ===")
                print("command:", subprocess.list2cmdline(cmd))

                completed = subprocess.run(
                    cmd,
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    encoding=SUBPROCESS_ENCODING,
                    errors="replace",
                )

                (scenario_dir / "stdout.log").write_text(completed.stdout or "", encoding="utf-8")
                (scenario_dir / "stderr.log").write_text(completed.stderr or "", encoding="utf-8")

                if completed.returncode != 0:
                    raise RuntimeError(
                        f"scenario={scenario_slug} failed with exit code {completed.returncode}"
                    )

                run_id = _extract_run_id(f"{completed.stdout}\n{completed.stderr}")
                conn = duckdb.connect(str(db_path), read_only=True)
                try:
                    metrics = _fetch_metrics(conn, run_id)
                    trades_csv_path = scenario_dir / "trades.csv"
                    _export_trades_csv(conn, run_id, trades_csv_path)
                finally:
                    conn.close()

                record = {
                    "name": scenario_slug,
                    "run_id": run_id,
                    "created_at": metrics["created_at"],
                    "cash": params["cash"],
                    "allocation_method": params["allocation_method"],
                    "threshold": scenario.get("threshold", 0.58),
                    "topix_size_multiplier_weak_bear": scenario.get(
                        "topix_size_multiplier_weak_bear", 0.50
                    ),
                    "topix_size_multiplier_strong_bear": scenario.get(
                        "topix_size_multiplier_strong_bear", 0.00
                    ),
                    "trailing_stop_atr": scenario.get("trailing_stop_atr_mult", 2.0),
                    "rsi_overbought_threshold": 65.0,
                    "max_positions": params["max_positions"],
                    "max_position_pct": params["max_position_pct"],
                    "max_utilization": params["max_utilization"],
                    "risk_pct": params["risk_pct"],
                    "stop_loss_pct": params["stop_loss_pct"],
                    "max_holding_days": params["max_holding_days"],
                    **metrics,
                    "trades_csv": str(scenario_dir / "trades.csv"),
                }

                jsonl_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                jsonl_file.flush()
                writer.writerow(record)
                csv_file.flush()

                print(
                    f"{scenario_slug}\t{run_id}\t"
                    f"{scenario.get('threshold', 0.58)}\t"
                    f"{scenario.get('stop_loss_pct', 0.09)}\t"
                    f"{scenario.get('trailing_stop_atr_mult', 2.0)}\t"
                    f"{scenario.get('max_holding_days', 60)}\t"
                    f"{scenario.get('allocation_method', 'risk_based')}\t"
                    f"{scenario.get('max_positions', 7)}\t"
                    f"{_format_metric(metrics['cagr'])}\t"
                    f"{_format_metric(metrics['sharpe'])}\t"
                    f"{_format_metric(metrics['max_drawdown'])}\t"
                    f"{_format_metric(metrics['profit_factor'])}\t"
                    f"{metrics['total_trades']}"
                )
        finally:
            STRATEGY_CONFIG_PATH.write_text(original_strategy_text, encoding="utf-8")
            RISK_CONFIG_PATH.write_text(original_risk_text, encoding="utf-8")

    print(f"\nresults_jsonl={log_jsonl_path}")
    print(f"results_csv={log_csv_path}")


if __name__ == "__main__":
    main()
