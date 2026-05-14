# scripts/run_portfolio_construction.py
"""Night batch: ポートフォリオ構築 (portfolio_construction_job)。

Task Scheduler から 21:00 に起動される。
signals テーブルから当日の BUY シグナルを読み込み、
ポートフォリオ構築を行って signal_queue と portfolio_targets に書き込む。

環境変数:
    PORTFOLIO_VALUE: Live 時フォールバック用総資産前提値（円）。
                     通常はカブステーション余力 API / DuckDB 実績値から自動取得されるため設定不要。
                     デフォルト: 10,000,000
    PAPER_TRADING_INITIAL_CASH: Paper 時フォールバック用初期資金（円）。
                                通常は paper_trading.db の約定履歴から自動算出される。
                                デフォルト: 10,000,000
"""

from __future__ import annotations

import calendar
import contextlib
import logging
import sqlite3
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kabusys.config import Settings
from kabusys.operations.job_run_recorder import write_job_result
from kabusys.operations.line_reports import (
    format_evening_message,
    format_monthly_message,
    format_weekly_message,
)
from kabusys.operations.night_batch_report import JobRunResult
from kabusys.operations.notifier import build_notifier
from kabusys.operations.performance_collector import (
    collect_monthly_rows,
    collect_weekly_rows,
)
from kabusys.operations.performance_report import build_report
from kabusys.operations.process_registry import register_process, update_process
from kabusys.portfolio.portfolio_builder import (
    calc_score_weights,
    load_portfolio_config,
    select_candidates,
)
from kabusys.portfolio.position_sizing import calc_position_sizes
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

_run_log = setup_logging(app_name="portfolio_construction", capture_stdio=True)
logger = logging.getLogger(__name__)

_MAX_UTILIZATION = 0.70
_JOB_NAME = "portfolio_construction_job"
_APP_NAME = "portfolio_construction"


def _calc_live_portfolio_value(
    settings: Settings,
    duckdb_conn: duckdb.DuckDBPyConnection,
) -> tuple[float, float]:
    """Live モード用 (portfolio_value, available_cash) を算出する。

    portfolio_value: DuckDB portfolio_performance の直近 equity → PORTFOLIO_VALUE 環境変数
    available_cash:  カブステーション /wallet/cash API → portfolio_value × max_utilization
    """
    fallback_pv = settings.portfolio_value

    portfolio_value = fallback_pv
    try:
        row = duckdb_conn.execute(
            "SELECT equity FROM portfolio_performance WHERE env = 'live' ORDER BY date DESC LIMIT 1"
        ).fetchone()
        if row and row[0] is not None:
            portfolio_value = float(row[0])
            logger.info("portfolio_value: DuckDB 実績値=%.0f 円 (env=live)", portfolio_value)
        else:
            logger.info(
                "portfolio_performance に live データなし。PORTFOLIO_VALUE=%.0f 円を使用",
                fallback_pv,
            )
    except Exception:
        logger.warning(
            "DuckDB portfolio_performance 参照に失敗。フォールバックを使用", exc_info=True
        )

    available_cash = portfolio_value * _MAX_UTILIZATION
    try:
        from kabusys.execution.kabu_client import KabuStationClient

        client = KabuStationClient(
            api_password=settings.kabu_api_password,
            trade_password=settings.kabu_trade_password,
            base_url=settings.kabu_api_base_url,
        )
        cash = client.get_available_cash()
        available_cash = cash
        logger.info("available_cash: カブステーション API 余力=%.0f 円", available_cash)
    except Exception:
        logger.warning(
            "カブステーション余力 API 呼び出しに失敗。"
            "portfolio_value × max_utilization=%.0f 円を使用",
            available_cash,
            exc_info=True,
        )

    return portfolio_value, available_cash


