# Market Close Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 引け後の締め確認レポート（Market Close Summary）を実装し、`python -m kabusys.run_market_close_report` の 1 コマンドで夜間バッチへ進んでよいかを OK / BLOCKED で判定できるようにする。

**Architecture:** pre_market_report と同様の 3 ファイル構成（collector + report + runner）。DuckDB（positions, portfolio_performance）と SQLite（signal_queue）を read-only で参照し、純粋関数層でレポートを生成する。build_report はキーワード引数のみ受け取り、DB への依存を持たない。

**Tech Stack:** Python 3.10+, DuckDB（`duckdb` パッケージ）, SQLite（`sqlite3` 標準ライブラリ）, pytest

---

## File Map

| ファイル | 役割 |
|---|---|
| `src/kabusys/operations/market_close_report.py` | 純粋関数のみ（データクラス・build_report・フォーマッター・save_report）|
| `src/kabusys/operations/market_close_collector.py` | DB クエリ専用（DuckDB + SQLite、MarketCloseData を返す）|
| `src/kabusys/run_market_close_report.py` | CLI エントリーポイント |
| `tests/test_market_close_report.py` | 全ユニットテスト |

---

### Task 1: market_close_report.py — データクラスとビジネスロジック

**Files:**
- Create: `tests/test_market_close_report.py`
- Create: `src/kabusys/operations/market_close_report.py`

- [ ] **Step 1: テストを書く**

`tests/test_market_close_report.py` を新規作成:

