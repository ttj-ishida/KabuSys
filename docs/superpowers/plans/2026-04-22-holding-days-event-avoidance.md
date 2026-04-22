# Holding Days & Event Avoidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement minimum holding days / re-entry restriction (#174) and earnings + major-event avoidance (#171) as three sequential PRs: PR-A → PR-B → PR-C.

**Architecture:** All BUY/SELL filters are added to `signal_generator.py` following the existing gap-filter / sector-filter pattern. A new `position_entries(code, entry_date, sell_date)` table tracks trade lifecycle; backtest engine writes it from `simulator.trades`; live engine writes it on order send. PR-A delivers #174 base logic, PR-B delivers #171, PR-C adds Bear-regime SELL exception for #174.

**Tech Stack:** Python 3.10+, DuckDB (`:memory:` for backtest), pytest, existing `calendar_management` utilities.

**Baseline:** 842 tests pass before starting. Run `python -m pytest --tb=no -q` to verify at each PR boundary.

---

## PR-A: #174 Part 1 — position_entries + min holding + re-entry restriction

---

### Task 1: `position_entries` テーブルを schema.py に追加

**Files:**
- Modify: `src/kabusys/data/schema.py`
- Test: `tests/test_signal_generator.py` (fixture が新テーブルを自動認識するか確認)

- [ ] **Step 1: DDL を追加する**

`src/kabusys/data/schema.py` の `_POSITIONS` 定義の直後（`_PORTFOLIO_PERFORMANCE` の前）に以下を追加:

```python
_POSITION_ENTRIES = """
CREATE TABLE IF NOT EXISTS position_entries (
    code        VARCHAR  NOT NULL,
    entry_date  DATE     NOT NULL,
    sell_date   DATE,
    PRIMARY KEY (code, entry_date)
)
"""
```

- [ ] **Step 2: `_ALL_DDL` リストに追加する**

`_ALL_DDL` の `_POSITIONS` の直後に `_POSITION_ENTRIES` を追加:

```python
_ALL_DDL: list[str] = [
    # ... 既存エントリー ...
    _POSITIONS,
    _POSITION_ENTRIES,   # ← ここに追加
    _PORTFOLIO_PERFORMANCE,
]
```

- [ ] **Step 3: スキーマが正しく作成されるか確認する**

```bash
python -c "
from kabusys.data.schema import init_schema
conn = init_schema(':memory:')
r = conn.execute(\"SELECT table_name FROM information_schema.tables WHERE table_name='position_entries'\").fetchone()
assert r is not None, 'テーブルが作成されていない'
print('OK: position_entries テーブル存在確認')
conn.close()
"
```

Expected: `OK: position_entries テーブル存在確認`

- [ ] **Step 4: 既存テストが通ることを確認する**

```bash
python -m pytest tests/test_signal_generator.py -q
```

Expected: all pass（fixture が `init_schema` を使っているため自動対応）

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/data/schema.py
git commit -m "feat: add position_entries table to schema (#174)"
```

---

### Task 2: signal_generator.py — 最低保有日数 + 再エントリー制限フィルタ追加

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py`
- Test: `tests/test_signal_generator.py`

- [ ] **Step 1: テストを書く（失敗することを確認）**

`tests/test_signal_generator.py` の末尾に以下のクラスを追加:

```python
# ---------------------------------------------------------------------------
# Task 2: 最低保有日数 / 再エントリー制限
# ---------------------------------------------------------------------------

def _insert_position(conn, code: str, d: date, avg_price: float = 1000.0) -> None:
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, ?, 100, ?)",
        [d, code, avg_price],
    )


def _insert_position_entry(
    conn, code: str, entry_date: date, sell_date: date | None = None
) -> None:
    conn.execute(
        "INSERT INTO position_entries (code, entry_date, sell_date) VALUES (?, ?, ?)",
        [code, entry_date, sell_date],
    )


def _insert_price(conn, code: str, d: date, close: float = 1000.0, open_: float = 1000.0) -> None:
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
        [d, code, open_, close * 1.01, close * 0.99, close],
    )


def _insert_calendar_days(conn, days: list[date]) -> None:
    for d in days:
        conn.execute(
            "INSERT OR IGNORE INTO market_calendar (date, is_trading_day, is_half_day) VALUES (?, TRUE, FALSE)",
            [d],
        )


class TestMinHoldingDays:
    """BUY 後 5営業日はストップロス以外の SELL を抑制する。"""

    def test_score_drop_sell_suppressed_within_5_biz_days(self, conn):
        """保有 3営業日では score_drop SELL が抑制される。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        # 4営業日分のカレンダー登録
        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(4)]  # 4/1〜4/4
        _insert_calendar_days(conn, biz_days)

        entry_date = biz_days[0]  # 4/1 にエントリー
        target_date = biz_days[3]  # 4/4 (3営業日後)

        code = "1001"
        # features を target_date に挿入（低スコア → score_drop SELL を誘発）
        _insert_feature(conn, code, target_date, high_score=False)
        # 保有ポジション
        _insert_price(conn, code, target_date, close=1000.0)
        _insert_position(conn, code, target_date, avg_price=1000.0)
        # position_entries に entry_date を登録
        _insert_position_entry(conn, code, entry_date)

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert len(sell_rows) == 0, "保有 3日目は score_drop SELL が抑制されるべき"

    def test_score_drop_sell_allowed_after_5_biz_days(self, conn):
        """保有 5営業日後は score_drop SELL が許可される。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(7)]  # 4/1〜4/7
        _insert_calendar_days(conn, biz_days)

        entry_date = biz_days[0]   # 4/1
        target_date = biz_days[5]  # 4/6 (5営業日後)

        code = "1002"
        _insert_feature(conn, code, target_date, high_score=False)
        _insert_price(conn, code, target_date, close=1000.0)
        _insert_position(conn, code, target_date, avg_price=1000.0)
        _insert_position_entry(conn, code, entry_date)

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in sell_rows), "5営業日後は SELL 許可されるべき"

    def test_stop_loss_bypasses_min_holding(self, conn):
        """ストップロス到達は保有日数チェックをスキップして即 SELL する。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        entry_date = biz_days[0]
        target_date = biz_days[1]  # 1営業日後

        code = "1003"
        avg_price = 1000.0
        stop_loss_price = avg_price * 0.85  # -15% → ストップロス (-8%) 確実に超える
        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=stop_loss_price)
        _insert_position(conn, code, target_date, avg_price=avg_price)
        _insert_position_entry(conn, code, entry_date)

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in sell_rows), "ストップロスは即 SELL されるべき"

    def test_no_position_entry_allows_sell(self, conn):
        """position_entries にレコードがない場合は安全側で SELL 許可する。"""
        from kabusys.strategy.signal_generator import generate_signals

        target_date = date(2026, 4, 1)
        code = "1004"
        _insert_feature(conn, code, target_date, high_score=False)
        _insert_price(conn, code, target_date, close=1000.0)
        _insert_position(conn, code, target_date, avg_price=1000.0)
        # position_entries に何も挿入しない

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in sell_rows), "レコードなしは SELL 許可"


class TestReentryRestriction:
    """SELL 後 5営業日は同一銘柄の再 BUY を禁止する。"""

    def test_buy_suppressed_within_5_biz_days_after_sell(self, conn):
        """SELL 後 3営業日は再 BUY が抑制される。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(5)]
        _insert_calendar_days(conn, biz_days)

        sell_date = biz_days[0]   # 4/1 に SELL
        target_date = biz_days[3]  # 4/4 (3営業日後)

        code = "2001"
        # 高スコア features → BUY シグナルが出るはず
        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        # 前日終値（gap filter 用）
        prev = biz_days[2]
        _insert_price(conn, code, prev, close=1000.0)
        # sell_date を登録
        _insert_position_entry(conn, code, sell_date - timedelta(days=10), sell_date)

        generate_signals(conn, target_date)

        buy_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        ).fetchall()
        assert not any(r[0] == code for r in buy_rows), "SELL 後 3日目は再 BUY 抑制"

    def test_buy_allowed_after_5_biz_days_cooldown(self, conn):
        """SELL 後 5営業日後は再 BUY が許可される。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(8)]
        _insert_calendar_days(conn, biz_days)

        sell_date = biz_days[0]
        target_date = biz_days[6]  # 6営業日後（5日経過）

        code = "2002"
        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        prev = biz_days[5]
        _insert_price(conn, code, prev, close=1000.0)
        _insert_position_entry(conn, code, sell_date - timedelta(days=10), sell_date)

        generate_signals(conn, target_date)

        buy_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in buy_rows), "5日後は再 BUY 許可"

    def test_no_sell_date_allows_buy(self, conn):
        """sell_date が NULL（保有中）は再エントリー制限なし。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[1]
        code = "2003"
        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        prev = biz_days[0]
        _insert_price(conn, code, prev, close=1000.0)
        # sell_date=None → 保有中
        _insert_position_entry(conn, code, biz_days[0], None)

        generate_signals(conn, target_date)

        buy_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in buy_rows), "sell_date=NULL は BUY 許可"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m pytest tests/test_signal_generator.py::TestMinHoldingDays tests/test_signal_generator.py::TestReentryRestriction -v 2>&1 | tail -20
```

