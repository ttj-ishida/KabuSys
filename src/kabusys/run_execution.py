# src/kabusys/run_execution.py
"""run_execution.py — ExecutionEngine 起動スクリプト。

KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、
data/paper_trading.db に記録する（本番 DB と完全分離）。
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from datetime import date, datetime, time, timezone
from pathlib import Path

import duckdb
import yaml

from kabusys.config import Settings
from kabusys.execution.broker_api import Position

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STOP_FLAG = _PROJECT_ROOT / "data" / "stop_requested.flag"
_EXECUTION_PID = _PROJECT_ROOT / "data" / "execution.pid"
_RISK_CONFIG = _PROJECT_ROOT / "config" / "risk_config.yaml"
from kabusys.execution.broker_factory import BrokerClientFactory  # noqa: E402
from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine  # noqa: E402
from kabusys.execution.order_manager import OrderManager  # noqa: E402
from kabusys.execution.order_repository import (  # noqa: E402
    OrderRepository,
    init_position_entries_db,
)
from kabusys.execution.reconciler import Reconciler  # noqa: E402
from kabusys.execution.risk_manager import RiskConfig, RiskManager  # noqa: E402
from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db  # noqa: E402
from kabusys.operations.execution_startup_report import (  # noqa: E402
    build_report,
    format_cli_summary,
    save_report,
)
from kabusys.operations.line_reports import format_morning_message  # noqa: E402
from kabusys.operations.notifier import build_notifier  # noqa: E402
from kabusys.operations.process_registry import register_process, update_process  # noqa: E402
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging  # noqa: E402
from kabusys.utils.process_priority import set_process_priority  # noqa: E402

logger = logging.getLogger(__name__)


def _env_time(name: str, default: time) -> time:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return time.fromisoformat(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be HH:MM or HH:MM:SS, got {raw!r}") from exc


def _count_pending_signals(conn: duckdb.DuckDBPyConnection, target_date: date) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM signal_queue WHERE date = ? AND status = 'pending'",
        [target_date],
    ).fetchone()
    return int(row[0]) if row else 0


def _load_risk_config(path: Path, initial_portfolio_value: float) -> RiskConfig:
    if not path.exists():
        logger.error(
            "リスク設定ファイルが見つかりません: %s"
            " → git checkout config/risk_config.yaml で復元してください",
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
        raise KeyError(f"risk_config.yaml にトップレベルキー 'risk' がありません: {path}") from exc

    def _get(key: str) -> object:
        try:
            return r[key]
        except KeyError as exc:
            raise KeyError(f"risk_config.yaml に 'risk.{key}' がありません: {path}") from exc

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


def _restore_paper_state(
    sqlite_path: Path,
    initial_cash: float,
) -> tuple[float, list[Position]]:
    """paper_trading.db の約定履歴からペーパートレードの残高・ポジションを復元する。

    DB が存在しない場合や読み込みに失敗した場合は (initial_cash, []) を返す。
    本システムは現物取引のみ（ショート非対応）のため net_qty < 0 のコードはスキップする。
    """
    import contextlib

    if not sqlite_path.exists():
        logger.info(
            "paper_trading.db が存在しないため初期資金 %.0f 円で起動します。",
            initial_cash,
        )
        return initial_cash, []

    try:
        with contextlib.closing(sqlite3.connect(str(sqlite_path))) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT side, code, filled_qty, avg_fill_price FROM orders"
                " WHERE filled_qty > 0 AND avg_fill_price IS NOT NULL"
            ).fetchall()
    except Exception:
        logger.warning(
            "paper_trading.db からの状態復元に失敗しました。初期資金で起動します。",
            exc_info=True,
        )
        return initial_cash, []

    # code → [buy_qty, buy_cost, sell_qty, sell_proceeds]
    data: dict[str, list[float]] = {}
    for row in rows:
        side = (row["side"] or "").lower()
        if side not in ("buy", "sell"):
            logger.warning(
                "orders テーブルに未知の side 値があります。スキップします: side=%r code=%s",
                row["side"],
                row["code"],
            )
            continue
        code = row["code"]
        filled_qty = int(row["filled_qty"])
        avg_price = float(row["avg_fill_price"])
        if code not in data:
            data[code] = [0.0, 0.0, 0.0, 0.0]
        if side == "buy":
            data[code][0] += filled_qty
            data[code][1] += filled_qty * avg_price
        else:
            data[code][2] += filled_qty
            data[code][3] += filled_qty * avg_price

    # net_cash は買いコストを差し引き・売り収入を加算する。
    # DB の不整合（例: 売り超過）により負値になり得るが MockBrokerClient 側で許容する。
    net_cash = initial_cash
    positions: list[Position] = []
    for code, (buy_qty, buy_cost, sell_qty, sell_proceeds) in data.items():
        net_cash -= buy_cost
        net_cash += sell_proceeds
        net_qty = int(buy_qty) - int(sell_qty)
        if net_qty < 0:
            # 現物取引のみ対応のためショートポジションは想定外。データ不整合として警告する。
            logger.warning(
                "ショートポジションが検出されました（非対応）。スキップします: code=%s net_qty=%d",
                code,
                net_qty,
            )
        elif net_qty > 0:
            avg_price = buy_cost / buy_qty if buy_qty > 0 else 0.0
            positions.append(Position(code=code, qty=net_qty, avg_price=avg_price))

    logger.info(
        "ペーパートレード状態復元: 残高 %.0f 円 / ポジション %d 銘柄",
        net_cash,
        len(positions),
    )
    return net_cash, positions


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


_APP_NAME = "execution"
_JOB_NAME = "execution_job"


def main() -> None:
    _run_log = setup_logging(app_name=_APP_NAME, capture_stdio=True)
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    run_id: int | None = None
    _exec_status = "failed"
    try:
        run_id = register_process(_JOB_NAME, log_file=str(_run_log) if _run_log else None)
    except Exception:
        logger.warning("process_registry 登録に失敗しました", exc_info=True)
    # 1. プロセス優先度を High に設定（最初に実行）
    set_process_priority("high")

    settings = Settings()
    logger.info("起動環境: KABUSYS_ENV=%s", settings.env)

    # 2. DB 接続 — paper_trading は専用 DB で本番と分離
    sqlite_path = settings.paper_sqlite_path if settings.is_paper else settings.sqlite_path
    sqlite_conn = sqlite3.connect(str(sqlite_path), timeout=30.0)
    init_monitoring_db(sqlite_conn)  # 監視テーブルが存在することを保証（冪等）
    init_position_entries_db(sqlite_conn)  # position_entries テーブルが存在することを保証（冪等）
    duckdb_conn = duckdb.connect(str(settings.duckdb_path), read_only=True)

    try:
        # 3. ブローカークライアント（paper mode は前回状態を復元）
        # sandbox モードでは restored_cash → PaperSandboxBroker.paper_cash に使用。
        # restored_positions は sandbox 分岐では利用しない（ポジションは検証環境 API から取得）。
        restored_cash: float | None = None
        restored_positions: list[Position] | None = None
        if settings.is_paper:
            restored_cash, restored_positions = _restore_paper_state(
                settings.paper_sqlite_path, settings.paper_trading_initial_cash
            )
        broker = BrokerClientFactory.create(
            settings,
            available_cash=restored_cash,
            initial_positions=restored_positions,
        )

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
            config=_load_risk_config(_RISK_CONFIG, initial_portfolio_value=total_assets),
        )
        reconciler = Reconciler(broker=broker, repo=repo, order_manager=order_manager)

        # 起動時リコンシリエーション + Execution Startup Summary 生成
        today = date.today()
        reconcile_result = reconciler.run()
        _report = None
        try:
            _report = build_report(reconcile_result=reconcile_result, startup_date=today)
            print(format_cli_summary(_report))
            save_report(_report)
        except Exception:
            logger.warning(
                "Execution Startup Summary の生成に失敗しました（起動を続行します）",
                exc_info=True,
            )

        # 朝の LINE 通知（失敗しても起動を継続する）
        try:
            notifier = build_notifier(settings)
            pending_count = _count_pending_signals(duckdb_conn, today)
            status = _report.status if _report is not None else "UNKNOWN"
            orders_no_status = _report.orders_no_status if _report is not None else 0
            msg = format_morning_message(
                status=status,
                orders_no_status=orders_no_status,
                pending_count=pending_count,
                report_date=today.isoformat(),
            )
            notifier.send(msg)
        except Exception:
            logger.warning("朝の LINE 通知に失敗しました（起動を続行します）", exc_info=True)

        # 5. ExecutionEngine 起動（reconciliation は上で完了済みのため reconciler=None）
        monitoring_db = MonitoringDB(sqlite_conn)
        engine = ExecutionEngine(
            broker=broker,
            repo=repo,
            risk_manager=risk_manager,
            order_manager=order_manager,
            duckdb_conn=duckdb_conn,
            sqlite_conn=sqlite_conn,
            config=EngineConfig(
                target_date=today,
                signal_send_start=_env_time("KABUSYS_SIGNAL_SEND_START", time(8, 50)),
                signal_send_end=_env_time("KABUSYS_SIGNAL_SEND_END", time(9, 10)),
                market_close=_env_time("KABUSYS_MARKET_CLOSE", time(15, 30)),
            ),
            reconciler=None,
            pid_file=_EXECUTION_PID,
            monitoring_db=monitoring_db,
        )
        # 停止フラグが既に立っている場合は起動せず終了
        if _STOP_FLAG.exists():
            logger.info("停止フラグを検知。エンジンを起動しません。")
            _exec_status = "success"
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
        log_run_end(_APP_NAME, status="success", started_at=started_at)
        _exec_status = "success"
    except Exception:
        log_run_end(_APP_NAME, status="failed", started_at=started_at)
        raise
    finally:
        if run_id is not None:
            try:
                update_process(run_id, status=_exec_status)
            except Exception:
                logger.warning("process_registry 更新に失敗しました", exc_info=True)
        sqlite_conn.close()
        duckdb_conn.close()


if __name__ == "__main__":
    main()