```python
"""Market Close Summary レポートのテスト。"""
from __future__ import annotations

import json
import sqlite3 as _sqlite3
from datetime import date

import duckdb as _duckdb
import pytest

from kabusys.operations.market_close_report import (
    STATUS_BLOCKED,
    STATUS_OK,
    CheckItem,
    MarketCloseReport,
    build_report,
    format_cli_summary,
    format_json,
    format_markdown,
    save_report,
)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _make_report(
    *,
    signal_pending_count: int = 0,
    positions_updated: bool = True,
    performance_recorded: bool = True,
    filled_count: int = 3,
    daily_return: float | None = 0.0032,
    equity_today: float | None = 5_234_000.0,
    equity_prev: float | None = 5_217_600.0,
    report_date: date = date(2026, 4, 28),
) -> MarketCloseReport:
    return build_report(
        report_date=report_date,
        signal_pending_count=signal_pending_count,
        positions_updated=positions_updated,
        performance_recorded=performance_recorded,
        filled_count=filled_count,
        daily_return=daily_return,
        equity_today=equity_today,
        equity_prev=equity_prev,
    )


# ---------------------------------------------------------------------------
# build_report — ステータス判定
# ---------------------------------------------------------------------------

def test_build_report_ok():
    report = _make_report()
    assert report.status == STATUS_OK


def test_build_report_blocked_pending():
    report = _make_report(signal_pending_count=2)
    assert report.status == STATUS_BLOCKED


def test_build_report_blocked_positions():
    report = _make_report(positions_updated=False)
    assert report.status == STATUS_BLOCKED


def test_build_report_blocked_performance():
    report = _make_report(performance_recorded=False)
    assert report.status == STATUS_BLOCKED


def test_build_report_all_blocked():
    report = _make_report(
        signal_pending_count=1,
        positions_updated=False,
        performance_recorded=False,
    )
    assert report.status == STATUS_BLOCKED
    assert len(report.warnings) == 3


# ---------------------------------------------------------------------------
# build_report — チェック項目
# ---------------------------------------------------------------------------

def test_build_report_check_items_count():
    report = _make_report()
    assert len(report.checks) == 3


def test_build_report_checks_all_ok():
    report = _make_report()
    assert all(c.status == "ok" for c in report.checks)


def test_build_report_checks_signal_failed():
    report = _make_report(signal_pending_count=3)
    sq = next(c for c in report.checks if c.name == "signal_queue")
    assert sq.status == "failed"
    assert "3 件" in sq.detail


def test_build_report_checks_positions_failed():
    report = _make_report(positions_updated=False)
    pos = next(c for c in report.checks if c.name == "positions")
    assert pos.status == "failed"


def test_build_report_checks_performance_failed():
    report = _make_report(performance_recorded=False)
    perf = next(c for c in report.checks if c.name == "portfolio_performance")
    assert perf.status == "failed"


# ---------------------------------------------------------------------------
# build_report — summary（損益額計算）
# ---------------------------------------------------------------------------

def test_build_report_pnl_amount_calculated():
    report = _make_report(equity_today=5_234_000.0, equity_prev=5_217_600.0)
    assert report.summary["pnl_amount"] == pytest.approx(16_400.0)


def test_build_report_pnl_amount_none_when_equity_today_missing():
    report = _make_report(equity_today=None, equity_prev=5_217_600.0)
    assert report.summary["pnl_amount"] is None


def test_build_report_pnl_amount_none_when_equity_prev_missing():
    report = _make_report(equity_today=5_234_000.0, equity_prev=None)
    assert report.summary["pnl_amount"] is None


def test_build_report_summary_fields():
    report = _make_report(filled_count=5, daily_return=0.0032)
    assert report.summary["filled_count"] == 5
    assert report.summary["daily_return"] == pytest.approx(0.0032)


# ---------------------------------------------------------------------------
# format_cli_summary
# ---------------------------------------------------------------------------

def test_format_cli_summary_ok():
    report = _make_report()
    out = format_cli_summary(report)
    assert "✅" in out
    assert STATUS_OK in out
    assert "pending: 0 件" in out


def test_format_cli_summary_blocked():
    report = _make_report(signal_pending_count=2)
    out = format_cli_summary(report)
    assert "🚫" in out
    assert STATUS_BLOCKED in out
    assert "Warnings" in out
    assert "2 件" in out


def test_format_cli_summary_summary_section():
    report = _make_report(
        filled_count=5,
        daily_return=0.0032,
        equity_today=5_234_000.0,
        equity_prev=5_217_600.0,
    )
    out = format_cli_summary(report)
    assert "5 件" in out
    assert "0.32%" in out
    assert "16,400" in out
    assert "5,234,000" in out


def test_format_cli_summary_none_values():
    report = _make_report(daily_return=None, equity_today=None, equity_prev=None)
    out = format_cli_summary(report)
    assert "N/A" in out


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------

def test_format_json_is_valid_json():
    report = _make_report()
    data = json.loads(format_json(report))
    assert data["status"] == STATUS_OK
    assert data["report_date"] == "2026-04-28"
    assert "checks" in data
    assert "summary" in data
    assert "warnings" in data


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------

def test_format_markdown_contains_sections():
    report = _make_report()
    md = format_markdown(report)
    assert "# Market Close Summary" in md
    assert "Overview" in md
    assert "Checks" in md
    assert "Summary" in md
    assert "Final Decision" in md
    assert STATUS_OK in md


def test_format_markdown_blocked_contains_warnings():
    report = _make_report(signal_pending_count=1)
    md = format_markdown(report)
    assert "Warnings" in md
    assert STATUS_BLOCKED in md


# ---------------------------------------------------------------------------
# save_report
# ---------------------------------------------------------------------------

def test_save_report_creates_files(tmp_path):
    report = _make_report()
    run_dir = save_report(report, output_dir=tmp_path)
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "warnings.json").exists()


def test_save_report_directory_name(tmp_path):
    report = _make_report()
    run_dir = save_report(report, output_dir=tmp_path)
    assert run_dir.name == "2026-04-28"


def test_save_report_invalid_date_format(tmp_path):
    report = _make_report()
    report.report_date = "20260428"
    with pytest.raises(ValueError):
        save_report(report, output_dir=tmp_path)


def test_save_report_invalid_calendar_date(tmp_path):
    report = _make_report()
    report.report_date = "2026-99-99"
    with pytest.raises(ValueError):
        save_report(report, output_dir=tmp_path)


# ---------------------------------------------------------------------------
# collector fixtures（Task 2 で使用）
# ---------------------------------------------------------------------------

TODAY = date(2026, 4, 28)
PREV = date(2026, 4, 25)


@pytest.fixture
def ddb():
    """インメモリ DuckDB（positions + portfolio_performance テーブル付き）。"""
    conn = _duckdb.connect(":memory:")
    conn.execute(
        "CREATE TABLE positions ("
        "  date DATE, code VARCHAR, position_size INTEGER,"
        "  avg_price FLOAT, market_value FLOAT"
        ")"
    )
    conn.execute(
        "CREATE TABLE portfolio_performance ("
        "  date DATE, equity FLOAT, cash FLOAT,"
        "  drawdown FLOAT, daily_return FLOAT"
        ")"
    )
    yield conn
    conn.close()


@pytest.fixture
def sdb():
    """インメモリ SQLite（signal_queue テーブル付き）。"""
    conn = _sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE signal_queue ("
        "  signal_id TEXT, date TEXT, code TEXT, side TEXT,"
        "  size INTEGER, order_type TEXT, price REAL,"
        "  status TEXT, created_at TEXT, processed_at TEXT"
        ")"
    )
    conn.commit()
    yield conn
    conn.close()


def _insert_signal(sdb, date_str: str, status: str, code: str = "1234") -> None:
    sdb.execute(
        "INSERT INTO signal_queue"
        " (signal_id, date, code, side, size, order_type, price, status, created_at, processed_at)"
        " VALUES (?, ?, ?, 'buy', 100, 'market', NULL, ?, '2026-04-28T08:00:00', NULL)",
        (f"sig-{code}-{status}", date_str, code, status),
    )
    sdb.commit()


def _insert_position(ddb, date_val: date, code: str = "1234") -> None:
    ddb.execute(
        "INSERT INTO positions VALUES (?, ?, 100, 1500.0, 150000.0)",
        [date_val.isoformat(), code],
    )


def _insert_performance(
    ddb,
    date_val: date,
    equity: float = 5_234_000.0,
    daily_return: float = 0.0032,
) -> None:
    ddb.execute(
        "INSERT INTO portfolio_performance VALUES (?, ?, 1000000.0, -0.005, ?)",
        [date_val.isoformat(), equity, daily_return],
    )
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_market_close_report.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'kabusys.operations.market_close_report'`

