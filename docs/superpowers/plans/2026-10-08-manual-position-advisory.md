# 手動ポジション助言モード Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 手動約定（`manual_trades`）の保有を、自動売買と同じ SELL 判定・BUY 株数計算・夜 LINE 通知・ダッシュボードに組み込み、発注はせず候補として提示する。

**Architecture:** 保有を `HeldPosition` で統一表現し、`_generate_sell_signals` は保有リストを受け取る純粋な判定ループにする。自動分は従来どおり `positions` / `position_entries` から、手動分は `manual_trades` から作り、本番スクリプトが `MANUAL_TRADING_ENABLED=true` のときだけ手動分を渡す。手動保有の SELL 候補は `manual_action_queue`（発注経路と無関係なテーブル）に記録する。

**Tech Stack:** Python 3.10+, DuckDB, SQLite, pytest, Streamlit, ruff 0.15.11

**Spec:** `docs/superpowers/specs/2026-10-07-manual-position-advisory-design.md`

## Global Constraints

- 環境変数: `MANUAL_TRADING_ENABLED`（bool, 既定 `false`）、`MANUAL_TRADING_INITIAL_CASH`（float, 未設定時は `PORTFOLIO_VALUE` と同値）
- `generate_signals` / `_generate_sell_signals` の既定は「手動保有なし」。`backtest/engine.py` からは手動保有を渡さない（Look-ahead Bias 制約）。
- 手動保有の SELL は `signal_queue` に入れない。Execution Engine（`src/kabusys/execution/`）は `manual_action_queue` を参照しない。
- `manual_action_queue.action_id` = `{date.isoformat()}_{code}_{action}`。再記録時は `qty` / `reason` のみ更新し `status` を保持。
- 既存の SELL 判定結果（自動分のみ）は改修前と同一であること。既存テストを修正して通すことは禁止。
- コミットは Conventional Commits、末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- 各タスク完了時に `python -m ruff check src tests scripts` と `python -m ruff format --check src tests scripts` が clean であること。

## Review Focus

1. 手動で全株売却した銘柄 → 保有に現れず、SELL 候補にも出ないこと（Task 1 でテスト）。
2. 売却後に同銘柄を買い直した場合 → 保有開始日が買い直し日にリセットされること（Task 1 でテスト）。
3. 手動保有銘柄の価格が `prices_daily` に無い → SELL 判定スキップ・総資産は時価 0 で継続（Task 2・Task 5 でテスト）。
4. `manual_action_queue` テーブルが無い DB（フラグ OFF 運用）で夜 LINE の SELL 取得が失敗しないこと（Task 6 でテスト）。
5. ユーザーが「対応済み」にした候補を夜間バッチ再実行で `open` に戻さないこと（Task 3 でテスト）。

---

### Task 1: 保有の統一表現 `HeldPosition` と読み込み・合算

**Files:**
- Create: `src/kabusys/strategy/holdings.py`
- Modify: `src/kabusys/operations/manual_trades.py`（`ManualPosition` に entry 日追加、`calculate_manual_positions` で追跡、`load_manual_held_positions` / `manual_position_qty_map` 追加）
- Test: `tests/test_holdings.py`（新規）、`tests/test_manual_trades.py`

**Interfaces:**
- Produces:
  - `HeldPosition(code: str, qty: int, avg_price: float, first_entry_date: date | None, latest_entry_date: date | None, source: str)`（frozen dataclass、`source` は `"auto" | "manual" | "mixed"`）
  - `load_auto_positions(conn: duckdb.DuckDBPyConnection, target_date: date, sqlite_conn: sqlite3.Connection | None = None) -> list[HeldPosition]`
  - `merge_positions(*groups: list[HeldPosition]) -> list[HeldPosition]`（code 昇順）
  - `ManualPosition.first_entry_date: date | None = None`, `ManualPosition.latest_entry_date: date | None = None`
  - `load_manual_held_positions(conn, target_date: date) -> list[HeldPosition]`
  - `manual_position_qty_map(conn, *, as_of: date) -> dict[str, int]`

- [ ] **Step 1: 失敗するテストを書く（holdings）**

`tests/test_holdings.py`:

```python
"""strategy/holdings.py のテスト"""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from kabusys.data.schema import init_schema
from kabusys.strategy.holdings import HeldPosition, load_auto_positions, merge_positions


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def test_load_auto_positions_reads_latest_open_positions_with_entry_dates(conn):
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES "
        "('2026-04-01', '1001', 100, 1000), ('2026-04-02', '1001', 200, 1100), "
        "('2026-04-02', '1002', 0, 500)"
    )
    conn.execute(
        "INSERT INTO position_entries (code, entry_date, sell_date) VALUES "
        "('1001', '2026-03-01', NULL), ('1001', '2026-03-10', NULL), "
        "('1001', '2026-02-01', '2026-02-20')"
    )

    result = load_auto_positions(conn, date(2026, 4, 2))

    assert result == [
        HeldPosition(
            code="1001",
            qty=200,
            avg_price=1100.0,
            first_entry_date=date(2026, 3, 1),
            latest_entry_date=date(2026, 3, 10),
            source="auto",
        )
    ]


def test_load_auto_positions_uses_sqlite_entries_when_given(conn):
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) "
        "VALUES ('2026-04-02', '1001', 100, 1000)"
    )
    sq = sqlite3.connect(":memory:")
    sq.execute("CREATE TABLE position_entries (code TEXT, entry_date TEXT, sell_date TEXT)")
    sq.execute("INSERT INTO position_entries VALUES ('1001', '2026-03-05', NULL)")

    result = load_auto_positions(conn, date(2026, 4, 2), sqlite_conn=sq)

    assert result[0].first_entry_date == date(2026, 3, 5)
    assert result[0].latest_entry_date == date(2026, 3, 5)


def test_load_auto_positions_without_entries_has_none_dates(conn):
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) "
        "VALUES ('2026-04-02', '1001', 100, 1000)"
    )
    result = load_auto_positions(conn, date(2026, 4, 2))
    assert result[0].first_entry_date is None
    assert result[0].latest_entry_date is None


def test_merge_positions_combines_same_code():
    auto = [HeldPosition("1001", 100, 1000.0, date(2026, 3, 1), date(2026, 3, 1), "auto")]
    manual = [
        HeldPosition("1001", 300, 1200.0, date(2026, 2, 1), date(2026, 3, 20), "manual"),
        HeldPosition("2002", 100, 500.0, date(2026, 3, 2), date(2026, 3, 2), "manual"),
    ]

    result = merge_positions(auto, manual)

    assert [p.code for p in result] == ["1001", "2002"]
    merged = result[0]
    assert merged.qty == 400
    assert merged.avg_price == pytest.approx(1150.0)
    assert merged.first_entry_date == date(2026, 2, 1)
    assert merged.latest_entry_date == date(2026, 3, 20)
    assert merged.source == "mixed"
    assert result[1].source == "manual"


def test_merge_positions_keeps_none_dates_when_other_side_missing():
    auto = [HeldPosition("1001", 100, 1000.0, None, None, "auto")]
    manual = [HeldPosition("1001", 100, 1000.0, date(2026, 3, 1), date(2026, 3, 1), "manual")]
    merged = merge_positions(auto, manual)[0]
    assert merged.first_entry_date == date(2026, 3, 1)
    assert merged.latest_entry_date == date(2026, 3, 1)
```

- [ ] **Step 2: 失敗するテストを書く（manual_trades の entry 日）**

`tests/test_manual_trades.py` の末尾に追加:

```python
def _buy(conn, d, code="7203", qty=100, price=1000.0):
    add_manual_trade(conn, ManualTradeInput(trade_date=d, code=code, side="buy", qty=qty, price=price))


def _sell(conn, d, code="7203", qty=100, price=1000.0):
    add_manual_trade(conn, ManualTradeInput(trade_date=d, code=code, side="sell", qty=qty, price=price))


def test_manual_positions_track_entry_dates(conn):
    _buy(conn, date(2026, 9, 1))
    _buy(conn, date(2026, 9, 3))

    pos = calculate_manual_positions(conn, as_of=date(2026, 9, 10))[0]

    assert pos.first_entry_date == date(2026, 9, 1)
    assert pos.latest_entry_date == date(2026, 9, 3)


def test_manual_positions_reset_entry_after_full_exit(conn):
    _buy(conn, date(2026, 9, 1))
    _sell(conn, date(2026, 9, 2))
    _buy(conn, date(2026, 9, 7))

    pos = calculate_manual_positions(conn, as_of=date(2026, 9, 10))[0]

    assert pos.qty == 100
    assert pos.first_entry_date == date(2026, 9, 7)
    assert pos.latest_entry_date == date(2026, 9, 7)


def test_fully_sold_manual_position_is_not_held(conn):
    from kabusys.operations.manual_trades import load_manual_held_positions

    _buy(conn, date(2026, 9, 1))
    _sell(conn, date(2026, 9, 2))

    assert load_manual_held_positions(conn, date(2026, 9, 10)) == []


def test_load_manual_held_positions_returns_held_positions(conn):
    from kabusys.operations.manual_trades import load_manual_held_positions
    from kabusys.strategy.holdings import HeldPosition

    _buy(conn, date(2026, 9, 1), price=1000.0)
    _buy(conn, date(2026, 9, 3), price=1200.0)
    _buy(conn, date(2026, 9, 20), price=1500.0)  # target_date より後 → 含めない

    result = load_manual_held_positions(conn, date(2026, 9, 10))

    assert result == [
        HeldPosition(
            code="7203",
            qty=200,
            avg_price=1100.0,
            first_entry_date=date(2026, 9, 1),
            latest_entry_date=date(2026, 9, 3),
            source="manual",
        )
    ]


def test_manual_position_qty_map(conn):
    from kabusys.operations.manual_trades import manual_position_qty_map

    _buy(conn, date(2026, 9, 1), code="7203", qty=200)
    _buy(conn, date(2026, 9, 1), code="6758", qty=100)
    _sell(conn, date(2026, 9, 2), code="6758", qty=100)

    assert manual_position_qty_map(conn, as_of=date(2026, 9, 10)) == {"7203": 200}
```

注: `build_manual_trade_id` は `{date}_{code}_{side}` 形式のため、同日・同銘柄・同方向の 2 件目は `DuplicateManualTradeError` になる。上記テストは日付をずらしている。

- [ ] **Step 3: テストが失敗することを確認**

Run: `python -m pytest tests/test_holdings.py tests/test_manual_trades.py -q`
Expected: FAIL（`ModuleNotFoundError: kabusys.strategy.holdings`、`AttributeError: ... first_entry_date`）

- [ ] **Step 4: `src/kabusys/strategy/holdings.py` を作成**

```python
"""保有ポジションの統一表現。

SELL 判定（signal_generator._generate_sell_signals）に渡す保有を、
自動売買分（positions / position_entries）と手動約定分（manual_trades）で
共通の形にそろえる。手動分の読み込みは operations.manual_trades 側に置く。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any

import duckdb


@dataclass(frozen=True)
class HeldPosition:
    code: str
    qty: int
    avg_price: float
    first_entry_date: date | None  # 現保有の最古エントリー日（ピーク価格の起点）
    latest_entry_date: date | None  # 現保有の最新エントリー日（保有日数の起点）
    source: str  # "auto" | "manual" | "mixed"


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def load_auto_positions(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    sqlite_conn: sqlite3.Connection | None = None,
) -> list[HeldPosition]:
    """positions の target_date 以前の最新行（position_size > 0）を保有として返す。

    entry 日は未クローズの position_entries から取得する。
    sqlite_conn 指定時は SQLite（ライブ実行）、未指定時は DuckDB（バックテスト互換）を参照する。
    """
    rows = conn.execute(
        """
        SELECT p.code, CAST(p.avg_price AS DOUBLE), p.position_size
        FROM positions p
        INNER JOIN (
            SELECT code, MAX(date) AS max_date
            FROM positions
            WHERE date <= ?
            GROUP BY code
        ) m ON p.code = m.code AND p.date = m.max_date
        WHERE p.position_size > 0
        ORDER BY p.code
        """,
        [target_date],
    ).fetchall()

    entry_source: Any = sqlite_conn if sqlite_conn is not None else conn
    positions: list[HeldPosition] = []
    for code, avg_price, size in rows:
        entry_row = entry_source.execute(
            "SELECT MIN(entry_date), MAX(entry_date) FROM position_entries "
            "WHERE code = ? AND sell_date IS NULL",
            [code],
        ).fetchone()
        first_entry, latest_entry = entry_row if entry_row is not None else (None, None)
        positions.append(
            HeldPosition(
                code=code,
                qty=int(size),
                avg_price=float(avg_price) if avg_price is not None else 0.0,
                first_entry_date=_to_date(first_entry),
                latest_entry_date=_to_date(latest_entry),
                source="auto",
            )
        )
    return positions


def _min_date(a: date | None, b: date | None) -> date | None:
    candidates = [d for d in (a, b) if d is not None]
    return min(candidates) if candidates else None


def _max_date(a: date | None, b: date | None) -> date | None:
    candidates = [d for d in (a, b) if d is not None]
    return max(candidates) if candidates else None


def merge_positions(*groups: list[HeldPosition]) -> list[HeldPosition]:
    """同一銘柄を数量合算・数量加重平均単価で 1 件にまとめる（code 昇順）。"""
    merged: dict[str, HeldPosition] = {}
    for group in groups:
        for pos in group:
            cur = merged.get(pos.code)
            if cur is None:
                merged[pos.code] = pos
                continue
            qty = cur.qty + pos.qty
            avg_price = (cur.qty * cur.avg_price + pos.qty * pos.avg_price) / qty if qty else 0.0
            merged[pos.code] = HeldPosition(
                code=pos.code,
                qty=qty,
                avg_price=avg_price,
                first_entry_date=_min_date(cur.first_entry_date, pos.first_entry_date),
                latest_entry_date=_max_date(cur.latest_entry_date, pos.latest_entry_date),
                source=cur.source if cur.source == pos.source else "mixed",
            )
    return sorted(merged.values(), key=lambda p: p.code)
```

- [ ] **Step 5: `operations/manual_trades.py` を修正**

`ManualPosition` に 2 フィールド（既定 None）を追加:

```python
@dataclass(frozen=True)
class ManualPosition:
    code: str
    qty: int
    avg_price: float
    realized_pnl: float
    last_trade_date: date
    first_entry_date: date | None = None
    latest_entry_date: date | None = None
```

`calculate_manual_positions` の state 初期値に `"first_entry_date": None, "latest_entry_date": None` を追加し、`side == "buy"` 分岐を次にする（`current_qty == 0` のときに保有開始日をリセット）:

```python
        if side == "buy":
            if current_qty == 0:
                pos["first_entry_date"] = trade_date
            pos["latest_entry_date"] = trade_date
            pos["qty"] = current_qty + qty
            pos["cost"] = current_cost + (qty * price) + fees
```

`ManualPosition(...)` 生成箇所に `first_entry_date=pos["first_entry_date"], latest_entry_date=pos["latest_entry_date"],` を追加。state の型注釈は `dict[str, dict[str, Any]]` に変更する。

ファイル末尾に追加:

```python
def load_manual_held_positions(
    conn: duckdb.DuckDBPyConnection, target_date: date
) -> list[HeldPosition]:
    """target_date 時点の手動保有を SELL 判定用の HeldPosition に変換する。"""
    return [
        HeldPosition(
            code=p.code,
            qty=p.qty,
            avg_price=p.avg_price,
            first_entry_date=p.first_entry_date,
            latest_entry_date=p.latest_entry_date,
            source="manual",
        )
        for p in calculate_manual_positions(conn, as_of=target_date)
    ]


def manual_position_qty_map(conn: duckdb.DuckDBPyConnection, *, as_of: date) -> dict[str, int]:
    """as_of 時点の手動保有数量 {code: qty}。"""
    return {p.code: p.qty for p in calculate_manual_positions(conn, as_of=as_of)}
```

import に `from kabusys.strategy.holdings import HeldPosition` を追加（`strategy/holdings.py` は operations を import しないので循環しない）。

- [ ] **Step 6: テストが通ることを確認**

Run: `python -m pytest tests/test_holdings.py tests/test_manual_trades.py tests/test_dashboard_pages.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/kabusys/strategy/holdings.py src/kabusys/operations/manual_trades.py tests/test_holdings.py tests/test_manual_trades.py
git commit -m "feat: add unified HeldPosition for auto and manual holdings (#410)"
```

---