Expected: FAILED (関数未実装)

- [ ] **Step 3: `signal_generator.py` にヘルパー関数と定数を追加する**

ファイル冒頭の import ブロックに追加:

```python
from kabusys.data.calendar_management import get_trading_days, next_trading_day
```

定数ブロック（`_SECTOR_QUARTILE` の直後）に追加:

```python
_MIN_HOLDING_DAYS: int = 5   # BUY 後この営業日数を経過するまで非ストップロス SELL を抑制
_REENTRY_COOLDOWN_DAYS: int = 5  # SELL 後この営業日数を経過するまで同一銘柄の BUY を禁止
```

`_generate_sell_signals()` の直前（`_sigmoid` 等のあとのヘルパー節）に以下を追加:

```python
def _held_days(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
) -> int | None:
    """position_entries から最新の未クローズ entry_date を取得し、
    entry_date 〜 target_date の営業日数を返す（entry_date 当日 = 0）。
    レコードなし → None（チェックスキップ・安全側）。
    """
    row = conn.execute(
        """
        SELECT entry_date FROM position_entries
        WHERE code = ? AND sell_date IS NULL
        ORDER BY entry_date DESC LIMIT 1
        """,
        [code],
    ).fetchone()
    if row is None:
        return None
    entry_date = row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0]))
    days = get_trading_days(conn, entry_date, target_date)
    return len(days) - 1  # 0 = entry 当日、5 = 5営業日後


def _is_reentry_blocked(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
) -> bool:
    """最新の sell_date から target_date までの営業日数が _REENTRY_COOLDOWN_DAYS 未満なら True。
    sell_date が NULL またはレコードなしは False（制限なし）。
    """
    row = conn.execute(
        """
        SELECT sell_date FROM position_entries
        WHERE code = ? AND sell_date IS NOT NULL
        ORDER BY sell_date DESC LIMIT 1
        """,
        [code],
    ).fetchone()
    if row is None or row[0] is None:
        return False
    sell_date = row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0]))
    days = get_trading_days(conn, sell_date, target_date)
    return (len(days) - 1) < _REENTRY_COOLDOWN_DAYS
```

- [ ] **Step 4: `_generate_sell_signals()` の SELL フローを修正する**

既存のストップロス判定ブロック（`pnl_rate <= _STOP_LOSS_RATE` の continue）の直後に最低保有日数チェックを挿入する。変更後の該当部分:

```python
        # 1. ストップロス（最優先・保有日数チェックをスキップ）
        pnl_rate = (close - avg_price) / avg_price
        if pnl_rate <= _STOP_LOSS_RATE:
            sell_signals.append(
                {
                    "code": code,
                    "score": final_score,
                    "reason": "stop_loss",
                }
            )
            continue

        # 最低保有日数チェック（stop_loss 以外の SELL を抑制）
        held = _held_days(conn, code, target_date)
        if held is not None and held < _MIN_HOLDING_DAYS:
            logger.debug(
                "_generate_sell_signals: %s 保有 %d 営業日（最低 %d 日）— SELL 抑制 date=%s",
                code,
                held,
                _MIN_HOLDING_DAYS,
                target_date,
            )
            continue

        # 2. スコア低下
        if final_score < threshold:
            sell_signals.append(
                {
                    "code": code,
                    "score": final_score,
                    "reason": "score_drop",
                }
            )
```

- [ ] **Step 5: `generate_signals()` の BUY ループに再エントリー制限を追加する**

既存のセクターフィルタ（`sector in bottom_sectors` の continue）の直後に挿入:

```python
            # 再エントリー制限チェック
            if _is_reentry_blocked(conn, r["code"], target_date):
                logger.debug(
                    "reentry blocked: %s — date=%s", r["code"], target_date
                )
                reentry_suppressed += 1
                continue
            buy_signals.append({"code": r["code"], "score": r["score"], "rank": rank})
```

`reentry_suppressed` 変数の初期化を `gap_suppressed = 0` の近くに追加:

```python
        reentry_suppressed = 0
```

ログ出力を `sector_suppressed` のログの後に追加:

```python
        if reentry_suppressed:
            logger.info(
                "generate_signals: reentry block — %d 銘柄を再エントリー制限で抑制 date=%s",
                reentry_suppressed,
                target_date,
            )
```

- [ ] **Step 6: テストを実行して合格することを確認する**

```bash
python -m pytest tests/test_signal_generator.py::TestMinHoldingDays tests/test_signal_generator.py::TestReentryRestriction -v
```

Expected: all PASS

- [ ] **Step 7: 全テストが通ることを確認する**

```bash
python -m pytest --tb=no -q
```

Expected: 842+ passed

- [ ] **Step 8: コミット**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_signal_generator.py
git commit -m "feat: add min holding days and re-entry restriction filters to signal_generator (#174)"
```

---

### Task 3: engine.py — バックテストで position_entries を書き込む

**Files:**
- Modify: `src/kabusys/backtest/engine.py`
- Test: `tests/test_backtest_framework.py`

- [ ] **Step 1: テストを書く（失敗することを確認）**

`tests/test_backtest_framework.py` に以下のテストを追加:

```python
def test_position_entries_written_on_buy(conn):
    """バックテストで BUY 約定後に position_entries が記録される。"""
    from datetime import timedelta
    from kabusys.backtest.engine import run_backtest
    from kabusys.data.schema import init_schema

    # 最小限のバックテスト環境を構築（テスト用インメモリ DB）
    # ※ このテストは run_backtest が position_entries を書くことを確認するため
    # 実際の run_backtest を呼ぶのではなく、_write_position_entries のユニットテストとする
    from kabusys.backtest.engine import _write_position_entries
    from kabusys.backtest.simulator import TradeRecord

    bt_conn = init_schema(":memory:")
    trades = [
        TradeRecord(
            date=date(2026, 4, 1),
            code="1001",
            side="buy",
            shares=100,
            price=1000.0,
            commission=55.0,
            realized_pnl=None,
        )
    ]
    _write_position_entries(bt_conn, trades, date(2026, 4, 1))

    row = bt_conn.execute(
        "SELECT entry_date, sell_date FROM position_entries WHERE code = '1001'"
    ).fetchone()
    assert row is not None
    assert str(row[0]) == "2026-04-01"
    assert row[1] is None
    bt_conn.close()


def test_position_entries_sell_date_updated(conn):
    """バックテストで SELL 約定後に position_entries.sell_date が更新される。"""
    from kabusys.backtest.engine import _write_position_entries
    from kabusys.backtest.simulator import TradeRecord

    from kabusys.data.schema import init_schema
    bt_conn = init_schema(":memory:")

    # まず BUY
    buy_trades = [
        TradeRecord(date(2026, 4, 1), "1001", "buy", 100, 1000.0, 55.0, None)
    ]
    _write_position_entries(bt_conn, buy_trades, date(2026, 4, 1))

    # 次に SELL
    sell_trades = [
        TradeRecord(date(2026, 4, 5), "1001", "sell", 100, 1050.0, 57.0, 4443.0)
    ]
    _write_position_entries(bt_conn, sell_trades, date(2026, 4, 5))

    row = bt_conn.execute(
        "SELECT entry_date, sell_date FROM position_entries WHERE code = '1001'"
    ).fetchone()
    assert str(row[1]) == "2026-04-05"
    bt_conn.close()
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m pytest tests/test_backtest_framework.py::test_position_entries_written_on_buy tests/test_backtest_framework.py::test_position_entries_sell_date_updated -v 2>&1 | tail -10
```

Expected: FAILED (関数未定義)

- [ ] **Step 3: `_write_position_entries()` を engine.py に追加する**

`engine.py` の `_write_positions()` 関数の直後に追加:

```python
def _write_position_entries(
    conn: duckdb.DuckDBPyConnection,
    trades: list[TradeRecord],
    trading_day: date,
) -> None:
    """当日の約定を position_entries テーブルに反映する。

    BUY 約定 → (code, entry_date) を INSERT（重複は無視）。
    SELL 約定 → 最新の未クローズレコードの sell_date を UPDATE。
    """
    today_trades = [t for t in trades if t.date == trading_day]
    for trade in today_trades:
        if trade.side == "buy":
            conn.execute(
                """
                INSERT INTO position_entries (code, entry_date)
                VALUES (?, ?)
                ON CONFLICT DO NOTHING
                """,
                [trade.code, trading_day],
            )
        elif trade.side == "sell":
            conn.execute(
                """
                UPDATE position_entries
                SET sell_date = ?
                WHERE code = ? AND sell_date IS NULL
                """,
                [trading_day, trade.code],
            )
```

- [ ] **Step 4: バックテストループに `_write_position_entries()` 呼び出しを追加する**

`run_backtest()` 内の `simulator.execute_orders(...)` 呼び出しの直後（`_write_positions(...)` の前）に追加:

```python
            simulator.execute_orders(
                next_day_orders,
                open_prices,
                slippage_rate,
                commission_rate,
                trading_day,
                lot_size=lot_size,
            )

            # position_entries テーブルに約定を反映（最低保有日数・再エントリー制限用）
            _write_position_entries(bt_conn, simulator.trades, trading_day)

            # Step 2: positions テーブルに書き戻し
            _write_positions(
                bt_conn, trading_day, simulator.positions, simulator.cost_basis
            )
```

- [ ] **Step 5: テストが通ることを確認する**

```bash
python -m pytest tests/test_backtest_framework.py::test_position_entries_written_on_buy tests/test_backtest_framework.py::test_position_entries_sell_date_updated -v
```

Expected: PASS

- [ ] **Step 6: 全テストが通ることを確認する**

```bash
python -m pytest --tb=no -q
```

Expected: 842+ passed

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/backtest/engine.py tests/test_backtest_framework.py
git commit -m "feat: write position_entries in backtest engine for holding-day tracking (#174)"
```

---

### Task 4: execution_engine.py — 本番/Paper Trading での position_entries 書き込み

**Files:**
- Modify: `src/kabusys/execution/execution_engine.py`
- Test: `tests/test_execution_engine.py`

- [ ] **Step 1: テストを書く**

`tests/test_execution_engine.py` に追加（既存テストの末尾）:

```python
class TestPositionEntriesOnFill:
    """BUY/SELL 発注成功時に position_entries が記録される。"""

    def test_buy_signal_inserts_position_entry(self, engine_fixture):
        """BUY 発注成功 → position_entries に entry_date が挿入される。"""
        # engine_fixture は既存の pytest fixture を流用
        # BUY シグナルを signals + portfolio_targets に挿入
        target_date = engine_fixture.config.target_date
        conn = engine_fixture.duckdb_conn
        conn.execute(
            "INSERT INTO signals (date, code, side, score, signal_rank) VALUES (?, '9999', 'buy', 0.9, 1)",
            [target_date],
        )
        conn.execute(
            "INSERT INTO portfolio_targets (date, code, target_weight, target_size, entry_price) "
            "VALUES (?, '9999', 0.1, 100, 1000.0)",
            [target_date],
        )

        engine_fixture._process_signals()

        row = conn.execute(
            "SELECT entry_date FROM position_entries WHERE code = '9999'"
        ).fetchone()
        assert row is not None, "BUY 発注後に position_entries が挿入されるべき"
```

> **Note:** `engine_fixture` の具体的な構造は既存の `tests/test_execution_engine.py` の fixture を参照すること。既存 fixture と合わない場合は、`init_schema(":memory:")` を使ったスタンドアロンの fixture を新規作成する。

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m pytest tests/test_execution_engine.py::TestPositionEntriesOnFill -v 2>&1 | tail -10
```

Expected: FAILED

- [ ] **Step 3: `execution_engine.py` の `_process_signals()` に position_entries 書き込みを追加する**

発注成功ログ (`logger.info("発注成功: ...")`) の直後に追加:

```python
                logger.info(
                    "発注成功: signal_id=%s, client_order_id=%s",
                    signal_id,
                    record.client_order_id,
                )
                # position_entries に約定を記録（最低保有日数・再エントリー制限用）
                try:
                    if side == "buy":
                        self._duckdb_conn.execute(
                            """
                            INSERT INTO position_entries (code, entry_date)
                            VALUES (?, ?)
                            ON CONFLICT DO NOTHING
                            """,
                            [code, self._config.target_date],
                        )
                    elif side == "sell":
                        self._duckdb_conn.execute(
                            """
                            UPDATE position_entries
                            SET sell_date = ?
                            WHERE code = ? AND sell_date IS NULL
                            """,
                            [self._config.target_date, code],
                        )
                except Exception as _pe_exc:
                    logger.warning(
                        "position_entries 書き込み失敗（発注フローは継続）: %s", _pe_exc
                    )
```

同様に `logger.info("発注保留（pending）: ...")` の直後にも同じブロックを追加する（ペンディング扱いでも position_entries に記録）。

- [ ] **Step 4: テストが通ることを確認する**

```bash
python -m pytest tests/test_execution_engine.py -v --tb=short 2>&1 | tail -20
```

Expected: all PASS

- [ ] **Step 5: 全テスト確認**

```bash
python -m pytest --tb=no -q
```

Expected: 842+ passed

- [ ] **Step 6: PR-A コミット & PR 作成**

```bash
git add src/kabusys/execution/execution_engine.py tests/test_execution_engine.py
git commit -m "feat: write position_entries on order send in ExecutionEngine (#174)"
```

PR-A 完成。PR を作成し `main` にマージ後、PR-B に進む。

---

## PR-B: #171 — 決算カレンダー + イベントカレンダー + BUY/SELL 制御

---

### Task 5: schema.py — `earnings_calendar` + `signals.size_multiplier` 追加

**Files:**
- Modify: `src/kabusys/data/schema.py`

- [ ] **Step 1: `earnings_calendar` DDL を追加する**

`_POSITION_ENTRIES` の直後に追加:

```python
_EARNINGS_CALENDAR = """
CREATE TABLE IF NOT EXISTS earnings_calendar (
    code              VARCHAR   NOT NULL,
    announcement_date DATE      NOT NULL,
    fetched_at        TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (code, announcement_date)
)
"""
```

`_ALL_DDL` の `_POSITION_ENTRIES` の直後に追加:

```python
    _POSITION_ENTRIES,
    _EARNINGS_CALENDAR,   # ← 追加