- [ ] **Step 3: market_close_report.py を実装する**

`src/kabusys/operations/market_close_report.py` を新規作成:

```python
"""
Market Close Summary レポート生成モジュール。

引け後（15:30 頃）に「今日の運用が正常に締まったか」を確認し、
夜間バッチへ進んでよいかを OK / BLOCKED で判定する。
DB への参照は行わず、呼び出し元から受け取ったデータのみを使用する。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

STATUS_OK = "OK"
STATUS_BLOCKED = "BLOCKED"

_STATUS_EMOJI = {
    STATUS_OK: "✅",
    STATUS_BLOCKED: "🚫",
}

_CHECK_STATUS_LABEL = {
    "ok": "ok  ",
    "failed": "FAIL",
}


@dataclass
class CheckItem:
    """1 チェック項目の結果。"""

    name: str
    status: str  # "ok" | "failed"
    detail: str


@dataclass
class MarketCloseReport:
    """Market Close Summary レポート全体。"""

    report_date: str   # ISO date（YYYY-MM-DD）
    generated_at: str  # ISO 8601 UTC
    status: str        # "OK" / "BLOCKED"
    checks: list[CheckItem]
    summary: dict
    warnings: list[str]


def _determine_status(
    *,
    signal_pending_count: int,
    positions_updated: bool,
    performance_recorded: bool,
) -> str:
    """OK / BLOCKED を判定する。

    BLOCKED 条件（いずれかが真）:
      - signal_pending_count > 0（pending シグナル残件あり）
      - positions_updated == False（positions 未更新）
      - performance_recorded == False（portfolio_performance 未記録）
    """
    if signal_pending_count > 0 or not positions_updated or not performance_recorded:
        return STATUS_BLOCKED
    return STATUS_OK


def _generate_warnings(
    *,
    signal_pending_count: int,
    positions_updated: bool,
    performance_recorded: bool,
) -> list[str]:
    """警告メッセージのリストを生成する。"""
    warnings: list[str] = []
    if signal_pending_count > 0:
        warnings.append(
            f"signal_queue に本日の pending シグナルが {signal_pending_count} 件残っています"
        )
    if not positions_updated:
        warnings.append("positions に当日分が記録されていません")
    if not performance_recorded:
        warnings.append("portfolio_performance に当日分が記録されていません")
    return warnings


def _build_check_items(
    *,
    signal_pending_count: int,
    positions_updated: bool,
    performance_recorded: bool,
) -> list[CheckItem]:
    return [
        CheckItem(
            name="signal_queue",
            status="ok" if signal_pending_count == 0 else "failed",
            detail=(
                "pending: 0 件（全シグナル処理済み）"
                if signal_pending_count == 0
                else f"pending: {signal_pending_count} 件（未処理シグナルあり）"
            ),
        ),
        CheckItem(
            name="positions",
            status="ok" if positions_updated else "failed",
            detail=(
                "positions: 当日分 更新済み"
                if positions_updated
                else "positions: 当日分 未更新"
            ),
        ),
        CheckItem(
            name="portfolio_performance",
            status="ok" if performance_recorded else "failed",
            detail=(
                "portfolio_performance: 当日分 記録済み"
                if performance_recorded
                else "portfolio_performance: 当日分 未記録"
            ),
        ),
    ]


def build_report(
    *,
    report_date: date,
    signal_pending_count: int,
    positions_updated: bool,
    performance_recorded: bool,
    filled_count: int,
    daily_return: float | None,
    equity_today: float | None,
    equity_prev: float | None,
) -> MarketCloseReport:
    """MarketCloseReport を構築する。"""
    kwargs = dict(
        signal_pending_count=signal_pending_count,
        positions_updated=positions_updated,
        performance_recorded=performance_recorded,
    )
    pnl_amount = (
        equity_today - equity_prev
        if equity_today is not None and equity_prev is not None
        else None
    )
    return MarketCloseReport(
        report_date=report_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=_determine_status(**kwargs),
        checks=_build_check_items(**kwargs),
        summary={
            "filled_count": filled_count,
            "daily_return": daily_return,
            "pnl_amount": pnl_amount,
            "equity_today": equity_today,
        },
        warnings=_generate_warnings(**kwargs),
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------


def _fmt_return(v: float | None) -> str:
    """日次リターンを符号付きパーセント文字列に変換する。"""
    if v is None:
        return "N/A"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2%}"


def _fmt_yen(v: float | None) -> str:
    """金額を符号付き円表記に変換する。"""
    if v is None:
        return "N/A"
    sign = "+" if v > 0 else ""
    return f"{sign}¥{int(v):,}"


def format_cli_summary(report: MarketCloseReport) -> str:
    """CLI 表示用サマリ文字列を返す。"""
    sep = "=" * 52
    thin = "-" * 52
    emoji = _STATUS_EMOJI.get(report.status, "")
    s = report.summary
    lines = [
        f"\n{sep}",
        f"  Market Close Summary  {report.report_date}",
        f"  Status : {emoji} {report.status}",
        f"{sep}",
        "  Checks:",
    ]
    for c in report.checks:
        label = _CHECK_STATUS_LABEL.get(c.status, c.status.upper())
        lines.append(f"    [{label}] {c.name:<22} {c.detail}")
    lines += [
        thin,
        "  Summary:",
        f"    約定件数    : {s['filled_count']} 件",
        f"    日次リターン : {_fmt_return(s['daily_return'])}",
        f"    当日損益額  : {_fmt_yen(s['pnl_amount'])}",
        f"    期末総資産  : {_fmt_yen(s['equity_today'])}",
    ]
    if report.warnings:
        lines.append(thin)
        lines.append("  Warnings:")
        for w in report.warnings:
            lines.append(f"    [!] {w}")
    lines.append(f"{sep}\n")
    return "\n".join(lines)


def _to_serializable(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(i) for i in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def format_json(report: MarketCloseReport) -> str:
    """全フィールドを含む JSON 文字列を返す。"""
    return json.dumps(_to_serializable(asdict(report)), ensure_ascii=False, indent=2)


def format_markdown(report: MarketCloseReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    lines: list[str] = []
    sec = 0

    def _section(title: str) -> str:
        nonlocal sec
        sec += 1
        return f"## {sec}. {title}"

    emoji = _STATUS_EMOJI.get(report.status, "")
    s = report.summary

    lines += [
        "# Market Close Summary",
        "",
        _section("Overview"),
        "",
        "| 項目 | 値 |",
        "|-----|---|",
        f"| 実行日 | {report.report_date} |",
        f"| 生成時刻 | {report.generated_at} |",
        f"| **最終判定** | **{emoji} {report.status}** |",
        "",
        _section("Checks"),
        "",
        "| チェック項目 | ステータス | 詳細 |",
        "|------------|-----------|------|",
    ]
    for c in report.checks:
        lines.append(f"| {c.name} | {c.status} | {c.detail} |")
    lines += [
        "",
        _section("Summary"),
        "",
        "| 項目 | 値 |",
        "|-----|---|",
        f"| 約定件数 | {s['filled_count']} 件 |",
        f"| 日次リターン | {_fmt_return(s['daily_return'])} |",
        f"| 当日損益額 | {_fmt_yen(s['pnl_amount'])} |",
        f"| 期末総資産 | {_fmt_yen(s['equity_today'])} |",
        "",
    ]
    if report.warnings:
        lines += [_section("Warnings"), ""]
        for w in report.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    lines += [_section("Final Decision"), ""]
    if report.status == STATUS_OK:
        lines += [
            f"**{STATUS_OK}** — 夜間バッチへ進んでください。",
            "",
            "- 全チェック項目が正常です。",
        ]
    else:
        lines += [
            f"**{STATUS_BLOCKED}** — 夜間バッチへ **進まないでください**。",
            "",
            "- 上記 Warnings を確認し、問題を解消してから再実行してください。",
        ]
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: MarketCloseReport,
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/market_close/{report_date}/ に保存する。

    Returns:
        保存先ディレクトリのパス。
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report.report_date):
        raise ValueError(f"Invalid report_date: {report.report_date!r}")
    try:
        date.fromisoformat(report.report_date)
    except ValueError:
        raise ValueError(f"Invalid report_date: {report.report_date!r}")
    base = Path(output_dir) if output_dir else Path("artifacts") / "market_close"
    run_dir = base / report.report_date
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(format_json(report), encoding="utf-8")
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")
    (run_dir / "warnings.json").write_text(
        json.dumps(report.warnings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return run_dir
```

