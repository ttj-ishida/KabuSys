# 10m MDD対策 & 1m アブレーション分析 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `engine.py` にポートフォリオドローダウンストップを追加し、10m MDD対策と1mスコアリングアブレーション分析の検証スクリプトを作成する。

**Architecture:** `_is_entry_blocked()` という純粋関数でドローダウン判定を分離し、`run_backtest()` のメインループにピーク追跡を追加。CLIに `--portfolio-drawdown-stop` を追加した後、6シナリオ×3年の10m MDD検証スクリプトと6シナリオ×3年の1mアブレーション検証スクリプトを作成する。

**Tech Stack:** Python 3.10+, DuckDB, pytest, PyYAML, subprocess

---

## ファイルマップ

| ファイル | 操作 | 役割 |
|---|---|---|
| `src/kabusys/backtest/engine.py` | 修正 | `portfolio_drawdown_stop_pct` パラメータ追加・`_is_entry_blocked()` 追加 |
| `src/kabusys/backtest/run.py` | 修正 | `--portfolio-drawdown-stop` CLI引数追加 |
| `tests/test_backtest_engine_params.py` | 修正 | `_is_entry_blocked` と新パラメータのテスト追加 |
| `backtest/backtest_improvement_plan/run_backtest_improvement_10m_mdd.py` | 新規作成 | 10m MDD対策 6シナリオ×3年 スウィープスクリプト |
| `backtest/backtest_improvement_plan/run_backtest_improvement_1m_ablation.py` | 新規作成 | 1m ファクターアブレーション 6シナリオ×3年 スウィープスクリプト |

---

## Task 1: `_is_entry_blocked()` のテストを書く（RED）

**Files:**
- Test: `tests/test_backtest_engine_params.py`

- [ ] **Step 1: 既存テストファイルの末尾に以下を追記する**

```python
# ── _is_entry_blocked ────────────────────────────────────────────────────────


def test_is_entry_blocked_returns_false_when_disabled():
    from kabusys.backtest.engine import _is_entry_blocked

    assert _is_entry_blocked(900_000.0, 1_000_000.0, None) is False


def test_is_entry_blocked_returns_false_when_within_threshold():
    from kabusys.backtest.engine import _is_entry_blocked

    # drawdown = -10%、threshold = 15% → ブロックしない
    assert _is_entry_blocked(900_000.0, 1_000_000.0, 0.15) is False


def test_is_entry_blocked_returns_true_when_exceeded():
    from kabusys.backtest.engine import _is_entry_blocked

    # drawdown = -20%、threshold = 15% → ブロック
    assert _is_entry_blocked(800_000.0, 1_000_000.0, 0.15) is True


def test_is_entry_blocked_at_exact_threshold_is_not_blocked():
    from kabusys.backtest.engine import _is_entry_blocked

    # drawdown = -15%（= threshold）→ 厳密に「未満」でないためブロックしない
    assert _is_entry_blocked(850_000.0, 1_000_000.0, 0.15) is False


def test_run_backtest_accepts_portfolio_drawdown_stop_pct():
    import inspect
    from kabusys.backtest.engine import run_backtest

    assert "portfolio_drawdown_stop_pct" in inspect.signature(run_backtest).parameters


def test_run_backtest_portfolio_drawdown_stop_pct_default_is_none():
    import inspect
    from kabusys.backtest.engine import run_backtest

    param = inspect.signature(run_backtest).parameters["portfolio_drawdown_stop_pct"]
    assert param.default is None
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_backtest_engine_params.py -k "is_entry_blocked or portfolio_drawdown_stop" -v
```

期待: `ImportError: cannot import name '_is_entry_blocked'` または `AssertionError`

---

## Task 2: `engine.py` に `_is_entry_blocked()` とパラメータを実装する（GREEN）

**Files:**
- Modify: `src/kabusys/backtest/engine.py`

- [ ] **Step 1: ヘルパー関数セクションの末尾（`_fetch_sector_map` の後）に追加する**

```python
def _is_entry_blocked(
    portfolio_value: float,
    peak_value: float,
    portfolio_drawdown_stop_pct: float | None,
) -> bool:
    """ポートフォリオドローダウンストップ判定。

    portfolio_value がピーク比で portfolio_drawdown_stop_pct を超えて下落している場合 True を返す。
    portfolio_drawdown_stop_pct が None の場合は常に False（機能無効）。
    """
    if portfolio_drawdown_stop_pct is None:
        return False
    return portfolio_value / peak_value - 1 < -portfolio_drawdown_stop_pct
```

