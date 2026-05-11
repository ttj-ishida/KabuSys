# tests/integration/test_paper_trading.py
"""Paper Trading 統合テストスイート（Issue #44）

MockBrokerClient + ExecutionEngine + MonitoringDB を組み合わせて
4指標（安定性・注文成功率・シグナル精度・APIレイテンシ）を自動検証する。
"""

from __future__ import annotations

import sqlite3
import time
from datetime import date

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
    """監視用 SQLite in-memory DB"""
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    yield conn
    conn.close()


def _sig(conn, code: str, side: str = "buy"):
    conn.execute(
        "INSERT INTO signals (date, code, side, score, signal_rank) VALUES (?, ?, ?, ?, ?)",
        [TARGET_DATE, code, side, 0.8, 1],
    )


def _tgt(conn, code: str, qty: int = 100, price: float = 1500.0):
    conn.execute(
        "INSERT INTO portfolio_targets VALUES (?, ?, ?, ?)",
        [TARGET_DATE, code, qty, price],
    )


def _engine(
    orders_conn, duckdb_conn, fill_mode="instant", cash=5_000_000.0, mon_conn=None
) -> ExecutionEngine:
    broker = MockBrokerClient(available_cash=cash, fill_mode=fill_mode)
    repo = OrderRepository(orders_conn)
    rm = RiskManager(
        broker=broker,
        repo=repo,
        config=RiskConfig(initial_portfolio_value=10_000_000.0),
    )
    om = OrderManager(broker=broker, repo=repo)
    mdb = MonitoringDB(mon_conn) if mon_conn is not None else None
    return ExecutionEngine(
        broker=broker,
        repo=repo,
        risk_manager=rm,
        order_manager=om,
        duckdb_conn=duckdb_conn,
        config=EngineConfig(target_date=TARGET_DATE),
        monitoring_db=mdb,
    )


class TestSystemStability:
    """システム安定性: 複数サイクル実行してもクラッシュしないことを検証"""

    def test_multiple_polling_cycles_no_crash(self, orders_conn, duckdb_conn):
        """3サイクル連続して _process_signals() が例外なく完走する"""
        _sig(duckdb_conn, "1234")
        _tgt(duckdb_conn, "1234")
        engine = _engine(orders_conn, duckdb_conn, fill_mode="instant")
        for _ in range(3):
            engine._process_signals()  # AssertionError / Exception が出ないこと

    def test_trade_logs_written_per_cycle(self, orders_conn, duckdb_conn, mon_conn):
        """シグナル処理後に monitoring_db.trade_logs へ 'Sent' イベントが記録される"""
        _sig(duckdb_conn, "1234")
        _tgt(duckdb_conn, "1234")
        engine = _engine(orders_conn, duckdb_conn, fill_mode="instant", mon_conn=mon_conn)
        engine._process_signals()
        count = mon_conn.execute(
            "SELECT COUNT(*) FROM trade_logs WHERE event_type = 'Sent'"
        ).fetchone()[0]
        assert count == 1


