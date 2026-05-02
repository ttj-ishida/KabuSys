# SQLite監視ログDB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `src/kabusys/monitoring/monitoring_db.py` を実装し、Phase 7 監視システムの SQLite 永続化基盤（5テーブル）を構築する。

**Architecture:** `order_repository.py` と同じパターン — `init_monitoring_db(conn)` でテーブルを冪等作成し、`MonitoringDB(conn)` クラスが読み書きを担当。5テーブル：`system_status`（追記）、`trade_logs`（追記）、`positions`（upsert）、`risk_logs`（追記）、`dashboard`（1行 upsert）。

**Tech Stack:** Python 3.13, SQLite3（標準ライブラリ）, pytest

---

## File Structure

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/kabusys/monitoring/monitoring_db.py` | 新規作成 | `init_monitoring_db`, `MonitoringDB` |
| `src/kabusys/monitoring/__init__.py` | 修正 | `MonitoringDB`, `init_monitoring_db` をエクスポート |
| `tests/conftest.py` | 修正 | `monitoring_conn` フィクスチャ追加 |
| `tests/test_monitoring_db.py` | 新規作成 | 全テストケース |

---

## Task 1: `init_monitoring_db()` + `monitoring_conn` フィクスチャ

**Files:**
- Create: `src/kabusys/monitoring/monitoring_db.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_monitoring_db.py`

- [ ] **Step 1: `monitoring_conn` フィクスチャを `conftest.py` に追加**

`tests/conftest.py` の末尾に追加（既存の `sqlite_conn` フィクスチャの直後）:

```python
from kabusys.monitoring.monitoring_db import init_monitoring_db


@pytest.fixture
def monitoring_conn():
    """テスト用インメモリ SQLite（監視ログ DB スキーマ）を返すフィクスチャ。"""
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    yield conn
    conn.close()
```

- [ ] **Step 2: テストファイルを作成し、失敗するテストを書く**

`tests/test_monitoring_db.py` を新規作成:

```python
"""MonitoringDB 単体テスト（Issue #36）"""
import sqlite3
from datetime import datetime, timezone, timedelta

import pytest

from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db


@pytest.fixture
def mdb(monitoring_conn):
    return MonitoringDB(monitoring_conn)


class TestInitMonitoringDb:

    def test_tables_created_idempotently(self, monitoring_conn):
        """init_monitoring_db を2回呼んでもエラーなし、5テーブルが存在する"""
        init_monitoring_db(monitoring_conn)  # 2回目の呼び出し
        tables = {
            row[0]
            for row in monitoring_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"system_status", "trade_logs", "positions", "risk_logs", "dashboard"}.issubset(tables)
