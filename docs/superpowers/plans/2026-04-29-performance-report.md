# 運用成績サマリーレポート Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `portfolio_performance` テーブルから日次・週次・月次の運用成績 Markdown レポートを生成する CLI を実装する。

**Architecture:** `performance_collector.py` が DuckDB を read-only で参照して行データを返し、`performance_report.py` が純粋関数でレポートを組み立て、`run_performance_report.py` が CLI として統合する。`live` / `paper_trading` の環境分離は `portfolio_performance.env` 列で実現する。

**Tech Stack:** Python 3.10+, DuckDB, dataclasses, pytest, argparse

---

## ファイル構成

| ファイル | 操作 | 役割 |
|---|---|---|
| `src/kabusys/data/schema.py` | 修正 | `env` 列追加 + マイグレーション |
| `src/kabusys/operations/performance_collector.py` | 新規 | DuckDB クエリ・集約ロジック |
| `src/kabusys/operations/performance_report.py` | 新規 | build / format_markdown / save_report |
| `src/kabusys/run_performance_report.py` | 新規 | CLI エントリーポイント |
| `tests/test_performance_report.py` | 新規 | 全テスト（インメモリ DuckDB） |

---

## Task 1: Schema — portfolio_performance に env 列を追加

**Files:**
- Modify: `src/kabusys/data/schema.py`

### 背景

`_PORTFOLIO_PERFORMANCE` DDL と `_MIGRATIONS` リストの両方を更新する。  
- DDL 変更: 新規 DB では最初から `env` 列を持つ  
- マイグレーション: 既存 DB には `ALTER TABLE` で後付け追加（失敗時は既存とみなしてスキップ、既存パターンに従う）

- [ ] **Step 1: `_PORTFOLIO_PERFORMANCE` DDL に `env` 列を追加する**

`src/kabusys/data/schema.py` の `_PORTFOLIO_PERFORMANCE` を以下に変更する:

```python
_PORTFOLIO_PERFORMANCE = """
CREATE TABLE IF NOT EXISTS portfolio_performance (
    date            DATE        NOT NULL PRIMARY KEY,
    equity          DECIMAL(20,4) NOT NULL,
    cash            DECIMAL(20,4) NOT NULL,
    drawdown        DOUBLE,
    daily_return    DOUBLE,
    env             VARCHAR     NOT NULL DEFAULT 'live'
)
"""
```

- [ ] **Step 2: `_MIGRATIONS` にマイグレーションを追加する**

同ファイルの `_MIGRATIONS` リストに以下を追加する:

```python
_MIGRATIONS: list[str] = [
    # v0.x → v0.y: signals に size_multiplier を追加
    "ALTER TABLE signals ADD COLUMN size_multiplier DOUBLE NOT NULL DEFAULT 1.0",
    # v0.x → v0.y: raw_prices に adj_factor を追加
    "ALTER TABLE raw_prices ADD COLUMN adj_factor DECIMAL(18,6)",
    # v0.x → v0.y: portfolio_performance に env を追加
    "ALTER TABLE portfolio_performance ADD COLUMN env VARCHAR NOT NULL DEFAULT 'live'",
]
```

- [ ] **Step 3: スキーマ変更を確認するテストを書く**

`tests/test_performance_report.py` を新規作成し、以下を書く:

```python
"""performance_collector / performance_report のテスト"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest


# ---------------------------------------------------------------------------
# テストヘルパー
# ---------------------------------------------------------------------------


def _make_conn(
    *perf_rows: dict,
    cal_rows: list[dict] | None = None,
) -> duckdb.DuckDBPyConnection:
    """インメモリ DuckDB にテーブルとデータを投入して返す。

    perf_rows キー: date (str), equity (float), cash (float, 省略可),
                    drawdown (float|None), daily_return (float|None),
                    env (str, 省略時 "live")
    cal_rows  キー: date (str), is_trading_day (bool)
    """
    conn = duckdb.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE portfolio_performance (
            date         DATE          NOT NULL PRIMARY KEY,
            equity       DECIMAL(20,4) NOT NULL,
            cash         DECIMAL(20,4) NOT NULL DEFAULT 0,
            drawdown     DOUBLE,
            daily_return DOUBLE,
            env          VARCHAR       NOT NULL DEFAULT 'live'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE market_calendar (
            date           DATE    NOT NULL PRIMARY KEY,
            is_trading_day BOOLEAN NOT NULL
        )
        """
    )
    for r in perf_rows:
        conn.execute(
            "INSERT INTO portfolio_performance"
            " (date, equity, cash, drawdown, daily_return, env)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                r["date"],
                r["equity"],
                r.get("cash", 0.0),
                r.get("drawdown"),
                r.get("daily_return"),
                r.get("env", "live"),
            ],
        )
    for r in cal_rows or []:
        conn.execute(
            "INSERT INTO market_calendar VALUES (?, ?)",
            [r["date"], r["is_trading_day"]],
        )
    return conn


# ---------------------------------------------------------------------------
# Task 1: schema smoke test
# ---------------------------------------------------------------------------


def test_schema_env_column_exists():
    """インメモリ DB で env 列が作れる（スキーマ定義の確認）。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0, "env": "live"},
    )
    row = conn.execute(
        "SELECT env FROM portfolio_performance WHERE date = '2026-04-21'"
    ).fetchone()
    assert row is not None
    assert row[0] == "live"
```

