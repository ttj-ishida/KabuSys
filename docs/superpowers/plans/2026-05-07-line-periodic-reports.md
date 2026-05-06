# LINE 定期レポート送信 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `LineNotifier` 基盤を活用し、Execution 起動時（朝）と portfolio_construction 完了後（夜）に定期 LINE 通知を送信する。金曜夜に週次、月末夜に月次のサマリも送る。

**Architecture:** メッセージ生成関数を `src/kabusys/operations/line_reports.py` に純粋関数として集約しテスト容易にする。`run_execution.py`（朝通知）と `scripts/run_portfolio_construction.py`（夜/週次/月次通知）に `build_notifier()` を追加して送信する。`LINE_NOTIFY_ENABLED=false` では `NullNotifier.send()` が呼ばれるだけで Core 機能に影響しない。

**Tech Stack:** Python 3.10+, 既存 `LineNotifier` / `NullNotifier` / `build_notifier()` (`operations/notifier.py`), `performance_collector.py`, `execution_startup_report.py`

---

## ファイル構成

| 操作 | パス | 役割 |
|---|---|---|
| Create | `src/kabusys/operations/line_reports.py` | LINE メッセージ文字列生成（純粋関数 4 本） |
| Create | `tests/test_line_reports.py` | line_reports.py のユニットテスト |
| Modify | `src/kabusys/run_execution.py` | 起動後 Startup Summary を元に朝通知を送信 |
| Modify | `scripts/run_portfolio_construction.py` | 完了後に夜通知・金曜週次・月末月次を送信 |

---

### Task 1: `line_reports.py` — メッセージ生成関数

**Files:**
- Create: `src/kabusys/operations/line_reports.py`
- Create: `tests/test_line_reports.py`

- [ ] **Step 1: テストを書く**

`tests/test_line_reports.py` を新規作成する:

```python
"""tests/test_line_reports.py — LINE 定期レポートメッセージ生成テスト"""

from __future__ import annotations

from kabusys.operations.line_reports import (
    format_evening_message,
    format_monthly_message,
    format_morning_message,
    format_weekly_message,
)


class TestFormatMorningMessage:
    def test_ready_with_pending(self):
        msg = format_morning_message(
            status="READY",
            orders_no_status=0,
            pending_count=3,
            report_date="2026-05-07",
        )
        assert "2026-05-07" in msg
        assert "READY" in msg
        assert "3" in msg

    def test_blocked_shows_orders_no_status(self):
        msg = format_morning_message(
            status="BLOCKED",
            orders_no_status=2,
            pending_count=0,
            report_date="2026-05-07",
        )
        assert "BLOCKED" in msg
        assert "2" in msg

    def test_ready_with_warnings(self):
        msg = format_morning_message(
            status="READY_WITH_WARNINGS",
            orders_no_status=0,
            pending_count=1,
            report_date="2026-05-07",
        )
        assert "READY_WITH_WARNINGS" in msg

    def test_zero_pending(self):
        msg = format_morning_message(
            status="READY",
            orders_no_status=0,
            pending_count=0,
            report_date="2026-05-07",
        )
        assert "0" in msg


class TestFormatEveningMessage:
    def test_with_daily_return(self):
        msg = format_evening_message(
            inserted=4,
            report_date="2026-05-07",
            daily_return=0.032,
        )
        assert "2026-05-07" in msg
        assert "4" in msg
        assert "3.2" in msg

    def test_negative_daily_return(self):
        msg = format_evening_message(
            inserted=2,
            report_date="2026-05-07",
            daily_return=-0.015,
        )
        assert "-1.5" in msg

    def test_no_daily_return(self):
        msg = format_evening_message(
            inserted=0,
            report_date="2026-05-07",
            daily_return=None,
        )
        assert "2026-05-07" in msg
        assert "0" in msg

    def test_return_is_string(self):
        msg = format_evening_message(
            inserted=3,
            report_date="2026-05-07",
            daily_return=0.01,
        )
        assert isinstance(msg, str)
        assert len(msg) > 0


class TestFormatWeeklyMessage:
    def test_with_full_summary(self):
        summary = {
            "cumulative_return": 0.032,
            "max_drawdown": -0.015,
            "win_rate": 0.6,
            "equity_start": 10_000_000,
            "equity_end": 10_320_000,
        }
        msg = format_weekly_message(
            summary=summary,
            from_date="2026-04-28",
            to_date="2026-05-02",
        )
        assert "2026-04-28" in msg
        assert "2026-05-02" in msg
        assert "3.2" in msg
        assert "60.0" in msg

    def test_with_none_values(self):
        summary = {
            "cumulative_return": None,
            "max_drawdown": None,
            "win_rate": None,
            "equity_start": None,
            "equity_end": None,
        }
        msg = format_weekly_message(
            summary=summary,
            from_date="2026-04-28",
            to_date="2026-05-02",
        )
        assert isinstance(msg, str)
        assert len(msg) > 0


class TestFormatMonthlyMessage:
    def test_with_full_summary(self):
        summary = {
            "cumulative_return": 0.058,
            "max_drawdown": -0.023,
            "win_rate": 0.553,
            "equity_start": 10_000_000,
            "equity_end": 10_580_000,
        }
        msg = format_monthly_message(
            summary=summary,
            from_date="2026-04-01",
            to_date="2026-04-30",
        )
        assert "2026-04-01" in msg
        assert "5.8" in msg
        assert "55.3" in msg

    def test_with_none_values(self):
        summary = {
            "cumulative_return": None,
            "max_drawdown": None,
            "win_rate": None,
            "equity_start": None,
            "equity_end": None,
        }
        msg = format_monthly_message(
            summary=summary,
            from_date="2026-04-01",
            to_date="2026-04-30",
        )
        assert isinstance(msg, str)
        assert len(msg) > 0
```

