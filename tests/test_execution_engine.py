# tests/test_execution_engine.py
"""ExecutionEngine 統合テスト（Issue #30 / #34）"""
# NOTE: 以下は Task 7/8 で追加するテストクラス用にプリステージ済み
import queue
import sqlite3
import threading
from datetime import date, time
from unittest.mock import MagicMock

import duckdb
import pytest

from kabusys.execution.broker_api import OrderRequest, Position
from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.execution.risk_manager import RiskConfig, RiskManager


TARGET_DATE = date(2026, 3, 29)


@pytest.fixture
def sqlite_conn():
    c = sqlite3.connect(":memory:")
    init_orders_db(c)
    yield c
    c.close()


@pytest.fixture
def duckdb_conn():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE signals (
            date DATE, code VARCHAR, side VARCHAR,
            score FLOAT, signal_rank INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE portfolio_targets (
            date DATE, code VARCHAR,
            target_size INTEGER, entry_price FLOAT
        )
    """)
    yield conn
    conn.close()


def _make_engine(broker, sqlite_conn, duckdb_conn, *, config=None) -> ExecutionEngine:
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
    )


def _insert_signal(conn, code: str, side: str = "buy", score: float = 0.8):
    conn.execute(
        "INSERT INTO signals VALUES (?, ?, ?, ?, ?)",
        [TARGET_DATE, code, side, score, 1],
    )


def _insert_target(conn, code: str, qty: int = 100, price: float = 1500.0):
    conn.execute(
        "INSERT INTO portfolio_targets VALUES (?, ?, ?, ?)",
        [TARGET_DATE, code, qty, price],
    )


class TestReadSignals:

    def test_reads_signals_joined_with_portfolio_targets(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        signals = engine._read_signals()
        assert len(signals) == 1
        assert signals[0]["code"] == "1234"
        assert signals[0]["side"] == "buy"
        assert signals[0]["qty"] == 100
        assert signals[0]["price"] == 1500.0

    def test_excludes_signals_without_portfolio_targets(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        # portfolio_targets なし → JOIN で除外される
        broker = MockBrokerClient(available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        signals = engine._read_signals()
        assert len(signals) == 0