- [ ] **Step 4: テストを実行して PASS を確認する**

```
pytest tests/test_performance_report.py::test_schema_env_column_exists -v
```

Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/data/schema.py tests/test_performance_report.py
git commit -m "feat: portfolio_performance に env 列追加 + スキーママイグレーション (Issue #195)"
```

---

## Task 2: performance_collector.py — DailyRow + collect_daily_rows

**Files:**
- Create: `src/kabusys/operations/performance_collector.py`
- Test: `tests/test_performance_report.py`

- [ ] **Step 1: collect_daily_rows の失敗テストを書く**

`tests/test_performance_report.py` に以下を追加する:

```python
from kabusys.operations.performance_collector import (
    DailyRow,
    collect_daily_rows,
)


# ---------------------------------------------------------------------------
# collect_daily_rows
# ---------------------------------------------------------------------------


def test_collect_daily_rows_basic():
    """基本的な日次行取得。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0, "daily_return": 0.004, "drawdown": -0.002},
        {"date": "2026-04-22", "equity": 5_020_000.0, "daily_return": 0.004, "drawdown": -0.001},
    )
    rows = collect_daily_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert len(rows) == 2
    assert isinstance(rows[0], DailyRow)
    assert rows[0].equity == 5_000_000.0


def test_collect_daily_rows_env_isolation():
    """live と paper_trading が混在しても正しく絞り込まれる。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0, "env": "live"},
        {"date": "2026-04-22", "equity": 4_500_000.0, "env": "paper_trading"},
    )
    rows = collect_daily_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert len(rows) == 1
    assert rows[0].env == "live"


def test_collect_daily_rows_empty():
    """データなし → []。"""
    conn = _make_conn()
    rows = collect_daily_rows(conn, "live", date(2026, 4, 1), date(2026, 4, 30))
    assert rows == []


def test_collect_daily_rows_cumulative_return():
    """累積リターンが期間内最初の equity を基準に計算される。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0},
        {"date": "2026-04-22", "equity": 5_100_000.0},
    )
    rows = collect_daily_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert rows[0].cumulative_return == pytest.approx(0.0)
    assert rows[1].cumulative_return == pytest.approx(0.02)


def test_collect_daily_rows_date_filter():
    """from_date / to_date で正しく絞り込まれる。"""
    conn = _make_conn(
        {"date": "2026-04-20", "equity": 4_900_000.0},
        {"date": "2026-04-21", "equity": 5_000_000.0},
        {"date": "2026-04-23", "equity": 5_100_000.0},
    )
    rows = collect_daily_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert len(rows) == 1
    assert rows[0].equity == 5_000_000.0
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

```
pytest tests/test_performance_report.py::test_collect_daily_rows_basic -v
```

Expected: FAIL with "ModuleNotFoundError" または "ImportError"

- [ ] **Step 3: `performance_collector.py` を作成する**

`src/kabusys/operations/performance_collector.py` を新規作成:

```python
"""運用成績データ収集モジュール。

DuckDB（portfolio_performance, market_calendar）を read-only で参照し、
DailyRow / WeeklyRow / MonthlyRow を返す。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import groupby


@dataclass
class DailyRow:
    date: date
    env: str
    equity: float
    daily_return: float | None
    drawdown: float | None
    cumulative_return: float | None  # (equity / first_equity_in_period) - 1.0


@dataclass
class WeeklyRow:
    week_label: str            # "2026-W17"
    trading_days: int
    equity_start: float | None
    equity_end: float | None
    weekly_return: float | None  # (equity_end / equity_start) - 1.0
    max_drawdown: float | None   # 週内の drawdown 最小値
    win_days: int               # daily_return > 0 の日数


@dataclass
class MonthlyRow:
    month_label: str             # "2026-04"
    trading_days: int
    equity_start: float | None
    equity_end: float | None
    monthly_return: float | None
    max_drawdown: float | None
    win_days: int


