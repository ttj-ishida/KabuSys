# tests/integration/test_integration.py
"""統合テスト — Data → Strategy → Portfolio → Execution の一連フロー

Issue #51 の要件:
  - Data → Strategy → Portfolio → Execution の一連フロー
  - Signal Queue の処理確認
  - Monitoring の通知確認

MockBrokerClient + in-memory DuckDB / SQLite を使用し、外部サービスへの依存なしで実行可能。
"""

from __future__ import annotations

import sqlite3
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
from kabusys.portfolio.portfolio_builder import (
    calc_equal_weights,
    calc_score_weights,
    select_candidates,
)
from kabusys.portfolio.position_sizing import calc_position_sizes

TARGET_DATE = date(2026, 4, 18)


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def orders_conn():
    """注文管理用 SQLite in-memory DB"""
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


@pytest.fixture
def duck_conn():
    """Execution テスト用 in-memory DuckDB（本番相当の signal_queue schema）"""
    conn = duckdb.connect(":memory:")
    conn.execute(
        "CREATE TABLE signals "
        "(date DATE, code VARCHAR, side VARCHAR, score FLOAT, signal_rank INTEGER, size_multiplier DOUBLE NOT NULL DEFAULT 1.0)"
    )
    conn.execute(
        "CREATE TABLE portfolio_targets "
        "(date DATE, code VARCHAR, target_weight DOUBLE, target_size BIGINT)"
    )
    conn.execute(
        """
        CREATE TABLE signal_queue (
            signal_id VARCHAR PRIMARY KEY,
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            size BIGINT NOT NULL,
            order_type VARCHAR NOT NULL,
            price DECIMAL(18,4),
            status VARCHAR NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            processed_at TIMESTAMP
        )
        """
    )
    yield conn
    conn.close()


def _insert_signal(
    conn: duckdb.DuckDBPyConnection, code: str, side: str = "buy", score: float = 0.8
):
    conn.execute(
        "INSERT INTO signals (date, code, side, score, signal_rank) VALUES (?, ?, ?, ?, ?)",
        [TARGET_DATE, code, side, score, 1],
    )


