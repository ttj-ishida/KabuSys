# src/kabusys/run_execution.py
"""run_execution.py — ExecutionEngine 起動スクリプト。

KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、
data/paper_trading.db に記録する（本番 DB と完全分離）。
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date

import duckdb

from kabusys.config import Settings
from kabusys.execution.broker_factory import BrokerClientFactory
from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_repository import OrderRepository
from kabusys.execution.reconciler import Reconciler
from kabusys.execution.risk_manager import RiskConfig, RiskManager
from kabusys.monitoring.monitoring_db import init_monitoring_db
from kabusys.utils.process_priority import set_process_priority

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # 1. プロセス優先度を High に設定（最初に実行）
    set_process_priority("high")

    settings = Settings()
    logger.info("起動環境: KABUSYS_ENV=%s", settings.env)

    # 2. DB 接続 — paper_trading は専用 DB で本番と分離
    sqlite_path = (
        settings.paper_sqlite_path if settings.is_paper else settings.sqlite_path
    )
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    init_monitoring_db(sqlite_conn)  # 監視テーブルが存在することを保証（冪等）
    duckdb_conn = duckdb.connect(str(settings.duckdb_path))

    try:
        # 3. ブローカークライアント
        broker = BrokerClientFactory.create(settings)

        # 4. 依存コンポーネント組み立て
        repo = OrderRepository(sqlite_conn)
        order_manager = OrderManager(broker, repo)
        risk_manager = RiskManager(
            broker=broker,
            repo=repo,
            config=RiskConfig(
                max_position_pct=0.20,
                max_utilization=0.80,
                rate_limit_per_sec=5,
                circuit_breaker_errors=10,
                circuit_breaker_window_sec=60,
                max_drawdown=0.20,
                initial_portfolio_value=broker.get_available_cash(),
            ),
        )
        reconciler = Reconciler(broker=broker, repo=repo, order_manager=order_manager)

        # 5. ExecutionEngine 起動
        engine = ExecutionEngine(
            broker=broker,
            repo=repo,
            risk_manager=risk_manager,
            order_manager=order_manager,
            duckdb_conn=duckdb_conn,
            config=EngineConfig(target_date=date.today()),
            reconciler=reconciler,
            pid_file=settings.pid_file_path,
        )
        engine.run_session()
    finally:
        sqlite_conn.close()
        duckdb_conn.close()


if __name__ == "__main__":
    main()