def _iso_week_label(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _month_label(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def _count_trading_days(conn, from_date: date, to_date: date) -> int:
    """market_calendar で from_date〜to_date の JPX 営業日数を返す。"""
    row = conn.execute(
        "SELECT COUNT(*) FROM market_calendar"
        " WHERE date >= ? AND date <= ? AND is_trading_day = true",
        [from_date.isoformat(), to_date.isoformat()],
    ).fetchone()
    return int(row[0]) if row else 0


def collect_daily_rows(
    conn,
    env: str,
    from_date: date,
    to_date: date,
) -> list[DailyRow]:
    """portfolio_performance から env フィルタ済み日次行を昇順で返す。

    cumulative_return は期間内最初の equity を基準に計算する。
    """
    rows = conn.execute(
        "SELECT date, env, equity, daily_return, drawdown"
        " FROM portfolio_performance"
        " WHERE env = ? AND date >= ? AND date <= ?"
        " ORDER BY date ASC",
        [env, from_date.isoformat(), to_date.isoformat()],
    ).fetchall()
    if not rows:
        return []
    first_equity = float(rows[0][2])
    result: list[DailyRow] = []
    for r in rows:
        equity = float(r[2])
        cum = (equity / first_equity - 1.0) if first_equity != 0.0 else None
        d = r[0]
        if not isinstance(d, date):
            d = date.fromisoformat(str(d))
        result.append(
            DailyRow(
                date=d,
                env=r[1],
                equity=equity,
                daily_return=float(r[3]) if r[3] is not None else None,
                drawdown=float(r[4]) if r[4] is not None else None,
                cumulative_return=cum,
            )
        )
    return result
```

- [ ] **Step 4: テストを実行して PASS を確認する**

```
pytest tests/test_performance_report.py -k "collect_daily" -v
```

Expected: 5 tests PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/operations/performance_collector.py tests/test_performance_report.py
git commit -m "feat: performance_collector - DailyRow + collect_daily_rows (Issue #195)"
```

---

## Task 3: performance_collector.py — WeeklyRow + MonthlyRow

**Files:**
- Modify: `src/kabusys/operations/performance_collector.py`
- Test: `tests/test_performance_report.py`

- [ ] **Step 1: collect_weekly_rows / collect_monthly_rows の失敗テストを書く**

`tests/test_performance_report.py` に以下を追加する:

```python
from kabusys.operations.performance_collector import (
    DailyRow,
    WeeklyRow,
    MonthlyRow,
    collect_daily_rows,
    collect_weekly_rows,
    collect_monthly_rows,
)


# ---------------------------------------------------------------------------
# collect_weekly_rows
# ---------------------------------------------------------------------------


def test_collect_weekly_rows_grouping():
    """同週の日次行が正しく 1 件の WeeklyRow に集約される。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0, "daily_return": 0.004, "drawdown": -0.002},
        {"date": "2026-04-22", "equity": 5_020_000.0, "daily_return": 0.004, "drawdown": -0.001},
        # 2026-04-21 と 2026-04-22 は同じ ISO 週（W17）
    )
    rows = collect_weekly_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert len(rows) == 1
    assert isinstance(rows[0], WeeklyRow)
    assert rows[0].week_label == "2026-W17"
    assert rows[0].equity_start == 5_000_000.0
    assert rows[0].equity_end == 5_020_000.0
    assert rows[0].win_days == 2


def test_collect_weekly_rows_trading_days():
    """market_calendar の営業日数が正しく集計される。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0},
        {"date": "2026-04-22", "equity": 5_020_000.0},
        cal_rows=[
            {"date": "2026-04-21", "is_trading_day": True},
            {"date": "2026-04-22", "is_trading_day": True},
            {"date": "2026-04-23", "is_trading_day": True},
            {"date": "2026-04-24", "is_trading_day": False},  # 祝日
            {"date": "2026-04-25", "is_trading_day": True},
        ],
    )
    rows = collect_weekly_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert rows[0].trading_days == 2  # 21 と 22 のみ（市場カレンダー上は 5 日だが portfolio_performance の範囲で集計）


def test_collect_weekly_rows_empty():
    """データなし → []。"""
    conn = _make_conn()
    rows = collect_weekly_rows(conn, "live", date(2026, 4, 1), date(2026, 4, 30))
    assert rows == []


def test_collect_weekly_rows_two_weeks():
    """2 週にまたがるデータが 2 件の WeeklyRow になる。"""
    conn = _make_conn(
        # W17: 2026-04-20(月)〜2026-04-26(日)
        {"date": "2026-04-21", "equity": 5_000_000.0, "daily_return": 0.004},
        # W18: 2026-04-27(月)〜
        {"date": "2026-04-28", "equity": 5_050_000.0, "daily_return": 0.010},
    )
    rows = collect_weekly_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 28))
    assert len(rows) == 2
    assert rows[0].week_label == "2026-W17"
    assert rows[1].week_label == "2026-W18"


# ---------------------------------------------------------------------------
# collect_monthly_rows
# ---------------------------------------------------------------------------


def test_collect_monthly_rows_grouping():
    """同月の日次行が正しく 1 件の MonthlyRow に集約される。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0, "daily_return": 0.004, "drawdown": -0.002},
        {"date": "2026-04-22", "equity": 5_020_000.0, "daily_return": -0.002, "drawdown": -0.003},
    )
    rows = collect_monthly_rows(conn, "live", date(2026, 4, 1), date(2026, 4, 30))
    assert len(rows) == 1
    assert isinstance(rows[0], MonthlyRow)
    assert rows[0].month_label == "2026-04"
    assert rows[0].equity_start == 5_000_000.0
    assert rows[0].equity_end == 5_020_000.0
    assert rows[0].max_drawdown == pytest.approx(-0.003)
    assert rows[0].win_days == 1  # daily_return > 0 は 1 日


def test_collect_monthly_rows_two_months():
    """2 ヶ月にまたがるデータが 2 件の MonthlyRow になる。"""
    conn = _make_conn(
        {"date": "2026-03-31", "equity": 4_900_000.0},
        {"date": "2026-04-01", "equity": 5_000_000.0},
    )
    rows = collect_monthly_rows(conn, "live", date(2026, 3, 1), date(2026, 4, 30))
    assert len(rows) == 2
    assert rows[0].month_label == "2026-03"
    assert rows[1].month_label == "2026-04"


def test_collect_monthly_rows_empty():
    """データなし → []。"""
    conn = _make_conn()
    rows = collect_monthly_rows(conn, "live", date(2026, 4, 1), date(2026, 4, 30))
    assert rows == []
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

```
pytest tests/test_performance_report.py -k "weekly or monthly" -v
```

Expected: FAIL with "ImportError: cannot import name 'WeeklyRow'"

- [ ] **Step 3: `collect_weekly_rows` と `collect_monthly_rows` を実装する**

`src/kabusys/operations/performance_collector.py` の末尾に追加する:

```python
def collect_weekly_rows(
    conn,
    env: str,
    from_date: date,
    to_date: date,
) -> list[WeeklyRow]:
    """日次行を ISO 週番号でグループ化して WeeklyRow を返す。

    JPX 営業日数は market_calendar で週内の from_date〜to_date 範囲を集計する。
    """
    daily = collect_daily_rows(conn, env, from_date, to_date)
    if not daily:
        return []
    result: list[WeeklyRow] = []
    for week_label, group_iter in groupby(daily, key=lambda r: _iso_week_label(r.date)):
        group = list(group_iter)
        week_from = group[0].date
        week_to = group[-1].date
        trading_days = _count_trading_days(conn, week_from, week_to)
        eq_start = group[0].equity
        eq_end = group[-1].equity
        weekly_return = (eq_end / eq_start - 1.0) if eq_start != 0.0 else None
        drawdowns = [r.drawdown for r in group if r.drawdown is not None]
        max_dd = min(drawdowns) if drawdowns else None
        win_days = sum(
            1 for r in group if r.daily_return is not None and r.daily_return > 0
        )
        result.append(
            WeeklyRow(
                week_label=week_label,
                trading_days=trading_days,
                equity_start=eq_start,
                equity_end=eq_end,
                weekly_return=weekly_return,
                max_drawdown=max_dd,
                win_days=win_days,
            )
        )
    return result


def collect_monthly_rows(
    conn,
    env: str,
    from_date: date,
    to_date: date,
) -> list[MonthlyRow]:
    """日次行を年月でグループ化して MonthlyRow を返す。

    JPX 営業日数は market_calendar で月内の from_date〜to_date 範囲を集計する。
    """
    daily = collect_daily_rows(conn, env, from_date, to_date)
    if not daily:
        return []
    result: list[MonthlyRow] = []
    for month_label, group_iter in groupby(daily, key=lambda r: _month_label(r.date)):
        group = list(group_iter)
        month_from = group[0].date
        month_to = group[-1].date
        trading_days = _count_trading_days(conn, month_from, month_to)
        eq_start = group[0].equity
        eq_end = group[-1].equity
        monthly_return = (eq_end / eq_start - 1.0) if eq_start != 0.0 else None
        drawdowns = [r.drawdown for r in group if r.drawdown is not None]
        max_dd = min(drawdowns) if drawdowns else None
        win_days = sum(
            1 for r in group if r.daily_return is not None and r.daily_return > 0
        )
        result.append(
            MonthlyRow(
                month_label=month_label,
                trading_days=trading_days,
                equity_start=eq_start,
                equity_end=eq_end,
                monthly_return=monthly_return,
                max_drawdown=max_dd,
                win_days=win_days,
            )
        )
    return result
```

- [ ] **Step 4: テストを実行して PASS を確認する**

```
pytest tests/test_performance_report.py -k "weekly or monthly" -v
```

Expected: 7 tests PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/operations/performance_collector.py tests/test_performance_report.py
git commit -m "feat: performance_collector - WeeklyRow + MonthlyRow (Issue #195)"
```

---

## Task 4: performance_report.py — build_report

**Files:**
- Create: `src/kabusys/operations/performance_report.py`
- Test: `tests/test_performance_report.py`

- [ ] **Step 1: build_report の失敗テストを書く**

`tests/test_performance_report.py` に以下を追加する:

```python
from kabusys.operations.performance_report import (
    PerformanceReport,
    build_report,
    format_markdown,
    save_report,
)


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def _make_daily_rows() -> list:
    from kabusys.operations.performance_collector import DailyRow
    return [
        DailyRow(date=date(2026, 4, 21), env="live", equity=5_000_000.0,
                 daily_return=0.004, drawdown=-0.002, cumulative_return=0.0),
        DailyRow(date=date(2026, 4, 22), env="live", equity=5_020_000.0,
                 daily_return=-0.001, drawdown=-0.003, cumulative_return=0.004),
        DailyRow(date=date(2026, 4, 23), env="live", equity=5_040_000.0,
                 daily_return=0.004, drawdown=-0.001, cumulative_return=0.008),
    ]


def test_build_report_summary_basic():
    """cumulative_return / max_drawdown / win_rate が正しく計算される。"""
    rows = _make_daily_rows()
    report = build_report(
        rows,
        report_type="daily",
        env="live",
        from_date=date(2026, 4, 21),
        to_date=date(2026, 4, 23),
    )
    assert isinstance(report, PerformanceReport)
    assert report.summary["total_trading_days"] == 3
    assert report.summary["equity_start"] == 5_000_000.0
    assert report.summary["equity_end"] == 5_040_000.0
    assert report.summary["cumulative_return"] == pytest.approx(0.008)
    assert report.summary["max_drawdown"] == pytest.approx(-0.003)
    assert report.summary["win_rate"] == pytest.approx(2 / 3)


def test_build_report_empty_rows():
    """rows=[] のとき summary は None 値（total_trading_days=0）。"""
    report = build_report(
        [],
        report_type="daily",
        env="live",
        from_date=date(2026, 4, 21),
        to_date=date(2026, 4, 23),
    )
    assert report.summary["total_trading_days"] == 0
    assert report.summary["cumulative_return"] is None
    assert report.summary["max_drawdown"] is None
    assert report.summary["win_rate"] is None


def test_build_report_weekly_summary():
    """週次 rows から summary が正しく集約される。"""
    from kabusys.operations.performance_collector import WeeklyRow
    rows = [
        WeeklyRow(week_label="2026-W17", trading_days=5,
                  equity_start=5_000_000.0, equity_end=5_025_000.0,
                  weekly_return=0.005, max_drawdown=-0.002, win_days=3),
        WeeklyRow(week_label="2026-W18", trading_days=5,
                  equity_start=5_025_000.0, equity_end=5_050_000.0,
                  weekly_return=0.005, max_drawdown=-0.001, win_days=4),
    ]
    report = build_report(
        rows,
        report_type="weekly",
        env="live",
        from_date=date(2026, 4, 20),
        to_date=date(2026, 4, 30),
    )
    assert report.summary["total_trading_days"] == 10
    assert report.summary["equity_start"] == 5_000_000.0
    assert report.summary["equity_end"] == 5_050_000.0
    assert report.summary["max_drawdown"] == pytest.approx(-0.002)
    assert report.summary["win_rate"] == pytest.approx(7 / 10)
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

```
pytest tests/test_performance_report.py -k "build_report" -v
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: `performance_report.py` を作成する（build_report まで）**

`src/kabusys/operations/performance_report.py` を新規作成:

```python
"""運用成績サマリーレポート生成モジュール。

DB への参照は行わず、呼び出し元から受け取ったデータのみを使用する。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from kabusys.operations.performance_collector import DailyRow, MonthlyRow, WeeklyRow


@dataclass
class PerformanceReport:
    report_type: str   # "daily" | "weekly" | "monthly"
    env: str           # "live" | "paper_trading"
    generated_at: str  # ISO 8601 UTC
    from_date: str     # YYYY-MM-DD
    to_date: str       # YYYY-MM-DD
    rows: list         # list[DailyRow | WeeklyRow | MonthlyRow]
    summary: dict


def build_report(
    rows: list,
    *,
    report_type: str,
    env: str,
    from_date: date,
    to_date: date,
) -> PerformanceReport:
    """PerformanceReport を構築する。rows が空の場合は summary を None 値で返す。"""
    if not rows:
        summary: dict = {
            "total_trading_days": 0,
            "cumulative_return": None,
            "max_drawdown": None,
            "win_rate": None,
            "equity_start": None,
            "equity_end": None,
        }
    elif report_type == "daily":
        total = len(rows)
        eq_start = rows[0].equity
        eq_end = rows[-1].equity
        cum = (eq_end / eq_start - 1.0) if eq_start != 0.0 else None
        drawdowns = [r.drawdown for r in rows if r.drawdown is not None]
        max_dd = min(drawdowns) if drawdowns else None
        win = sum(1 for r in rows if r.daily_return is not None and r.daily_return > 0)
        summary = {
            "total_trading_days": total,
            "cumulative_return": cum,
            "max_drawdown": max_dd,
            "win_rate": win / total if total > 0 else None,
            "equity_start": eq_start,
            "equity_end": eq_end,
        }
    else:
        # weekly または monthly
        total = sum(r.trading_days for r in rows)
        eq_start = rows[0].equity_start
        eq_end = rows[-1].equity_end
        cum = (eq_end / eq_start - 1.0) if (eq_start and eq_start != 0.0) else None
        drawdowns = [r.max_drawdown for r in rows if r.max_drawdown is not None]
        max_dd = min(drawdowns) if drawdowns else None
        win = sum(r.win_days for r in rows)
        summary = {
            "total_trading_days": total,
            "cumulative_return": cum,
            "max_drawdown": max_dd,
            "win_rate": win / total if total > 0 else None,
            "equity_start": eq_start,
            "equity_end": eq_end,
        }
    return PerformanceReport(
        report_type=report_type,
        env=env,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        from_date=from_date.isoformat(),
        to_date=to_date.isoformat(),
        rows=rows,
        summary=summary,
    )


def format_markdown(report: PerformanceReport) -> str:
    raise NotImplementedError


def save_report(
    report: PerformanceReport,
    output_dir: Path | str | None = None,
) -> Path:
    raise NotImplementedError
```

- [ ] **Step 4: テストを実行して PASS を確認する**

```
pytest tests/test_performance_report.py -k "build_report" -v
```

Expected: 3 tests PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/operations/performance_report.py tests/test_performance_report.py
git commit -m "feat: performance_report - PerformanceReport dataclass + build_report (Issue #195)"
```

---

## Task 5: performance_report.py — format_markdown + save_report

**Files:**
- Modify: `src/kabusys/operations/performance_report.py`
- Test: `tests/test_performance_report.py`

- [ ] **Step 1: format_markdown / save_report の失敗テストを書く**

`tests/test_performance_report.py` に以下を追加する:

```python
# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------


def test_format_markdown_daily():
    """日次 Markdown にサマリー表と日次明細テーブルが含まれる。"""
    rows = _make_daily_rows()
    report = build_report(
        rows, report_type="daily", env="live",
        from_date=date(2026, 4, 21), to_date=date(2026, 4, 23),
    )
    md = format_markdown(report)
    assert "# 運用成績レポート（日次）" in md
    assert "## サマリー" in md
    assert "## 日次明細" in md
    assert "2026-04-21" in md
    assert "累積リターン" in md


def test_format_markdown_weekly():
    """週次 Markdown に週次明細テーブルが含まれる。"""
    from kabusys.operations.performance_collector import WeeklyRow
    rows = [
        WeeklyRow(week_label="2026-W17", trading_days=5,
                  equity_start=5_000_000.0, equity_end=5_025_000.0,
                  weekly_return=0.005, max_drawdown=-0.002, win_days=3),
    ]
    report = build_report(
        rows, report_type="weekly", env="live",
        from_date=date(2026, 4, 20), to_date=date(2026, 4, 26),
    )
    md = format_markdown(report)
    assert "# 運用成績レポート（週次）" in md
    assert "## 週次明細" in md
    assert "2026-W17" in md


def test_format_markdown_monthly():
    """月次 Markdown に月次明細テーブルが含まれる。"""
    from kabusys.operations.performance_collector import MonthlyRow
    rows = [
        MonthlyRow(month_label="2026-04", trading_days=20,
                   equity_start=5_000_000.0, equity_end=5_100_000.0,
                   monthly_return=0.02, max_drawdown=-0.005, win_days=12),
    ]
    report = build_report(
        rows, report_type="monthly", env="live",
        from_date=date(2026, 4, 1), to_date=date(2026, 4, 30),
    )
    md = format_markdown(report)
    assert "# 運用成績レポート（月次）" in md
    assert "## 月次明細" in md
    assert "2026-04" in md


def test_format_markdown_empty_rows():
    """rows=[] でも正常に Markdown が出力される。"""
    report = build_report(
        [], report_type="daily", env="live",
        from_date=date(2026, 4, 21), to_date=date(2026, 4, 21),
    )
    md = format_markdown(report)
    assert "# 運用成績レポート（日次）" in md
    assert "0 日" in md


# ---------------------------------------------------------------------------
# save_report
# ---------------------------------------------------------------------------


def test_save_report_daily(tmp_path):
    """`artifacts/performance/live/daily/{date}/report.md` が生成される。"""
    rows = _make_daily_rows()
    report = build_report(
        rows, report_type="daily", env="live",
        from_date=date(2026, 4, 21), to_date=date(2026, 4, 23),
    )
    saved = save_report(report, output_dir=tmp_path)
    expected = tmp_path / "live" / "daily" / "2026-04-23" / "report.md"
    assert expected.exists()
    assert saved == expected.parent


def test_save_report_weekly(tmp_path):
    """`artifacts/performance/live/weekly/YYYY-Www/report.md` が生成される。"""
    from kabusys.operations.performance_collector import WeeklyRow
    rows = [
        WeeklyRow(week_label="2026-W17", trading_days=5,
                  equity_start=5_000_000.0, equity_end=5_025_000.0,
                  weekly_return=0.005, max_drawdown=-0.002, win_days=3),
    ]
    report = build_report(
        rows, report_type="weekly", env="live",
        from_date=date(2026, 4, 20), to_date=date(2026, 4, 26),
    )
    saved = save_report(report, output_dir=tmp_path)
    expected = tmp_path / "live" / "weekly" / "2026-W17" / "report.md"
    assert expected.exists()
    assert saved == expected.parent


def test_save_report_monthly(tmp_path):
    """`artifacts/performance/live/monthly/YYYY-MM/report.md` が生成される。"""
    from kabusys.operations.performance_collector import MonthlyRow
    rows = [
        MonthlyRow(month_label="2026-04", trading_days=20,
                   equity_start=5_000_000.0, equity_end=5_100_000.0,
                   monthly_return=0.02, max_drawdown=-0.005, win_days=12),
    ]
    report = build_report(
        rows, report_type="monthly", env="paper_trading",
        from_date=date(2026, 4, 1), to_date=date(2026, 4, 30),
    )
    saved = save_report(report, output_dir=tmp_path)
    expected = tmp_path / "paper_trading" / "monthly" / "2026-04" / "report.md"
    assert expected.exists()
    assert saved == expected.parent
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

```
pytest tests/test_performance_report.py -k "format_markdown or save_report" -v
```

Expected: FAIL with "NotImplementedError"

- [ ] **Step 3: `format_markdown` と `save_report` を実装する**

`src/kabusys/operations/performance_report.py` の `format_markdown` と `save_report` を置き換える:

```python
_REPORT_TYPE_JA = {"daily": "日次", "weekly": "週次", "monthly": "月次"}


def _fmt_return(v: float | None) -> str:
    if v is None:
        return "N/A"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2%}"


def _fmt_yen(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"¥{int(v):,}"


def _fmt_rate(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v:.1%}"


def format_markdown(report: PerformanceReport) -> str:
    """PerformanceReport を Markdown 文字列に変換する。"""
    type_ja = _REPORT_TYPE_JA.get(report.report_type, report.report_type)
    s = report.summary
    lines = [
        f"# 運用成績レポート（{type_ja}）",
        "",
        f"- 環境: {report.env}",
        f"- 期間: {report.from_date} 〜 {report.to_date}",
        f"- 生成日時: {report.generated_at}",
        "",
        "## サマリー",
        "",
        "| 項目 | 値 |",
        "|---|---|",
        f"| 営業日数 | {s['total_trading_days']} 日 |",
        f"| 累積リターン | {_fmt_return(s['cumulative_return'])} |",
        f"| 最大ドローダウン | {_fmt_return(s['max_drawdown'])} |",
        f"| 勝率 | {_fmt_rate(s['win_rate'])} |",
        f"| 期首総資産 | {_fmt_yen(s['equity_start'])} |",
        f"| 期末総資産 | {_fmt_yen(s['equity_end'])} |",
        "",
    ]

    if report.report_type == "daily":
        lines += [
            "## 日次明細",
            "",
            "| 日付 | 総資産 | 日次リターン | ドローダウン | 累積リターン |",
            "|---|---|---|---|---|",
        ]
        for r in report.rows:
            lines.append(
                f"| {r.date} | {_fmt_yen(r.equity)} | {_fmt_return(r.daily_return)}"
                f" | {_fmt_return(r.drawdown)} | {_fmt_return(r.cumulative_return)} |"
            )
    elif report.report_type == "weekly":
        lines += [
            "## 週次明細",
            "",
            "| 週 | 営業日数 | 期首資産 | 期末資産 | 週次リターン | 最大DD | 勝ち日数 |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in report.rows:
            lines.append(
                f"| {r.week_label} | {r.trading_days} | {_fmt_yen(r.equity_start)}"
                f" | {_fmt_yen(r.equity_end)} | {_fmt_return(r.weekly_return)}"
                f" | {_fmt_return(r.max_drawdown)} | {r.win_days} |"
            )
    else:  # monthly
        lines += [
            "## 月次明細",
            "",
            "| 月 | 営業日数 | 期首資産 | 期末資産 | 月次リターン | 最大DD | 勝ち日数 |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in report.rows:
            lines.append(
                f"| {r.month_label} | {r.trading_days} | {_fmt_yen(r.equity_start)}"
                f" | {_fmt_yen(r.equity_end)} | {_fmt_return(r.monthly_return)}"
                f" | {_fmt_return(r.max_drawdown)} | {r.win_days} |"
            )

    lines.append("")
    return "\n".join(lines)


def save_report(
    report: PerformanceReport,
    output_dir: Path | str | None = None,
) -> Path:
    """artifacts/performance/{env}/{report_type}/{period}/report.md に保存する。

    period:
      daily   → report.to_date (YYYY-MM-DD)
      weekly  → rows[-1].week_label (YYYY-Www)
      monthly → rows[-1].month_label (YYYY-MM)
      rows が空の場合は report.to_date を使用。
    """
    base = Path(output_dir) if output_dir else Path("artifacts") / "performance"

    if report.report_type == "weekly" and report.rows:
        period = report.rows[-1].week_label
    elif report.report_type == "monthly" and report.rows:
        period = report.rows[-1].month_label
    else:
        period = report.to_date  # daily またはフォールバック

    run_dir = base / report.env / report.report_type / period
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")
    return run_dir
```

- [ ] **Step 4: テストを実行して PASS を確認する**

```
pytest tests/test_performance_report.py -k "format_markdown or save_report" -v
```

Expected: 7 tests PASS

- [ ] **Step 5: 全テストを実行して回帰がないことを確認する**

```
pytest tests/test_performance_report.py -v
```

Expected: 全テスト PASS

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/operations/performance_report.py tests/test_performance_report.py
git commit -m "feat: performance_report - format_markdown + save_report (Issue #195)"
```

---

## Task 6: run_performance_report.py — CLI

**Files:**
- Create: `src/kabusys/run_performance_report.py`
- Test: `tests/test_performance_report.py`

- [ ] **Step 1: CLI の失敗テストを書く**

`tests/test_performance_report.py` に以下を追加する:

```python
# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_returns_1_when_no_data(tmp_path, monkeypatch):
    """データなしのとき終了コード 1 を返す。"""
    import duckdb as _duckdb
    from kabusys.run_performance_report import main

    db_path = tmp_path / "test.duckdb"
    conn = _duckdb.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE portfolio_performance (
            date DATE NOT NULL PRIMARY KEY, equity DECIMAL(20,4) NOT NULL,
            cash DECIMAL(20,4) NOT NULL DEFAULT 0, drawdown DOUBLE,
            daily_return DOUBLE, env VARCHAR NOT NULL DEFAULT 'live'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE market_calendar (
            date DATE NOT NULL PRIMARY KEY, is_trading_day BOOLEAN NOT NULL
        )
        """
    )
    conn.close()

    monkeypatch.setenv("DUCKDB_PATH", str(db_path))
    result = main(["--type", "daily", "--from", "2026-04-01", "--to", "2026-04-30"])
    assert result == 1


def test_cli_returns_0_when_data_exists(tmp_path, monkeypatch):
    """データありのとき終了コード 0 を返す。"""
    import duckdb as _duckdb
    from kabusys.run_performance_report import main

    db_path = tmp_path / "test.duckdb"
    conn = _duckdb.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE portfolio_performance (
            date DATE NOT NULL PRIMARY KEY, equity DECIMAL(20,4) NOT NULL,
            cash DECIMAL(20,4) NOT NULL DEFAULT 0, drawdown DOUBLE,
            daily_return DOUBLE, env VARCHAR NOT NULL DEFAULT 'live'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE market_calendar (
            date DATE NOT NULL PRIMARY KEY, is_trading_day BOOLEAN NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO portfolio_performance (date, equity, cash, env) VALUES ('2026-04-21', 5000000, 0, 'live')"
    )
    conn.close()

    monkeypatch.setenv("DUCKDB_PATH", str(db_path))
    result = main(["--type", "daily", "--from", "2026-04-21", "--to", "2026-04-21"])
    assert result == 0
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

```
pytest tests/test_performance_report.py -k "cli" -v
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: `run_performance_report.py` を作成する**

`src/kabusys/run_performance_report.py` を新規作成:

```python
"""運用成績サマリーレポート エントリーポイント。

使用方法:
    python -m kabusys.run_performance_report --type daily
    python -m kabusys.run_performance_report --type weekly --env paper_trading
    python -m kabusys.run_performance_report --type monthly --from 2026-01-01 --to 2026-04-30
    python -m kabusys.run_performance_report --type daily --save
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta

import duckdb

from kabusys.config import Settings
from kabusys.operations.performance_collector import (
    collect_daily_rows,
    collect_monthly_rows,
    collect_weekly_rows,
)
from kabusys.operations.performance_report import (
    build_report,
    format_markdown,
    save_report,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="運用成績サマリーレポートを生成する")
    parser.add_argument(
        "--type",
        dest="report_type",
        required=True,
        choices=["daily", "weekly", "monthly"],
        help="レポート種別 (daily / weekly / monthly)",
    )
    parser.add_argument(
        "--env",
        default="live",
        choices=["live", "paper_trading"],
        help="対象環境 (live / paper_trading)、省略時は live",
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        type=lambda s: date.fromisoformat(s),
        default=date.today() - timedelta(days=30),
        metavar="YYYY-MM-DD",
        help="集計開始日（省略時は過去30日）",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        type=lambda s: date.fromisoformat(s),
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="集計終了日（省略時は今日）",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="artifacts/performance/ に保存する",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)

    try:
        if args.report_type == "daily":
            rows = collect_daily_rows(conn, args.env, args.from_date, args.to_date)
        elif args.report_type == "weekly":
            rows = collect_weekly_rows(conn, args.env, args.from_date, args.to_date)
        else:
            rows = collect_monthly_rows(conn, args.env, args.from_date, args.to_date)
    finally:
        conn.close()

    report = build_report(
        rows,
        report_type=args.report_type,
        env=args.env,
        from_date=args.from_date,
        to_date=args.to_date,
    )

    print(format_markdown(report))

    if args.save:
        saved_path = save_report(report)
        print(f"\n保存先: {saved_path}")

    return 1 if not rows else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テストを実行して PASS を確認する**

```
pytest tests/test_performance_report.py -k "cli" -v
```

Expected: 2 tests PASS

- [ ] **Step 5: 全テストを実行して回帰がないことを確認する**

```
pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: 全テスト PASS（既存テスト含む）

- [ ] **Step 6: ruff チェックを通す**

```
ruff check src/kabusys/operations/performance_collector.py src/kabusys/operations/performance_report.py src/kabusys/run_performance_report.py tests/test_performance_report.py
```

エラーがあれば修正する。よくある問題: `from __future__ import annotations` の位置（先頭）、未使用インポート。

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/run_performance_report.py tests/test_performance_report.py
git commit -m "feat: run_performance_report CLI エントリーポイント (Issue #195)"
```

---

## 完了確認

- [ ] `pytest tests/test_performance_report.py -v` で全テスト PASS
- [ ] `pytest tests/ -v --tb=short 2>&1 | tail -5` で既存テストも PASS
- [ ] `ruff check src/kabusys/` でエラーなし
- [ ] `python -m kabusys.run_performance_report --type daily --help` が正常に動作する