class TestOrderSuccessRate:
    """注文成功率: 各 fill_mode で期待する注文状態になることを検証"""

    def test_instant_mode_order_accepted(self, orders_conn, duckdb_conn):
        """fill_mode=instant → _process_signals() 後は OrderAccepted 状態になる
        (sync_order() を呼ぶと Filled になるが、_process_signals() 単体では OrderAccepted)"""
        _sig(duckdb_conn, "1234")
        _tgt(duckdb_conn, "1234", qty=100)
        engine = _engine(orders_conn, duckdb_conn, fill_mode="instant")
        engine._process_signals()
        orders = engine._repo.list_active()
        assert len(orders) == 1
        assert orders[0].state == OrderState.OrderAccepted

    def test_reject_mode_no_active_orders(self, orders_conn, duckdb_conn):
        """fill_mode=reject → Rejected 注文は list_active() に含まれない"""
        _sig(duckdb_conn, "1234")
        _tgt(duckdb_conn, "1234", qty=100)
        engine = _engine(orders_conn, duckdb_conn, fill_mode="reject")
        engine._process_signals()
        assert len(engine._repo.list_active()) == 0

    def test_partial_mode_order_accepted(self, orders_conn, duckdb_conn):
        """fill_mode=partial → _process_signals() 後は OrderAccepted 状態になる
        (broker 側で partial fill されているが、sync_order() を呼ぶまで DB の filled_qty は 0)"""
        _sig(duckdb_conn, "1234")
        _tgt(duckdb_conn, "1234", qty=100)
        engine = _engine(orders_conn, duckdb_conn, fill_mode="partial")
        engine._process_signals()
        orders = engine._repo.list_active()
        assert len(orders) == 1
        assert orders[0].state == OrderState.OrderAccepted

    def test_never_mode_order_stays_sent(self, orders_conn, duckdb_conn):
        """fill_mode=never → 注文が OrderSent 状態のまま残る"""
        _sig(duckdb_conn, "1234")
        _tgt(duckdb_conn, "1234", qty=100)
        engine = _engine(orders_conn, duckdb_conn, fill_mode="never")
        engine._process_signals()
        orders = engine._repo.list_active()
        assert len(orders) == 1
        assert orders[0].state == OrderState.OrderSent


class TestSignalAccuracy:
    """シグナル精度: BUY/SELL シグナルが正しく注文に変換されることを検証"""

    def test_buy_signal_creates_buy_order(self, orders_conn, duckdb_conn):
        """BUY シグナル → side='buy' の注文が作成される"""
        _sig(duckdb_conn, "1234", side="buy")
        _tgt(duckdb_conn, "1234")
        engine = _engine(orders_conn, duckdb_conn, fill_mode="instant")
        engine._process_signals()
        orders = engine._repo.list_active()
        assert len(orders) == 1
        assert orders[0].side == "buy"

    def test_sell_signal_creates_sell_order(self, orders_conn, duckdb_conn):
        """SELL シグナル → side='sell' の注文が作成される"""
        _sig(duckdb_conn, "1234", side="sell")
        _tgt(duckdb_conn, "1234")
        engine = _engine(orders_conn, duckdb_conn, fill_mode="instant")
        engine._process_signals()
        orders = engine._repo.list_active()
        assert len(orders) == 1
        assert orders[0].side == "sell"

    def test_risk_rejection_blocks_order_creation(self, orders_conn, duckdb_conn):
        """余力不足（cash=0.0）→ リスクゲートが BUY を拒否し注文レコードが作られない"""
        _sig(duckdb_conn, "1234", side="buy")
        _tgt(duckdb_conn, "1234")
        engine = _engine(orders_conn, duckdb_conn, cash=0.0)
        engine._process_signals()
        orders = engine._repo.list_active()
        assert orders == []


class TestApiLatency:
    """API レイテンシ: 発注の遅延が許容範囲内に収まることを検証"""

    def test_send_order_latency_recorded(self, orders_conn, duckdb_conn, mon_conn):
        """_process_signals() 後に trade_logs の Sent イベントに latency_ms が記録される"""
        _sig(duckdb_conn, "1234")
        _tgt(duckdb_conn, "1234")
        engine = _engine(orders_conn, duckdb_conn, fill_mode="instant", mon_conn=mon_conn)
        engine._process_signals()
        row = mon_conn.execute(
            "SELECT latency_ms FROM trade_logs WHERE event_type = 'Sent'"
        ).fetchone()
        assert row is not None
        assert row[0] is not None

    def test_send_order_latency_under_500ms(self):
        """MockBrokerClient.send_order() の呼び出しが 500ms 未満で完了する"""
        from kabusys.execution.broker_api import OrderRequest

        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        req = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
        start = time.perf_counter()
        broker.send_order(req)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500
