# src/kabusys/execution/execution_engine.py
"""ExecutionEngine — Signal Queue Pull 型発注エンジン。

シグナル処理（8:50-9:10）+ WebSocket push ドレインループ（9:10-15:30）。
"""
from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from datetime import date, time

import duckdb

from kabusys.execution.broker_api import BrokerAPIProtocol
# DuplicateOrderError は _process_signals() (Task 7) で使用
from kabusys.execution.order_manager import DuplicateOrderError, OrderManager
from kabusys.execution.order_repository import OrderRepository
from kabusys.execution.risk_manager import RiskManager

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    target_date: date
    signal_send_start: time = time(8, 50)  # 発注開始時刻
    signal_send_end: time = time(9, 10)    # 発注締切時刻
    market_close: time = time(15, 30)      # セッション終了時刻


class ExecutionEngine:
    def __init__(
        self,
        broker: BrokerAPIProtocol,
        repo: OrderRepository,
        risk_manager: RiskManager,
        order_manager: OrderManager,
        duckdb_conn: duckdb.DuckDBPyConnection,
        config: EngineConfig,
    ) -> None:
        self._broker = broker
        self._repo = repo
        self._risk_manager = risk_manager
        self._order_manager = order_manager
        self._duckdb_conn = duckdb_conn
        self._config = config
        self._stop_event = threading.Event()
        self._push_queue: queue.Queue[dict] = queue.Queue()

    def _read_signals(self) -> list[dict]:
        """DuckDB から今日のシグナルを portfolio_targets と JOIN して返す。"""
        rows = self._duckdb_conn.execute(
            """
            SELECT s.code, s.side, pt.target_size AS qty, pt.entry_price AS price
            FROM signals s
            JOIN portfolio_targets pt ON s.date = pt.date AND s.code = pt.code
            WHERE s.date = ?
            ORDER BY s.signal_rank ASC NULLS LAST
            """,
            [self._config.target_date],
        ).fetchall()
        return [
            {"code": r[0], "side": r[1], "qty": int(r[2]), "price": float(r[3])}
            for r in rows
        ]