```

- [ ] **Step 3: テストが失敗することを確認**

```
pytest tests/test_monitoring_db.py::TestInitMonitoringDb::test_tables_created_idempotently -v
```

Expected: `ModuleNotFoundError` または `ImportError`（`monitoring_db.py` 未作成のため）

- [ ] **Step 4: `monitoring_db.py` を作成し `init_monitoring_db` を実装**

`src/kabusys/monitoring/monitoring_db.py` を新規作成:

```python
# src/kabusys/monitoring/monitoring_db.py
"""MonitoringDB — SQLite を使った監視ログの永続化層。

ビジネスロジックを持たない。読み書きのみ。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def init_monitoring_db(conn: sqlite3.Connection) -> None:
    """5テーブル + インデックスを作成する（冪等）。"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS system_status (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at    TEXT    NOT NULL,
            cpu_percent    REAL    NOT NULL,
            memory_percent REAL    NOT NULL,
            disk_percent   REAL    NOT NULL,
            process_ok     INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_system_status_recorded_at
            ON system_status (recorded_at);

        CREATE TABLE IF NOT EXISTS trade_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            logged_at       TEXT    NOT NULL,
            event_type      TEXT    NOT NULL,
            client_order_id TEXT    NOT NULL,
            code            TEXT    NOT NULL,
            side            TEXT    NOT NULL,
            qty             INTEGER NOT NULL,
            price           REAL    NOT NULL DEFAULT 0.0,
            filled_qty      INTEGER NOT NULL DEFAULT 0,
            state           TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_trade_logs_logged_at
            ON trade_logs (logged_at);
        CREATE INDEX IF NOT EXISTS idx_trade_logs_client_order_id
            ON trade_logs (client_order_id);

        CREATE TABLE IF NOT EXISTS positions (
            code          TEXT    PRIMARY KEY,
            qty           INTEGER NOT NULL,
            avg_price     REAL    NOT NULL,
            current_price REAL,
            updated_at    TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_positions_updated_at
            ON positions (updated_at);

        CREATE TABLE IF NOT EXISTS risk_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            logged_at    TEXT    NOT NULL,
            event_type   TEXT    NOT NULL,
            metric_name  TEXT    NOT NULL,
            metric_value REAL    NOT NULL,
            threshold    REAL    NOT NULL,
            detail       TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_risk_logs_logged_at
            ON risk_logs (logged_at);
        CREATE INDEX IF NOT EXISTS idx_risk_logs_event_type
            ON risk_logs (event_type);

        CREATE TABLE IF NOT EXISTS dashboard (
            id                INTEGER PRIMARY KEY CHECK (id = 1),
            updated_at        TEXT    NOT NULL,
            portfolio_value   REAL    NOT NULL,
            cash              REAL    NOT NULL,
            drawdown_pct      REAL    NOT NULL,
            open_order_count  INTEGER NOT NULL,
            position_count    INTEGER NOT NULL
        );
    """)
    conn.commit()


class MonitoringDB:
    """監視ログ DB の読み書きクラス。ビジネスロジックを持たない。

    Notes:
        __init__ で conn.row_factory = sqlite3.Row を設定する（order_repository.py と同パターン）。
        これは呼び出し元の conn オブジェクトへの副作用だが、monitoring.db と orders.db は
        別ファイルのため共有されない。
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        conn.row_factory = sqlite3.Row
        self._conn = conn

    def _now(self) -> str:
        """現在時刻を ISO8601 UTC 文字列で返す。"""
        return datetime.now(timezone.utc).isoformat()
```

- [ ] **Step 5: テストを実行してパスを確認**

```
pytest tests/test_monitoring_db.py::TestInitMonitoringDb -v
```

Expected: `1 passed`

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/monitoring/monitoring_db.py tests/conftest.py tests/test_monitoring_db.py
git commit -m "feat: add init_monitoring_db and monitoring_conn fixture (Issue #36)"
```

---

## Task 2: `log_system_status()`

**Files:**
- Modify: `src/kabusys/monitoring/monitoring_db.py`
- Modify: `tests/test_monitoring_db.py`

- [ ] **Step 1: テストを追加**

`tests/test_monitoring_db.py` の `TestInitMonitoringDb` クラスの後に追加:

```python
class TestLogSystemStatus:

    def test_appends_row(self, mdb, monitoring_conn):
        """2回呼ぶと2行追記される"""
        mdb.log_system_status(50.0, 60.0, 70.0, True)
        mdb.log_system_status(55.0, 65.0, 75.0, False)
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM system_status"
        ).fetchone()[0]
        assert count == 2

    def test_default_recorded_at_is_utc_now(self, mdb, monitoring_conn):
        """`recorded_at` 省略時に ISO8601 UTC 文字列が入り、now との差が5秒以内"""
        before = datetime.now(timezone.utc)
        mdb.log_system_status(50.0, 60.0, 70.0, True)
        after = datetime.now(timezone.utc)
        row = monitoring_conn.execute(
            "SELECT recorded_at FROM system_status"
        ).fetchone()
        recorded = datetime.fromisoformat(row[0])
        assert before - timedelta(seconds=5) <= recorded <= after + timedelta(seconds=5)
```

- [ ] **Step 2: テストが失敗することを確認**

```
pytest tests/test_monitoring_db.py::TestLogSystemStatus -v
```

Expected: `AttributeError: 'MonitoringDB' object has no attribute 'log_system_status'`

- [ ] **Step 3: `log_system_status` を実装**

`MonitoringDB` クラスに追加（`_now` メソッドの後）:

```python
    def log_system_status(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
        process_ok: bool,
        recorded_at: datetime | None = None,
    ) -> None:
        """システム状態を system_status テーブルに追記する。"""
        ts = recorded_at.isoformat() if recorded_at else self._now()
        self._conn.execute(
            """
            INSERT INTO system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ts, cpu_percent, memory_percent, disk_percent, 1 if process_ok else 0),
        )
        self._conn.commit()
```

- [ ] **Step 4: テストを実行してパスを確認**

```
pytest tests/test_monitoring_db.py::TestLogSystemStatus -v
```

Expected: `2 passed`

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/monitoring_db.py tests/test_monitoring_db.py
git commit -m "feat: add MonitoringDB.log_system_status (Issue #36)"
```

---

## Task 3: `log_trade_event()`

**Files:**
- Modify: `src/kabusys/monitoring/monitoring_db.py`
- Modify: `tests/test_monitoring_db.py`

- [ ] **Step 1: テストを追加**

`tests/test_monitoring_db.py` に追加:

```python
class TestLogTradeEvent:

    def test_appends_row_with_correct_fields(self, mdb, monitoring_conn):
        """全フィールドが正しく保存される"""
        ts = datetime(2026, 3, 30, 9, 0, 0, tzinfo=timezone.utc)
        mdb.log_trade_event(
            event_type="filled",
            client_order_id="order-001",
            code="1234",
            side="buy",
            qty=100,
            price=1500.0,
            filled_qty=100,
            state="filled",
            logged_at=ts,
        )
        row = monitoring_conn.execute(
            "SELECT * FROM trade_logs WHERE client_order_id = 'order-001'"
        ).fetchone()
        assert row["event_type"] == "filled"
        assert row["code"] == "1234"
        assert row["qty"] == 100
        assert row["price"] == 1500.0
        assert row["filled_qty"] == 100
        assert row["state"] == "filled"

    def test_market_order_price_defaults_to_zero(self, mdb, monitoring_conn):
        """成行注文は price=0.0 で記録できる（order_repository.py と同規約）"""
        mdb.log_trade_event(
            event_type="order_created",
            client_order_id="order-002",
            code="5678",
            side="buy",
            qty=100,
            price=0.0,
            state="created",
        )
        row = monitoring_conn.execute(
            "SELECT price FROM trade_logs WHERE client_order_id = 'order-002'"
        ).fetchone()
        assert row[0] == 0.0
```

- [ ] **Step 2: テストが失敗することを確認**

```
pytest tests/test_monitoring_db.py::TestLogTradeEvent -v
```

Expected: `AttributeError: 'MonitoringDB' object has no attribute 'log_trade_event'`

- [ ] **Step 3: `log_trade_event` を実装**

`MonitoringDB` クラスに追加:

```python
    def log_trade_event(
        self,
        event_type: str,
        client_order_id: str,
        code: str,
        side: str,
        qty: int,
        price: float,
        filled_qty: int = 0,
        state: str = "",
        logged_at: datetime | None = None,
    ) -> None:
        """発注イベントを trade_logs テーブルに追記する。

        price: 成行注文は 0.0（order_repository.py と同規約）
        filled_qty / state: スキーマ列順と一致させること
        """
        ts = logged_at.isoformat() if logged_at else self._now()
        self._conn.execute(
            """
            INSERT INTO trade_logs
                (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, event_type, client_order_id, code, side, qty, price, filled_qty, state),
        )
        self._conn.commit()
```

- [ ] **Step 4: テストを実行してパスを確認**

```
pytest tests/test_monitoring_db.py::TestLogTradeEvent -v
```

Expected: `2 passed`

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/monitoring_db.py tests/test_monitoring_db.py
git commit -m "feat: add MonitoringDB.log_trade_event (Issue #36)"
```

---

## Task 4: `upsert_position()` + `delete_position()`

**Files:**
- Modify: `src/kabusys/monitoring/monitoring_db.py`
- Modify: `tests/test_monitoring_db.py`

- [ ] **Step 1: テストを追加**

```python
class TestUpsertPosition:

    def test_insert_new_position(self, mdb, monitoring_conn):
        """新規 code が挿入される"""
        mdb.upsert_position("1234", 100, 1500.0)
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM positions"
        ).fetchone()[0]
        assert count == 1

    def test_update_existing_position(self, mdb, monitoring_conn):
        """同一 code を2回 upsert すると上書きされる（行数は1のまま）"""
        mdb.upsert_position("1234", 100, 1500.0)
        mdb.upsert_position("1234", 50, 1600.0)
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM positions"
        ).fetchone()[0]
        assert count == 1
        row = monitoring_conn.execute(
            "SELECT qty, avg_price FROM positions WHERE code = '1234'"
        ).fetchone()
        assert row[0] == 50
        assert row[1] == 1600.0

    def test_delete_position(self, mdb, monitoring_conn):
        """`delete_position` 後にその code は取得されない"""
        mdb.upsert_position("1234", 100, 1500.0)
        mdb.delete_position("1234")
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM positions WHERE code = '1234'"
        ).fetchone()[0]
        assert count == 0
```

- [ ] **Step 2: テストが失敗することを確認**

```
pytest tests/test_monitoring_db.py::TestUpsertPosition -v
```

Expected: `AttributeError: 'MonitoringDB' object has no attribute 'upsert_position'`

- [ ] **Step 3: `upsert_position` と `delete_position` を実装**

`MonitoringDB` クラスに追加:

```python
    def upsert_position(
        self,
        code: str,
        qty: int,
        avg_price: float,
        current_price: float | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        """保有ポジションを upsert する（code をキーに上書き）。"""
        ts = updated_at.isoformat() if updated_at else self._now()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO positions (code, qty, avg_price, current_price, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (code, qty, avg_price, current_price, ts),
        )
        self._conn.commit()

    def delete_position(self, code: str) -> None:
        """ポジション解消時に code を削除する。"""
        self._conn.execute("DELETE FROM positions WHERE code = ?", (code,))
        self._conn.commit()
```

- [ ] **Step 4: テストを実行してパスを確認**

```
pytest tests/test_monitoring_db.py::TestUpsertPosition -v
```

Expected: `3 passed`

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/monitoring_db.py tests/test_monitoring_db.py
git commit -m "feat: add MonitoringDB.upsert_position and delete_position (Issue #36)"
```

---

## Task 5: `log_risk_event()`

**Files:**
- Modify: `src/kabusys/monitoring/monitoring_db.py`
- Modify: `tests/test_monitoring_db.py`

- [ ] **Step 1: テストを追加**

```python
class TestLogRiskEvent:

    def test_appends_row(self, mdb, monitoring_conn):
        """全フィールドが正しく保存される"""
        ts = datetime(2026, 3, 30, 9, 0, 0, tzinfo=timezone.utc)
        mdb.log_risk_event(
            event_type="drawdown_warning",
            metric_name="drawdown_pct",
            metric_value=5.5,
            threshold=5.0,
            detail='{"portfolio_value": 9450000}',
            logged_at=ts,
        )
        row = monitoring_conn.execute("SELECT * FROM risk_logs").fetchone()
        assert row["event_type"] == "drawdown_warning"
        assert row["metric_name"] == "drawdown_pct"
        assert row["metric_value"] == 5.5
        assert row["threshold"] == 5.0
        assert row["detail"] == '{"portfolio_value": 9450000}'

    def test_detail_can_be_none(self, mdb, monitoring_conn):
        """`detail` は NULL 可"""
        mdb.log_risk_event("circuit_breaker", "api_error_count", 3.0, 3.0)
        row = monitoring_conn.execute("SELECT detail FROM risk_logs").fetchone()
        assert row[0] is None
```

- [ ] **Step 2: テストが失敗することを確認**

```
pytest tests/test_monitoring_db.py::TestLogRiskEvent -v
```

Expected: `AttributeError: 'MonitoringDB' object has no attribute 'log_risk_event'`

- [ ] **Step 3: `log_risk_event` を実装**

`MonitoringDB` クラスに追加:

```python
    def log_risk_event(
        self,
        event_type: str,
        metric_name: str,
        metric_value: float,
        threshold: float,
        detail: str | None = None,
        logged_at: datetime | None = None,
    ) -> None:
        """リスクイベントを risk_logs テーブルに追記する。

        detail: JSON 文字列等の追加情報（NULL 可）
        """
        ts = logged_at.isoformat() if logged_at else self._now()
        self._conn.execute(
            """
            INSERT INTO risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ts, event_type, metric_name, metric_value, threshold, detail),
        )
        self._conn.commit()