### Task 2: SELL 判定を保有リスト入力に共通化

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py`（`_peak_close` / `_held_days` 周辺 840-930 行、`_generate_sell_signals` 989-1236 行、`generate_signals` の SELL 呼び出し 1938-1957 行・書き込み後）
- Test: `tests/test_manual_sell_advisory.py`（新規）

**Interfaces:**
- Consumes: `HeldPosition`, `load_auto_positions`, `merge_positions`（Task 1）
- Produces:
  - `_generate_sell_signals(..., positions: list[HeldPosition] | None = None)` — 戻り値要素は `{"code": str, "score": float, "reason": str, "qty": int, "source": str}`
  - `generate_signals(..., manual_positions: list[HeldPosition] | None = None, sell_signals_out: list[dict[str, Any]] | None = None) -> int`（キーワード専用。`sell_signals_out` には signals 書き込み成功後に SELL リストが extend される）
  - `_peak_close_since(conn, code: str, first_entry_date: date | None, target_date: date) -> float | None`
  - `_held_days_since(conn, entry_date: date | None, target_date: date) -> int | None`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_manual_sell_advisory.py`:

```python
"""手動保有への SELL 判定（助言モード）のテスト"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from kabusys.data.schema import init_schema
from kabusys.operations.manual_trades import ManualTradeInput, add_manual_trade
from kabusys.strategy.holdings import HeldPosition
from kabusys.strategy.signal_generator import _generate_sell_signals, generate_signals

TARGET = date(2026, 4, 6)  # 月曜


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def _weekdays_before(d: date, n: int) -> list[date]:
    result: list[date] = []
    cur = d - timedelta(days=1)
    while len(result) < n:
        if cur.weekday() < 5:
            result.insert(0, cur)
        cur -= timedelta(days=1)
    return result


def _price(conn, d: date, code: str, close: float) -> None:
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
        [d, code, close, close + 10, close - 10, close],
    )


def _calendar(conn, days: list[date]) -> None:
    for d in days:
        conn.execute(
            "INSERT OR IGNORE INTO market_calendar (date, is_trading_day, is_half_day) "
            "VALUES (?, TRUE, FALSE)",
            [d],
        )


def _manual(code: str, avg: float, entry: date | None, qty: int = 100) -> HeldPosition:
    return HeldPosition(code, qty, avg, entry, entry, "manual")


def _sell(conn, positions, **kwargs):
    return _generate_sell_signals(
        conn, TARGET, score_map=kwargs.pop("score_map", {}), threshold=0.6,
        positions=positions, **kwargs,
    )


def test_stop_loss_for_manual_position(conn):
    _price(conn, TARGET, "M1", 900.0)
    result = _sell(conn, [_manual("M1", 1000.0, TARGET - timedelta(days=1))], score_map={"M1": 1.0})
    assert result == [{"code": "M1", "score": 1.0, "reason": "stop_loss", "qty": 100, "source": "manual"}]


def test_trailing_stop_for_manual_position(conn):
    days = _weekdays_before(TARGET, 20)
    for i, d in enumerate(days):
        _price(conn, d, "M2", 1100.0 if i == 15 else 1000.0)
    _price(conn, TARGET, "M2", 1020.0)
    # peak=1100, ATR=(17*20+110+110+30)/20=29.5 → 閾値 1100-2*29.5=1041 > 1020
    result = _sell(conn, [_manual("M2", 1000.0, days[0])], score_map={"M2": 1.0})
    assert [r["reason"] for r in result] == ["trailing_stop"]


def test_time_exit_counts_from_manual_entry_date(conn):
    days = _weekdays_before(TARGET, 5)
    _calendar(conn, days + [TARGET])
    _price(conn, TARGET, "M3", 1000.0)
    result = _sell(
        conn, [_manual("M3", 1000.0, days[0])], score_map={"M3": 1.0}, max_holding_days=5
    )
    assert [r["reason"] for r in result] == ["time_exit"]


def test_score_drop_for_manual_position_after_min_holding(conn):
    days = _weekdays_before(TARGET, 6)
    _calendar(conn, days + [TARGET])
    _price(conn, TARGET, "M4", 1000.0)
    result = _sell(conn, [_manual("M4", 1000.0, days[0])], score_map={"M4": 0.1})
    assert [r["reason"] for r in result] == ["score_drop"]


def test_score_drop_suppressed_within_min_holding(conn):
    days = _weekdays_before(TARGET, 2)
    _calendar(conn, days + [TARGET])
    _price(conn, TARGET, "M5", 1000.0)
    assert _sell(conn, [_manual("M5", 1000.0, days[0])], score_map={"M5": 0.1}) == []


def test_missing_price_skips_manual_position(conn):
    assert _sell(conn, [_manual("M6", 1000.0, TARGET)]) == []


def test_generate_signals_includes_manual_positions_and_reports_out(conn):
    _price(conn, TARGET, "M7", 900.0)
    out: list[dict] = []

    generate_signals(
        conn, TARGET,
        manual_positions=[_manual("M7", 1000.0, TARGET - timedelta(days=1))],
        sell_signals_out=out,
    )

    rows = conn.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'", [TARGET]
    ).fetchall()
    assert rows == [("M7",)]
    assert out[0]["code"] == "M7"
    assert out[0]["reason"] == "stop_loss"
    assert out[0]["source"] == "manual"


def test_generate_signals_ignores_manual_trades_by_default(conn):
    """manual_positions 未指定（バックテスト・フラグ OFF）では manual_trades を読まない。"""
    add_manual_trade(
        conn,
        ManualTradeInput(trade_date=TARGET - timedelta(days=3), code="M8", side="buy", qty=100, price=1000.0),
    )
    _price(conn, TARGET, "M8", 800.0)

    generate_signals(conn, TARGET)

    rows = conn.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'", [TARGET]
    ).fetchall()
    assert rows == []


def test_generate_signals_merges_auto_and_manual_same_code(conn):
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, 'M9', 100, 1000)",
        [TARGET],
    )
    _price(conn, TARGET, "M9", 900.0)
    out: list[dict] = []

    generate_signals(
        conn, TARGET,
        manual_positions=[_manual("M9", 1000.0, TARGET - timedelta(days=1), qty=200)],
        sell_signals_out=out,
    )

    assert out[0]["qty"] == 300
    assert out[0]["source"] == "mixed"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_manual_sell_advisory.py -q`
Expected: FAIL（`TypeError: _generate_sell_signals() got an unexpected keyword argument 'positions'`）

- [ ] **Step 3: entry 日を直接受け取るヘルパーを追加し、既存ヘルパーをラッパー化**

`signal_generator.py` の `_peak_close` の直前に追加:

```python
def _peak_close_since(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    first_entry_date: date | None,
    target_date: date,
) -> float | None:
    """first_entry_date 〜 target_date の最高 close。entry 日不明・価格なしは None。"""
    if first_entry_date is None:
        return None
    row = conn.execute(
        "SELECT MAX(close) FROM prices_daily WHERE code = ? AND date >= ? AND date <= ?",
        [code, first_entry_date, target_date],
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return float(row[0])


def _held_days_since(
    conn: duckdb.DuckDBPyConnection,
    entry_date: date | None,
    target_date: date,
) -> int | None:
    """entry_date 〜 target_date の営業日数（entry 当日 = 0）。entry 日不明は None。"""
    if entry_date is None:
        return None
    if entry_date > target_date:
        return 0
    days = get_trading_days(conn, entry_date, target_date)
    return len(days) - 1
```

既存 `_peak_close` / `_held_days` は（`tests/test_trailing_stop.py` が直接使うため）残し、本体を次に置き換える。docstring は既存のまま:

```python
    entry_source: Any = sqlite_conn if sqlite_conn is not None else conn
    row = entry_source.execute(
        "SELECT MIN(entry_date) FROM position_entries WHERE code = ? AND sell_date IS NULL",
        [code],
    ).fetchone()
    first_entry = _to_date(row[0]) if row is not None else None
    return _peak_close_since(conn, code, first_entry, target_date)
```

```python
    entry_source: Any = sqlite_conn if sqlite_conn is not None else conn
    row = entry_source.execute(
        "SELECT MAX(entry_date) FROM position_entries WHERE code = ? AND sell_date IS NULL",
        [code],
    ).fetchone()
    entry_date = _to_date(row[0]) if row is not None else None
    return _held_days_since(conn, entry_date, target_date)
```

`_to_date` は `from kabusys.strategy.holdings import HeldPosition, _to_date, load_auto_positions, merge_positions` で import する（`Any` が未 import なら `typing` から追加）。

- [ ] **Step 4: `_generate_sell_signals` を保有リスト入力に変更**