- [ ] **Step 2: `run_backtest()` のシグネチャに新パラメータを追加する**

`volume_breakout_threshold: float | None = None,` の行の直後に以下を追加:

```python
    portfolio_drawdown_stop_pct: float | None = None,
```

- [ ] **Step 3: `run_backtest()` の docstring に新パラメータの説明を追加する**

`volume_breakout_threshold:` の説明の直後に追加:

```
        portfolio_drawdown_stop_pct: ポートフォリオがピーク比でこの割合を超えて下落した場合、
                           新規 BUY エントリーを停止する（既存ポジションの SELL は継続）。
                           None（デフォルト）で無効。0 < x < 1 の範囲で指定すること。
```

- [ ] **Step 4: `run_backtest()` のバリデーションブロックに追加する**

`trailing_stop_atr <= 0` の `raise ValueError` の直後に追加:

```python
    if portfolio_drawdown_stop_pct is not None and not (0 < portfolio_drawdown_stop_pct < 1):
        raise ValueError(
            f"portfolio_drawdown_stop_pct は (0, 1) の範囲で指定してください: {portfolio_drawdown_stop_pct}"
        )
```

- [ ] **Step 5: ループ前の変数初期化に `peak_value` を追加する**

`next_day_orders: list[dict] = []` の直後に追加:

```python
    peak_value: float = initial_cash  # ポートフォリオドローダウンストップ用ピーク追跡
```

- [ ] **Step 6: メインループ内で `current_pv` 計算の直後にドローダウンチェックを追加する**

現在の `current_pv = (...)` 行（`available_cash` 計算の直前）の直後に追加:

```python
            peak_value = max(peak_value, current_pv)
            entry_blocked = _is_entry_blocked(current_pv, peak_value, portfolio_drawdown_stop_pct)
            if entry_blocked:
                logger.debug(
                    "run_backtest: ドローダウンストップ発動 date=%s drawdown=%.2f%%",
                    trading_day,
                    (current_pv / peak_value - 1) * 100,
                )
```

- [ ] **Step 7: `next_day_orders` の BUY 構築部分を `entry_blocked` で条件分岐させる**

現在の `next_day_orders = [...]` ブロックを以下に置き換える:

```python
            sm_map = {s["code"]: s.get("size_multiplier", 1.0) for s in buy_signals}
            next_day_orders = (
                []
                if entry_blocked
                else [
                    {
                        "code": code,
                        "side": "buy",
                        "shares": max(
                            0, (int(shares * sm_map.get(code, 1.0)) // lot_size) * lot_size
                        ),
                    }
                    for code, shares in sized.items()
                    if shares > 0 and code not in sell_codes
                ]
            ) + [{"code": s["code"], "side": "sell"} for s in sell_signals]
            # shares=0 になったエントリーを除外
            next_day_orders = [o for o in next_day_orders if o.get("shares", 1) > 0]
```

- [ ] **Step 8: テストがすべて通ることを確認する**

```
pytest tests/test_backtest_engine_params.py -k "is_entry_blocked or portfolio_drawdown_stop" -v
```

期待: すべて PASS

- [ ] **Step 9: 既存テスト全体が壊れていないことを確認する**

```
pytest tests/test_backtest_engine_params.py -v
```

期待: すべて PASS

- [ ] **Step 10: コミット**

```bash
git add src/kabusys/backtest/engine.py tests/test_backtest_engine_params.py
git commit -m "feat: run_backtest にポートフォリオドローダウンストップを追加 (portfolio_drawdown_stop_pct)"
```

---

## Task 3: `run.py` に CLI 引数を追加する（TDD）

**Files:**
- Test: `tests/test_backtest_engine_params.py`
- Modify: `src/kabusys/backtest/run.py`

- [ ] **Step 1: テストファイルの末尾に以下を追記する**

```python
def test_run_py_cli_has_portfolio_drawdown_stop_arg():
    import argparse
    import importlib.util
    import sys
    from pathlib import Path

    run_path = Path("src/kabusys/backtest/run.py")
    spec = importlib.util.spec_from_file_location("run_module", run_path)
    module = importlib.util.module_from_spec(spec)

    original_argv = sys.argv[:]
    try:
        sys.argv = ["run.py", "--help"]
        try:
            spec.loader.exec_module(module)
        except SystemExit:
            pass
    finally:
        sys.argv = original_argv

    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio-drawdown-stop", type=float, default=None)
    args = parser.parse_args(["--portfolio-drawdown-stop", "0.15"])
    assert args.portfolio_drawdown_stop == 0.15
```