- [ ] **Step 4: テストを実行して通ることを確認**

```bash
python -m pytest tests/test_market_close_report.py -v -k "not ddb and not sdb and not collect"
```

Expected: collector fixture 以外の全テスト PASS（`ddb`/`sdb` fixture は Task 2 で使用）

- [ ] **Step 5: コミット**

```bash
git add tests/test_market_close_report.py src/kabusys/operations/market_close_report.py
git commit -m "feat: Market Close Summary レポートモジュールを実装 (Issue #205)"
```

---

### Task 2: market_close_collector.py — DB クエリ関数と collect_market_close_data

**Files:**
- Create: `src/kabusys/operations/market_close_collector.py`
- Test: `tests/test_market_close_report.py`（collector テストは既に Step 1 で記述済み）

- [ ] **Step 1: collector テストが失敗することを確認**

```bash
python -m pytest tests/test_market_close_report.py -v -k "ddb or sdb or collect"
```

Expected: `ModuleNotFoundError: No module named 'kabusys.operations.market_close_collector'`

- [ ] **Step 2: market_close_collector.py を実装する**

`src/kabusys/operations/market_close_collector.py` を新規作成:

```python
"""
Market Close Summary データ収集モジュール。

DuckDB（positions, portfolio_performance）と SQLite（signal_queue）を
read-only で参照し、MarketCloseData を返す。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class MarketCloseData:
    """collect_market_close_data() が返す生データ。"""

    signal_pending_count: int     # 当日 pending シグナル件数
    positions_updated: bool       # positions に当日分が存在するか
    performance_recorded: bool    # portfolio_performance に当日分が存在するか
    filled_count: int             # 当日 filled シグナル件数
    daily_return: float | None    # 当日日次リターン（未記録なら None）
    equity_today: float | None    # 当日期末資産（未記録なら None）
    equity_prev: float | None     # 前営業日期末資産（存在しなければ None）


def check_signal_pending(sqlite_conn, today: date) -> int:
    """当日の pending シグナル件数を返す。"""
    row = sqlite_conn.execute(
        "SELECT COUNT(*) FROM signal_queue WHERE status = 'pending' AND date = ?",
        (today.isoformat(),),
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def check_signal_filled(sqlite_conn, today: date) -> int:
    """当日の filled シグナル件数を返す。"""
    row = sqlite_conn.execute(
        "SELECT COUNT(*) FROM signal_queue WHERE status = 'filled' AND date = ?",
        (today.isoformat(),),
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def check_positions_updated(duckdb_conn, today: date) -> bool:
    """positions テーブルに当日分のレコードが存在すれば True。"""
    row = duckdb_conn.execute(
        "SELECT COUNT(*) FROM positions WHERE date = ?",
        [today.isoformat()],
    ).fetchone()
    return int(row[0] if row and row[0] is not None else 0) > 0


def check_performance_recorded(duckdb_conn, today: date) -> bool:
    """portfolio_performance テーブルに当日分のレコードが存在すれば True。"""
    row = duckdb_conn.execute(
        "SELECT COUNT(*) FROM portfolio_performance WHERE date = ?",
        [today.isoformat()],
    ).fetchone()
    return int(row[0] if row and row[0] is not None else 0) > 0


def get_performance_row(
    duckdb_conn, today: date
) -> tuple[float | None, float | None]:
    """(daily_return, equity) を返す。当日レコードがなければ (None, None)。"""
    row = duckdb_conn.execute(
        "SELECT daily_return, equity FROM portfolio_performance WHERE date = ?",
        [today.isoformat()],
    ).fetchone()
    if row is None:
        return None, None
    return (
        float(row[0]) if row[0] is not None else None,
        float(row[1]) if row[1] is not None else None,
    )


def get_prev_equity(duckdb_conn, today: date) -> float | None:
    """today より前の最新 equity を返す。存在しなければ None。"""
    row = duckdb_conn.execute(
        "SELECT equity FROM portfolio_performance"
        " WHERE date < ? ORDER BY date DESC LIMIT 1",
        [today.isoformat()],
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def collect_market_close_data(
    duckdb_conn, sqlite_conn, today: date
) -> MarketCloseData:
    """全チェック関数を呼び出して MarketCloseData を返す。"""
    daily_return, equity_today = get_performance_row(duckdb_conn, today)
    return MarketCloseData(
        signal_pending_count=check_signal_pending(sqlite_conn, today),
        positions_updated=check_positions_updated(duckdb_conn, today),
        performance_recorded=check_performance_recorded(duckdb_conn, today),
        filled_count=check_signal_filled(sqlite_conn, today),
        daily_return=daily_return,
        equity_today=equity_today,
        equity_prev=get_prev_equity(duckdb_conn, today),
    )
```