引数末尾に `positions: list[HeldPosition] | None = None,` を追加し、docstring の Args に「positions: 判定対象の保有。None のとき positions / position_entries から読み込む（従来動作）。」を追記。冒頭の `pos_rows = conn.execute(...)` 〜 `for code, avg_price, close in pos_rows:` を次に置き換える:

```python
    if positions is None:
        positions = load_auto_positions(conn, target_date, sqlite_conn=sqlite_conn)
    closes = _latest_closes(conn, [p.code for p in positions], target_date)

    sell_signals: list[dict[str, Any]] = []
    for pos in positions:
        code = pos.code
        avg_price = pos.avg_price
        close = closes.get(code)
```

ループ内の変更:
- `peak = _peak_close(conn, code, target_date, sqlite_conn=sqlite_conn)` → `peak = _peak_close_since(conn, code, pos.first_entry_date, target_date)`
- `_held_days(conn, code, target_date, sqlite_conn=sqlite_conn)`（2 箇所: `held_for_trail` と `held`）→ `_held_days_since(conn, pos.latest_entry_date, target_date)`
- `sell_signals.append({...})` の 5 箇所すべてに `"qty": pos.qty, "source": pos.source` を追加。

`_generate_sell_signals` の直前に追加:

```python
def _latest_closes(
    conn: duckdb.DuckDBPyConnection, codes: list[str], target_date: date
) -> dict[str, float]:
    """codes の target_date 以前で最新の終値 {code: close}。"""
    if not codes:
        return {}
    placeholders = ",".join(["?"] * len(codes))
    rows = conn.execute(
        f"""
        SELECT pd.code, CAST(pd.close AS DOUBLE)
        FROM prices_daily pd
        INNER JOIN (
            SELECT code, MAX(date) AS max_date
            FROM prices_daily
            WHERE date <= ? AND code IN ({placeholders})
            GROUP BY code
        ) mp ON pd.code = mp.code AND pd.date = mp.max_date
        """,
        [target_date, *codes],
    ).fetchall()
    return {code: close for code, close in rows if close is not None}
```

- [ ] **Step 5: `generate_signals` に `manual_positions` / `sell_signals_out` を追加**

キーワード専用引数（`sqlite_conn` の後）に追加:

```python
    manual_positions: list[HeldPosition] | None = None,
    sell_signals_out: list[dict[str, Any]] | None = None,
```

docstring Args に追記:
- `manual_positions: 手動約定由来の保有。指定時は自動分と合算して SELL 判定する。バックテストでは指定しないこと。`
- `sell_signals_out: 指定時、signals 書き込み成功後に SELL シグナル（code/score/reason/qty/source）を extend する。`

`# 7. SELL シグナル生成` の呼び出しを次に変更:

```python
    held_positions = load_auto_positions(conn, target_date, sqlite_conn=sqlite_conn)
    if manual_positions:
        held_positions = merge_positions(held_positions, manual_positions)
    sell_signals = _generate_sell_signals(
        conn,
        target_date,
        score_map,
        threshold,
        # …既存の引数はそのまま…
        score_drop_atr_gate=score_drop_atr_gate,
        positions=held_positions,
    )
```

signals 書き込みの `COMMIT` を含む try/except の直後（`total = ...` の前）に:

```python
    if sell_signals_out is not None:
        sell_signals_out.extend(sell_signals)
```

- [ ] **Step 6: 新規テストと既存の SELL 系テストが通ることを確認**

Run: `python -m pytest tests/test_manual_sell_advisory.py tests/test_signal_generator.py tests/test_trailing_stop.py tests/test_generate_signals_config.py tests/test_bb_reversal.py -q`
Expected: PASS（既存テストは無修正）

- [ ] **Step 7: 全テストで回帰がないことを確認**

Run: `python -m pytest -q`
Expected: 全 PASS

- [ ] **Step 8: Commit**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_manual_sell_advisory.py
git commit -m "feat: evaluate sell rules on unified holdings incl. manual positions (#410)"
```

---

### Task 3: 設定と `manual_action_queue`

**Files:**
- Modify: `src/kabusys/config.py`（`portfolio_value` の後）
- Modify: `src/kabusys/data/schema.py`（`_MANUAL_TRADES` の後と `_ALL_DDL`）
- Modify: `src/kabusys/operations/manual_trades.py`
- Modify: `.env.example`
- Test: `tests/test_manual_actions.py`（新規）、`tests/test_config.py`

**Interfaces:**
- Consumes: Task 2 の SELL dict（`code`, `reason`, `qty`, `source`）
- Produces:
  - `Settings.manual_trading_enabled -> bool`、`Settings.manual_trading_initial_cash -> float`
  - `ManualAction(action_id: str, date: date, code: str, action: str, qty: int, reason: str, status: str, created_at: datetime, updated_at: datetime | None)`
  - `ensure_manual_action_schema(conn) -> None`
  - `build_action_id(target_date: date, code: str, action: str) -> str`
  - `record_sell_candidates(conn, target_date: date, sell_signals: list[dict[str, Any]]) -> int`
  - `list_manual_actions(conn, *, target_date: date | None = None, status: str | None = None) -> list[ManualAction]`
  - `update_manual_action_status(conn, action_id: str, status: str) -> int`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_manual_actions.py`:

```python
"""manual_action_queue（手動売却候補）のテスト"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from kabusys.operations.manual_trades import (
    ensure_manual_action_schema,
    list_manual_actions,
    record_sell_candidates,
    update_manual_action_status,
)

D = date(2026, 10, 8)


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    ensure_manual_action_schema(c)
    yield c
    c.close()


def _sig(code, reason="stop_loss", qty=100, source="manual"):
    return {"code": code, "score": 0.1, "reason": reason, "qty": qty, "source": source}


def test_records_only_manual_and_mixed(conn):
    n = record_sell_candidates(
        conn, D, [_sig("A", source="manual"), _sig("B", source="mixed"), _sig("C", source="auto")]
    )
    assert n == 2
    actions = list_manual_actions(conn, target_date=D)
    assert [(a.action_id, a.code, a.action, a.status) for a in actions] == [
        ("2026-10-08_A_sell_candidate", "A", "sell_candidate", "open"),
        ("2026-10-08_B_sell_candidate", "B", "sell_candidate", "open"),
    ]


def test_rerecord_updates_reason_and_keeps_status(conn):
    record_sell_candidates(conn, D, [_sig("A", reason="score_drop", qty=100)])
    update_manual_action_status(conn, "2026-10-08_A_sell_candidate", "done")

    record_sell_candidates(conn, D, [_sig("A", reason="stop_loss", qty=200)])

    [action] = list_manual_actions(conn, target_date=D)
    assert action.status == "done"
    assert action.reason == "stop_loss"
    assert action.qty == 200
    assert action.updated_at is not None


def test_list_filters_by_status(conn):
    record_sell_candidates(conn, D, [_sig("A"), _sig("B")])
    update_manual_action_status(conn, "2026-10-08_B_sell_candidate", "skipped")
    assert [a.code for a in list_manual_actions(conn, status="open")] == ["A"]


def test_update_rejects_unknown_status(conn):
    record_sell_candidates(conn, D, [_sig("A")])
    with pytest.raises(ValueError):
        update_manual_action_status(conn, "2026-10-08_A_sell_candidate", "sold")


def test_init_schema_creates_manual_action_queue():
    from kabusys.data.schema import init_schema

    c = init_schema(":memory:")
    row = c.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'manual_action_queue'"
    ).fetchone()
    assert row[0] == 1


def test_execution_package_never_references_manual_action_queue():
    """Execution Engine 側が手動売却候補を発注対象として読まないこと。"""
    import kabusys.execution as execution_pkg

    pkg_dir = Path(execution_pkg.__file__).parent
    offenders = [
        p.name for p in pkg_dir.rglob("*.py") if "manual_action_queue" in p.read_text(encoding="utf-8")
    ]
    assert offenders == []
```

`tests/test_config.py` に追加（既存の monkeypatch パターンに合わせる）:

```python
def test_manual_trading_defaults(monkeypatch):
    from kabusys.config import Settings

    monkeypatch.delenv("MANUAL_TRADING_ENABLED", raising=False)
    monkeypatch.delenv("MANUAL_TRADING_INITIAL_CASH", raising=False)
    monkeypatch.setenv("PORTFOLIO_VALUE", "3000000")
    s = Settings()
    assert s.manual_trading_enabled is False
    assert s.manual_trading_initial_cash == 3_000_000.0


def test_manual_trading_initial_cash_explicit(monkeypatch):
    from kabusys.config import Settings

    monkeypatch.setenv("MANUAL_TRADING_ENABLED", "true")
    monkeypatch.setenv("MANUAL_TRADING_INITIAL_CASH", "2000000")
    s = Settings()
    assert s.manual_trading_enabled is True
    assert s.manual_trading_initial_cash == 2_000_000.0


def test_manual_trading_initial_cash_invalid(monkeypatch):
    import pytest

    from kabusys.config import Settings

    monkeypatch.setenv("MANUAL_TRADING_INITIAL_CASH", "abc")
    with pytest.raises(ValueError):
        _ = Settings().manual_trading_initial_cash
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_manual_actions.py tests/test_config.py -q`
Expected: FAIL（`ImportError: cannot import name 'ensure_manual_action_schema'`、`AttributeError: manual_trading_enabled`）

- [ ] **Step 3: 設定を追加**

`config.py` の `portfolio_value` プロパティの後に:

```python
    @property
    def manual_trading_enabled(self) -> bool:
        """手動約定の保有を SELL 判定・BUY 株数計算に含めるか（MANUAL_TRADING_ENABLED、既定 false）。"""
        return _parse_bool_env("MANUAL_TRADING_ENABLED", default=False)

    @property
    def manual_trading_initial_cash(self) -> float:
        """手動運用の元手（MANUAL_TRADING_INITIAL_CASH、未設定時は PORTFOLIO_VALUE）。"""
        raw = os.environ.get("MANUAL_TRADING_INITIAL_CASH")
        if raw is None or raw.strip() == "":
            return self.portfolio_value
        try:
            val = float(raw)
        except ValueError as exc:
            raise ValueError(
                f"MANUAL_TRADING_INITIAL_CASH の値が不正です: '{raw}'. 正の数値で設定してください。"
            ) from exc
        if val <= 0:
            raise ValueError(
                f"MANUAL_TRADING_INITIAL_CASH は正の数値で設定してください: {val}"
            )
        return val
```

`.env.example` の `LINE_NOTIFY_ENABLED` ブロックの前に:

```
# --- 手動注文メイン運用 ---
# true のとき、手動約定（manual_trades）の保有を SELL 判定・BUY 株数計算に含める
MANUAL_TRADING_ENABLED=false
# 手動運用の元手（未設定時は PORTFOLIO_VALUE）
MANUAL_TRADING_INITIAL_CASH=
```

- [ ] **Step 4: スキーマを追加**

`schema.py` の `_MANUAL_TRADES` の後:

```python
_MANUAL_ACTION_QUEUE = """
CREATE TABLE IF NOT EXISTS manual_action_queue (
    action_id   VARCHAR   NOT NULL PRIMARY KEY,
    date        DATE      NOT NULL,
    code        VARCHAR   NOT NULL,
    action      VARCHAR   NOT NULL CHECK (action IN ('sell_candidate')),
    qty         BIGINT    NOT NULL CHECK (qty > 0),
    reason      VARCHAR   NOT NULL,
    status      VARCHAR   NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done', 'skipped')),
    created_at  TIMESTAMP NOT NULL DEFAULT current_timestamp,
    updated_at  TIMESTAMP
)
"""
```

`_ALL_DDL` の `_MANUAL_TRADES,` の後に `_MANUAL_ACTION_QUEUE,` を追加。

- [ ] **Step 5: 操作関数を追加**

`operations/manual_trades.py` に追加（`from typing import Any` は既存）:

```python
_ACTION_STATUSES = frozenset({"open", "done", "skipped"})
_MANUAL_SOURCES = frozenset({"manual", "mixed"})


@dataclass(frozen=True)
class ManualAction:
    action_id: str
    date: date
    code: str
    action: str
    qty: int
    reason: str
    status: str
    created_at: datetime
    updated_at: datetime | None


def ensure_manual_action_schema(conn: duckdb.DuckDBPyConnection) -> None:
    from kabusys.data.schema import _MANUAL_ACTION_QUEUE

    try:
        conn.execute(_MANUAL_ACTION_QUEUE)
    except duckdb.Error as exc:
        msg = str(exc).lower()
        if "read-only" in msg or "read only" in msg:
            return
        raise


def build_action_id(target_date: date, code: str, action: str) -> str:
    return f"{target_date.isoformat()}_{code}_{action}"


def record_sell_candidates(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    sell_signals: list[dict[str, Any]],
) -> int:
    """手動保有（source=manual/mixed）の SELL を売却候補として記録する（冪等）。

    既存行は qty / reason のみ更新し、ユーザーが変更した status は保持する。
    発注は行わない。Execution Engine はこのテーブルを参照しない。
    """
    ensure_manual_action_schema(conn)
    recorded = 0
    for sig in sell_signals:
        if sig.get("source") not in _MANUAL_SOURCES:
            continue
        conn.execute(
            """
            INSERT INTO manual_action_queue (action_id, date, code, action, qty, reason)
            VALUES (?, ?, ?, 'sell_candidate', ?, ?)
            ON CONFLICT (action_id) DO UPDATE SET
                qty = excluded.qty,
                reason = excluded.reason,
                updated_at = current_timestamp
            """,
            [
                build_action_id(target_date, sig["code"], "sell_candidate"),
                target_date,
                sig["code"],
                int(sig["qty"]),
                str(sig["reason"]),
            ],
        )
        recorded += 1
    return recorded


def list_manual_actions(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_date: date | None = None,
    status: str | None = None,
) -> list[ManualAction]:
    ensure_manual_action_schema(conn)
    where: list[str] = []
    params: list[Any] = []
    if target_date is not None:
        where.append("date = ?")
        params.append(target_date)
    if status is not None:
        where.append("status = ?")
        params.append(status)
    sql = (
        "SELECT action_id, date, code, action, qty, reason, status, created_at, updated_at "
        "FROM manual_action_queue"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, code"
    return [
        ManualAction(
            action_id=r[0], date=r[1], code=r[2], action=r[3], qty=int(r[4]),
            reason=r[5], status=r[6], created_at=r[7], updated_at=r[8],
        )
        for r in conn.execute(sql, params).fetchall()
    ]


def update_manual_action_status(
    conn: duckdb.DuckDBPyConnection, action_id: str, status: str
) -> int:
    if status not in _ACTION_STATUSES:
        raise ValueError(f"status は open/done/skipped を指定してください: {status!r}")
    ensure_manual_action_schema(conn)
    before = conn.execute(
        "SELECT COUNT(*) FROM manual_action_queue WHERE action_id = ?", [action_id]
    ).fetchone()[0]
    conn.execute(
        "UPDATE manual_action_queue SET status = ?, updated_at = current_timestamp "
        "WHERE action_id = ?",
        [status, action_id],
    )
    return int(before)
```

- [ ] **Step 6: テストが通ることを確認**

Run: `python -m pytest tests/test_manual_actions.py tests/test_config.py tests/test_manual_trades.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/kabusys/config.py src/kabusys/data/schema.py src/kabusys/operations/manual_trades.py .env.example tests/test_manual_actions.py tests/test_config.py
git commit -m "feat: add manual trading settings and manual_action_queue (#410)"
```

---

### Task 4: 夜間シグナルジョブへの配線

**Files:**
- Modify: `scripts/run_strategy_signal.py`（import と 283-303 行の `generate_signals` 呼び出し周辺）
- Test: `tests/test_manual_sell_advisory.py`

**Interfaces:**
- Consumes: `Settings.manual_trading_enabled`（Task 3）、`load_manual_held_positions`（Task 1）、`generate_signals(manual_positions=, sell_signals_out=)`（Task 2）、`record_sell_candidates`（Task 3）
- Produces: `run_manual_signal_step(conn, target_date, *, enabled: bool, generate: Callable[..., int]) -> tuple[int, int]` を `kabusys/operations/manual_trades.py` に置き、スクリプトはそれを呼ぶ（テスト可能にするため）。戻り値は `(signals 件数, 記録した売却候補件数)`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_manual_sell_advisory.py` に追加:

```python
def test_run_manual_signal_step_records_candidates_when_enabled(conn):
    from kabusys.operations.manual_trades import list_manual_actions, run_manual_signal_step

    add_manual_trade(
        conn,
        ManualTradeInput(trade_date=TARGET - timedelta(days=3), code="S1", side="buy", qty=100, price=1000.0),
    )
    _price(conn, TARGET, "S1", 900.0)

    n, recorded = run_manual_signal_step(conn, TARGET, enabled=True, generate=generate_signals)

    assert n >= 1
    assert recorded == 1
    [action] = list_manual_actions(conn, target_date=TARGET)
    assert (action.code, action.reason, action.qty) == ("S1", "stop_loss", 100)


