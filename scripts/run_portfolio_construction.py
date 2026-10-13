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

import argparse
import calendar
import contextlib
import logging
import math
import sqlite3
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kabusys.config import Settings
from kabusys.execution.signal_queue_status import sync_to_duckdb
from kabusys.operations.job_run_recorder import write_job_result
from kabusys.operations.line_reports import (
    format_evening_message,
    format_monthly_message,
    format_weekly_message,
)
from kabusys.operations.manual_trades import (
    calc_manual_portfolio_value,
    manual_position_qty_map,
    merge_current_positions,
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

_MAX_UTILIZATION = 0.70  # Live/その他環境でのフォールバック時に適用。Paper では適用しない
_JOB_NAME = "portfolio_construction_job"
_APP_NAME = "portfolio_construction"


def _sync_signal_queue_status(conn: duckdb.DuckDBPyConnection, settings: Settings) -> int:
    """Execution Engine が SQLite に記録した signal_queue の状態を DuckDB に反映する（Issue #413）。

    夜間バッチは DuckDB を排他利用する時間帯に動くため、ここで反映する。
    pending の行には触れない。失敗しても警告ログだけ出して処理を続ける。
    Execution Engine と同じく paper_trading では paper 用 SQLite を参照する。
    """
    try:
        sqlite_path = Path(
            settings.paper_sqlite_path if settings.is_paper else settings.sqlite_path
        )
        if not sqlite_path.exists():
            logger.info("signal_queue_status 同期: SQLite が未作成のためスキップ (%s)", sqlite_path)
            return 0
        sqlite_uri = sqlite_path.resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(sqlite_uri, uri=True)) as sqlite_conn:
            updated = sync_to_duckdb(conn, sqlite_conn)
        logger.info("signal_queue_status を DuckDB signal_queue に同期: %d 件", updated)
        return updated
    except Exception:
        logger.warning(
            "signal_queue_status の DuckDB 同期に失敗しました（処理は続行します）", exc_info=True
        )
        return 0


def _fetch_close_prices(
    conn: duckdb.DuckDBPyConnection, codes: list[str], as_of: date
) -> dict[str, float]:
    """各銘柄の as_of 以前で最新の終値を返す。

    --date で過去日を指定して再実行した場合に、それより後の価格（未来情報）を
    参照しないよう date <= as_of で制限する（Issue #413 / Look-ahead Bias 防止）。
    """
    if not codes:
        return {}
    code_params = ",".join(["?"] * len(codes))
    rows = conn.execute(
        f"""
        SELECT p.code, p.close
        FROM prices_daily p
        INNER JOIN (
            SELECT code, MAX(date) AS max_date
            FROM prices_daily
            WHERE code IN ({code_params}) AND date <= ?
            GROUP BY code
        ) latest ON p.code = latest.code AND p.date = latest.max_date
        """,
        [*codes, as_of],
    ).fetchall()
    return {r[0]: float(r[1]) for r in rows if r[1] is not None}