- [ ] **Step 3: collector テストに不足している import を追加する**

`tests/test_market_close_report.py` の既存 import ブロックの末尾に追加:

```python
from kabusys.operations.market_close_collector import (
    MarketCloseData,
    check_signal_pending,
    check_signal_filled,
    check_positions_updated,
    check_performance_recorded,
    get_performance_row,
    get_prev_equity,
    collect_market_close_data,
)
```

そして `tests/test_market_close_report.py` の末尾（`_insert_performance` 関数の後）に以下を追記:

```python
# ---------------------------------------------------------------------------
# check_signal_pending
# ---------------------------------------------------------------------------

def test_check_signal_pending_zero_when_empty(sdb):
    assert check_signal_pending(sdb, TODAY) == 0


def test_check_signal_pending_counts_pending(sdb):
    _insert_signal(sdb, TODAY.isoformat(), "pending", "1234")
    _insert_signal(sdb, TODAY.isoformat(), "pending", "5678")
    assert check_signal_pending(sdb, TODAY) == 2


def test_check_signal_pending_ignores_other_status(sdb):
    _insert_signal(sdb, TODAY.isoformat(), "filled")
    assert check_signal_pending(sdb, TODAY) == 0


def test_check_signal_pending_ignores_other_date(sdb):
    _insert_signal(sdb, "2026-04-27", "pending")
    assert check_signal_pending(sdb, TODAY) == 0


# ---------------------------------------------------------------------------
# check_signal_filled
# ---------------------------------------------------------------------------

def test_check_signal_filled_zero_when_empty(sdb):
    assert check_signal_filled(sdb, TODAY) == 0


def test_check_signal_filled_counts_filled(sdb):
    _insert_signal(sdb, TODAY.isoformat(), "filled", "1234")
    _insert_signal(sdb, TODAY.isoformat(), "filled", "5678")
    assert check_signal_filled(sdb, TODAY) == 2


def test_check_signal_filled_ignores_pending(sdb):
    _insert_signal(sdb, TODAY.isoformat(), "pending")
    assert check_signal_filled(sdb, TODAY) == 0


# ---------------------------------------------------------------------------
# check_positions_updated
# ---------------------------------------------------------------------------

def test_check_positions_updated_false_when_empty(ddb):
    assert check_positions_updated(ddb, TODAY) is False


def test_check_positions_updated_true_when_today_exists(ddb):
    _insert_position(ddb, TODAY)
    assert check_positions_updated(ddb, TODAY) is True


def test_check_positions_updated_false_when_only_prev(ddb):
    _insert_position(ddb, PREV)
    assert check_positions_updated(ddb, TODAY) is False


# ---------------------------------------------------------------------------
# check_performance_recorded
# ---------------------------------------------------------------------------

def test_check_performance_recorded_false_when_empty(ddb):
    assert check_performance_recorded(ddb, TODAY) is False


def test_check_performance_recorded_true_when_today_exists(ddb):
    _insert_performance(ddb, TODAY)
    assert check_performance_recorded(ddb, TODAY) is True


# ---------------------------------------------------------------------------
# get_performance_row
# ---------------------------------------------------------------------------

def test_get_performance_row_none_when_empty(ddb):
    daily_return, equity = get_performance_row(ddb, TODAY)
    assert daily_return is None
    assert equity is None


def test_get_performance_row_returns_values(ddb):
    _insert_performance(ddb, TODAY, equity=5_234_000.0, daily_return=0.0032)
    daily_return, equity = get_performance_row(ddb, TODAY)
    assert daily_return == pytest.approx(0.0032)
    assert equity == pytest.approx(5_234_000.0)


# ---------------------------------------------------------------------------
# get_prev_equity
# ---------------------------------------------------------------------------

def test_get_prev_equity_none_when_no_history(ddb):
    assert get_prev_equity(ddb, TODAY) is None


def test_get_prev_equity_returns_most_recent_before_today(ddb):
    _insert_performance(ddb, PREV, equity=5_217_600.0)
    _insert_performance(ddb, date(2026, 4, 24), equity=5_200_000.0)
    result = get_prev_equity(ddb, TODAY)
    assert result == pytest.approx(5_217_600.0)


def test_get_prev_equity_ignores_today(ddb):
    _insert_performance(ddb, TODAY, equity=5_234_000.0)
    assert get_prev_equity(ddb, TODAY) is None


# ---------------------------------------------------------------------------
# collect_market_close_data
# ---------------------------------------------------------------------------

def test_collect_market_close_data_all_ok(ddb, sdb):
    _insert_signal(sdb, TODAY.isoformat(), "filled")
    _insert_position(ddb, TODAY)
    _insert_performance(ddb, TODAY, equity=5_234_000.0, daily_return=0.0032)
    _insert_performance(ddb, PREV, equity=5_217_600.0)
    data = collect_market_close_data(ddb, sdb, TODAY)
    assert data.signal_pending_count == 0
    assert data.filled_count == 1
    assert data.positions_updated is True
    assert data.performance_recorded is True
    assert data.daily_return == pytest.approx(0.0032)
    assert data.equity_today == pytest.approx(5_234_000.0)
    assert data.equity_prev == pytest.approx(5_217_600.0)


def test_collect_market_close_data_blocked(ddb, sdb):
    _insert_signal(sdb, TODAY.isoformat(), "pending")
    data = collect_market_close_data(ddb, sdb, TODAY)
    assert data.signal_pending_count == 1
    assert data.positions_updated is False
    assert data.performance_recorded is False
```