- [ ] **Step 2: テストが失敗することを確認**

```
python -m pytest tests/test_line_reports.py -v
```

Expected: `ImportError: cannot import name 'format_morning_message' from 'kabusys.operations.line_reports'`

- [ ] **Step 3: `line_reports.py` を実装**

`src/kabusys/operations/line_reports.py` を新規作成する:

```python
"""line_reports.py — LINE 定期レポートのメッセージ文字列生成。

すべて純粋関数。送信は呼び出し元（run_execution.py 等）が行う。
"""

from __future__ import annotations


def _fmt_rate(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:+.1f}%"


def _fmt_yen(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.0f} 円"


def format_morning_message(
    *,
    status: str,
    orders_no_status: int,
    pending_count: int,
    report_date: str,
) -> str:
    """Execution 起動完了時の朝通知メッセージを生成する。

    Args:
        status:           READY / READY_WITH_WARNINGS / BLOCKED
        orders_no_status: ステータス不明の注文件数
        pending_count:    当日 signal_queue の pending 件数
        report_date:      YYYY-MM-DD
    """
    lines = [
        f"【KabuSys 朝】{report_date}",
        f"ステータス: {status}",
        f"pending シグナル: {pending_count} 件",
    ]
    if orders_no_status > 0:
        lines.append(f"⚠ ステータス不明の注文: {orders_no_status} 件（要確認）")
    return "\n".join(lines)


def format_evening_message(
    *,
    inserted: int,
    report_date: str,
    daily_return: float | None = None,
) -> str:
    """portfolio_construction 完了後の夜通知メッセージを生成する。

    Args:
        inserted:     signal_queue に挿入した件数
        report_date:  YYYY-MM-DD
        daily_return: 当日の日次リターン（0.032 = +3.2%）、取得できない場合は None
    """
    lines = [
        f"【KabuSys 夜】{report_date}",
        f"翌日シグナル: {inserted} 件",
        f"当日リターン: {_fmt_rate(daily_return)}",
    ]
    return "\n".join(lines)


def format_weekly_message(
    *,
    summary: dict,
    from_date: str,
    to_date: str,
) -> str:
    """週次サマリ通知メッセージを生成する。

    Args:
        summary:   PerformanceReport.summary dict
        from_date: YYYY-MM-DD（週の開始日）
        to_date:   YYYY-MM-DD（週の終了日）
    """
    lines = [
        f"【KabuSys 週次】{from_date} 〜 {to_date}",
        f"累積リターン: {_fmt_rate(summary.get('cumulative_return'))}",
        f"最大ドローダウン: {_fmt_rate(summary.get('max_drawdown'))}",
        f"勝率: {_fmt_rate(summary.get('win_rate'))}",
        f"期末資産: {_fmt_yen(summary.get('equity_end'))}",
    ]
    return "\n".join(lines)


def format_monthly_message(
    *,
    summary: dict,
    from_date: str,
    to_date: str,
) -> str:
    """月次サマリ通知メッセージを生成する。

    Args:
        summary:   PerformanceReport.summary dict
        from_date: YYYY-MM-DD（月初）
        to_date:   YYYY-MM-DD（月末）
    """
    lines = [
        f"【KabuSys 月次】{from_date} 〜 {to_date}",
        f"累積リターン: {_fmt_rate(summary.get('cumulative_return'))}",
        f"最大ドローダウン: {_fmt_rate(summary.get('max_drawdown'))}",
        f"勝率: {_fmt_rate(summary.get('win_rate'))}",
        f"期末資産: {_fmt_yen(summary.get('equity_end'))}",
    ]
    return "\n".join(lines)
```