```

- [ ] **Step 2: `signals` DDL に `size_multiplier` を追加する**

`_SIGNALS` の定義を以下に変更:

```python
_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    date             DATE        NOT NULL,
    code             VARCHAR     NOT NULL,
    side             VARCHAR     NOT NULL CHECK (side IN ('buy', 'sell')),
    score            DOUBLE,
    signal_rank      INTEGER,
    size_multiplier  DOUBLE      NOT NULL DEFAULT 1.0,
    PRIMARY KEY (date, code, side)
)
"""
```

- [ ] **Step 3: 動作確認**

```bash
python -c "
from kabusys.data.schema import init_schema
conn = init_schema(':memory:')
r1 = conn.execute(\"SELECT table_name FROM information_schema.tables WHERE table_name='earnings_calendar'\").fetchone()
r2 = conn.execute(\"PRAGMA table_info(signals)\").fetchall()
assert r1 is not None
cols = [r[1] for r in r2]
assert 'size_multiplier' in cols, f'size_multiplier が signals にない: {cols}'
print('OK: earnings_calendar + size_multiplier 確認')
conn.close()
"
```

- [ ] **Step 4: 全テストが通ることを確認する**

```bash
python -m pytest --tb=no -q
```

Expected: 842+ passed（`size_multiplier DEFAULT 1.0` なので既存テストは影響なし）

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/data/schema.py
git commit -m "feat: add earnings_calendar table and size_multiplier to signals (#171)"
```

---

### Task 6: jquants_client.py + pipeline.py — 決算カレンダー取得・保存

**Files:**
- Modify: `src/kabusys/data/jquants_client.py`
- Modify: `src/kabusys/data/pipeline.py`
- Test: `tests/test_data_pipeline.py`

- [ ] **Step 1: テストを書く**

`tests/test_data_pipeline.py` の末尾に追加:

```python
class TestEarningsCalendarPipeline:
    def test_save_earnings_calendar_idempotent(self):
        """save_earnings_calendar は重複実行で件数が増えない。"""
        from kabusys.data.schema import init_schema
        from kabusys.data import jquants_client as jq

        conn = init_schema(":memory:")
        records = [
            {"Code": "1001", "Date": "20260501"},
            {"Code": "1002", "Date": "20260502"},
        ]
        n1 = jq.save_earnings_calendar(conn, records)
        n2 = jq.save_earnings_calendar(conn, records)
        assert n1 == 2
        assert n2 == 2  # 冪等: 2回目も 2件処理するが重複挿入なし
        count = conn.execute("SELECT COUNT(*) FROM earnings_calendar").fetchone()[0]
        assert count == 2
        conn.close()

    def test_save_earnings_calendar_skips_invalid_date(self):
        """不正な日付フォーマットはスキップされる。"""
        from kabusys.data.schema import init_schema
        from kabusys.data import jquants_client as jq

        conn = init_schema(":memory:")
        records = [
            {"Code": "1001", "Date": "not-a-date"},
            {"Code": "1002", "Date": "20260502"},
        ]
        n = jq.save_earnings_calendar(conn, records)
        assert n == 1  # 有効な 1件のみ保存
        conn.close()
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m pytest tests/test_data_pipeline.py::TestEarningsCalendarPipeline -v 2>&1 | tail -10
```

Expected: FAILED

- [ ] **Step 3: `jquants_client.py` に `fetch_earnings_calendar` / `save_earnings_calendar` を追加する**

`fetch_market_calendar()` の直後に追加:

```python
def fetch_earnings_calendar(
    id_token: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    """決算発表予定カレンダーを取得する（/equities/earnings-calendar）。

    Args:
        id_token:  認証トークン。省略時はキャッシュを使用。
        date_from: 取得開始日。
        date_to:   取得終了日。

    Returns:
        決算カレンダーレコードのリスト。各要素は {"Code": str, "Date": "YYYYMMDD"} を含む。
    """
    params: dict[str, str] = {}
    if date_from:
        params["dateFrom"] = date_from.strftime("%Y%m%d")
    if date_to:
        params["dateTo"] = date_to.strftime("%Y%m%d")
    data = _request("/equities/earnings-calendar", params=params, id_token=id_token)
    records = data.get("earningsCalendar", [])
    logger.info("fetch_earnings_calendar: %d レコード取得", len(records))
    return records


def save_earnings_calendar(
    conn: duckdb.DuckDBPyConnection,
    records: list[dict[str, Any]],
) -> int:
    """決算カレンダーを earnings_calendar テーブルへ冪等保存する。

    Args:
        conn:    DuckDB 接続。
        records: fetch_earnings_calendar() の戻り値。

    Returns:
        保存を試みたレコード数（スキップ分を除く）。
    """
    rows: list[tuple] = []
    for r in records:
        code = r.get("Code", "")
        date_str = r.get("Date", "")
        if not code or not date_str:
            continue
        try:
            ann_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
        except (ValueError, IndexError):
            logger.warning("save_earnings_calendar: 不正な日付フォーマット '%s'—スキップ", date_str)
            continue
        rows.append((code, ann_date))

    if not rows:
        return 0

    conn.executemany(
        """
        INSERT INTO earnings_calendar (code, announcement_date)
        VALUES (?, ?)
        ON CONFLICT DO NOTHING
        """,
        rows,
    )
    logger.info("save_earnings_calendar: %d 件を earnings_calendar に保存", len(rows))
    return len(rows)
```

- [ ] **Step 4: `pipeline.py` の `ETLResult` に `earnings_calendar` フィールドを追加する**

`ETLResult` dataclass に追加:

```python
    earnings_calendar_fetched: int = 0
    earnings_calendar_saved: int = 0
```

`to_dict()` メソッドは `asdict()` を使っているため自動対応。

- [ ] **Step 5: `pipeline.py` の夜間バッチ関数に決算カレンダー取得を追加する**

`pipeline.py` 内の `run_nightly_etl()` または主要な ETL 関数（既存の関数名を確認して適用）の中で、`jq.fetch_market_calendar` 呼び出しの近くに追加:

```python
    # 決算カレンダー（翌30日分を先読み取得・冪等保存）
    try:
        ec_records = jq.fetch_earnings_calendar(
            id_token=id_token,
            date_from=today,
            date_to=today + timedelta(days=30),
        )
        ec_saved = jq.save_earnings_calendar(conn, ec_records)
        result.earnings_calendar_fetched = len(ec_records)
        result.earnings_calendar_saved = ec_saved
    except Exception as exc:
        result.errors.append(f"earnings_calendar: {exc}")
        logger.warning("決算カレンダー取得失敗（ETL継続）: %s", exc)
```

- [ ] **Step 6: テストが通ることを確認する**

```bash
python -m pytest tests/test_data_pipeline.py::TestEarningsCalendarPipeline -v
```

Expected: PASS

- [ ] **Step 7: 全テスト確認**

```bash
python -m pytest --tb=no -q
```

Expected: 842+ passed

- [ ] **Step 8: コミット**

```bash
git add src/kabusys/data/jquants_client.py src/kabusys/data/pipeline.py tests/test_data_pipeline.py
git commit -m "feat: add earnings_calendar fetch/save to jquants_client and pipeline (#171)"
```

---

### Task 7: event_calendar.py 新規作成 + config/event_calendar.md 作成

**Files:**
- Create: `src/kabusys/data/event_calendar.py`
- Create: `config/event_calendar.md`
- Test: `tests/test_event_calendar.py`（新規）

- [ ] **Step 1: テストを書く**

`tests/test_event_calendar.py` を新規作成:

```python
"""event_calendar.py のユニットテスト。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest


@pytest.fixture
def sample_md(tmp_path: Path) -> Path:
    md = tmp_path / "event_calendar.md"
    md.write_text(
        "## 2026年\n\n"
        "### FOMC\n"
        "- 2026-01-29\n"
        "- 2026-03-19\n\n"
        "### 日銀決定会合\n"
        "- 2026-01-24\n\n"
        "### 米CPI\n"
        "- 2026-01-15\n",
        encoding="utf-8",
    )
    return md


def test_load_event_dates_parses_all_dates(sample_md):
    from kabusys.data.event_calendar import load_event_dates

    result = load_event_dates(sample_md)
    assert date(2026, 1, 29) in result
    assert date(2026, 3, 19) in result
    assert date(2026, 1, 24) in result
    assert date(2026, 1, 15) in result


def test_load_event_dates_returns_event_name(sample_md):
    from kabusys.data.event_calendar import load_event_dates

    result = load_event_dates(sample_md)
    assert result[date(2026, 1, 29)] == "FOMC"
    assert result[date(2026, 1, 24)] == "日銀決定会合"
    assert result[date(2026, 1, 15)] == "米CPI"


def test_load_event_dates_missing_file_returns_empty(tmp_path):
    from kabusys.data.event_calendar import load_event_dates

    result = load_event_dates(tmp_path / "nonexistent.md")
    assert result == {}


def test_load_event_dates_ignores_malformed_lines(tmp_path):
    from kabusys.data.event_calendar import load_event_dates

    md = tmp_path / "bad.md"
    md.write_text("### FOMC\n- not-a-date\n- 2026-02-01\n", encoding="utf-8")
    result = load_event_dates(md)
    assert date(2026, 2, 1) in result
    assert len(result) == 1
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m pytest tests/test_event_calendar.py -v 2>&1 | tail -10
```

Expected: FAILED (モジュール未存在)

- [ ] **Step 3: `src/kabusys/data/event_calendar.py` を作成する**

```python
"""イベントカレンダーパーサー。

config/event_calendar.md から FOMC・日銀・CPI 等の市場イベント日を読み込む。
"""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


