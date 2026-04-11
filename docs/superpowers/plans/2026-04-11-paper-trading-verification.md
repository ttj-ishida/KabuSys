# Paper Trading 検証テスト Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paper Trading の4指標（安定性・注文成功率・シグナル精度・APIレイテンシ）を自動検証する pytest 統合テストスイートと、稼働データを集計する検証レポートスクリプトを実装する。

**Architecture:** `monitoring_db.py` に `latency_ms` カラムを追加し、`ExecutionEngine` がブローカーAPI応答時間を計測して記録する。統合テストは SQLite in-memory + MockBrokerClient でフルスタックを検証。レポートスクリプトは `paper_trading.db` を直接クエリして指標を集計する。

**Tech Stack:** Python 3.10+, pytest, sqlite3, duckdb, psutil

---

## ファイル構成

| ファイル | 操作 | 責務 |
|---|---|---|
| `src/kabusys/monitoring/monitoring_db.py` | 変更 | `trade_logs` に `latency_ms` 追加 + `log_trade_event()` 更新 |
| `src/kabusys/execution/execution_engine.py` | 変更 | `MonitoringDB` オプション依存 + latency 計測 |
| `src/kabusys/tools/__init__.py` | 新規 | パッケージマーカー |
| `src/kabusys/tools/paper_verification_report.py` | 新規 | 稼働データ集計レポート |
| `tests/integration/__init__.py` | 新規 | パッケージマーカー |
| `tests/integration/test_paper_trading.py` | 新規 | 統合テストスイート（11テスト） |
| `tests/test_monitoring_db.py` | 変更 | `latency_ms` 関連テスト追加 |
| `tests/test_execution_engine.py` | 変更 | latency 記録テスト追加 + `_make_engine` 更新 |

---

## Task 1: `trade_logs` スキーマ拡張 + `log_trade_event()` 更新

**Files:**
- Modify: `src/kabusys/monitoring/monitoring_db.py:82-86,125-151`
- Test: `tests/test_monitoring_db.py`

### 背景知識

- `init_monitoring_db()` の `executescript()` ブロックには `latency_ms` がない
- 既存マイグレーションパターン（line 82-86）: `PRAGMA table_info()` でカラム存在確認 → `ALTER TABLE ADD COLUMN`
- `log_trade_event()` は現在9列の INSERT。`latency_ms` を10列目に追加する

- [ ] **Step 1: テストを書く**（`tests/test_monitoring_db.py` の `TestLogTradeEvent` クラスに追加）

```python
def test_latency_ms_stored_and_retrieved(self, mdb, monitoring_conn):
    """latency_ms が正しく格納・取得できる"""
    mdb.log_trade_event(
        event_type="Sent",
        client_order_id="order-lat",
        code="1234",
        side="buy",
        qty=100,
        price=1500.0,
        state="sent",
        latency_ms=42.5,
    )
    row = monitoring_conn.execute(
        "SELECT latency_ms FROM trade_logs WHERE client_order_id = 'order-lat'"
    ).fetchone()
    assert row["latency_ms"] == pytest.approx(42.5)

def test_latency_ms_defaults_to_none(self, mdb, monitoring_conn):
    """latency_ms 省略時は NULL が格納される"""
    mdb.log_trade_event(
        event_type="Created",
        client_order_id="order-nolat",
        code="5678",
        side="buy",
        qty=50,
        price=1000.0,
        state="created",
    )
    row = monitoring_conn.execute(
        "SELECT latency_ms FROM trade_logs WHERE client_order_id = 'order-nolat'"
    ).fetchone()
    assert row["latency_ms"] is None

def test_migration_adds_latency_ms_column(self):
    """init_monitoring_db() が latency_ms カラムを trade_logs に追加する"""
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(trade_logs)")}
    assert "latency_ms" in cols
    conn.close()

def test_migration_is_idempotent(self):
    """init_monitoring_db() を2回呼んでも latency_ms カラムが1つだけ"""
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    init_monitoring_db(conn)  # 2回目
    count = sum(
        1 for row in conn.execute("PRAGMA table_info(trade_logs)")
        if row[1] == "latency_ms"
    )
    assert count == 1
    conn.close()
```