def _calc_live_portfolio_value(
    settings: Settings,
    duckdb_conn: duckdb.DuckDBPyConnection,
    as_of: date | None = None,
) -> tuple[float, float]:
    """Live モード用 (portfolio_value, available_cash) を算出する。

    portfolio_value: DuckDB portfolio_performance の直近 equity → PORTFOLIO_VALUE 環境変数
    available_cash:  カブステーション /wallet/cash API → portfolio_value × max_utilization
    """
    fallback_pv = settings.portfolio_value
    as_of = as_of or date.today()

    portfolio_value = fallback_pv
    try:
        row = duckdb_conn.execute(
            "SELECT equity FROM portfolio_performance WHERE env = 'live' AND date <= ?"
            " ORDER BY date DESC LIMIT 1",
            [as_of],
        ).fetchone()
        if row and row[0] is not None:
            equity = float(row[0])
            if math.isfinite(equity) and equity > 0:
                portfolio_value = equity
                logger.info("portfolio_value: DuckDB 実績値=%.0f 円 (env=live)", portfolio_value)
            else:
                logger.warning(
                    "DuckDB equity が不正値(%.0f)。PORTFOLIO_VALUE=%.0f 円を使用",
                    equity,
                    fallback_pv,
                )
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
        if isinstance(cash, (int, float)) and math.isfinite(cash) and cash >= 0:
            available_cash = float(cash)
            logger.info("available_cash: カブステーション API 余力=%.0f 円", available_cash)
        else:
            logger.warning(
                "Kabu API 余力が不正値(%s)。pv×max_utilization=%.0f 円を使用",
                cash,
                available_cash,
            )
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
    as_of: date | None = None,
) -> tuple[float, float]:
    """Paper モード用 (portfolio_value, available_cash) を算出する。

    paper_trading.db の約定履歴から現金残高・保有ポジション時価を計算する。
    DB が存在しない・読み取り失敗時は PAPER_TRADING_INITIAL_CASH にフォールバックする。

    portfolio_value = 現金残高 + 保有ロングポジション時価
    available_cash  = 現金残高（マイナスの場合は 0 に補正）
    注: ショートポジション（net_qty < 0）は市場価値に含めない（Paper ではショート非対応）。
    """
    initial_cash = settings.paper_trading_initial_cash
    sqlite_path = settings.paper_sqlite_path
    as_of = as_of or date.today()

    if not sqlite_path.exists():
        logger.info(
            "paper_trading.db が未存在。PAPER_TRADING_INITIAL_CASH=%.0f 円を使用", initial_cash
        )
        return initial_cash, initial_cash

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
        return initial_cash, initial_cash

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
        try:
            prices = _fetch_close_prices(duckdb_conn, list(positions.keys()), as_of)
            for pcode, price in prices.items():
                if pcode in positions:
                    market_value += positions[pcode] * price
        except Exception:
            logger.warning(
                "ポジション時価計算に失敗。現金のみで portfolio_value を算出します", exc_info=True
            )

    available_cash = max(net_cash, 0.0)
    portfolio_value = max(net_cash + market_value, 0.0)

    logger.info(
        "Paper portfolio_value 算出: 現金=%.0f 円, 時価=%.0f 円, 合計=%.0f 円, 利用可能現金=%.0f 円",
        net_cash,
        market_value,
        portfolio_value,
        available_cash,
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


def _collect_evening_signals(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    manual_codes: set[str] | None = None,
) -> tuple[list[dict] | None, list[dict] | None]:
    """LINE 夜通知用の BUY/SELL シグナル詳細を取得する。

    BUY は signal_queue JOIN stocks（size あり）。
    SELL は signals JOIN stocks。manual_action_queue があれば理由・株数を付与（テーブル無しでも動作）。
    BUY クエリ失敗時は (None, None) を返し、呼び出し元が件数表示にフォールバックする。
    """
    buy: list[dict] = []
    try:
        rows = conn.execute(
            """
            SELECT q.code, COALESCE(st.name, q.code) AS name, CAST(q.size AS BIGINT) AS size
            FROM signal_queue q
            LEFT JOIN stocks st ON q.code = st.code
            WHERE q.date = ? AND q.side = 'buy' AND q.status = 'pending'
            ORDER BY q.code
            """,
            [target_date],
        ).fetchall()
        # signal_queue.size は BIGINT NOT NULL のため r[2] が None になることはない
        manual = manual_codes or set()
        buy = [
            {"code": r[0], "name": r[1], "size": int(r[2]), "add_on": r[0] in manual} for r in rows
        ]
    except Exception:
        logger.warning("LINE通知用BUYシグナル詳細の取得に失敗しました", exc_info=True)
        return None, None

    sell: list[dict] = []
    try:
        has_actions = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'main' AND table_name = 'manual_action_queue'"
        ).fetchone()[0]
        if has_actions:
            rows = conn.execute(
                """
                SELECT s.code, COALESCE(st.name, s.code), m.qty, m.reason, m.action_id IS NOT NULL
                FROM signals s
                LEFT JOIN stocks st ON s.code = st.code
                LEFT JOIN manual_action_queue m
                  ON m.date = s.date AND m.code = s.code AND m.action = 'sell_candidate'
                WHERE s.date = ? AND s.side = 'sell'
                ORDER BY s.code
                """,
                [target_date],
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT s.code, COALESCE(st.name, s.code), NULL, NULL, FALSE
                FROM signals s
                LEFT JOIN stocks st ON s.code = st.code
                WHERE s.date = ? AND s.side = 'sell'
                ORDER BY s.code
                """,
                [target_date],
            ).fetchall()
        sell = [
            {
                "code": r[0],
                "name": r[1],
                "qty": int(r[2]) if r[2] is not None else None,
                "reason": r[3],
                "manual": bool(r[4]),
            }
            for r in rows
        ]
    except Exception:
        logger.warning("LINE通知用SELLシグナル詳細の取得に失敗しました", exc_info=True)

    return buy, sell


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """CLI 引数を解析する。argv=None（テスト等の直接呼び出し）は引数なしとして扱う。

    --date: 対象日（既定: 今日）。夜間バッチが失敗した翌朝に、前営業日を指定して
            再実行するために使う（signal_queue.date がその日付になり、当日の執行で読まれる）。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="対象日（省略時: 今日）。翌朝の再実行時は前営業日を指定する",
    )
    return parser.parse_args(argv if argv is not None else [])


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    run_id: int | None = None
    try:
        run_id = register_process(_JOB_NAME, log_file=str(_run_log) if _run_log else None)
    except Exception:
        logger.warning("process_registry 登録に失敗しました", exc_info=True)
    conn = None
    target_date = args.date
    _failed = False
    _errors: list[str] = []
    _updated_rows: dict[str, int] = {}

    try:
        settings = Settings()
        conn = duckdb.connect(str(settings.duckdb_path))
        _sync_signal_queue_status(conn, settings)

        manual_qty: dict[str, int] = {}
        if settings.manual_trading_enabled:
            portfolio_value, available_cash = calc_manual_portfolio_value(
                conn, settings.manual_trading_initial_cash, as_of=target_date
            )
            manual_qty = manual_position_qty_map(conn, as_of=target_date)
            logger.info(
                "手動運用: portfolio_value=%.0f 円, available_cash=%.0f 円, 手動保有 %d 銘柄",
                portfolio_value,
                available_cash,
                len(manual_qty),
            )
        elif settings.is_live:
            portfolio_value, available_cash = _calc_live_portfolio_value(
                settings, conn, as_of=target_date
            )
        elif settings.is_paper or settings.is_dev:
            portfolio_value, available_cash = _calc_paper_portfolio_value(
                settings, conn, as_of=target_date
            )
        else:
            portfolio_value = settings.portfolio_value
            available_cash = portfolio_value * _MAX_UTILIZATION
            logger.info(
                "portfolio_value: PORTFOLIO_VALUE=%.0f 円 (env=%s)", portfolio_value, settings.env
            )
            logger.info(
                "available_cash: pv×max_utilization=%.0f 円 (env=%s)", available_cash, settings.env
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
                    close_prices = _fetch_close_prices(conn, codes, target_date)

                    pos_cur = conn.execute(
                        "SELECT code, position_size FROM positions WHERE code IN ("
                        + code_params
                        + ")",
                        codes,
                    )
                    current_positions = {r[0]: int(r[1]) for r in pos_cur.fetchall()}
                    current_positions = merge_current_positions(
                        current_positions, manual_qty, codes
                    )

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
            buy_sigs, sell_sigs = _collect_evening_signals(
                conn, target_date, manual_codes=set(manual_qty)
            )
            notifier.send(
                format_evening_message(
                    inserted=inserted,
                    report_date=target_date.isoformat(),
                    daily_return=daily_return,
                    buy_signals=buy_sigs,
                    sell_signals=sell_sigs,
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
    main(sys.argv[1:])
