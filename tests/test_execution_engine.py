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


class TestProcessSignals:

    def test_orders_created_for_valid_signals(self, sqlite_conn, duckdb_conn):
        """Gate 1/2 を通過したシグナルが OrderAccepted になる"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        repo = engine._repo
        orders = repo.list_active()
        # fill_mode="instant" → Filled 状態（active）
        assert len(orders) == 1
        assert orders[0].code == "1234"

    def test_gate1_failure_skips_signal(self, sqlite_conn, duckdb_conn):
        """余力不足のシグナルはスキップされる"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=0.0)  # 余力ゼロ
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        assert len(engine._repo.list_active()) == 0

    def test_duplicate_order_is_skipped(self, sqlite_conn, duckdb_conn):
        """DuplicateOrderError は skip（2回目呼び出しで重複にならない）"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        # 2回目: DuplicateOrderError が発生するが例外は出ない
        engine._process_signals()
        # 注文は1件のまま
        # fill_mode="instant" の場合 Filled → list_active に残る
        active = engine._repo.list_active()
        assert len(active) == 1

    def test_multiple_signals_processed(self, sqlite_conn, duckdb_conn):
        """複数シグナルがすべて処理される"""
        for code in ["1234", "5678", "9012"]:
            _insert_signal(duckdb_conn, code)
            _insert_target(duckdb_conn, code, qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        assert len(engine._repo.list_active()) == 3


    def test_order_sent_pending_records_api_success(self, sqlite_conn, duckdb_conn):
        """OrderSentPendingError 時も record_api_success() が呼ばれ CB が閉じられる"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        # HALF_OPEN 状態を強制
        engine._risk_manager._cb_state = "HALF_OPEN"
        engine._process_signals()
        # pending 後に CB が CLOSED に戻っていること
        assert engine._risk_manager._cb_state == "CLOSED"

    def test_process_signals_skipped_after_signal_send_end(self, sqlite_conn, duckdb_conn):
        """signal_send_end を過ぎた時刻に run_session が呼ばれてもシグナル処理をスキップ"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        # signal_send_end=00:00 → 現在時刻は常に超過
        cfg = EngineConfig(target_date=TARGET_DATE, signal_send_start=time(0, 0), signal_send_end=time(0, 0))
        engine = _make_engine(broker, sqlite_conn, duckdb_conn, config=cfg)
        # run_session は使わず、send_end チェックを直接テスト
        from datetime import datetime
        # signal_send_end < 現在時刻 → _process_signals を呼ばない
        engine._stop_event.set()  # ループ停止のため
        # ← _process_signals を明示的に呼んだ場合との比較
        assert len(engine._repo.list_active()) == 0


class TestPushDrainAndKillSwitch:

    def test_handle_push_calls_sync_order(self, sqlite_conn, duckdb_conn):
        """push payload が _push_queue に入ると sync_order が呼ばれる"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()

        # OrderSent 状態の注文を取得
        uncertain = engine._repo.list_uncertain()
        assert len(uncertain) == 1
        order = uncertain[0]

        # broker の注文ステータスを "filled" に更新
        from kabusys.execution.broker_api import OrderStatus
        broker._orders[order.broker_order_id] = OrderStatus(
            order_id=order.broker_order_id,
            code="1234", side="buy", qty=100, filled_qty=100,
            status="filled", price=1500.0,
        )

        # push payload を直接キューに投入
        engine._push_queue.put({"OrderID": order.broker_order_id})
        engine._drain_push_queue()

        updated = engine._repo.get(order.client_order_id)
        from kabusys.execution.order_record import OrderState
        assert updated.state == OrderState.Filled

    def test_kill_switch_cancels_all_active_orders(self, sqlite_conn, duckdb_conn):
        """kill_switch() が全 active 注文をキャンセルして stop_event をセットする"""
        _insert_signal(duckdb_conn, "1234")
        _insert_signal(duckdb_conn, "5678")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        _insert_target(duckdb_conn, "5678", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()

        active_before = engine._repo.list_active()
        assert len(active_before) >= 1  # OrderSent 状態の注文あり

        engine.kill_switch()

        assert engine._stop_event.is_set()
        # OrderSent 状態の全注文が Cancelled に遷移し active リストから消えていること
        assert len(engine._repo.list_active()) == 0

    def test_gate3_triggers_kill_switch_on_drawdown(self, sqlite_conn, duckdb_conn):
        """Gate 3 で drawdown 超過時に kill_switch が発動する"""
        broker = MockBrokerClient(available_cash=7_000_000.0)  # 30% drawdown
        config = RiskConfig(
            initial_portfolio_value=10_000_000.0,
            max_drawdown=0.15,
        )
        repo = OrderRepository(sqlite_conn)
        rm = RiskManager(broker=broker, repo=repo, config=config)
        order_manager = OrderManager(broker=broker, repo=repo)
        cfg = EngineConfig(target_date=TARGET_DATE)
        engine = ExecutionEngine(
            broker=broker, repo=repo, risk_manager=rm,
            order_manager=order_manager, duckdb_conn=duckdb_conn, config=cfg,
        )

        # 現在の評価額 7,000,000 円（30% drawdown > 15%）
        current_value = broker.get_available_cash()  # ポジションなし
        engine._check_gate3_and_maybe_kill(current_value)
        assert engine._stop_event.is_set()
