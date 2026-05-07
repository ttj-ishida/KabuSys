# scripts/run_portfolio_construction.py
"""Night batch: ポートフォリオ構築 (portfolio_construction_job)。

Task Scheduler から 21:00 に起動される。
signals テーブルから当日の BUY シグナルを読み込み、
ポートフォリオ構築を行って signal_queue と portfolio_targets に書き込む。

環境変数:
    PORTFOLIO_VALUE: 総資産額（円）。デフォルト: 10,000,000
"""

from __future__ import annotations

import calendar
import logging
import os
import sys
import uuid
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kabusys.config import Settings
from kabusys.operations.line_reports import (
    format_evening_message,
    format_monthly_message,
    format_weekly_message,
)
from kabusys.operations.notifier import build_notifier
from kabusys.operations.performance_collector import (
    collect_monthly_rows,
    collect_weekly_rows,
)
from kabusys.operations.performance_report import build_report
from kabusys.portfolio.portfolio_builder import calc_score_weights, select_candidates
from kabusys.portfolio.position_sizing import calc_position_sizes
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="portfolio_construction")
logger = logging.getLogger(__name__)

_DEFAULT_PORTFOLIO_VALUE = 10_000_000  # 1000万円
_MAX_UTILIZATION = 0.70


def _get_today_return(
    conn: duckdb.DuckDBPyConnection, target_date: date, env: str
) -> float | None:
    row = conn.execute(
        "SELECT daily_return FROM portfolio_performance"
        " WHERE date = ? AND env = ? LIMIT 1",
        [target_date, env],
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return float(row[0])


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    target_date = date.today()

    try:
        portfolio_value_str = os.environ.get(
            "PORTFOLIO_VALUE", str(_DEFAULT_PORTFOLIO_VALUE)
        )
        try:
            portfolio_value = float(portfolio_value_str)
        except ValueError:
            logger.warning(
                "PORTFOLIO_VALUE が不正な値です (%s)。デフォルト値を使用します: %s",
                portfolio_value_str,
                _DEFAULT_PORTFOLIO_VALUE,
            )
            portfolio_value = float(_DEFAULT_PORTFOLIO_VALUE)
        available_cash = portfolio_value * _MAX_UTILIZATION
        inserted = 0

        # 1. 当日の BUY シグナルを取得
        cur = conn.execute(
            "SELECT code, side, score, signal_rank FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        )
        rows = cur.fetchall()
        buy_signals = [dict(zip([d[0] for d in cur.description], row)) for row in rows]

        if not buy_signals:
            logger.info("本日の BUY シグナルが 0 件です。signal_queue を更新しません。")
        else:
            # 2. 銘柄選定・重み計算（メモリ内）
            candidates = select_candidates(buy_signals)
            if not candidates:
                logger.info("銘柄選定結果が 0 件です。signal_queue を更新しません。")
            else:
                weights = calc_score_weights(candidates)
                if not weights:
                    logger.info(
                        "重み計算結果が 0 件です。signal_queue を更新しません。"
                    )
                else:
                    # 3. 最新終値を取得（直近の prices_daily から）
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
                        r[0]: float(r[1])
                        for r in price_cur.fetchall()
                        if r[1] is not None
                    }

                    # 4. 現在のポジション取得
                    pos_cur = conn.execute(
                        "SELECT code, size FROM positions WHERE code IN ("
                        + code_params
                        + ")",
                        codes,
                    )
                    current_positions = {r[0]: int(r[1]) for r in pos_cur.fetchall()}

                    # 5. ポジションサイズ計算
                    sizes = calc_position_sizes(
                        weights=weights,
                        candidates=candidates,
                        portfolio_value=portfolio_value,
                        available_cash=available_cash,
                        current_positions=current_positions,
                        open_prices=close_prices,
                    )

                    # 6. portfolio_targets / signal_queue をトランザクション内で更新
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

                        # 7. signal_queue を更新（当日の pending シグナルをクリアして再挿入）
                        conn.execute(
                            "DELETE FROM signal_queue WHERE date = ? AND status = 'pending'",
                            [target_date],
                        )
                        for code, shares in sizes.items():
                            if shares <= 0:
                                continue
                            price = close_prices.get(code)
                            if price is None:
                                logger.warning(
                                    "価格不明のため銘柄 %s をスキップします。", code
                                )
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
                monthly_rows = collect_monthly_rows(
                    conn, env, month_start, target_date
                )
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

    except Exception:
        logger.exception("ポートフォリオ構築が失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