- [ ] **Step 4: 全テストを実行して通ることを確認**

```bash
python -m pytest tests/test_market_close_report.py -v
```

Expected: 全テスト PASS

- [ ] **Step 5: コミット**

```bash
git add tests/test_market_close_report.py src/kabusys/operations/market_close_collector.py
git commit -m "feat: market_close_collector.py を実装 (Issue #205)"
```

---

### Task 3: run_market_close_report.py — CLI エントリーポイント

**Files:**
- Create: `src/kabusys/run_market_close_report.py`

- [ ] **Step 1: run_market_close_report.py を実装する**

`src/kabusys/run_market_close_report.py` を新規作成:

```python
"""Market Close Summary エントリーポイント。

使用方法:
    python -m kabusys.run_market_close_report
    python -m kabusys.run_market_close_report --date 2026-04-28
    python -m kabusys.run_market_close_report --save
    python -m kabusys.run_market_close_report --json
    python -m kabusys.run_market_close_report --save --json
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import date
from pathlib import Path

import duckdb

from kabusys.config import Settings
from kabusys.operations.market_close_collector import collect_market_close_data
from kabusys.operations.market_close_report import (
    STATUS_BLOCKED,
    build_report,
    format_cli_summary,
    format_json,
    save_report,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Market Close Summary を生成する"
    )
    parser.add_argument(
        "--date",
        type=lambda s: date.fromisoformat(s),
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="レポートの日付ラベル兼クエリ対象日（省略時は今日）",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="artifacts/market_close/ に保存する",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON 形式で出力する",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    settings = Settings()
    duckdb_conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    sqlite_uri = Path(settings.sqlite_path).resolve().as_uri() + "?mode=ro"
    sqlite_conn = sqlite3.connect(sqlite_uri, uri=True)

    try:
        data = collect_market_close_data(duckdb_conn, sqlite_conn, args.date)
    finally:
        duckdb_conn.close()
        sqlite_conn.close()

    report = build_report(
        report_date=args.date,
        signal_pending_count=data.signal_pending_count,
        positions_updated=data.positions_updated,
        performance_recorded=data.performance_recorded,
        filled_count=data.filled_count,
        daily_return=data.daily_return,
        equity_today=data.equity_today,
        equity_prev=data.equity_prev,
    )

    if args.json:
        print(format_json(report))
    else:
        print(format_cli_summary(report))

    if args.save:
        run_dir = save_report(report)
        dest_msg = f"保存先: {run_dir}"
        if args.json:
            sys.stderr.write(dest_msg + "\n")
        else:
            print(dest_msg)

    return 1 if report.status == STATUS_BLOCKED else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: lint + format チェック**

```bash
python -m ruff check src/kabusys/operations/market_close_report.py src/kabusys/operations/market_close_collector.py src/kabusys/run_market_close_report.py
python -m ruff format --check src/kabusys/operations/market_close_report.py src/kabusys/operations/market_close_collector.py src/kabusys/run_market_close_report.py
```

Expected: `All checks passed!` / `N files already formatted`

フォーマットエラーがあれば修正:

```bash
python -m ruff format src/kabusys/operations/market_close_report.py src/kabusys/operations/market_close_collector.py src/kabusys/run_market_close_report.py
```

- [ ] **Step 3: 全テスト実行**

```bash
python -m pytest tests/test_market_close_report.py -v
```

Expected: 全テスト PASS

- [ ] **Step 4: コミット**

```bash
git add src/kabusys/run_market_close_report.py
git commit -m "feat: run_market_close_report.py CLI エントリーポイントを実装 (Issue #205)"
```