```

- [ ] **Step 4: テストを実行してパスを確認**

```
pytest tests/test_monitoring_db.py::TestLogRiskEvent -v
```

Expected: `2 passed`

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/monitoring_db.py tests/test_monitoring_db.py
git commit -m "feat: add MonitoringDB.log_risk_event (Issue #36)"
```

---

## Task 6: `upsert_dashboard()` + `get_dashboard()`

**Files:**
- Modify: `src/kabusys/monitoring/monitoring_db.py`
- Modify: `tests/test_monitoring_db.py`

- [ ] **Step 1: テストを追加**

```python
class TestUpsertDashboard:

    def test_first_upsert_creates_row(self, mdb, monitoring_conn):
        """最初の upsert でレコードが作成される"""
        mdb.upsert_dashboard(10_000_000.0, 5_000_000.0, 0.0, 3, 5)
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM dashboard"
        ).fetchone()[0]
        assert count == 1

    def test_second_upsert_overwrites(self, mdb, monitoring_conn):
        """2回 upsert しても行数は1のまま、値は最新"""
        mdb.upsert_dashboard(10_000_000.0, 5_000_000.0, 0.0, 3, 5)
        mdb.upsert_dashboard(9_500_000.0, 4_500_000.0, 5.0, 1, 3)
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM dashboard"
        ).fetchone()[0]
        assert count == 1

    def test_get_dashboard_returns_latest(self, mdb):
        """`get_dashboard()` が最新の dict を返す"""
        mdb.upsert_dashboard(10_000_000.0, 5_000_000.0, 0.0, 3, 5)
        mdb.upsert_dashboard(9_500_000.0, 4_500_000.0, 5.0, 1, 3)
        result = mdb.get_dashboard()
        assert result is not None
        assert result["portfolio_value"] == 9_500_000.0
        assert result["drawdown_pct"] == 5.0
        assert result["position_count"] == 3

    def test_get_dashboard_returns_none_when_empty(self, mdb):
        """レコードなし時は None を返す"""
        result = mdb.get_dashboard()
        assert result is None
```