実際には `run.py` 自体のパーサー定義を確認するため、以下のより直接的なテストを使う:

```python
def test_run_py_cli_has_portfolio_drawdown_stop_arg():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "kabusys.backtest.run", "--help"],
        capture_output=True,
        text=True,
    )
    assert "--portfolio-drawdown-stop" in result.stdout
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_backtest_engine_params.py -k "portfolio_drawdown_stop_arg" -v
```

期待: FAIL（`--portfolio-drawdown-stop` が --help に存在しない）

- [ ] **Step 3: `run.py` に引数を追加する**

`--volume-breakout-threshold` の `add_argument` の直後に追加:

```python
    parser.add_argument(
        "--portfolio-drawdown-stop",
        type=float,
        default=None,
        help=(
            "ポートフォリオがピーク比でこの割合（例: 0.15 = 15%%）を超えて下落した場合、"
            "新規 BUY エントリーを停止する。None（デフォルト）で無効。"
        ),
    )
```

- [ ] **Step 4: `run_backtest()` 呼び出しに新引数を追加する**

`volume_breakout_threshold=args.volume_breakout_threshold,` の直後に追加:

```python
            portfolio_drawdown_stop_pct=args.portfolio_drawdown_stop,
```

- [ ] **Step 5: テストが通ることを確認する**

```
pytest tests/test_backtest_engine_params.py -k "portfolio_drawdown_stop_arg" -v
```

期待: PASS

- [ ] **Step 6: 全テストが壊れていないことを確認する**

```
pytest tests/test_backtest_engine_params.py -v
```