- [ ] **Step 2: テストが失敗することを確認**

```
pytest tests/test_monitoring_db.py::TestLogTradeEvent::test_latency_ms_stored_and_retrieved -v
```
Expected: `FAIL` ("no such column: latency_ms" or similar)

- [ ] **Step 3: `monitoring_db.py` を実装する**

`init_monitoring_db()` の `peak_value` マイグレーション（line 82-86）の**直後**に追加：

```python
# 既存 DB に latency_ms カラムがない場合のマイグレーション（peak_value と同パターン）
existing_trade_cols = {row[1] for row in conn.execute("PRAGMA table_info(trade_logs)")}
if "latency_ms" not in existing_trade_cols:
    conn.execute("ALTER TABLE trade_logs ADD COLUMN latency_ms REAL")
    conn.commit()
```

`log_trade_event()` のシグネチャ（line 125-136）を更新：

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
    latency_ms: float | None = None,  # ← 追加（末尾オプション）
) -> None:
```

INSERT 文（line 143-150）を更新：

```python
        self._conn.execute(
            """
            INSERT INTO trade_logs
                (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms),
        )
```

- [ ] **Step 4: テストが通ることを確認**

```
pytest tests/test_monitoring_db.py -v
```
Expected: 全テスト PASS（既存 + 新規4件）

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/monitoring_db.py tests/test_monitoring_db.py
git commit -m "feat: add latency_ms column to trade_logs schema and log_trade_event() (Issue #44)"
```

---

## Task 2: `ExecutionEngine` に `MonitoringDB` 依存を追加してレイテンシを記録する

**Files:**
- Modify: `src/kabusys/execution/execution_engine.py:1-30,38-58,113-135`
- Test: `tests/test_execution_engine.py`

### 背景知識

- `ExecutionEngine.__init__` は現在8パラメータ（`reconciler` と `pid_file` はオプション）
- `_process_signals()` の `send_order()` 呼び出しは line 124-135 の `try/except` ブロック
- `fill_mode="never"` は `OrderSentPendingError` を送出するが、ブローカーはリクエストを受理済みなのでレイテンシは計測・記録する
- `self._repo.get(client_order_id)` で最新の `OrderRecord` を取得できる（get は `OrderRecord | None` を返す）

- [ ] **Step 1: テストを書く**（`tests/test_execution_engine.py` の `TestProcessSignals` クラスに追加）

まず `_make_engine()` ヘルパーに `monitoring_db` パラメータを追加：

```python
def _make_engine(broker, sqlite_conn, duckdb_conn, *, config=None, monitoring_db=None) -> ExecutionEngine:
    repo = OrderRepository(sqlite_conn)
    risk_config = RiskConfig(initial_portfolio_value=10_000_000.0)
    rm = RiskManager(broker=broker, repo=repo, config=risk_config)
    order_manager = OrderManager(broker=broker, repo=repo)
    cfg = config or EngineConfig(target_date=TARGET_DATE)
    return ExecutionEngine(
        broker=broker,
        repo=repo,
        risk_manager=rm,
        order_manager=order_manager,
        duckdb_conn=duckdb_conn,
        config=cfg,
        monitoring_db=monitoring_db,
    )
```

次にテストを追加（`test_monitoring_db.py` の import を追加: `from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db`）：

```python
def test_latency_ms_recorded_in_monitoring_db(self, sqlite_conn, duckdb_conn, monitoring_conn):
    """send_order() 後に monitoring_db.trade_logs.latency_ms が記録される"""
    _insert_signal(duckdb_conn, "1234")
    _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
    broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
    mdb = MonitoringDB(monitoring_conn)
    engine = _make_engine(broker, sqlite_conn, duckdb_conn, monitoring_db=mdb)
    engine._process_signals()
    monitoring_conn.row_factory = sqlite3.Row
    row = monitoring_conn.execute(
        "SELECT latency_ms FROM trade_logs WHERE event_type = 'Sent'"
    ).fetchone()
    assert row is not None
    assert row["latency_ms"] is not None
    assert row["latency_ms"] >= 0.0

def test_latency_ms_recorded_for_pending_order(self, sqlite_conn, duckdb_conn, monitoring_conn):
    """fill_mode=never (OrderSentPendingError) でも latency_ms が記録される"""
    _insert_signal(duckdb_conn, "1234")
    _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
    broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
    mdb = MonitoringDB(monitoring_conn)
    engine = _make_engine(broker, sqlite_conn, duckdb_conn, monitoring_db=mdb)
    engine._process_signals()
    monitoring_conn.row_factory = sqlite3.Row
    row = monitoring_conn.execute(
        "SELECT latency_ms FROM trade_logs WHERE event_type = 'Sent'"
    ).fetchone()
    assert row is not None
    assert row["latency_ms"] is not None
    assert row["latency_ms"] >= 0.0

def test_no_monitoring_db_does_not_raise(self, sqlite_conn, duckdb_conn):
    """monitoring_db=None のとき例外なく動作する（既存テストとの後方互換）"""
    _insert_signal(duckdb_conn, "1234")
    _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
    broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
    engine = _make_engine(broker, sqlite_conn, duckdb_conn)  # monitoring_db 省略
    engine._process_signals()  # 例外が出ないこと
```

- [ ] **Step 2: テストが失敗することを確認**

```
pytest tests/test_execution_engine.py::TestProcessSignals::test_latency_ms_recorded_in_monitoring_db -v
```
Expected: `FAIL` ("unexpected keyword argument 'monitoring_db'" or AttributeError)

- [ ] **Step 3: `execution_engine.py` を実装する**

**インポート追加**（line 9-10 付近、既存 import の後）：

```python
import time

from kabusys.monitoring.monitoring_db import MonitoringDB
```

**`__init__` にパラメータ追加**（`pid_file: Path | None = None,` の後）：

```python
monitoring_db: MonitoringDB | None = None,
```

**`self._pid_file = pid_file` の後**：

```python
self._monitoring_db = monitoring_db
```

**`_process_signals()` の発注ブロック（line 124-135）を置き換え**：

```python
            t0 = time.perf_counter()
            try:
                self._order_manager.send_order(record.client_order_id)
                latency_ms = (time.perf_counter() - t0) * 1000
                self._risk_manager.record_api_success()
                if self._monitoring_db is not None:
                    updated = self._repo.get(record.client_order_id)
                    self._monitoring_db.log_trade_event(
                        "Sent", record.client_order_id, record.code, record.side,
                        record.qty, record.price,
                        updated.filled_qty if updated else 0,
                        updated.state.value if updated else "",
                        latency_ms=latency_ms,
                    )
                logger.info("発注成功: signal_id=%s, client_order_id=%s", signal_id, record.client_order_id)
            except OrderSentPendingError:
                latency_ms = (time.perf_counter() - t0) * 1000
                self._risk_manager.record_api_success()
                if self._monitoring_db is not None:
                    updated = self._repo.get(record.client_order_id)
                    self._monitoring_db.log_trade_event(
                        "Sent", record.client_order_id, record.code, record.side,
                        record.qty, record.price,
                        updated.filled_qty if updated else 0,
                        updated.state.value if updated else "",
                        latency_ms=latency_ms,
                    )
                logger.info("発注保留（pending）: signal_id=%s", signal_id)
            except Exception as exc:
                self._risk_manager.record_api_error()
                logger.error("発注失敗: signal_id=%s: %s", signal_id, exc)
```

- [ ] **Step 4: テストが通ることを確認**

```
pytest tests/test_execution_engine.py -v
```
Expected: 全テスト PASS（既存 + 新規3件）

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/execution/execution_engine.py tests/test_execution_engine.py
git commit -m "feat: add MonitoringDB optional dep to ExecutionEngine for latency recording (Issue #44)"
```

---

## Task 3: 統合テスト基盤 + TestSystemStability + TestOrderSuccessRate

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_paper_trading.py`（このタスクでは TestSystemStability + TestOrderSuccessRate の6テスト）

### 背景知識

- 統合テストは `tests/conftest.py` の既存 `monitoring_conn` / `duckdb_conn` / `sqlite_conn` フィクスチャを使わず、自前で定義する（フィクスチャ名の衝突を避け、独立性を保つ）
- `OrderState.Filled.value = "filled"`, `OrderState.OrderSent.value = "sent"`, `OrderState.Rejected.value = "rejected"`
- `fill_mode="instant"` → `repo.list_active()` は1件（Filled は active）
- `fill_mode="reject"` → `repo.list_active()` は0件（Rejected は active でない）
- `fill_mode="never"` → `repo.list_active()` は1件（OrderSent = pending は active）
- `fill_mode="partial"` → `filled_qty = qty // 2`

- [ ] **Step 1: `tests/integration/__init__.py` を作成**

```python
# tests/integration/__init__.py
```

- [ ] **Step 2: 統合テストのヘルパーとフィクスチャを書く**

`tests/integration/test_paper_trading.py` を作成し、以下を記述：

```python
# tests/integration/test_paper_trading.py
"""Paper Trading 統合テストスイート（Issue #44）

MockBrokerClient + ExecutionEngine + MonitoringDB を組み合わせて
4指標（安定性・注文成功率・シグナル精度・APIレイテンシ）を自動検証する。
"""
from __future__ import annotations

import sqlite3
import time
from datetime import date

import duckdb
import pytest

from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.execution.risk_manager import RiskConfig, RiskManager
from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db

TARGET_DATE = date(2026, 4, 11)


@pytest.fixture
def orders_conn():
    """注文用 SQLite in-memory DB"""
    conn = sqlite3.connect(":memory:")
    init_orders_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def mon_conn():
    """監視用 SQLite in-memory DB（row_factory 設定済み）"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_monitoring_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def signals_conn():
    """シグナル + ポートフォリオターゲット用 DuckDB in-memory"""
    conn = duckdb.connect(":memory:")
    conn.execute(
        "CREATE TABLE signals (date DATE, code VARCHAR, side VARCHAR, score FLOAT, signal_rank INTEGER)"
    )
    conn.execute(
        "CREATE TABLE portfolio_targets (date DATE, code VARCHAR, target_size INTEGER, entry_price FLOAT)"
    )
    yield conn
    conn.close()


def _sig(conn, code: str, side: str = "buy"):
    conn.execute("INSERT INTO signals VALUES (?, ?, ?, ?, ?)", [TARGET_DATE, code, side, 0.8, 1])


def _tgt(conn, code: str, qty: int = 100, price: float = 1500.0):
    conn.execute("INSERT INTO portfolio_targets VALUES (?, ?, ?, ?)", [TARGET_DATE, code, qty, price])


def _engine(
    orders_conn, signals_conn, fill_mode="instant", cash=5_000_000.0, mon_conn=None
) -> ExecutionEngine:
    broker = MockBrokerClient(available_cash=cash, fill_mode=fill_mode)
    repo = OrderRepository(orders_conn)
    rm = RiskManager(broker=broker, repo=repo, config=RiskConfig(initial_portfolio_value=10_000_000.0))
    om = OrderManager(broker=broker, repo=repo)
    mdb = MonitoringDB(mon_conn) if mon_conn is not None else None
    return ExecutionEngine(
        broker=broker,
        repo=repo,
        risk_manager=rm,
        order_manager=om,
        duckdb_conn=signals_conn,
        config=EngineConfig(target_date=TARGET_DATE),
        monitoring_db=mdb,
    )
```

- [ ] **Step 3: TestSystemStability のテストを書く（同ファイルに追加）**

```python
class TestSystemStability:
    """システム安定性: 複数サイクル実行してもクラッシュしないことを検証"""

    def test_multiple_polling_cycles_no_crash(self, orders_conn, signals_conn):
        """3サイクル連続して _process_signals() が例外なく完走する"""
        _sig(signals_conn, "1234")
        _tgt(signals_conn, "1234")
        engine = _engine(orders_conn, signals_conn, fill_mode="instant")
        for _ in range(3):
            engine._process_signals()  # AssertionError / Exception が出ないこと

    def test_trade_logs_written_per_cycle(self, orders_conn, signals_conn, mon_conn):
        """シグナル処理後に monitoring_db.trade_logs へ 'Sent' イベントが記録される"""
        _sig(signals_conn, "1234")
        _tgt(signals_conn, "1234")
        engine = _engine(orders_conn, signals_conn, fill_mode="instant", mon_conn=mon_conn)
        engine._process_signals()
        count = mon_conn.execute(
            "SELECT COUNT(*) FROM trade_logs WHERE event_type = 'Sent'"
        ).fetchone()[0]
        assert count == 1
```

- [ ] **Step 4: TestOrderSuccessRate のテストを書く（同ファイルに追加）**

```python
class TestOrderSuccessRate:
    """注文成功率: 各 fill_mode で期待する注文状態になることを検証"""

    def test_instant_mode_order_filled(self, orders_conn, signals_conn):
        """fill_mode=instant → 注文が Filled 状態になる"""
        _sig(signals_conn, "1234")
        _tgt(signals_conn, "1234", qty=100)
        engine = _engine(orders_conn, signals_conn, fill_mode="instant")
        engine._process_signals()
        orders = engine._repo.list_active()
        assert len(orders) == 1
        assert orders[0].state == OrderState.Filled

    def test_reject_mode_no_active_orders(self, orders_conn, signals_conn):
        """fill_mode=reject → Rejected 注文は list_active() に含まれない"""
        _sig(signals_conn, "1234")
        _tgt(signals_conn, "1234", qty=100)
        engine = _engine(orders_conn, signals_conn, fill_mode="reject")
        engine._process_signals()
        assert len(engine._repo.list_active()) == 0

    def test_partial_mode_half_qty_filled(self, orders_conn, signals_conn):
        """fill_mode=partial → filled_qty が qty // 2 になる"""
        _sig(signals_conn, "1234")
        _tgt(signals_conn, "1234", qty=100)
        engine = _engine(orders_conn, signals_conn, fill_mode="partial")
        engine._process_signals()
        orders = engine._repo.list_active()
        assert len(orders) == 1
        assert orders[0].filled_qty == 50  # 100 // 2

    def test_never_mode_order_stays_sent(self, orders_conn, signals_conn):
        """fill_mode=never → 注文が OrderSent 状態のまま残る"""
        _sig(signals_conn, "1234")
        _tgt(signals_conn, "1234", qty=100)
        engine = _engine(orders_conn, signals_conn, fill_mode="never")
        engine._process_signals()
        orders = engine._repo.list_active()
        assert len(orders) == 1
        assert orders[0].state == OrderState.OrderSent
```

- [ ] **Step 5: テストが通ることを確認**

```
pytest tests/integration/test_paper_trading.py::TestSystemStability tests/integration/test_paper_trading.py::TestOrderSuccessRate -v
```
Expected: 6件 PASS

- [ ] **Step 6: コミット**

```bash
git add tests/integration/__init__.py tests/integration/test_paper_trading.py
git commit -m "test: add Paper Trading integration tests - stability and order success rate (Issue #44)"
```

---

## Task 4: TestSignalAccuracy + TestApiLatency

**Files:**
- Modify: `tests/integration/test_paper_trading.py`（5テストを追加）

### 背景知識

- `TestSignalAccuracy` の `test_risk_rejection_blocks_order`: `available_cash=0.0` で Gate1 が失敗し `OrderRecord` 自体が作成されない
- `TestApiLatency.test_send_order_latency_under_threshold`: `broker.send_order()` を直接呼んでレイテンシを計測する（ExecutionEngine を使わない）
- `time.perf_counter()` は高精度クロック（マイクロ秒オーダー）

- [ ] **Step 1: TestSignalAccuracy のテストを書く（`test_paper_trading.py` に追加）**

```python
class TestSignalAccuracy:
    """シグナル精度: シグナルが正しい注文に変換されることを検証"""

    def test_buy_signal_creates_buy_order(self, orders_conn, signals_conn):
        """BUY シグナルが side='buy' の注文に変換される"""
        _sig(signals_conn, "1234", side="buy")
        _tgt(signals_conn, "1234")
        engine = _engine(orders_conn, signals_conn, fill_mode="instant")
        engine._process_signals()
        orders = engine._repo.list_active()
        assert len(orders) == 1
        assert orders[0].side == "buy"

    def test_sell_signal_creates_sell_order(self, orders_conn, signals_conn):
        """SELL シグナルが side='sell' の注文に変換される"""
        _sig(signals_conn, "1234", side="sell")
        _tgt(signals_conn, "1234")
        engine = _engine(orders_conn, signals_conn, fill_mode="instant")
        engine._process_signals()
        orders = engine._repo.list_active()
        assert len(orders) == 1
        assert orders[0].side == "sell"

    def test_risk_rejection_blocks_order_creation(self, orders_conn, signals_conn):
        """余力不足（Gate1 NG）のシグナルは OrderRecord が作成されない"""
        _sig(signals_conn, "1234")
        _tgt(signals_conn, "1234", qty=100, price=1500.0)
        # available_cash=0 → order_value(150,000) > max_position(0*0.20) → Gate1 NG
        engine = _engine(orders_conn, signals_conn, fill_mode="instant", cash=0.0)
        engine._process_signals()
        assert len(engine._repo.list_active()) == 0
```

- [ ] **Step 2: TestApiLatency のテストを書く（`test_paper_trading.py` に追加）**

```python
class TestApiLatency:
    """APIレイテンシ: ブローカーAPI応答時間の記録と閾値検証"""

    def test_send_order_latency_recorded(self, orders_conn, signals_conn, mon_conn):
        """send_order() 後に trade_logs.latency_ms が NOT NULL で記録される"""
        _sig(signals_conn, "1234")
        _tgt(signals_conn, "1234")
        engine = _engine(orders_conn, signals_conn, fill_mode="instant", mon_conn=mon_conn)
        engine._process_signals()
        row = mon_conn.execute(
            "SELECT latency_ms FROM trade_logs WHERE event_type = 'Sent'"
        ).fetchone()
        assert row is not None
        assert row["latency_ms"] is not None
        assert row["latency_ms"] >= 0.0

    def test_send_order_latency_under_500ms(self):
        """MockBrokerClient.send_order() の応答が 500ms 以内"""
        from kabusys.execution.broker_api import OrderRequest
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        request = OrderRequest(code="1234", side="buy", qty=100, order_type="limit", price=1500.0)
        t0 = time.perf_counter()
        broker.send_order(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 500.0, f"send_order() が {elapsed_ms:.1f}ms かかりました（閾値: 500ms）"
```

- [ ] **Step 3: 全統合テストが通ることを確認**

```
pytest tests/integration/test_paper_trading.py -v
```
Expected: 11件全て PASS

- [ ] **Step 4: コミット**

```bash
git add tests/integration/test_paper_trading.py
git commit -m "test: add Paper Trading integration tests - signal accuracy and API latency (Issue #44)"
```

---

## Task 5: `paper_verification_report.py` 作成

**Files:**
- Create: `src/kabusys/tools/__init__.py`
- Create: `src/kabusys/tools/paper_verification_report.py`

### 背景知識

- `process_ok` は `system_status.process_ok INTEGER`（0 or 1）。`SUM(process_ok)` で稼働行数を集計
- SQLite は `PERCENTILE()` を持たないため、P95 は Python 側で `sorted()` を使って計算する
- `PAPER_TRADING_SQLITE_PATH` 環境変数でDB パスを上書きできる（デフォルト: `data/paper_trading.db`）
- `--from` / `--to` はオプション。省略時は全期間を集計

- [ ] **Step 1: `src/kabusys/tools/__init__.py` を作成**

```python
# src/kabusys/tools/__init__.py
```

- [ ] **Step 2: `paper_verification_report.py` を実装する**

```python
# src/kabusys/tools/paper_verification_report.py
"""Paper Trading 検証レポート出力スクリプト。

稼働後の paper_trading.db を集計し、ゴーライブ判断に必要な4指標を表示する。

Usage:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import date
from pathlib import Path

# 合格基準
UPTIME_THRESHOLD = 99.0         # 稼働率 ≥ 99%
SUCCESS_RATE_THRESHOLD = 90.0   # 注文成功率（Filled/Created） ≥ 90%
SEND_RATE_THRESHOLD = 95.0      # 送信率（Sent/Created） ≥ 95%
LATENCY_P95_THRESHOLD = 200.0   # P95レイテンシ ≤ 200ms

DEFAULT_DB_PATH = Path("data/paper_trading.db")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Paper Trading 検証レポート")
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat, default=None,
                        metavar="YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", type=date.fromisoformat, default=None,
                        metavar="YYYY-MM-DD")
    return parser.parse_args()


def _date_filter(date_from: date | None, date_to: date | None, col: str = "logged_at") -> tuple[str, list]:
    """WHERE 句に付加できる AND 条件文字列と引数リストを返す。"""
    conds, params = [], []
    if date_from:
        conds.append(f"{col} >= ?")
        params.append(date_from.isoformat())
    if date_to:
        conds.append(f"{col} <= ?")
        params.append(date_to.isoformat() + "T23:59:59+00:00")  # UTC タイムスタンプと正しく比較するため +00:00 必須
    return ("AND " + " AND ".join(conds) if conds else ""), params


def _uptime(conn: sqlite3.Connection, date_from: date | None, date_to: date | None) -> dict:
    suf, params = _date_filter(date_from, date_to, col="recorded_at")
    row = conn.execute(
        f"SELECT COUNT(*), SUM(process_ok) FROM system_status WHERE 1=1 {suf}",
        params,
    ).fetchone()
    total = row[0] or 0
    ok = int(row[1] or 0)
    return {
        "total": total,
        "errors": total - ok,
        "rate": (ok / total * 100) if total > 0 else 0.0,
    }


def _order_success(conn: sqlite3.Connection, date_from: date | None, date_to: date | None) -> dict:
    suf, params = _date_filter(date_from, date_to)
    created = conn.execute(
        f"SELECT COUNT(*) FROM trade_logs WHERE event_type='Created' {suf}", params
    ).fetchone()[0]
    filled = conn.execute(
        f"SELECT COUNT(*) FROM trade_logs WHERE event_type='Filled' {suf}", params
    ).fetchone()[0]
    return {
        "total": created,
        "filled": filled,
        "rate": (filled / created * 100) if created > 0 else 0.0,
    }


def _signal_accuracy(conn: sqlite3.Connection, date_from: date | None, date_to: date | None) -> dict:
    suf, params = _date_filter(date_from, date_to)
    created = conn.execute(
        f"SELECT COUNT(*) FROM trade_logs WHERE event_type='Created' {suf}", params
    ).fetchone()[0]
    sent = conn.execute(
        f"SELECT COUNT(*) FROM trade_logs WHERE event_type='Sent' {suf}", params
    ).fetchone()[0]
    risk_rejections = conn.execute(
        f"SELECT COUNT(*) FROM risk_logs WHERE 1=1 {suf}", params
    ).fetchone()[0]
    return {
        "created": created,
        "sent": sent,
        "rate": (sent / created * 100) if created > 0 else 0.0,
        "risk_rejections": risk_rejections,
    }


def _latency(conn: sqlite3.Connection, date_from: date | None, date_to: date | None) -> dict:
    suf, params = _date_filter(date_from, date_to)
    rows = conn.execute(
        f"SELECT latency_ms FROM trade_logs WHERE latency_ms IS NOT NULL {suf}",
        params,
    ).fetchall()
    values = sorted(r[0] for r in rows)
    if not values:
        return {"avg": None, "max": None, "p95": None}
    avg = sum(values) / len(values)
    max_ = values[-1]
    # statistics.quantiles() は len >= 2 必須かつ単一要素で StatisticsError が発生するため
    # 手動インデックス計算を使用（len==1 でも正しく values[0] を返す）
    idx = max(0, int(len(values) * 0.95) - 1)
    p95 = values[idx]
    return {"avg": avg, "max": max_, "p95": p95}


def _verdict(uptime_rate: float, success_rate: float, send_rate: float, p95: float | None) -> str:
    ok = (
        uptime_rate >= UPTIME_THRESHOLD
        and success_rate >= SUCCESS_RATE_THRESHOLD
        and send_rate >= SEND_RATE_THRESHOLD
        and (p95 is None or p95 <= LATENCY_P95_THRESHOLD)
    )
    return "PASS" if ok else "FAIL"


def generate_report(db_path: Path, date_from: date | None = None, date_to: date | None = None) -> str:
    """レポート文字列を生成して返す（テスト・CLI 共用）。"""
    conn = sqlite3.connect(str(db_path))
    try:
        u = _uptime(conn, date_from, date_to)
        s = _order_success(conn, date_from, date_to)
        sig = _signal_accuracy(conn, date_from, date_to)
        lat = _latency(conn, date_from, date_to)
    finally:
        conn.close()

    period = f"{date_from or '(全期間)'} ~ {date_to or '(全期間)'}"
    v = _verdict(u["rate"], s["rate"], sig["rate"], lat["p95"])

    lat_lines = ["[APIレイテンシ]"]
    if lat["avg"] is not None:
        lat_lines += [
            f"  平均レイテンシ:    {lat['avg']:.1f} ms",
            f"  最大レイテンシ:    {lat['max']:.1f} ms",
            f"  P95レイテンシ:     {lat['p95']:.1f} ms",
        ]
    else:
        lat_lines.append("  データなし")

    lines = [
        "=" * 40,
        " Paper Trading 検証レポート",
        f" 期間: {period}",
        "=" * 40,
        "[システム安定性]",
        f"  総ポーリング数:   {u['total']}",
        f"  エラー発生数:     {u['errors']}",
        f"  稼働率:           {u['rate']:.1f}%",
        "",
        "[注文成功率]",
        f"  総注文数:         {s['total']}",
        f"  成立数(Filled):   {s['filled']}",
        f"  成功率:           {s['rate']:.1f}%",
        "",
        "[シグナル精度]",
        f"  Created 注文数:   {sig['created']}",
        f"  Sent 注文数:      {sig['sent']}",
        f"  送信率:           {sig['rate']:.1f}%",
        f"  リスク却下数:     {sig['risk_rejections']} 件  (risk_logs 参照)",
        "",
        *lat_lines,
        "",
        f"判定: {v} {'(全指標が基準値を満たしています)' if v == 'PASS' else '(基準値を満たさない指標があります)'}",
        "=" * 40,
    ]
    return "\n".join(lines)


def main() -> None:
    args = _parse_args()
    db_path = Path(os.environ.get("PAPER_TRADING_SQLITE_PATH", str(DEFAULT_DB_PATH)))
    if not db_path.exists():
        print(f"[ERROR] DB が見つかりません: {db_path}")
        return
    print(generate_report(db_path, args.date_from, args.date_to))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: `pytest` と手動実行で動作確認**

まず既存テストが全て通ることを確認：

```
pytest tests/ -v --tb=short
```
Expected: 全テスト PASS（既存 + 新規15件）

次に構文エラーがないことを確認：

```
python -c "from kabusys.tools.paper_verification_report import generate_report; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: コミット**

```bash
git add src/kabusys/tools/__init__.py src/kabusys/tools/paper_verification_report.py
git commit -m "feat: add paper_verification_report script for Paper Trading verification (Issue #44)"
```

---

## 最終確認

- [ ] **全テストスイートを実行**

```
pytest tests/ -v --tb=short
```
Expected: 全テスト PASS

- [ ] **完了コミット確認**

```bash
git log --oneline -5
```
Expected: Task 1〜5 の5コミットが積み上がっている