def _calc_paper_portfolio_value(
    settings: Settings,
    duckdb_conn: duckdb.DuckDBPyConnection,
) -> tuple[float, float]:
    """Paper モード用 (portfolio_value, available_cash) を算出する。

    paper_trading.db の約定履歴から現金残高・保有ポジション時価を計算する。
    DB が存在しない・読み取り失敗時は PAPER_TRADING_INITIAL_CASH にフォールバックする。

    portfolio_value = 現金残高 + 保有ポジション時価
    available_cash  = 現金残高（マイナスの場合は 0 に補正）
    """
    initial_cash = settings.paper_trading_initial_cash
    sqlite_path = settings.paper_sqlite_path

    if not sqlite_path.exists():
        logger.info(
            "paper_trading.db が未存在。PAPER_TRADING_INITIAL_CASH=%.0f 円を使用", initial_cash
        )
        return initial_cash, initial_cash * _MAX_UTILIZATION

    try:
        with contextlib.closing(sqlite3.connect(str(sqlite_path))) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT side, code, filled_qty, avg_fill_price FROM orders"
                " WHERE filled_qty > 0 AND avg_fill_price IS NOT NULL"
            ).fetchall()
    except Exception:
        logger.warning(
            "paper_trading.db の読み込みに失敗。PAPER_TRADING_INITIAL_CASH=%.0f 円を使用",
            initial_cash,
            exc_info=True,
        )
        return initial_cash, initial_cash * _MAX_UTILIZATION

    data: dict[str, list[float]] = {}
    for row in rows:
        side = (row["side"] or "").lower()
        if side not in ("buy", "sell"):
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

    net_cash = initial_cash
    positions: dict[str, int] = {}
    for code, (buy_qty, buy_cost, sell_qty, sell_proceeds) in data.items():
        net_cash -= buy_cost
        net_cash += sell_proceeds
        net_qty = int(buy_qty) - int(sell_qty)
        if net_qty > 0:
            positions[code] = net_qty

    market_value = 0.0
    if positions:
        codes = list(positions.keys())
        code_params = ",".join(["?"] * len(codes))
        try:
            price_rows = duckdb_conn.execute(
                f"""
                SELECT p.code, p.close
                FROM prices_daily p
                INNER JOIN (
                    SELECT code, MAX(date) AS max_date
                    FROM prices_daily
                    WHERE code IN ({code_params})
                    GROUP BY code
                ) latest ON p.code = latest.code AND p.date = latest.max_date
                """,
                codes,
            ).fetchall()
            for pcode, price in price_rows:
                if price is not None and pcode in positions:
                    market_value += positions[pcode] * float(price)
        except Exception:
            logger.warning(
                "ポジション時価計算に失敗。現金のみで portfolio_value を算出します", exc_info=True
            )

    available_cash = max(net_cash, 0.0)
    portfolio_value = max(net_cash + market_value, 0.0)

    logger.info(
        "Paper portfolio_value 算出: 現金=%.0f 円, 時価=%.0f 円, 合計=%.0f 円",
        net_cash,
        market_value,
        portfolio_value,
    )
    return portfolio_value, available_cash