- [ ] **Step 4: テストが通ることを確認**

```
python -m pytest tests/test_line_reports.py -v
```

Expected: 13 passed

- [ ] **Step 5: ruff チェック**

```
python -m ruff check src/kabusys/operations/line_reports.py tests/test_line_reports.py
python -m ruff format --check src/kabusys/operations/line_reports.py tests/test_line_reports.py
```

Expected: `All checks passed!` / `N files already formatted`

- [ ] **Step 6: コミット**

```
git add src/kabusys/operations/line_reports.py tests/test_line_reports.py
git commit -m "feat: LINE 定期レポートメッセージ生成関数を追加 (Issue #256)"
```

---

### Task 2: `run_execution.py` に朝通知を追加

**Files:**
- Modify: `src/kabusys/run_execution.py:32-36`（imports）、`src/kabusys/run_execution.py:278-291`（report 生成後）

- [ ] **Step 1: テストを書く**

`tests/test_line_reports.py` の末尾に追加する:

```python
# run_execution の朝通知ヘルパーのテスト
from unittest.mock import MagicMock, patch


class TestCountPendingSignals:
    def test_returns_count_from_db(self):
        from kabusys.run_execution import _count_pending_signals
        from datetime import date

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (5,)
        result = _count_pending_signals(conn, date(2026, 5, 7))
        assert result == 5

    def test_returns_zero_when_no_rows(self):
        from kabusys.run_execution import _count_pending_signals
        from datetime import date

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (0,)
        result = _count_pending_signals(conn, date(2026, 5, 7))
        assert result == 0
```

- [ ] **Step 2: テストが失敗することを確認**

```
python -m pytest tests/test_line_reports.py::TestCountPendingSignals -v
```

Expected: `ImportError: cannot import name '_count_pending_signals' from 'kabusys.run_execution'`

- [ ] **Step 3: `run_execution.py` を修正**

`src/kabusys/run_execution.py` の import セクション（line 32 付近）に追加:

```python
from kabusys.operations.line_reports import format_morning_message  # noqa: E402
from kabusys.operations.notifier import build_notifier  # noqa: E402
```

同ファイルに `_count_pending_signals` 関数を追加（`_load_risk_config` の直前付近、line 44 付近）:

```python
def _count_pending_signals(conn, target_date: date) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM signal_queue WHERE date = ? AND status = 'pending'",
        [target_date],
    ).fetchone()
    return int(row[0]) if row else 0
```

同ファイルの Execution Startup Summary 生成ブロック（line 278-291）を以下に置き換える:

```python
        # 起動時リコンシリエーション + Execution Startup Summary 生成
        today = date.today()
        reconcile_result = reconciler.run()
        _report = None
        try:
            _report = build_report(
                reconcile_result=reconcile_result, startup_date=today
            )
            print(format_cli_summary(_report))
            save_report(_report)
        except Exception:
            logger.warning(
                "Execution Startup Summary の生成に失敗しました（起動を続行します）",
                exc_info=True,
            )

        # 朝の LINE 通知（失敗しても起動を継続する）
        try:
            notifier = build_notifier(settings)
            pending_count = _count_pending_signals(duckdb_conn, today)
            status = _report.status if _report is not None else "UNKNOWN"
            orders_no_status = _report.orders_no_status if _report is not None else 0
            msg = format_morning_message(
                status=status,
                orders_no_status=orders_no_status,
                pending_count=pending_count,
                report_date=today.isoformat(),
            )
            notifier.send(msg)
        except Exception:
            logger.warning("朝の LINE 通知に失敗しました（起動を続行します）", exc_info=True)
```

- [ ] **Step 4: テストが通ることを確認**

```
python -m pytest tests/test_line_reports.py::TestCountPendingSignals -v
```

Expected: 2 passed

- [ ] **Step 5: 全テスト回帰確認**

```
python -m pytest tests/test_line_reports.py tests/test_notifier.py -v
```

Expected: 全テスト pass

- [ ] **Step 6: ruff チェック**

```
python -m ruff check src/kabusys/run_execution.py
python -m ruff format --check src/kabusys/run_execution.py
```

Expected: `All checks passed!`

- [ ] **Step 7: コミット**

```
git add src/kabusys/run_execution.py tests/test_line_reports.py
git commit -m "feat: run_execution.py に朝の LINE 通知を追加 (Issue #256)"
```

---

### Task 3: `run_portfolio_construction.py` に夜/週次/月次通知を追加

**Files:**
- Modify: `scripts/run_portfolio_construction.py`

- [ ] **Step 1: テストを書く**

`tests/test_line_reports.py` の末尾に追加する:

```python
class TestGetTodayReturn:
    def test_returns_float_when_row_exists(self):
        from scripts.run_portfolio_construction import _get_today_return
        from datetime import date

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (0.032,)
        result = _get_today_return(conn, date(2026, 5, 7))
        assert result == 0.032

    def test_returns_none_when_no_row(self):
        from scripts.run_portfolio_construction import _get_today_return
        from datetime import date

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        result = _get_today_return(conn, date(2026, 5, 7))
        assert result is None

    def test_returns_none_when_value_is_null(self):
        from scripts.run_portfolio_construction import _get_today_return
        from datetime import date

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (None,)
        result = _get_today_return(conn, date(2026, 5, 7))
        assert result is None
```

- [ ] **Step 2: テストが失敗することを確認**

```
python -m pytest tests/test_line_reports.py::TestGetTodayReturn -v
```

Expected: `ImportError: cannot import name '_get_today_return' from 'scripts.run_portfolio_construction'`

- [ ] **Step 3: `run_portfolio_construction.py` を修正**

import セクションの末尾（`from kabusys.utils.logging_setup import setup_logging` の後）に追加:

```python
import calendar

from kabusys.operations.line_reports import (
    format_evening_message,
    format_monthly_message,
    format_weekly_message,
)
from kabusys.operations.notifier import build_notifier
from kabusys.operations.performance_collector import (
    collect_monthly_rows,
    collect_weekly_rows,
)
from kabusys.operations.performance_report import build_report
```

`main()` 関数の直前に `_get_today_return` ヘルパーを追加:

```python
def _get_today_return(conn, target_date: date) -> float | None:
    row = conn.execute(
        "SELECT daily_return FROM portfolio_performance"
        " WHERE date = ? AND env = 'live' LIMIT 1",
        [target_date],
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return float(row[0])
```

`main()` 関数の `conn.execute("COMMIT")` の直後（`logger.info("ポートフォリオ構築完了...")`の後）に追加:

```python
        logger.info(
            "ポートフォリオ構築完了: %d 銘柄を signal_queue に挿入 (date=%s)",
            inserted,
            target_date,
        )

        # LINE 通知（失敗しても例外を伝播させない）
        try:
            notifier = build_notifier(settings)

            # 夜の日次通知
            daily_return = _get_today_return(conn, target_date)
            notifier.send(
                format_evening_message(
                    inserted=inserted,
                    report_date=target_date.isoformat(),
                    daily_return=daily_return,
                )
            )

            # 週次通知（金曜日: weekday == 4）
            if target_date.weekday() == 4:
                week_start = date.fromisocalendar(
                    target_date.isocalendar()[0],
                    target_date.isocalendar()[1],
                    1,
                )
                weekly_rows = collect_weekly_rows(conn, "live", week_start, target_date)
                weekly_report = build_report(
                    weekly_rows,
                    report_type="weekly",
                    env="live",
                    from_date=week_start,
                    to_date=target_date,
                )
                notifier.send(
                    format_weekly_message(
                        summary=weekly_report.summary,
                        from_date=week_start.isoformat(),
                        to_date=target_date.isoformat(),
                    )
                )

            # 月次通知（月末）
            last_day = calendar.monthrange(target_date.year, target_date.month)[1]
            if target_date.day == last_day:
                month_start = target_date.replace(day=1)
                monthly_rows = collect_monthly_rows(conn, "live", month_start, target_date)
                monthly_report = build_report(
                    monthly_rows,
                    report_type="monthly",
                    env="live",
                    from_date=month_start,
                    to_date=target_date,
                )
                notifier.send(
                    format_monthly_message(
                        summary=monthly_report.summary,
                        from_date=month_start.isoformat(),
                        to_date=target_date.isoformat(),
                    )
                )

        except Exception:
            logger.warning("LINE 通知に失敗しました", exc_info=True)
```

- [ ] **Step 4: テストが通ることを確認**

```
python -m pytest tests/test_line_reports.py::TestGetTodayReturn -v
```

Expected: 3 passed

- [ ] **Step 5: 全テスト回帰確認**

```
python -m pytest tests/test_line_reports.py -v
```

Expected: 全テスト pass (18 件)

- [ ] **Step 6: ruff チェック**

```
python -m ruff check scripts/run_portfolio_construction.py
python -m ruff format --check scripts/run_portfolio_construction.py
```

Expected: `All checks passed!`

- [ ] **Step 7: 全テスト回帰確認（全体）**

```
python -m pytest --tb=short -q
```

Expected: 全テスト pass（回帰なし）

- [ ] **Step 8: コミット**

```
git add scripts/run_portfolio_construction.py tests/test_line_reports.py
git commit -m "feat: portfolio_construction 完了後に夜・週次・月次 LINE 通知を追加 (Issue #256)"
```
