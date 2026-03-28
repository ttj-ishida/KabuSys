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

    def _process_signals(self) -> None:
        """今日のシグナルを読み込み、Gate 1/2 を通して発注する。"""
        from kabusys.execution.broker_api import OrderRequest

        signals = self._read_signals()
        logger.info("シグナル処理開始: %d 件", len(signals))

        for sig in signals:
            if self._stop_event.is_set():
                break

            code: str = sig["code"]
            side: str = sig["side"]
            qty: int = sig["qty"]
            price: float = sig["price"]
            signal_id = f"{self._config.target_date.isoformat()}_{code}_{side}"
            order_value = price * qty

            # Gate 1: シグナルレベル検査
            g1 = self._risk_manager.check_signal(signal_id, code, order_value)
            if not g1.passed:
                logger.info("Gate 1 NG - signal_id=%s: %s", signal_id, g1.reason)
                continue

            # Gate 2: エグゼキューションレベル検査（レート制限: リトライ最大3回）
            g2_passed = False
            for attempt in range(3):
                g2 = self._risk_manager.check_execution()
                if g2.passed:
                    g2_passed = True
                    break
                if "サーキットブレーカー" in g2.reason:
                    logger.warning("Gate 2 CB OPEN: シグナルループ停止 - %s", g2.reason)
                    return  # ドレインループは継続するため return のみ
                logger.debug("Gate 2 rate limit (attempt %d/3), waiting 0.2s", attempt + 1)
                self._stop_event.wait(timeout=0.2)

            if not g2_passed:
                logger.info("Gate 2 NG - signal_id=%s: %s", signal_id, g2.reason)
                continue

            # 発注
            try:
                order_type = "market" if price == 0.0 else "limit"
                record = self._order_manager.create_order(
                    signal_id,
                    OrderRequest(code=code, side=side, qty=qty, order_type=order_type, price=price),
                )
            except DuplicateOrderError:
                logger.info("DuplicateOrderError - skip: signal_id=%s", signal_id)
                continue

            try:
                self._order_manager.send_order(record.client_order_id)
                self._risk_manager.record_api_success()
                logger.info("発注成功: signal_id=%s, client_order_id=%s", signal_id, record.client_order_id)
            except Exception as exc:
                self._risk_manager.record_api_error()
                logger.error("発注失敗: signal_id=%s: %s", signal_id, exc)

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