def load_event_dates(md_path: str | Path) -> dict[date, str]:
    """config/event_calendar.md をパースして {event_date: event_name} を返す。

    フォーマット:
        ### イベント名
        - YYYY-MM-DD

    ファイルが存在しない場合は空 dict を返す（安全側）。
    不正な日付行はスキップしてログを出力する。
    """
    path = Path(md_path)
    if not path.exists():
        logger.warning("load_event_dates: ファイルが見つかりません: %s", path)
        return {}

    text = path.read_text(encoding="utf-8")
    result: dict[date, str] = {}
    current_event = "event"

    for line in text.splitlines():
        m_header = re.match(r"^###\s+(.+)", line)
        if m_header:
            current_event = m_header.group(1).strip()
            continue

        m_date = re.match(r"^-\s+(\d{4}-\d{2}-\d{2})\s*$", line)
        if m_date:
            try:
                d = date.fromisoformat(m_date.group(1))
                result[d] = current_event
            except ValueError:
                logger.debug("load_event_dates: 不正な日付 '%s'—スキップ", m_date.group(1))

    logger.info("load_event_dates: %d 件のイベント日を読み込み: %s", len(result), path)
    return result
```

- [ ] **Step 4: `config/event_calendar.md` を作成する**

```bash
mkdir -p config
```

`config/event_calendar.md` を以下の内容で作成:

```markdown
# マーケットイベントカレンダー

FOMC・日銀決定会合・米CPI 等の主要イベント日。
翌営業日がイベント日の場合、新規 BUY サイズを 50% に縮小する。
AI アシストで年次更新する。

---

## 2026年

### FOMC
- 2026-01-29
- 2026-03-19
- 2026-05-07
- 2026-06-18
- 2026-07-30
- 2026-09-17
- 2026-11-05
- 2026-12-17

### 日銀決定会合
- 2026-01-24
- 2026-03-19
- 2026-04-30
- 2026-06-17
- 2026-07-31
- 2026-09-19
- 2026-10-29
- 2026-12-18

### 米CPI
- 2026-01-15
- 2026-02-11
- 2026-03-11
- 2026-04-10
- 2026-05-13
- 2026-06-10
- 2026-07-15
- 2026-08-12
- 2026-09-11
- 2026-10-14
- 2026-11-12
- 2026-12-11
```

- [ ] **Step 5: テストが通ることを確認する**

```bash
python -m pytest tests/test_event_calendar.py -v
```

Expected: PASS

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/data/event_calendar.py config/event_calendar.md tests/test_event_calendar.py
git commit -m "feat: add event_calendar parser and config/event_calendar.md (#171)"
```

---

### Task 8: signal_generator.py — 決算回避 BUY/SELL + イベントサイズ縮小

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py`
- Test: `tests/test_signal_generator.py`

- [ ] **Step 1: テストを書く**

`tests/test_signal_generator.py` に追加:

```python
# ---------------------------------------------------------------------------
# Task 8: 決算回避・イベントサイズ縮小
# ---------------------------------------------------------------------------


def _insert_earnings(conn, code: str, ann_date: date) -> None:
    conn.execute(
        "INSERT INTO earnings_calendar (code, announcement_date) VALUES (?, ?)",
        [code, ann_date],
    )


class TestEarningsAvoidance:
    """翌営業日が決算日の銘柄は BUY 抑制 + 保有分は SELL 強制。"""

    def test_buy_suppressed_when_earnings_next_day(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[0]
        next_day = biz_days[1]
        code = "3001"

        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        _insert_price(conn, code, base - timedelta(days=1), close=1000.0)
        _insert_earnings(conn, code, next_day)  # 翌営業日が決算

        generate_signals(conn, target_date)

        buy_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        ).fetchall()
        assert not any(r[0] == code for r in buy_rows), "決算翌日の銘柄は BUY 抑制"

    def test_buy_allowed_when_no_upcoming_earnings(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[0]
        code = "3002"

        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        _insert_price(conn, code, base - timedelta(days=1), close=1000.0)
        # earnings_calendar に登録なし

        generate_signals(conn, target_date)

        buy_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in buy_rows), "決算なしは BUY 許可"

    def test_sell_forced_when_earnings_next_day(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[0]
        next_day = biz_days[1]
        code = "3003"

        # 高スコア（score_drop SELL は発生しない）
        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        _insert_position(conn, code, target_date, avg_price=950.0)  # 保有中
        _insert_earnings(conn, code, next_day)

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in sell_rows), "決算前は強制 SELL"