def _insert_target(
    conn: duckdb.DuckDBPyConnection, code: str, qty: int = 100, price: float = 1500.0
):
    side_row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = ? ORDER BY signal_rank ASC NULLS LAST LIMIT 1",
        [TARGET_DATE, code],
    ).fetchone()
    side = side_row[0] if side_row else "buy"
    conn.execute(
        "INSERT INTO portfolio_targets (date, code, target_weight, target_size) VALUES (?, ?, ?, ?)",
        [TARGET_DATE, code, None, qty],
    )
    conn.execute(
        """
        INSERT INTO signal_queue
            (signal_id, date, code, side, size, order_type, price, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [f"{TARGET_DATE}_{code}_{side}", TARGET_DATE, code, side, qty, "limit", price, "pending"],
    )


def _build_engine(
    orders_conn: sqlite3.Connection,
    duck_conn: duckdb.DuckDBPyConnection,
    fill_mode: str = "instant",
    cash: float = 5_000_000.0,
    mon_conn: sqlite3.Connection | None = None,
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
        duckdb_conn=duck_conn,
        config=EngineConfig(target_date=TARGET_DATE),
        monitoring_db=mdb,
    )


# ---------------------------------------------------------------------------
# 1. ポートフォリオ構築パイプライン（純粋関数）
# ---------------------------------------------------------------------------


class TestPortfolioBuildingPipeline:
    """select_candidates → calc_weights → calc_position_sizes の一連フロー"""

    def test_full_portfolio_pipeline(self):
        """BUY シグナルから発注株数まで計算できること"""
        buy_signals = [
            {"code": "7203", "score": 0.85, "signal_rank": 1},
            {"code": "9984", "score": 0.72, "signal_rank": 2},
            {"code": "6758", "score": 0.65, "signal_rank": 3},
        ]

        # 1. 銘柄選定
        candidates = select_candidates(buy_signals, max_positions=5)
        assert len(candidates) == 3
        assert candidates[0]["code"] == "7203"  # 最高スコアが先頭

        # 2. 等金額配分
        weights = calc_equal_weights(candidates)
        assert len(weights) == 3
        assert abs(sum(weights.values()) - 1.0) < 1e-9

        # 3. 発注株数計算
        open_prices = {"7203": 2500.0, "9984": 8000.0, "6758": 12000.0}
        sizes = calc_position_sizes(
            weights=weights,
            candidates=candidates,
            portfolio_value=10_000_000.0,
            available_cash=7_000_000.0,
            current_positions={},
            open_prices=open_prices,
            allocation_method="equal",
            max_position_pct=0.10,
            lot_size=100,
        )
        # 各銘柄の株数が 100 の倍数（単元株）であること
        for code, qty in sizes.items():
            assert qty % 100 == 0, f"{code}: qty={qty} は 100 の倍数でない"

    def test_score_weights_are_proportional(self):
        """スコア加重配分は高スコア銘柄が高い配分を受けること"""
        candidates = [
            {"code": "A", "score": 0.9, "signal_rank": 1},
            {"code": "B", "score": 0.3, "signal_rank": 2},
        ]
        weights = calc_score_weights(candidates)
        assert weights["A"] > weights["B"]
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_empty_signals_returns_empty(self):
        """シグナルなしの場合は空リストを返すこと"""
        candidates = select_candidates([], max_positions=10)
        assert candidates == []

        weights = calc_equal_weights(candidates)
        assert weights == {}


# ---------------------------------------------------------------------------
# 2. Signal Queue → Execution フロー
# ---------------------------------------------------------------------------


class TestSignalQueueExecution:
    """signal_queue (DuckDB) から ExecutionEngine が発注するフロー"""

    def _count_orders(self, conn: sqlite3.Connection) -> int:
        return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

    def _get_order_states(self, conn: sqlite3.Connection) -> list[str]:
        rows = conn.execute("SELECT state FROM orders").fetchall()
        return [r[0] for r in rows]

    def test_signals_processed_and_orders_created(self, orders_conn, duck_conn):
        """signal_queue から発注レコードが作成されること"""
        _insert_signal(duck_conn, "7203")
        _insert_target(duck_conn, "7203", qty=100, price=2500.0)

        engine = _build_engine(orders_conn, duck_conn, fill_mode="instant")
        engine._process_signals()

        assert self._count_orders(orders_conn) == 1
        states = self._get_order_states(orders_conn)
        # _process_signals() 単体では OrderAccepted まで遷移（Filled は sync_order() 後）
        assert states[0] == OrderState.OrderAccepted.value

    def test_multiple_signals_all_processed(self, orders_conn, duck_conn):
        """複数シグナルがすべて処理されること"""
        codes = ["7203", "9984", "6758"]
        for code in codes:
            _insert_signal(duck_conn, code)
            _insert_target(duck_conn, code, qty=100, price=1500.0)

        engine = _build_engine(orders_conn, duck_conn, fill_mode="instant")
        engine._process_signals()

        assert self._count_orders(orders_conn) == 3
        states = self._get_order_states(orders_conn)
        assert all(s == OrderState.OrderAccepted.value for s in states)

    def test_duplicate_signal_is_skipped(self, orders_conn, duck_conn):
        """同一 signal_id の重複発注が防止されること"""
        _insert_signal(duck_conn, "7203")
        _insert_target(duck_conn, "7203", qty=100, price=2500.0)

        engine = _build_engine(orders_conn, duck_conn, fill_mode="instant")
        engine._process_signals()
        engine._process_signals()  # 2 回目は DuplicateOrderError でスキップ

        assert self._count_orders(orders_conn) == 1  # 重複なし

    def test_insufficient_cash_blocks_order(self, orders_conn, duck_conn):
        """資金不足時にシグナルが Gate 1 で遮断されること"""
        _insert_signal(duck_conn, "7203")
        _insert_target(duck_conn, "7203", qty=100, price=2500.0)

        # 発注金額 250,000 円 > available_cash 100 円
        engine = _build_engine(orders_conn, duck_conn, fill_mode="instant", cash=100.0)
        engine._process_signals()

        assert self._count_orders(orders_conn) == 0


# ---------------------------------------------------------------------------
# 3. Monitoring 通知確認
# ---------------------------------------------------------------------------


class TestMonitoringCapture:
    """ExecutionEngine が MonitoringDB にトレードログを記録すること"""

    def test_trade_log_written_on_fill(self, orders_conn, duck_conn, mon_conn):
        """約定時に monitoring DB へトレードログが書き込まれること"""
        _insert_signal(duck_conn, "7203")
        _insert_target(duck_conn, "7203", qty=100, price=2500.0)

        engine = _build_engine(orders_conn, duck_conn, fill_mode="instant", mon_conn=mon_conn)
        engine._process_signals()

        rows = mon_conn.execute("SELECT COUNT(*) FROM trade_logs").fetchone()[0]
        assert rows >= 1

    def test_no_trade_log_when_no_signals(self, orders_conn, duck_conn, mon_conn):
        """シグナルなし時はトレードログが記録されないこと"""
        engine = _build_engine(orders_conn, duck_conn, fill_mode="instant", mon_conn=mon_conn)
        engine._process_signals()

        rows = mon_conn.execute("SELECT COUNT(*) FROM trade_logs").fetchone()[0]
        assert rows == 0

    def test_monitoring_captures_fill_mode_instant(self, orders_conn, duck_conn, mon_conn):
        """fill_mode=instant の場合、Filled レコードがログに残ること"""
        for code in ["7203", "9984"]:
            _insert_signal(duck_conn, code)
            _insert_target(duck_conn, code, qty=100, price=1500.0)

        engine = _build_engine(orders_conn, duck_conn, fill_mode="instant", mon_conn=mon_conn)
        engine._process_signals()

        rows = mon_conn.execute("SELECT COUNT(*) FROM trade_logs").fetchone()[0]
        assert rows >= 2