def test_run_manual_signal_step_disabled_ignores_manual_trades(conn):
    from kabusys.operations.manual_trades import list_manual_actions, run_manual_signal_step

    add_manual_trade(
        conn,
        ManualTradeInput(trade_date=TARGET - timedelta(days=3), code="S2", side="buy", qty=100, price=1000.0),
    )
    _price(conn, TARGET, "S2", 900.0)

    _, recorded = run_manual_signal_step(conn, TARGET, enabled=False, generate=generate_signals)

    assert recorded == 0
    assert list_manual_actions(conn, target_date=TARGET) == []
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_manual_sell_advisory.py -q -k run_manual_signal_step`
Expected: FAIL（`ImportError: cannot import name 'run_manual_signal_step'`）

- [ ] **Step 3: `run_manual_signal_step` を実装**

`operations/manual_trades.py` に追加（`from collections.abc import Callable` を import）:

```python
def run_manual_signal_step(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    *,
    enabled: bool,
    generate: Callable[..., int],
    **generate_kwargs: Any,
) -> tuple[int, int]:
    """generate_signals を手動保有込みで実行し、手動保有の SELL を売却候補として記録する。

    enabled=False のときは手動保有を渡さず、候補も記録しない（従来動作）。
    signals 書き込み後に候補記録が失敗した場合は例外を送出する（ジョブを失敗扱いにするため）。
    """
    manual_positions = load_manual_held_positions(conn, target_date) if enabled else None
    sell_out: list[dict[str, Any]] = []
    n = generate(
        conn,
        target_date,
        manual_positions=manual_positions,
        sell_signals_out=sell_out,
        **generate_kwargs,
    )
    recorded = record_sell_candidates(conn, target_date, sell_out) if enabled else 0
    return n, recorded
```

- [ ] **Step 4: スクリプトを配線**

`scripts/run_strategy_signal.py` に `from kabusys.operations.manual_trades import run_manual_signal_step` を追加し、`n = generate_signals(conn, target_date, use_ma200_filter=True, ...)` を次に置き換える（キーワード引数は既存と同じものをそのまま `**generate_kwargs` に渡す）:

```python
        n, manual_recorded = run_manual_signal_step(
            conn,
            target_date,
            enabled=settings.manual_trading_enabled,
            generate=generate_signals,
            use_ma200_filter=True,
            adaptive_threshold_vol_regime=True,
            topix_vol_low_threshold=0.12,
            dynamic_trailing_stop=True,
            trail_stage2_mult=1.8,
            trail_stage3_mult=1.5,
            entry_blocked=entry_blocked,
            block_entries_by_regime=False,
            sqlite_conn=sqlite_conn,
            # W1_08 IS パラメータ
            entry_3d_max_abs_return=0.08,
            quality_score_min=-0.30,
            score_drop_atr_gate=1.0,
        )
        _updated_rows["signals"] = n
        if settings.manual_trading_enabled:
            _updated_rows["manual_action_queue"] = manual_recorded
            logger.info("手動売却候補: %d 件記録 (date=%s)", manual_recorded, target_date)