def _get_today_return(conn: duckdb.DuckDBPyConnection, target_date: date, env: str) -> float | None:
    row = conn.execute(
        "SELECT daily_return FROM portfolio_performance WHERE date = ? AND env = ? LIMIT 1",
        [target_date, env],
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return float(row[0])


def main() -> None:
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    run_id: int | None = None
    try:
        run_id = register_process(_JOB_NAME, log_file=str(_run_log) if _run_log else None)
    except Exception:
        logger.warning("process_registry 登録に失敗しました", exc_info=True)
    conn = None
    target_date = date.today()
    _failed = False
    _errors: list[str] = []
    _updated_rows: dict[str, int] = {}

    try:
        settings = Settings()
        conn = duckdb.connect(str(settings.duckdb_path))

        if settings.is_live:
            portfolio_value, available_cash = _calc_live_portfolio_value(settings, conn)
        elif settings.is_paper or settings.is_dev:
            portfolio_value, available_cash = _calc_paper_portfolio_value(settings, conn)
        else:
            portfolio_value = settings.portfolio_value
            available_cash = portfolio_value * _MAX_UTILIZATION
            logger.info(
                "portfolio_value: PORTFOLIO_VALUE=%.0f 円 (env=%s)", portfolio_value, settings.env
            )

        inserted = 0

        cur = conn.execute(
            "SELECT code, side, score, signal_rank FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        )
        rows = cur.fetchall()
        buy_signals = [dict(zip([d[0] for d in cur.description], row)) for row in rows]

        portfolio_cfg = load_portfolio_config()
        max_positions = portfolio_cfg["max_positions"]
        logger.info("最大保有銘柄数: %d", max_positions)

        if not buy_signals:
            logger.info("本日の BUY シグナルが 0 件です。signal_queue を更新しません。")
            _updated_rows["signal_queue"] = 0
        else:
            candidates = select_candidates(buy_signals, max_positions=max_positions)
            if not candidates:
                logger.info("銘柄選定結果が 0 件です。signal_queue を更新しません。")
                _updated_rows["signal_queue"] = 0
            else:
                weights = calc_score_weights(candidates)
                if not weights:
                    logger.info("重み計算結果が 0 件です。signal_queue を更新しません。")
                    _updated_rows["signal_queue"] = 0
                else:
                    codes = [c["code"] for c in candidates]
                    code_params = ",".join(["?"] * len(codes))
                    price_cur = conn.execute(
                        f"""
                        SELECT p.code, p.close
                        FROM prices_daily p
                        INNER JOIN (
                            SELECT code, MAX(date) AS max_date
                            FROM prices_daily
                            WHERE code IN ({code_params})
                            GROUP BY code
                        ) latest ON p.code = latest.code AND p.date = latest.max_date
                        """,
                        codes,
                    )
                    close_prices = {
                        r[0]: float(r[1]) for r in price_cur.fetchall() if r[1] is not None
                    }

                    pos_cur = conn.execute(
                        "SELECT code, position_size FROM positions WHERE code IN ("
                        + code_params
                        + ")",
                        codes,
                    )
                    current_positions = {r[0]: int(r[1]) for r in pos_cur.fetchall()}

                    sizes = calc_position_sizes(
                        weights=weights,
                        candidates=candidates,
                        portfolio_value=portfolio_value,
                        available_cash=available_cash,
                        current_positions=current_positions,
                        open_prices=close_prices,
                    )

                    conn.execute("BEGIN")
                    try:
                        conn.execute(
                            "DELETE FROM portfolio_targets WHERE date = ?",
                            [target_date],
                        )
                        for code, weight in weights.items():
                            size = sizes.get(code, 0)
                            conn.execute(
                                "INSERT INTO portfolio_targets (date, code, target_weight, target_size) VALUES (?,?,?,?)",
                                [target_date, code, weight, size],
                            )

                        conn.execute(
                            "DELETE FROM signal_queue WHERE date = ? AND status = 'pending'",
                            [target_date],
                        )
                        for code, shares in sizes.items():
                            if shares <= 0:
                                continue
                            price = close_prices.get(code)
                            if price is None:
                                logger.warning("価格不明のため銘柄 %s をスキップします。", code)
                                continue
                            conn.execute(
                                """INSERT INTO signal_queue
                                   (signal_id, date, code, side, size, order_type, price, status)
                                   VALUES (?, ?, ?, 'buy', ?, 'market', ?, 'pending')""",
                                [str(uuid.uuid4()), target_date, code, shares, price],
                            )
                            inserted += 1

                        conn.execute("COMMIT")
                    except Exception:
                        conn.execute("ROLLBACK")
                        raise

                    _updated_rows["signal_queue"] = inserted
                    logger.info(
                        "ポートフォリオ構築完了: %d 銘柄を signal_queue に挿入 (date=%s)",
                        inserted,
                        target_date,
                    )

        # LINE 通知（失敗しても例外を伝播させない）
        try:
            notifier = build_notifier(settings)
            env = settings.env

            # 夜の日次通知
            daily_return = _get_today_return(conn, target_date, env)
            notifier.send(
                format_evening_message(
                    inserted=inserted,
                    report_date=target_date.isoformat(),
                    daily_return=daily_return,
                )
            )

            # 週次通知（金曜日: weekday == 4）
            if target_date.weekday() == 4:
                iso = target_date.isocalendar()
                week_start = date.fromisocalendar(iso.year, iso.week, 1)
                weekly_rows = collect_weekly_rows(conn, env, week_start, target_date)
                weekly_report = build_report(
                    weekly_rows,
                    report_type="weekly",
                    env=env,
                    from_date=week_start,
                    to_date=target_date,
                )
                notifier.send(
                    format_weekly_message(
                        summary=weekly_report.summary,
                        from_date=week_start.isoformat(),
                        to_date=target_date.isoformat(),
                    )
                )

            # 月次通知（月末）
            last_day = calendar.monthrange(target_date.year, target_date.month)[1]
            if target_date.day == last_day:
                month_start = target_date.replace(day=1)
                monthly_rows = collect_monthly_rows(conn, env, month_start, target_date)
                monthly_report = build_report(
                    monthly_rows,
                    report_type="monthly",
                    env=env,
                    from_date=month_start,
                    to_date=target_date,
                )
                notifier.send(
                    format_monthly_message(
                        summary=monthly_report.summary,
                        from_date=month_start.isoformat(),
                        to_date=target_date.isoformat(),
                    )
                )

        except Exception:
            logger.warning("LINE 通知に失敗しました", exc_info=True)

    except Exception as exc:
        logger.exception("ポートフォリオ構築が失敗しました")
        _errors.append(str(exc))
        _failed = True
    finally:
        if conn is not None:
            conn.close()

    finished_at = datetime.now(timezone.utc)
    try:
        write_job_result(
            JobRunResult(
                job_name=_JOB_NAME,
                status="failed" if _failed else "success",
                started_at=started_at,
                finished_at=finished_at,
                duration_sec=(finished_at - started_at).total_seconds(),
                updated_rows=_updated_rows,
                warnings=[],
                errors=_errors,
            )
        )
    except Exception:
        logger.warning("JobRunResult の書き出しに失敗しました", exc_info=True)

    if run_id is not None:
        try:
            update_process(run_id, status="failed" if _failed else "success")
        except Exception:
            logger.warning("process_registry 更新に失敗しました", exc_info=True)

    log_run_end(_APP_NAME, status="failed" if _failed else "success", started_at=started_at)
    if _failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
