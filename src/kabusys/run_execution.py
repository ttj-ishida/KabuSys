# src/kabusys/run_execution.py
"""run_execution.py — ExecutionEngine 起動スクリプト。

KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、
data/paper_trading.db に記録する（本番 DB と完全分離）。
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import date
from pathlib import Path

import duckdb
import yaml

from kabusys.config import Settings

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STOP_FLAG = _PROJECT_ROOT / "data" / "stop_requested.flag"
_EXECUTION_PID = _PROJECT_ROOT / "data" / "execution.pid"
_RISK_CONFIG = _PROJECT_ROOT / "config" / "risk_config.yaml"
from kabusys.execution.broker_factory import BrokerClientFactory  # noqa: E402
from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine  # noqa: E402
from kabusys.execution.order_manager import OrderManager  # noqa: E402
from kabusys.execution.order_repository import OrderRepository  # noqa: E402
from kabusys.execution.reconciler import Reconciler  # noqa: E402
from kabusys.execution.risk_manager import RiskConfig, RiskManager  # noqa: E402
from kabusys.monitoring.monitoring_db import init_monitoring_db  # noqa: E402
from kabusys.utils.logging_setup import setup_logging  # noqa: E402
from kabusys.utils.process_priority import set_process_priority  # noqa: E402

logger = logging.getLogger(__name__)


def _load_risk_config(path: Path, initial_portfolio_value: float) -> RiskConfig:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    r = data["risk"]
    return RiskConfig(
        max_position_pct=r["max_position_pct"],
        max_utilization=r["max_utilization"],
        rate_limit_per_sec=r["rate_limit_per_sec"],
        circuit_breaker_errors=r["circuit_breaker_errors"],
        circuit_breaker_window_sec=r["circuit_breaker_window_sec"],
        max_drawdown=r["max_drawdown"],
        initial_portfolio_value=initial_portfolio_value,
    )


def main() -> None:
    setup_logging(app_name="execution")
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
            pid_file=_EXECUTION_PID,
        )
        # 停止フラグが既に立っている場合は起動せず終了
        if _STOP_FLAG.exists():
            logger.info("停止フラグを検知。エンジンを起動しません。")
            return

        thread = threading.Thread(target=engine.run_session, daemon=True)
        thread.start()
        while thread.is_alive():
            if _STOP_FLAG.exists():
                logger.info("停止フラグを検知。エンジンを停止します。")
                engine.stop()
                break
            thread.join(timeout=1.0)
        thread.join(timeout=30.0)
    finally:
        sqlite_conn.close()
        duckdb_conn.close()


if __name__ == "__main__":
    main()