```

候補記録の例外は既存の `except Exception` に落ち、ジョブは `failed` になる（signals はコミット済み）。

- [ ] **Step 5: テストとスクリプトの import 確認**

Run: `python -m pytest tests/test_manual_sell_advisory.py tests/test_scripts_batch.py -q`
Run: `python -c "import scripts.run_strategy_signal"`
Expected: PASS / エラーなし

- [ ] **Step 6: Commit**

```bash
git add src/kabusys/operations/manual_trades.py scripts/run_strategy_signal.py tests/test_manual_sell_advisory.py
git commit -m "feat: record manual sell candidates in nightly signal job (#410)"
```

---

### Task 5: BUY 側（資金計算と買い増し）

**Files:**
- Modify: `src/kabusys/operations/manual_trades.py`
- Modify: `scripts/run_portfolio_construction.py`（`main` の portfolio_value 分岐 314-327 行、`current_positions` 365-374 行、`_collect_evening_signals` 呼び出し）
- Test: `tests/test_manual_trades.py`

**Interfaces:**
- Consumes: `evaluate_manual_positions`（既存）、`manual_position_qty_map`（Task 1）、`Settings.manual_trading_*`（Task 3）
- Produces:
  - `calc_manual_portfolio_value(conn, initial_cash: float, *, as_of: date) -> tuple[float, float]`（`(portfolio_value, available_cash)`）
  - `merge_current_positions(current: dict[str, int], manual_qty: dict[str, int], codes: list[str]) -> dict[str, int]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_manual_trades.py` に追加:

```python
def _prices_table(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS prices_daily (date DATE, code VARCHAR, open DOUBLE, "
        "high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)"
    )


def test_calc_manual_portfolio_value(conn):
    from kabusys.operations.manual_trades import calc_manual_portfolio_value

    _prices_table(conn)
    add_manual_trade(conn, ManualTradeInput(trade_date=date(2026, 9, 1), code="7203", side="buy", qty=200, price=1000.0, fees=100.0))
    add_manual_trade(conn, ManualTradeInput(trade_date=date(2026, 9, 2), code="7203", side="sell", qty=100, price=1100.0, fees=50.0))
    conn.execute("INSERT INTO prices_daily VALUES ('2026-09-02', '7203', 0, 0, 0, 1200, 0)")

    pv, cash = calc_manual_portfolio_value(conn, 1_000_000.0, as_of=date(2026, 9, 2))

    # 現金 = 1,000,000 - (200,000 + 100) + (110,000 - 50) = 909,850
    assert cash == pytest.approx(909_850.0)
    # 総資産 = 現金 + 100株 × 1200
    assert pv == pytest.approx(1_029_850.0)


def test_calc_manual_portfolio_value_missing_price_counts_zero(conn):
    from kabusys.operations.manual_trades import calc_manual_portfolio_value

    _prices_table(conn)
    add_manual_trade(conn, ManualTradeInput(trade_date=date(2026, 9, 1), code="7203", side="buy", qty=100, price=1000.0))

    pv, cash = calc_manual_portfolio_value(conn, 500_000.0, as_of=date(2026, 9, 2))

    assert cash == pytest.approx(400_000.0)
    assert pv == pytest.approx(400_000.0)


def test_calc_manual_portfolio_value_no_trades(conn):
    from kabusys.operations.manual_trades import calc_manual_portfolio_value

    assert calc_manual_portfolio_value(conn, 500_000.0, as_of=date(2026, 9, 2)) == (500_000.0, 500_000.0)


def test_merge_current_positions_adds_manual_qty_for_candidates():
    from kabusys.operations.manual_trades import merge_current_positions

    result = merge_current_positions({"7203": 100}, {"7203": 200, "6758": 100, "9984": 100}, ["7203", "6758"])
    assert result == {"7203": 300, "6758": 100}
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_manual_trades.py -q -k "portfolio_value or merge_current"`
Expected: FAIL（ImportError）

- [ ] **Step 3: 実装**

`operations/manual_trades.py` に追加（`import logging` と `logger = logging.getLogger(__name__)` が無ければ追加）:

```python
def calc_manual_portfolio_value(
    conn: duckdb.DuckDBPyConnection,
    initial_cash: float,
    *,
    as_of: date,
) -> tuple[float, float]:
    """手動運用の (総資産, 利用可能現金) を返す。

    現金 = 元手 − Σ(BUY 約定額 + 手数料) + Σ(SELL 約定額 − 手数料)
    総資産 = 現金 + Σ(手動保有数量 × as_of 以前の最新終値)。終値なしは時価 0 として warning。
    """
    ensure_manual_trade_schema(conn)
    cash = float(initial_cash)
    rows = conn.execute(
        """
        SELECT side, SUM(qty * price), SUM(fees)
        FROM manual_trades
        WHERE trade_date <= ?
        GROUP BY side
        """,
        [as_of],
    ).fetchall()
    for side, amount, fees in rows:
        amount_f = float(amount or 0.0)
        fees_f = float(fees or 0.0)
        if side == "buy":
            cash -= amount_f + fees_f
        else:
            cash += amount_f - fees_f

    market_value = 0.0
    for valuation in evaluate_manual_positions(conn, as_of=as_of):
        if valuation.market_value is None:
            logger.warning(
                "手動保有 %s の終値がないため時価 0 として総資産を計算します as_of=%s",
                valuation.code,
                as_of,
            )
            continue
        market_value += valuation.market_value
    return max(cash + market_value, 0.0), max(cash, 0.0)


def merge_current_positions(
    current: dict[str, int], manual_qty: dict[str, int], codes: list[str]
) -> dict[str, int]:
    """BUY 候補 codes について、自動分の保有株数に手動保有数量を加算する。"""
    merged = dict(current)
    for code in codes:
        qty = manual_qty.get(code, 0)
        if qty > 0:
            merged[code] = merged.get(code, 0) + qty
    return merged
```

- [ ] **Step 4: スクリプトを配線**

`scripts/run_portfolio_construction.py`:
- import に `from kabusys.operations.manual_trades import calc_manual_portfolio_value, manual_position_qty_map, merge_current_positions` を追加。
- `main` の `if settings.is_live:` を次の分岐で包む（既存の live / paper / その他分岐は `elif` / `else` 内にそのまま残す）:

```python
        manual_qty: dict[str, int] = {}
        if settings.manual_trading_enabled:
            portfolio_value, available_cash = calc_manual_portfolio_value(
                conn, settings.manual_trading_initial_cash, as_of=target_date
            )
            manual_qty = manual_position_qty_map(conn, as_of=target_date)
            logger.info(
                "手動運用: portfolio_value=%.0f 円, available_cash=%.0f 円, 手動保有 %d 銘柄",
                portfolio_value,
                available_cash,
                len(manual_qty),
            )
        elif settings.is_live:
            portfolio_value, available_cash = _calc_live_portfolio_value(settings, conn)
        elif settings.is_paper or settings.is_dev:
            # …既存のまま…
```

- `current_positions = {r[0]: int(r[1]) for r in pos_cur.fetchall()}` の直後に:

```python
                    current_positions = merge_current_positions(
                        current_positions, manual_qty, codes
                    )
```

- [ ] **Step 5: テストとスクリプト import 確認**

Run: `python -m pytest tests/test_manual_trades.py tests/test_line_reports.py -q`
Run: `python -c "import scripts.run_portfolio_construction"`
Expected: PASS / エラーなし

- [ ] **Step 6: Commit**

```bash
git add src/kabusys/operations/manual_trades.py scripts/run_portfolio_construction.py tests/test_manual_trades.py
git commit -m "feat: size buys with manual holdings and manual cash (#410)"
```

---

### Task 6: 夜 LINE 通知

**Files:**
- Modify: `src/kabusys/operations/line_reports.py`（`format_evening_message` 140-188 行）
- Modify: `scripts/run_portfolio_construction.py`（`_collect_evening_signals` 243-286 行）
- Test: `tests/test_line_reports.py`

**Interfaces:**
- Consumes: `manual_action_queue`（Task 3）、`main()` 内の `manual_qty`（Task 5）
- Produces:
  - `format_evening_message` の入力 dict に任意キー追加: BUY `add_on: bool`、SELL `qty: int | None`, `reason: str | None`, `manual: bool`
  - `_collect_evening_signals(conn, target_date, manual_codes: set[str] | None = None)`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_line_reports.py` に追加:

```python
def test_evening_message_shows_manual_sell_details_and_add_on():
    msg = format_evening_message(
        inserted=1,
        report_date="2026-10-08",
        buy_signals=[{"code": "7203", "name": "トヨタ", "size": 100, "add_on": True}],
        sell_signals=[
            {"code": "6758", "name": "ソニー", "qty": 200, "reason": "stop_loss", "manual": True},
            {"code": "9984", "name": "SBG"},
        ],
    )
    assert "  7203 トヨタ  100株 [買い増し]" in msg
    assert "  6758 ソニー  200株 (損切り) [手動保有]" in msg
    assert "  9984 SBG\n" in msg + "\n"


def test_collect_evening_signals_without_manual_action_table():
    import duckdb

    from scripts.run_portfolio_construction import _collect_evening_signals

    c = duckdb.connect(":memory:")
    c.execute("CREATE TABLE signal_queue (signal_id VARCHAR, date DATE, code VARCHAR, side VARCHAR, size BIGINT, status VARCHAR)")
    c.execute("CREATE TABLE signals (date DATE, code VARCHAR, side VARCHAR, score DOUBLE)")
    c.execute("CREATE TABLE stocks (code VARCHAR, name VARCHAR)")
    c.execute("INSERT INTO signals VALUES ('2026-10-08', '6758', 'sell', 0.1)")

    buy, sell = _collect_evening_signals(c, date(2026, 10, 8))

    assert buy == []
    assert sell == [{"code": "6758", "name": "6758", "qty": None, "reason": None, "manual": False}]


def test_collect_evening_signals_with_manual_actions():
    import duckdb

    from kabusys.operations.manual_trades import record_sell_candidates
    from scripts.run_portfolio_construction import _collect_evening_signals

    d = date(2026, 10, 8)
    c = duckdb.connect(":memory:")
    c.execute("CREATE TABLE signal_queue (signal_id VARCHAR, date DATE, code VARCHAR, side VARCHAR, size BIGINT, status VARCHAR)")
    c.execute("CREATE TABLE signals (date DATE, code VARCHAR, side VARCHAR, score DOUBLE)")
    c.execute("CREATE TABLE stocks (code VARCHAR, name VARCHAR)")
    c.execute("INSERT INTO stocks VALUES ('7203', 'トヨタ'), ('6758', 'ソニー')")
    c.execute("INSERT INTO signal_queue VALUES ('q1', '2026-10-08', '7203', 'buy', 100, 'pending')")
    c.execute("INSERT INTO signals VALUES ('2026-10-08', '6758', 'sell', 0.1)")
    record_sell_candidates(c, d, [{"code": "6758", "reason": "trailing_stop", "qty": 300, "source": "manual"}])

    buy, sell = _collect_evening_signals(c, d, manual_codes={"7203"})

    assert buy == [{"code": "7203", "name": "トヨタ", "size": 100, "add_on": True}]
    assert sell == [{"code": "6758", "name": "ソニー", "qty": 300, "reason": "trailing_stop", "manual": True}]
```

既存 `_collect_evening_signals` テストがあり、BUY dict に `add_on`、SELL dict に新キーが増えて等価比較が壊れる場合は、Step 3 の結果に合わせて **期待値に新キーを追加する** 形で更新してよい（挙動変更ではなくキー追加のため）。

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_line_reports.py -q`
Expected: FAIL

- [ ] **Step 3: `format_evening_message` を拡張**

モジュール先頭付近に:

```python
_SELL_REASON_LABELS: dict[str, str] = {
    "stop_loss": "損切り",
    "trailing_stop": "トレーリング",
    "time_exit": "保有期限",
    "score_drop": "スコア低下",
    "earnings_avoidance": "決算回避",
}
```

BUY 行と SELL 行の組み立てを次に変更:

```python
            for s in shown:
                suffix = " [買い増し]" if s.get("add_on") else ""
                lines.append(f"  {s['code']} {s['name']}  {s['size']}株{suffix}")
```

```python
            for s in shown:
                line = f"  {s['code']} {s['name']}"
                if s.get("qty"):
                    line += f"  {s['qty']}株"
                if s.get("reason"):
                    line += f" ({_SELL_REASON_LABELS.get(s['reason'], s['reason'])})"
                if s.get("manual"):
                    line += " [手動保有]"
                lines.append(line)
```

docstring の要素説明を更新:
- `buy_signals 各要素: {"code", "name", "size", "add_on"(任意)}`
- `sell_signals 各要素: {"code", "name", "qty"(任意), "reason"(任意), "manual"(任意)}`

- [ ] **Step 4: `_collect_evening_signals` を拡張**

シグネチャを `(conn, target_date, manual_codes: set[str] | None = None)` にし、BUY の dict 生成を:

```python
        manual = manual_codes or set()
        buy = [
            {"code": r[0], "name": r[1], "size": int(r[2]), "add_on": r[0] in manual}
            for r in rows
        ]
```

SELL 取得を次に置き換える:

```python
    sell: list[dict] = []
    try:
        has_actions = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'main' AND table_name = 'manual_action_queue'"
        ).fetchone()[0]
        if has_actions:
            rows = conn.execute(
                """
                SELECT s.code, COALESCE(st.name, s.code), m.qty, m.reason, m.action_id IS NOT NULL
                FROM signals s
                LEFT JOIN stocks st ON s.code = st.code
                LEFT JOIN manual_action_queue m
                  ON m.date = s.date AND m.code = s.code AND m.action = 'sell_candidate'
                WHERE s.date = ? AND s.side = 'sell'
                ORDER BY s.code
                """,
                [target_date],
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT s.code, COALESCE(st.name, s.code), NULL, NULL, FALSE
                FROM signals s
                LEFT JOIN stocks st ON s.code = st.code
                WHERE s.date = ? AND s.side = 'sell'
                ORDER BY s.code
                """,
                [target_date],
            ).fetchall()
        sell = [
            {
                "code": r[0],
                "name": r[1],
                "qty": int(r[2]) if r[2] is not None else None,
                "reason": r[3],
                "manual": bool(r[4]),
            }
            for r in rows
        ]
    except Exception:
        logger.warning("LINE通知用SELLシグナル詳細の取得に失敗しました", exc_info=True)
```

docstring に「SELL は manual_action_queue があれば理由・株数を付与（テーブル無しでも動作）」を追記。

`main()` の夜通知で `_collect_evening_signals(conn, target_date)` を `_collect_evening_signals(conn, target_date, manual_codes=set(manual_qty))` に変更する。

- [ ] **Step 5: テストが通ることを確認**

Run: `python -m pytest tests/test_line_reports.py tests/test_scripts_batch.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/kabusys/operations/line_reports.py scripts/run_portfolio_construction.py tests/test_line_reports.py
git commit -m "feat: show manual sell candidates and add-on buys in evening LINE (#410)"
```

---

### Task 7: ダッシュボード「売却候補」タブ

**Files:**
- Modify: `src/kabusys/monitoring/dashboard_data.py`（`load_manual_positions` の後）
- Modify: `src/kabusys/monitoring/pages/12_Manual_Trades.py`
- Test: `tests/test_dashboard_pages.py`

**Interfaces:**
- Consumes: `list_manual_actions`, `update_manual_action_status`（Task 3）
- Produces: `load_manual_actions(conn, *, target_date: date | None = None, status: str | None = None) -> pd.DataFrame`（列: `action_id, date, code, action, qty, reason, status, updated_at`）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_dashboard_pages.py` に追加:

```python
def test_load_manual_actions_returns_dataframe():
    import duckdb

    from kabusys.monitoring.dashboard_data import load_manual_actions
    from kabusys.operations.manual_trades import record_sell_candidates

    c = duckdb.connect(":memory:")
    d = date(2026, 10, 8)
    record_sell_candidates(c, d, [{"code": "7203", "reason": "stop_loss", "qty": 100, "source": "manual"}])

    df = load_manual_actions(c, target_date=d)

    assert list(df.columns) == ["action_id", "date", "code", "action", "qty", "reason", "status", "updated_at"]
    assert df.iloc[0]["code"] == "7203"
    assert df.iloc[0]["status"] == "open"


def test_load_manual_actions_empty():
    import duckdb

    from kabusys.monitoring.dashboard_data import load_manual_actions

    df = load_manual_actions(duckdb.connect(":memory:"))
    assert df.empty
    assert "action_id" in df.columns
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_dashboard_pages.py -q -k manual_actions`
Expected: FAIL（ImportError）

- [ ] **Step 3: ローダーを実装**

`dashboard_data.py` に追加（`list_manual_actions` を import）:

読み取り専用接続では `ensure_manual_action_schema` が CREATE を黙ってスキップするため、テーブル未作成時に SELECT が `duckdb.CatalogException` になる。これを捕捉して空 DataFrame を返す。

```python
_MANUAL_ACTION_COLUMNS = ["action_id", "date", "code", "action", "qty", "reason", "status", "updated_at"]


def load_manual_actions(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_date: date | None = None,
    status: str | None = None,
) -> pd.DataFrame:
    """manual_action_queue（手動売却候補）を DataFrame で返す。テーブル未作成時は空。"""
    try:
        rows = list_manual_actions(conn, target_date=target_date, status=status)
    except duckdb.CatalogException:
        rows = []
    return pd.DataFrame(
        [{col: getattr(r, col) for col in _MANUAL_ACTION_COLUMNS} for r in rows],
        columns=_MANUAL_ACTION_COLUMNS,
    )
```

- [ ] **Step 4: ページにタブを追加**

`12_Manual_Trades.py`:
- import に `load_manual_actions` と `update_manual_action_status` を追加。
- タブ定義を `tab_add, tab_positions, tab_actions, tab_history = st.tabs(["入力", "手動ポジション", "売却候補", "履歴"])` に変更。
- `with tab_history:` の前に:

```python
_REASON_LABELS = {
    "stop_loss": "損切り",
    "trailing_stop": "トレーリング",
    "time_exit": "保有期限",
    "score_drop": "スコア低下",
    "earnings_avoidance": "決算回避",
}

with tab_actions:
    st.subheader("手動売却候補")
    st.caption("KabuSys は発注しません。証券画面で手動売却後、約定を「入力」タブで登録してください。")
    show_all = st.checkbox("対応済み・見送りも表示", value=False)
    conn = connect_duckdb_ro(settings.duckdb_path)
    try:
        actions = load_manual_actions(conn, status=None if show_all else "open")
    finally:
        conn.close()

    if actions.empty:
        st.info("売却候補はありません。")
    else:
        for row in actions.itertuples():
            reason = _REASON_LABELS.get(row.reason, row.reason)
            cols = st.columns([4, 1, 1])
            cols[0].write(f"{row.date} **{row.code}** {row.qty}株 — {reason}（{row.status}）")
            for col, label, new_status in ((cols[1], "対応済み", "done"), (cols[2], "見送り", "skipped")):
                if col.button(label, key=f"{new_status}_{row.action_id}", disabled=row.status == new_status):
                    conn = init_schema(settings.duckdb_path)
                    try:
                        update_manual_action_status(conn, row.action_id, new_status)
                    finally:
                        conn.close()
                    st.rerun()
```

- [ ] **Step 5: テストとページ import 確認**

Run: `python -m pytest tests/test_dashboard_pages.py -q`
Run: `python -m py_compile src/kabusys/monitoring/pages/12_Manual_Trades.py`
Expected: PASS / エラーなし

- [ ] **Step 6: Commit**

```bash
git add src/kabusys/monitoring/dashboard_data.py src/kabusys/monitoring/pages/12_Manual_Trades.py tests/test_dashboard_pages.py
git commit -m "feat: add manual sell candidates tab to dashboard (#410)"
```

---

### Task 8: 運用ドキュメントと最終検証

**Files:**
- Modify: `documents/WebManual/C_ManualOrderOperation.md`
- Modify: `documents/08_Operations/TODO_ManualTradeImportAdvisoryMode.md`（完了項目にチェック）

- [ ] **Step 1: WebManual に追記**

`C_ManualOrderOperation.md` の「注文後」節の後に、次の節を追加:

```markdown
## 手動保有の SELL 判定と買い増し

`.env` で次を設定すると、手動約定の保有が自動売買と同じロジックで評価される。

    MANUAL_TRADING_ENABLED=true
    MANUAL_TRADING_INITIAL_CASH=3000000

- 夜間バッチ（strategy_signal）が手動保有に損切り・トレーリングストップ・保有期限・スコア低下などの SELL 判定を行い、該当銘柄を `manual_action_queue` に「売却候補」として記録する。KabuSys は発注しない。
- 夜 LINE の SELL 行に株数・理由・`[手動保有]` が表示される。
- 手動保有中の銘柄が BUY 候補になった場合、目標株数との差分だけが提示され、`[買い増し]` と表示される。
- BUY 株数は「元手 − 手動買付額 + 売却額 + 保有時価」を総資産として計算する。
- Streamlit **Manual Trades → 売却候補** タブで、候補を「対応済み」「見送り」に更新できる。売却したら必ず「入力」タブで SELL 約定を登録する。
```

- [ ] **Step 2: TODO ドキュメント更新**

`TODO_ManualTradeImportAdvisoryMode.md` の該当チェックボックス（手動約定 CLI、助言モード SELL 判定、自動発注しない安全設計、レポート・通知、テスト）を `[x]` にし、未対応として「CSV 一括投入」「ロット別管理」「承認後発注」を残す。

- [ ] **Step 3: 全体検証**

Run: `python -m pytest -q`
Run: `python -m ruff check src tests scripts`
Run: `python -m ruff format --check src tests scripts`
Expected: 全 PASS / clean

- [ ] **Step 4: Commit**

```bash
git add documents/WebManual/C_ManualOrderOperation.md documents/08_Operations/TODO_ManualTradeImportAdvisoryMode.md
git commit -m "docs: document manual position advisory mode (#410)"
```