- [ ] **Step 2: テストが失敗することを確認**

```
pytest tests/test_monitoring_db.py::TestUpsertDashboard -v
```

Expected: `AttributeError: 'MonitoringDB' object has no attribute 'upsert_dashboard'`

- [ ] **Step 3: `upsert_dashboard` と `get_dashboard` を実装**

`MonitoringDB` クラスに追加:

```python
    def upsert_dashboard(
        self,
        portfolio_value: float,
        cash: float,
        drawdown_pct: float,
        open_order_count: int,
        position_count: int,
        updated_at: datetime | None = None,
    ) -> None:
        """ダッシュボード集計を更新する（常に id=1 の1行のみ保持）。

        id=1 を明示的にバインドすること（DEFAULT に頼らない）。
        CHECK (id = 1) 制約により DB レベルでも id=1 以外は拒否される。
        """
        ts = updated_at.isoformat() if updated_at else self._now()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO dashboard
                (id, updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count)
            VALUES (1, ?, ?, ?, ?, ?, ?)
            """,
            (ts, portfolio_value, cash, drawdown_pct, open_order_count, position_count),
        )
        self._conn.commit()

    def get_dashboard(self) -> dict | None:
        """ダッシュボード集計を dict で返す。レコードなしの場合は None。

        row_factory = sqlite3.Row が設定済みであることを前提とする。
        """
        cursor = self._conn.execute("SELECT * FROM dashboard WHERE id = 1")
        row = cursor.fetchone()
        return dict(row) if row else None
```

- [ ] **Step 4: テストを実行してパスを確認**

```
pytest tests/test_monitoring_db.py::TestUpsertDashboard -v
```

Expected: `4 passed`

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/monitoring_db.py tests/test_monitoring_db.py
git commit -m "feat: add MonitoringDB.upsert_dashboard and get_dashboard (Issue #36)"
```

---

## Task 7: `__init__.py` エクスポート + 全テスト確認

**Files:**
- Modify: `src/kabusys/monitoring/__init__.py`

- [ ] **Step 1: `__init__.py` を更新**

`src/kabusys/monitoring/__init__.py` を以下の内容で上書き:

```python
from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db

__all__ = ["MonitoringDB", "init_monitoring_db"]
```

- [ ] **Step 2: インポートが機能することを確認**

```
python -c "from kabusys.monitoring import MonitoringDB, init_monitoring_db; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 全テストを実行してパスを確認**

```
pytest tests/test_monitoring_db.py -v
```

Expected: 全テストが PASS（最低13件）

- [ ] **Step 4: リグレッションなしを確認**

```
pytest --tb=short -q
```

Expected: 全テストが PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/__init__.py
git commit -m "feat: export MonitoringDB and init_monitoring_db from monitoring package (Issue #36)"
```