class TestEventSizeMultiplier:
    """主要イベント前は size_multiplier=0.5 が付与される。"""

    def test_size_multiplier_half_on_event_day(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals
        from kabusys.data.event_calendar import load_event_dates
        from pathlib import Path

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[0]
        next_day = biz_days[1]
        code = "4001"

        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        _insert_price(conn, code, base - timedelta(days=1), close=1000.0)

        # イベント日を next_day に設定
        event_dates = {next_day: "FOMC"}

        generate_signals(conn, target_date, event_dates=event_dates)

        row = conn.execute(
            "SELECT size_multiplier FROM signals WHERE date = ? AND code = ? AND side = 'buy'",
            [target_date, code],
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 0.5) < 1e-9, f"size_multiplier は 0.5 のはず: {row[0]}"

    def test_size_multiplier_one_when_no_event(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[0]
        code = "4002"

        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        _insert_price(conn, code, base - timedelta(days=1), close=1000.0)

        generate_signals(conn, target_date, event_dates={})

        row = conn.execute(
            "SELECT size_multiplier FROM signals WHERE date = ? AND code = ? AND side = 'buy'",
            [target_date, code],
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 1.0) < 1e-9
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m pytest tests/test_signal_generator.py::TestEarningsAvoidance tests/test_signal_generator.py::TestEventSizeMultiplier -v 2>&1 | tail -15
```

Expected: FAILED

- [ ] **Step 3: `signal_generator.py` にヘルパー関数を追加する**

`_is_reentry_blocked()` の直後に追加:

```python
def _has_upcoming_earnings(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
) -> bool:
    """翌営業日が earnings_calendar の announcement_date に登録されている銘柄なら True。"""
    next_day = next_trading_day(conn, target_date)
    row = conn.execute(
        "SELECT 1 FROM earnings_calendar WHERE code = ? AND announcement_date = ?",
        [code, next_day],
    ).fetchone()
    return row is not None


def _get_event_size_multiplier(
    event_dates: dict[date, str],
    target_date: date,
    conn: duckdb.DuckDBPyConnection,
) -> float:
    """翌営業日が event_dates に含まれる場合 0.5、それ以外は 1.0 を返す。"""
    if not event_dates:
        return 1.0
    next_day = next_trading_day(conn, target_date)
    return 0.5 if next_day in event_dates else 1.0
```

- [ ] **Step 4: `generate_signals()` のシグネチャに `event_dates` 引数を追加する**

```python
def generate_signals(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    threshold: float = _DEFAULT_THRESHOLD,
    weights: dict[str, float] | None = None,
    event_dates: dict[date, str] | None = None,  # ← 追加
) -> int:
```

関数冒頭（weights 処理の直後、feat_rows 取得の前）に追加:

```python
    event_dates = event_dates or {}
    size_multiplier = _get_event_size_multiplier(event_dates, target_date, conn)
```

- [ ] **Step 5: BUY ループに決算回避フィルタを追加する**

再エントリー制限チェックの直後に追加:

```python
            # 決算回避フィルタ（翌営業日が決算日の銘柄は BUY 抑制）
            if _has_upcoming_earnings(conn, r["code"], target_date):
                logger.debug(
                    "earnings filter: %s — 翌営業日決算のため BUY 抑制 date=%s",
                    r["code"],
                    target_date,
                )
                earnings_suppressed += 1
                continue
```

`reentry_suppressed = 0` の近くに追加:

```python
        earnings_suppressed = 0
```

ログ出力を末尾近くに追加:

```python
        if earnings_suppressed:
            logger.info(
                "generate_signals: earnings filter — %d 銘柄を決算回避で抑制 date=%s",
                earnings_suppressed,
                target_date,
            )
```

- [ ] **Step 6: BUY シグナルを signals テーブルに書き込む際に size_multiplier を追加する**

`buy_params` の定義を変更:

```python
    buy_params = [
        (target_date, r["code"], r["score"], r["rank"], size_multiplier)
        for r in buy_signals
    ]
```

`executemany` の SQL を変更:

```python
            conn.executemany(
                "INSERT INTO signals (date, code, side, score, signal_rank, size_multiplier) "
                "VALUES (?, ?, 'buy', ?, ?, ?)",
                buy_params,
            )
```

- [ ] **Step 7: `_generate_sell_signals()` に決算回避 SELL を追加する**

ストップロス `continue` の直後（最低保有日数チェックの前）に挿入:

```python
        # 決算回避 SELL（翌営業日が決算日 → 最低保有日数を問わず即 SELL）
        if _has_upcoming_earnings(conn, code, target_date):
            sell_signals.append(
                {
                    "code": code,
                    "score": final_score,
                    "reason": "earnings_avoidance",
                }
            )
            continue
```

- [ ] **Step 8: テストが通ることを確認する**

```bash
python -m pytest tests/test_signal_generator.py::TestEarningsAvoidance tests/test_signal_generator.py::TestEventSizeMultiplier -v
```

Expected: PASS

- [ ] **Step 9: 全テスト確認**

```bash
python -m pytest --tb=no -q
```

Expected: 842+ passed

- [ ] **Step 10: コミット**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_signal_generator.py
git commit -m "feat: add earnings avoidance and event size multiplier to signal_generator (#171)"
```

---

### Task 9: engine.py — バックテストで earnings_calendar コピー + size_multiplier 適用

**Files:**
- Modify: `src/kabusys/backtest/engine.py`
- Test: `tests/test_backtest_framework.py`

- [ ] **Step 1: `_build_backtest_conn()` に `earnings_calendar` コピーを追加する**

`stocks` コピーブロックの直後に追加:

```python
    # earnings_calendar は end_date 以前の全件コピー
    try:
        rows = source_conn.execute(
            "SELECT code, announcement_date FROM earnings_calendar "
            "WHERE announcement_date <= ?",
            [end_date],
        ).fetchall()
        if rows:
            bt_conn.executemany(
                "INSERT INTO earnings_calendar (code, announcement_date) VALUES (?, ?)",
                rows,
            )
    except Exception as exc:
        logger.warning(
            "_build_backtest_conn: earnings_calendar のコピーをスキップ: %s", exc
        )
```

- [ ] **Step 2: `_read_day_signals()` に `size_multiplier` を追加する**

```python
def _read_day_signals(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> tuple[list[dict], list[dict]]:
    buy_rows = conn.execute(
        "SELECT code, signal_rank, score, size_multiplier FROM signals "
        "WHERE date = ? AND side = 'buy' ORDER BY signal_rank",
        [trading_day],
    ).fetchall()
    sell_rows = conn.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
        [trading_day],
    ).fetchall()
    buy_signals = [
        {
            "code": row[0],
            "signal_rank": row[1],
            "score": row[2] or 0.0,
            "size_multiplier": row[3] if row[3] is not None else 1.0,
        }
        for row in buy_rows
    ]
    sell_signals = [{"code": row[0]} for row in sell_rows]
    return buy_signals, sell_signals
```

- [ ] **Step 3: `run_backtest()` の発注リスト作成時に `size_multiplier` を適用する**

`next_day_orders` の BUY リスト生成部分を変更:

```python
            # size_multiplier を各 BUY に適用（主要イベント前は 50% 縮小）
            sm_map = {s["code"]: s.get("size_multiplier", 1.0) for s in buy_signals}
            next_day_orders = [
                {
                    "code": code,
                    "side": "buy",
                    "shares": max(0, (int(shares * sm_map.get(code, 1.0)) // lot_size) * lot_size),
                }
                for code, shares in sized.items()
                if shares > 0 and code not in sell_codes
            ] + [{"code": s["code"], "side": "sell"} for s in sell_signals]
            # shares=0 になったエントリーを除外
            next_day_orders = [o for o in next_day_orders if o.get("shares", 1) > 0]
```

- [ ] **Step 4: `generate_signals()` 呼び出しを更新して `event_dates` を渡せるようにする**

`run_backtest()` のシグネチャに `event_dates` を追加:

```python
def run_backtest(
    conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
    initial_cash: float = 10_000_000,
    slippage_rate: float = 0.001,
    commission_rate: float = 0.00055,
    max_position_pct: float = 0.10,
    max_utilization: float = 0.70,
    max_positions: int = 10,
    allocation_method: str = "risk_based",
    risk_pct: float = 0.005,
    stop_loss_pct: float = 0.08,
    lot_size: int = 100,
    event_dates: dict | None = None,  # ← 追加
) -> BacktestResult:
```

ループ内の `generate_signals()` 呼び出しを更新:

```python
            generate_signals(bt_conn, target_date=trading_day, event_dates=event_dates or {})
```

- [ ] **Step 5: 全テスト確認**

```bash
python -m pytest --tb=no -q
```

Expected: 842+ passed

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/backtest/engine.py
git commit -m "feat: copy earnings_calendar + apply size_multiplier in backtest engine (#171)"
```

---

### Task 10: execution_engine.py — size_multiplier を発注サイズに適用する

**Files:**
- Modify: `src/kabusys/execution/execution_engine.py`

- [ ] **Step 1: `_read_signals()` に `size_multiplier` を追加する**

現在の `_read_signals()`:

```python
    def _read_signals(self) -> list[dict]:
        rows = self._duckdb_conn.execute(
            """
            SELECT s.code, s.side, pt.target_size AS qty, pt.entry_price AS price
            FROM signals s
            ...
            """,
            [self._config.target_date],
        ).fetchall()
```

`size_multiplier` を追加:

```python
    def _read_signals(self) -> list[dict]:
        rows = self._duckdb_conn.execute(
            """
            SELECT s.code, s.side, pt.target_size AS qty, pt.entry_price AS price,
                   COALESCE(s.size_multiplier, 1.0) AS size_multiplier
            FROM signals s
            JOIN portfolio_targets pt ON pt.code = s.code AND pt.date = s.date
            WHERE s.date = ?
            ORDER BY s.signal_rank NULLS LAST
            """,
            [self._config.target_date],
        ).fetchall()
        return [
            {
                "code": r[0],
                "side": r[1],
                "qty": r[2],
                "price": r[3],
                "size_multiplier": r[4],
            }
            for r in rows
        ]
```

- [ ] **Step 2: `_process_signals()` の `qty` 取得時に `size_multiplier` を適用する**

現在の `qty: int = sig["qty"]` を変更:

```python
            sm = sig.get("size_multiplier", 1.0)
            raw_qty = sig["qty"]
            qty: int = max(0, (int(raw_qty * sm) // 100) * 100)
            if qty <= 0:
                logger.info(
                    "size_multiplier 適用後 qty=0 のためスキップ: signal_id=%s sm=%.2f",
                    signal_id, sm,
                )
                continue
```

- [ ] **Step 3: 全テスト確認**

```bash
python -m pytest --tb=no -q
```

Expected: 842+ passed

- [ ] **Step 4: PR-B コミット**

```bash
git add src/kabusys/execution/execution_engine.py
git commit -m "feat: apply size_multiplier to order qty in ExecutionEngine (#171)"
```

PR-B 完成。PR を作成し `main` にマージ後、PR-C に進む。

---

## PR-C: #174 Part 2 — Bear レジーム移行時の保有日数スキップ例外

---

### Task 11: signal_generator.py — Bear レジーム時の最低保有日数スキップ

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py`
- Test: `tests/test_signal_generator.py`

- [ ] **Step 1: テストを書く**

```python
class TestMinHoldingDaysBearException:
    """Bear レジーム移行時は最低保有日数チェックをスキップして即 SELL する。"""

    def test_score_drop_sell_allowed_in_bear_regime_within_5_days(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(4)]
        _insert_calendar_days(conn, biz_days)

        entry_date = biz_days[0]
        target_date = biz_days[2]  # 2営業日後（通常は SELL 抑制されるはず）

        code = "5001"
        _insert_feature(conn, code, target_date, high_score=False)  # score_drop
        _insert_price(conn, code, target_date, close=1000.0)
        _insert_position(conn, code, target_date, avg_price=1000.0)
        _insert_position_entry(conn, code, entry_date)

        # Bear レジームを設定
        conn.execute(
            "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, -1.0, 'bear')",
            [target_date],
        )

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in sell_rows), "Bear レジームは保有日数スキップで SELL"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m pytest tests/test_signal_generator.py::TestMinHoldingDaysBearException -v 2>&1 | tail -10
```

Expected: FAILED（Bear でも現状は SELL 抑制される）

- [ ] **Step 3: `_generate_sell_signals()` シグネチャに `is_bear` を追加する**

```python
def _generate_sell_signals(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    score_map: dict[str, float],
    threshold: float,
    is_bear: bool = False,          # ← 追加
) -> list[dict[str, Any]]:
```

最低保有日数チェック部分を変更:

```python
        # 最低保有日数チェック（Bear レジーム時はスキップ）
        if not is_bear:
            held = _held_days(conn, code, target_date)
            if held is not None and held < _MIN_HOLDING_DAYS:
                logger.debug(
                    "_generate_sell_signals: %s 保有 %d 営業日（最低 %d 日）— SELL 抑制 date=%s",
                    code,
                    held,
                    _MIN_HOLDING_DAYS,
                    target_date,
                )
                continue
```

- [ ] **Step 4: `generate_signals()` 内の呼び出しに `is_bear` を渡す**

```python
    sell_signals = _generate_sell_signals(
        conn, target_date, score_map, threshold, is_bear=regime_is_bear
    )
```

- [ ] **Step 5: テストが通ることを確認する**

```bash
python -m pytest tests/test_signal_generator.py::TestMinHoldingDaysBearException -v
```

Expected: PASS

- [ ] **Step 6: 全テストが通ることを確認する**

```bash
python -m pytest --tb=no -q
```

Expected: 842+ passed

- [ ] **Step 7: PR-C コミット**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_signal_generator.py
git commit -m "feat: skip min holding days check on Bear regime transition (#174)"
```

PR-C 完成。PR を作成し `main` にマージ。Issue #174 / #171 クローズ。

---

## 自己レビュー

### スペックカバレッジ確認

| 要件 | 対応タスク |
|-----|---------|
| `position_entries` テーブル追加 | Task 1 |
| 最低保有日数 5営業日チェック（SELL 側） | Task 2 |
| 再エントリー制限 5営業日チェック（BUY 側） | Task 2 |
| バックテスト position_entries 書き込み | Task 3 |
| 本番/Paper Trading position_entries 書き込み | Task 4 |
| `earnings_calendar` テーブル追加 | Task 5 |
| `signals.size_multiplier` カラム追加 | Task 5 |
| J-Quants 決算カレンダー取得・保存 | Task 6 |
| pipeline.py への組み込み | Task 6 |
| `event_calendar.py` パーサー | Task 7 |
| `config/event_calendar.md` 作成 | Task 7 |
| 決算回避 BUY 抑制 | Task 8 |
| 決算前 SELL 強制（`earnings_avoidance`） | Task 8 |
| イベント前 BUY サイズ縮小（`size_multiplier=0.5`） | Task 8 |
| バックテストで earnings_calendar コピー | Task 9 |
| バックテストで size_multiplier 適用 | Task 9 |
| 本番 size_multiplier 適用 | Task 10 |
| Bear レジーム時の保有日数スキップ例外 | Task 11 |
| earnings_avoidance は保有日数をバイパス | Task 8（SELL flow の順序で自然に対応） |
