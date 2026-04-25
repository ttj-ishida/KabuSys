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
    if not path.exists():
        logger.error(
            "リスク設定ファイルが見つかりません: %s"
            " → config/risk_config.yaml を作成してください（python -m kabusys.config_setup を参照）",
            path,
        )
        raise FileNotFoundError(f"リスク設定ファイルが見つかりません: {path}")
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"risk_config.yaml のパース失敗: {path}") from exc

    try:
        r = data["risk"]
    except (TypeError, KeyError) as exc:
        raise KeyError(
            f"risk_config.yaml にトップレベルキー 'risk' がありません: {path}"
        ) from exc

    def _get(key: str) -> object:
        try:
            return r[key]
        except KeyError as exc:
            raise KeyError(
                f"risk_config.yaml に 'risk.{key}' がありません: {path}"
            ) from exc

    max_position_pct = float(_get("max_position_pct"))
    max_utilization = float(_get("max_utilization"))
    rate_limit_per_sec = int(_get("rate_limit_per_sec"))
    circuit_breaker_errors = int(_get("circuit_breaker_errors"))
    circuit_breaker_window_sec = int(_get("circuit_breaker_window_sec"))
    max_drawdown = float(_get("max_drawdown"))

    for name, val in (
        ("max_position_pct", max_position_pct),
        ("max_utilization", max_utilization),
        ("max_drawdown", max_drawdown),
    ):
        if not (0 < val <= 1):
            raise ValueError(
                f"risk_config.yaml: {name} は (0, 1] の範囲で設定してください（現在値: {val}）: {path}"
            )
    if max_position_pct > max_utilization:
        raise ValueError(
            f"risk_config.yaml: max_position_pct({max_position_pct}) は"
            f" max_utilization({max_utilization}) 以下にしてください: {path}"
        )
    for name, val in (
        ("rate_limit_per_sec", rate_limit_per_sec),
        ("circuit_breaker_errors", circuit_breaker_errors),
        ("circuit_breaker_window_sec", circuit_breaker_window_sec),
    ):
        if val < 1:
            raise ValueError(
                f"risk_config.yaml: {name} は 1 以上で設定してください（現在値: {val}）: {path}"
            )

    config = RiskConfig(
        max_position_pct=max_position_pct,
        max_utilization=max_utilization,
        rate_limit_per_sec=rate_limit_per_sec,
        circuit_breaker_errors=circuit_breaker_errors,
        circuit_breaker_window_sec=circuit_breaker_window_sec,
        max_drawdown=max_drawdown,
        initial_portfolio_value=initial_portfolio_value,
    )
    logger.info(
        "RiskConfig 読み込み完了: max_position_pct=%.0f%% max_utilization=%.0f%%"
        " max_drawdown=%.0f%% rate_limit=%d/s CB_errors=%d CB_window=%ds",
        max_position_pct * 100,
        max_utilization * 100,
        max_drawdown * 100,
        rate_limit_per_sec,
        circuit_breaker_errors,
        circuit_breaker_window_sec,
    )
    return config


def _pos_value(p: object) -> float:
    price = (
        p.current_price  # type: ignore[attr-defined]
        if (p.current_price is not None and p.current_price > 0)  # type: ignore[attr-defined]
        else p.avg_price  # type: ignore[attr-defined]
    )
    if price is None or price <= 0:
        logger.warning(
            "ポジション評価額を 0 として扱います: code=%s current_price=%s avg_price=%s",
            getattr(p, "code", "?"),
            getattr(p, "current_price", None),
            getattr(p, "avg_price", None),
        )
        return 0.0
    return float(p.qty) * float(price)  # type: ignore[attr-defined]


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

        # 4. 起動時総資産を計算（現金 + 保有評価額）
        cash = broker.get_available_cash()
        positions = broker.get_positions()
        total_assets = cash + sum(_pos_value(p) for p in positions)
        logger.debug(
            "起動時総資産: %.0f 円（現金 %.0f 円 + ポジション %d 件）",
            total_assets,
            cash,
            len(positions),
        )

        # 5. 依存コンポーネント組み立て
        repo = OrderRepository(sqlite_conn)
        order_manager = OrderManager(broker, repo)
        risk_manager = RiskManager(
            broker=broker,
            repo=repo,
            config=_load_risk_config(
                _RISK_CONFIG, initial_portfolio_value=total_assets
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