期待: すべて PASS

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/backtest/run.py tests/test_backtest_engine_params.py
git commit -m "feat: backtest CLI に --portfolio-drawdown-stop 引数を追加"
```

---

## Task 4: `run_backtest_improvement_10m_mdd.py` を作成する

**Files:**
- Create: `backtest/backtest_improvement_plan/run_backtest_improvement_10m_mdd.py`

- [ ] **Step 1: スクリプトを作成する**

```python
"""10m MDD対策 検証スクリプト

2024年のMaxDD 41%（8月ブラックマンデー）対策として、
TOPIXベアガード強化とポートフォリオドローダウンストップの
2段構えを検証する。

シナリオ（計6件）× 3年（2023/2024/2025）= 18ラン:
  base          : 変更なし（OOS2ベースラインの再現）
  bear_stronger : TOPIXガード強化のみ（-0.10 / 0.25）
  dd_stop15     : ポートフォリオストップのみ（15%）
  dd_stop12     : ポートフォリオストップのみ（12%）
  combined15    : TOPIX強化 + ポートフォリオストップ15%
  combined12    : TOPIX強化 + ポートフォリオストップ12%
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
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest_improvement_10m_mdd"

# 10m_equal_4slots の固定パラメータ（OOS2 ベースライン設定）
_BASE = {
    "cash": 10_000_000,
    "allocation_method": "equal",
    "max_positions": 4,
    "max_position_pct": 0.22,
    "max_utilization": 0.80,
    "risk_pct": 0.005,
    "stop_loss_pct": 0.07,
    "threshold": 0.58,
    "topix_size_multiplier_bear": 0.50,
    "topix_drawdown_threshold": -0.15,
    "trailing_stop_atr_mult": 2.0,
    "max_holding_days": 60,
    "portfolio_drawdown_stop_pct": None,
}

SCENARIOS = [
    # ── ベースライン（OOS2 との内部一貫性確認）─────────────────────────────
    {**_BASE, "name": "base"},
    # ── TOPIXガード強化のみ ──────────────────────────────────────────────
    {
        **_BASE,
        "name": "bear_stronger",
        "topix_drawdown_threshold": -0.10,
        "topix_size_multiplier_bear": 0.25,
    },
    # ── ポートフォリオストップのみ（15%）────────────────────────────────────
    {**_BASE, "name": "dd_stop15", "portfolio_drawdown_stop_pct": 0.15},
    # ── ポートフォリオストップのみ（12%）────────────────────────────────────
    {**_BASE, "name": "dd_stop12", "portfolio_drawdown_stop_pct": 0.12},
    # ── TOPIX強化 + ポートフォリオストップ15% ───────────────────────────────
    {
        **_BASE,
        "name": "combined15",
        "topix_drawdown_threshold": -0.10,
        "topix_size_multiplier_bear": 0.25,
        "portfolio_drawdown_stop_pct": 0.15,
    },
    # ── TOPIX強化 + ポートフォリオストップ12% ───────────────────────────────
    {
        **_BASE,
        "name": "combined12",
        "topix_drawdown_threshold": -0.10,
        "topix_size_multiplier_bear": 0.25,
        "portfolio_drawdown_stop_pct": 0.12,
    },
]

YEARS = [2023, 2024, 2025]


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
    return {"db_path": db_path, "strategy_config": strategy_config, "risk_config": risk_config}


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

    regime_section["topix_drawdown_threshold"] = scenario.get("topix_drawdown_threshold", -0.15)
    regime_section["topix_size_multiplier_bear"] = scenario.get("topix_size_multiplier_bear", 0.50)

    portfolio_section["max_positions"] = scenario.get("max_positions", 4)
    return strategy_config


def _build_risk_config(base: dict, scenario: dict[str, object]) -> dict:
    risk_config = deepcopy(base)
    risk_section = risk_config.setdefault("risk", {})
    risk_section["max_position_pct"] = scenario.get("max_position_pct", 0.22)
    risk_section["max_utilization"] = scenario.get("max_utilization", 0.80)
    return risk_config


def _build_backtest_params(scenario: dict[str, object], year: int) -> dict[str, object]:
    return {
        "start": f"{year}-01-01",
        "end": f"{year}-12-31",
        "cash": scenario["cash"],
        "allocation_method": scenario.get("allocation_method", "equal"),
        "max_positions": scenario.get("max_positions", 4),
        "max_position_pct": scenario.get("max_position_pct", 0.22),
        "max_utilization": scenario.get("max_utilization", 0.80),
        "risk_pct": scenario.get("risk_pct", 0.005),
        "stop_loss_pct": scenario.get("stop_loss_pct", 0.07),
        "min_holding_days": 5,
        "max_holding_days": scenario.get("max_holding_days", 60),
        "trailing_stop_atr": scenario.get("trailing_stop_atr_mult", 2.0),
        "threshold": scenario.get("threshold", 0.58),
        "topix_drawdown_threshold": scenario.get("topix_drawdown_threshold", -0.15),
        "topix_size_multiplier_bear": scenario.get("topix_size_multiplier_bear", 0.50),
        "portfolio_drawdown_stop_pct": scenario.get("portfolio_drawdown_stop_pct"),
    }


def _build_command(db_path: Path, params: dict[str, object], output_dir: Path) -> list[str]:
    cmd = [
        sys.executable, "-m", "kabusys.backtest.run",
        "--db", str(db_path),
        "--start", str(params["start"]),
        "--end", str(params["end"]),
        "--cash", str(params["cash"]),
        "--allocation-method", str(params["allocation_method"]),
        "--max-position-pct", str(params["max_position_pct"]),
        "--max-utilization", str(params["max_utilization"]),
        "--max-positions", str(params["max_positions"]),
        "--risk-pct", str(params["risk_pct"]),
        "--stop-loss-pct", str(params["stop_loss_pct"]),
        "--min-holding-days", str(params["min_holding_days"]),
        "--max-holding-days", str(params["max_holding_days"]),
        "--trailing-stop-atr", str(params["trailing_stop_atr"]),
        "--threshold", str(params["threshold"]),
        "--topix-drawdown-threshold", str(params["topix_drawdown_threshold"]),
        "--topix-size-multiplier-bear", str(params["topix_size_multiplier_bear"]),
        "--output-format", "all",
        "--output-dir", str(output_dir),
    ]
    if params.get("portfolio_drawdown_stop_pct") is not None:
        cmd.extend(["--portfolio-drawdown-stop", str(params["portfolio_drawdown_stop_pct"])])
    return cmd


def _extract_run_id(output: str) -> str:
    match = RUN_ID_PATTERN.search(output)
    if not match:
        raise RuntimeError("run_id could not be found in backtest output.")
    return match.group(1) or match.group(2)


def _fetch_metrics(conn: duckdb.DuckDBPyConnection, run_id: str) -> dict[str, object]:
    row = conn.execute(
        """
        SELECT created_at, cagr, sharpe, max_drawdown, win_rate,
               payoff_ratio, profit_factor, avg_holding_days, total_trades
        FROM backtest_runs WHERE run_id = ?
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
        SELECT trade_seq, date, code, side, shares, price, commission, realized_pnl
        FROM backtest_trades WHERE run_id = ? ORDER BY trade_seq
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
        json.dumps(SCENARIOS, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    original_strategy_text = STRATEGY_CONFIG_PATH.read_text(encoding="utf-8")
    original_risk_text = RISK_CONFIG_PATH.read_text(encoding="utf-8")

    fieldnames = [
        "name", "year",
        "topix_drawdown_threshold", "topix_size_multiplier_bear", "portfolio_drawdown_stop_pct",
        "run_id", "created_at", "cash", "allocation_method",
        "threshold", "stop_loss_pct", "trailing_stop_atr", "max_holding_days",
        "max_positions", "max_position_pct", "max_utilization",
        "cagr", "sharpe", "max_drawdown", "win_rate",
        "payoff_ratio", "profit_factor", "avg_holding_days", "total_trades", "trades_csv",
    ]

    print(f"output_dir={output_dir}")
    print("scenario\tyear\tbear_thr\tbear_mult\tdd_stop\tcagr\tsharpe\tmax_dd\ttrades")

    with log_jsonl_path.open("w", encoding="utf-8") as jsonl_file, log_csv_path.open(
        "w", newline="", encoding="utf-8"
    ) as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        try:
            for scenario in SCENARIOS:
                for year in YEARS:
                    strategy_config = _build_strategy_config(context["strategy_config"], scenario)
                    risk_config = _build_risk_config(context["risk_config"], scenario)
                    _save_yaml(STRATEGY_CONFIG_PATH, strategy_config)
                    _save_yaml(RISK_CONFIG_PATH, risk_config)

                    scenario_name = str(scenario["name"])
                    run_slug = f"{scenario_name}_{year}"
                    scenario_dir = output_dir / run_slug
                    scenario_dir.mkdir(parents=True, exist_ok=True)

                    params = _build_backtest_params(scenario, year)
                    (scenario_dir / "effective_backtest_params.json").write_text(
                        json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8"
                    )

                    report_base_dir = scenario_dir / "report"
                    cmd = _build_command(db_path, params, report_base_dir)
                    print(f"\n=== running: {run_slug} ===")

                    completed = subprocess.run(
                        cmd,
                        cwd=str(REPO_ROOT),
                        capture_output=True,
                        text=True,
                        encoding=SUBPROCESS_ENCODING,
                        errors="replace",
                    )

                    (scenario_dir / "stdout.log").write_text(
                        completed.stdout or "", encoding="utf-8"
                    )
                    (scenario_dir / "stderr.log").write_text(
                        completed.stderr or "", encoding="utf-8"
                    )

                    if completed.returncode != 0:
                        raise RuntimeError(
                            f"scenario={run_slug} failed with exit code {completed.returncode}"
                        )

                    run_id = _extract_run_id(f"{completed.stdout}\n{completed.stderr}")
                    conn = duckdb.connect(str(db_path), read_only=True)
                    try:
                        metrics = _fetch_metrics(conn, run_id)
                        _export_trades_csv(conn, run_id, scenario_dir / "trades.csv")
                    finally:
                        conn.close()

                    record = {
                        "name": scenario_name,
                        "year": year,
                        "topix_drawdown_threshold": params["topix_drawdown_threshold"],
                        "topix_size_multiplier_bear": params["topix_size_multiplier_bear"],
                        "portfolio_drawdown_stop_pct": params["portfolio_drawdown_stop_pct"],
                        "run_id": run_id,
                        "created_at": metrics["created_at"],
                        "cash": params["cash"],
                        "allocation_method": params["allocation_method"],
                        "threshold": params["threshold"],
                        "stop_loss_pct": params["stop_loss_pct"],
                        "trailing_stop_atr": params["trailing_stop_atr"],
                        "max_holding_days": params["max_holding_days"],
                        "max_positions": params["max_positions"],
                        "max_position_pct": params["max_position_pct"],
                        "max_utilization": params["max_utilization"],
                        **metrics,
                        "trades_csv": str(scenario_dir / "trades.csv"),
                    }

                    jsonl_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                    jsonl_file.flush()
                    writer.writerow(record)
                    csv_file.flush()

                    print(
                        f"{run_slug}\t{year}\t"
                        f"{params['topix_drawdown_threshold']}\t"
                        f"{params['topix_size_multiplier_bear']}\t"
                        f"{params['portfolio_drawdown_stop_pct']}\t"
                        f"{_format_metric(metrics['cagr'])}\t"
                        f"{_format_metric(metrics['sharpe'])}\t"
                        f"{_format_metric(metrics['max_drawdown'])}\t"
                        f"{metrics['total_trades']}"
                    )
        finally:
            STRATEGY_CONFIG_PATH.write_text(original_strategy_text, encoding="utf-8")
            RISK_CONFIG_PATH.write_text(original_risk_text, encoding="utf-8")

    print(f"\nresults_jsonl={log_jsonl_path}")
    print(f"results_csv={log_csv_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: コミット**

```bash
git add backtest/backtest_improvement_plan/run_backtest_improvement_10m_mdd.py
git commit -m "feat: 10m MDD対策 検証スクリプトを追加 (6シナリオ×3年)"
```

---

## Task 5: `run_backtest_improvement_1m_ablation.py` を作成する

**Files:**
- Create: `backtest/backtest_improvement_plan/run_backtest_improvement_1m_ablation.py`

- [ ] **Step 1: スクリプトを作成する**

```python
"""1m ファクターアブレーション分析スクリプト

各ファクターを1つずつ weight=0 にして 2023/2024/2025 を検証し、
どのファクターが 2023/2024 の損失を引き起こしているかを特定する。

残りの重みは generate_signals() 内で自動正規化されるため合計が 1.0 でなくても動作する。

シナリオ（計6件）× 3年（2023/2024/2025）= 18ラン:
  base          : 現行重み（momentum=0.40, value=0.20, vol=0.15, liq=0.15, news=0.10）
  no_momentum   : momentum weight = 0
  no_value      : value weight = 0
  no_volatility : volatility weight = 0
  no_liquidity  : liquidity weight = 0
  no_news       : news weight = 0
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
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "backtest_improvement_1m_ablation"

# 1m_equal_4slots の固定ベースパラメータ（v2 最良設定）
_BASE = {
    "cash": 1_000_000,
    "allocation_method": "equal",
    "max_positions": 4,
    "max_position_pct": 0.22,
    "max_utilization": 0.80,
    "risk_pct": 0.005,
    "stop_loss_pct": 0.09,
    "threshold": 0.58,
    "topix_size_multiplier_bear": 0.50,
    "topix_drawdown_threshold": -0.15,
    "trailing_stop_atr_mult": 2.0,
    "max_holding_days": 60,
}

# 現行の重み（ベースライン）
_WEIGHTS_BASE = {
    "momentum": 0.40,
    "value": 0.20,
    "volatility": 0.15,
    "liquidity": 0.15,
    "news": 0.10,
}

SCENARIOS = [
    {**_BASE, "name": "base", "weights": _WEIGHTS_BASE},
    {**_BASE, "name": "no_momentum", "weights": {**_WEIGHTS_BASE, "momentum": 0.0}},
    {**_BASE, "name": "no_value",    "weights": {**_WEIGHTS_BASE, "value": 0.0}},
    {**_BASE, "name": "no_volatility", "weights": {**_WEIGHTS_BASE, "volatility": 0.0}},
    {**_BASE, "name": "no_liquidity",  "weights": {**_WEIGHTS_BASE, "liquidity": 0.0}},
    {**_BASE, "name": "no_news",       "weights": {**_WEIGHTS_BASE, "news": 0.0}},
]

YEARS = [2023, 2024, 2025]


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
    return {"db_path": db_path, "strategy_config": strategy_config, "risk_config": risk_config}


def _build_strategy_config(base: dict, scenario: dict[str, object]) -> dict:
    strategy_config = deepcopy(base)
    strategy_section = strategy_config.setdefault("strategy", {})
    sector_section = strategy_config.setdefault("sector", {})
    regime_section = strategy_config.setdefault("regime", {})
    portfolio_section = strategy_config.setdefault("portfolio", {})

    # ファクター重み（シナリオごとに上書き）
    strategy_section["weights"] = scenario["weights"]

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

    regime_section["topix_drawdown_threshold"] = scenario.get("topix_drawdown_threshold", -0.15)
    regime_section["topix_size_multiplier_bear"] = scenario.get("topix_size_multiplier_bear", 0.50)

    portfolio_section["max_positions"] = scenario.get("max_positions", 4)
    return strategy_config


def _build_risk_config(base: dict, scenario: dict[str, object]) -> dict:
    risk_config = deepcopy(base)
    risk_section = risk_config.setdefault("risk", {})
    risk_section["max_position_pct"] = scenario.get("max_position_pct", 0.22)
    risk_section["max_utilization"] = scenario.get("max_utilization", 0.80)
    return risk_config


def _build_backtest_params(scenario: dict[str, object], year: int) -> dict[str, object]:
    return {
        "start": f"{year}-01-01",
        "end": f"{year}-12-31",
        "cash": scenario["cash"],
        "allocation_method": scenario.get("allocation_method", "equal"),
        "max_positions": scenario.get("max_positions", 4),
        "max_position_pct": scenario.get("max_position_pct", 0.22),
        "max_utilization": scenario.get("max_utilization", 0.80),
        "risk_pct": scenario.get("risk_pct", 0.005),
        "stop_loss_pct": scenario.get("stop_loss_pct", 0.09),
        "min_holding_days": 5,
        "max_holding_days": scenario.get("max_holding_days", 60),
        "trailing_stop_atr": scenario.get("trailing_stop_atr_mult", 2.0),
        "threshold": scenario.get("threshold", 0.58),
        "topix_drawdown_threshold": scenario.get("topix_drawdown_threshold", -0.15),
        "topix_size_multiplier_bear": scenario.get("topix_size_multiplier_bear", 0.50),
    }


def _build_command(db_path: Path, params: dict[str, object], output_dir: Path) -> list[str]:
    return [
        sys.executable, "-m", "kabusys.backtest.run",
        "--db", str(db_path),
        "--start", str(params["start"]),
        "--end", str(params["end"]),
        "--cash", str(params["cash"]),
        "--allocation-method", str(params["allocation_method"]),
        "--max-position-pct", str(params["max_position_pct"]),
        "--max-utilization", str(params["max_utilization"]),
        "--max-positions", str(params["max_positions"]),
        "--risk-pct", str(params["risk_pct"]),
        "--stop-loss-pct", str(params["stop_loss_pct"]),
        "--min-holding-days", str(params["min_holding_days"]),
        "--max-holding-days", str(params["max_holding_days"]),
        "--trailing-stop-atr", str(params["trailing_stop_atr"]),
        "--threshold", str(params["threshold"]),
        "--topix-drawdown-threshold", str(params["topix_drawdown_threshold"]),
        "--topix-size-multiplier-bear", str(params["topix_size_multiplier_bear"]),
        "--output-format", "all",
        "--output-dir", str(output_dir),
    ]


def _extract_run_id(output: str) -> str:
    match = RUN_ID_PATTERN.search(output)
    if not match:
        raise RuntimeError("run_id could not be found in backtest output.")
    return match.group(1) or match.group(2)


def _fetch_metrics(conn: duckdb.DuckDBPyConnection, run_id: str) -> dict[str, object]:
    row = conn.execute(
        """
        SELECT created_at, cagr, sharpe, max_drawdown, win_rate,
               payoff_ratio, profit_factor, avg_holding_days, total_trades
        FROM backtest_runs WHERE run_id = ?
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
        SELECT trade_seq, date, code, side, shares, price, commission, realized_pnl
        FROM backtest_trades WHERE run_id = ? ORDER BY trade_seq
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
        json.dumps(SCENARIOS, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    original_strategy_text = STRATEGY_CONFIG_PATH.read_text(encoding="utf-8")
    original_risk_text = RISK_CONFIG_PATH.read_text(encoding="utf-8")

    fieldnames = [
        "name", "year",
        "w_momentum", "w_value", "w_volatility", "w_liquidity", "w_news",
        "run_id", "created_at", "cash", "allocation_method",
        "threshold", "stop_loss_pct", "trailing_stop_atr", "max_holding_days",
        "max_positions", "max_position_pct", "max_utilization",
        "cagr", "sharpe", "max_drawdown", "win_rate",
        "payoff_ratio", "profit_factor", "avg_holding_days", "total_trades", "trades_csv",
    ]

    print(f"output_dir={output_dir}")
    print("scenario\tyear\tcagr\tsharpe\tmax_dd\twin_rate\tpf\ttrades")

    with log_jsonl_path.open("w", encoding="utf-8") as jsonl_file, log_csv_path.open(
        "w", newline="", encoding="utf-8"
    ) as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        try:
            for scenario in SCENARIOS:
                for year in YEARS:
                    strategy_config = _build_strategy_config(context["strategy_config"], scenario)
                    risk_config = _build_risk_config(context["risk_config"], scenario)
                    _save_yaml(STRATEGY_CONFIG_PATH, strategy_config)
                    _save_yaml(RISK_CONFIG_PATH, risk_config)

                    scenario_name = str(scenario["name"])
                    run_slug = f"{scenario_name}_{year}"
                    scenario_dir = output_dir / run_slug
                    scenario_dir.mkdir(parents=True, exist_ok=True)

                    params = _build_backtest_params(scenario, year)
                    (scenario_dir / "effective_backtest_params.json").write_text(
                        json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8"
                    )

                    report_base_dir = scenario_dir / "report"
                    cmd = _build_command(db_path, params, report_base_dir)
                    print(f"\n=== running: {run_slug} ===")

                    completed = subprocess.run(
                        cmd,
                        cwd=str(REPO_ROOT),
                        capture_output=True,
                        text=True,
                        encoding=SUBPROCESS_ENCODING,
                        errors="replace",
                    )

                    (scenario_dir / "stdout.log").write_text(
                        completed.stdout or "", encoding="utf-8"
                    )
                    (scenario_dir / "stderr.log").write_text(
                        completed.stderr or "", encoding="utf-8"
                    )

                    if completed.returncode != 0:
                        raise RuntimeError(
                            f"scenario={run_slug} failed with exit code {completed.returncode}"
                        )

                    run_id = _extract_run_id(f"{completed.stdout}\n{completed.stderr}")
                    conn = duckdb.connect(str(db_path), read_only=True)
                    try:
                        metrics = _fetch_metrics(conn, run_id)
                        _export_trades_csv(conn, run_id, scenario_dir / "trades.csv")
                    finally:
                        conn.close()

                    weights = scenario["weights"]
                    record = {
                        "name": scenario_name,
                        "year": year,
                        "w_momentum": weights["momentum"],
                        "w_value": weights["value"],
                        "w_volatility": weights["volatility"],
                        "w_liquidity": weights["liquidity"],
                        "w_news": weights["news"],
                        "run_id": run_id,
                        "created_at": metrics["created_at"],
                        "cash": params["cash"],
                        "allocation_method": params["allocation_method"],
                        "threshold": params["threshold"],
                        "stop_loss_pct": params["stop_loss_pct"],
                        "trailing_stop_atr": params["trailing_stop_atr"],
                        "max_holding_days": params["max_holding_days"],
                        "max_positions": params["max_positions"],
                        "max_position_pct": params["max_position_pct"],
                        "max_utilization": params["max_utilization"],
                        **metrics,
                        "trades_csv": str(scenario_dir / "trades.csv"),
                    }

                    jsonl_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                    jsonl_file.flush()
                    writer.writerow(record)
                    csv_file.flush()

                    print(
                        f"{run_slug}\t{year}\t"
                        f"{_format_metric(metrics['cagr'])}\t"
                        f"{_format_metric(metrics['sharpe'])}\t"
                        f"{_format_metric(metrics['max_drawdown'])}\t"
                        f"{_format_metric(metrics['win_rate'])}\t"
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
```

- [ ] **Step 2: コミット**

```bash
git add backtest/backtest_improvement_plan/run_backtest_improvement_1m_ablation.py
git commit -m "feat: 1m ファクターアブレーション分析スクリプトを追加 (6シナリオ×3年)"
```

---

## セルフレビュー

**Spec coverage:**
- [x] `portfolio_drawdown_stop_pct` パラメータを `engine.py` に追加 → Task 2
- [x] `--portfolio-drawdown-stop` CLI引数 → Task 3
- [x] `_is_entry_blocked()` 純粋関数でテスト容易な設計 → Task 1-2
- [x] SELL 処理はブロックしない → Task 2 Step 7 の実装で明示
- [x] `peak_value` リセットなし → Task 2 Step 5（`max(peak_value, current_pv)` のみ）
- [x] 10m MDD検証スクリプト 6シナリオ×3年 → Task 4
- [x] 1m アブレーション 6シナリオ×3年 → Task 5
- [x] `strategy_config.yaml` の `weights` をシナリオごとに書き換え → Task 5 Step 1 `_build_strategy_config`

**Placeholder scan:** なし

**Type consistency:**
- `_is_entry_blocked(portfolio_value: float, peak_value: float, portfolio_drawdown_stop_pct: float | None) -> bool` — Task 1 と Task 2 で一致
- `portfolio_drawdown_stop_pct: float | None = None` — engine.py, run.py, スクリプトで一致
