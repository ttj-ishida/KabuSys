# scripts/run_strategy_signal.py
"""Night batch: 売買シグナル生成 (strategy_signal_job)。

Task Scheduler から 20:00 に起動される。
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.execution.order_repository import init_position_entries_db
from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db
from kabusys.operations.job_run_recorder import write_job_result
from kabusys.operations.night_batch_report import JobRunResult
from kabusys.operations.process_registry import register_process, update_process
from kabusys.strategy.signal_generator import generate_signals
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

_DD_STOP_PCT = 0.12  # ポートフォリオが peak 比 12% 以上下落したら BUY を停止
_DD_STOP_TIMEOUT_DAYS = 30  # 停止発動から 30 カレンダー日後に自動解除

_REPORT_LOT_SIZE = 100
_REPORT_MAX_UTILIZATION = 0.30
_REPORT_MAX_POSITION_PCT = 0.10

_run_log = setup_logging(app_name="strategy_signal", capture_stdio=True)
logger = logging.getLogger(__name__)

_JOB_NAME = "strategy_signal_job"
_APP_NAME = "strategy_signal"


def _print_signal_report(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    portfolio_value: float | None,
) -> None:
    """翌日シグナルの銘柄名・コード・推定購入数量を標準出力に出力する。"""

    # --- BUY シグナル ---
    try:
        buy_rows = conn.execute(
            """
            SELECT s.code, COALESCE(st.name, s.code) AS name,
                   s.signal_rank, COALESCE(s.size_multiplier, 1.0) AS sm
            FROM signals s
            LEFT JOIN stocks st ON s.code = st.code
            WHERE s.date = ? AND s.side = 'buy'
            ORDER BY COALESCE(s.signal_rank, 9999), s.code
            """,
            [target_date],
        ).fetchall()
    except Exception:
        logger.warning("BUY シグナル取得に失敗しました", exc_info=True)
        buy_rows = []

    # --- SELL シグナル ---
    try:
        sell_rows = conn.execute(
            """
            SELECT s.code, COALESCE(st.name, s.code) AS name
            FROM signals s
            LEFT JOIN stocks st ON s.code = st.code
            WHERE s.date = ? AND s.side = 'sell'
            ORDER BY s.code
            """,
            [target_date],
        ).fetchall()
    except Exception:
        logger.warning("SELL シグナル取得に失敗しました", exc_info=True)
        sell_rows = []

    # --- 最新終値 ---
    all_codes = list({r[0] for r in buy_rows} | {r[0] for r in sell_rows})
    prices: dict[str, float] = {}
    if all_codes:
        try:
            ph = ", ".join("?" * len(all_codes))
            price_rows = conn.execute(
                f"""
                SELECT p.code, p.close
                FROM prices_daily p
                INNER JOIN (
                    SELECT code, MAX(date) AS max_date
                    FROM prices_daily
                    WHERE date <= ? AND code IN ({ph})
                    GROUP BY code
                ) t ON p.code = t.code AND p.date = t.max_date
                """,  # noqa: S608
                [target_date, *all_codes],
            ).fetchall()
            prices = {r[0]: float(r[1]) for r in price_rows}
        except Exception:
            logger.warning("終値取得に失敗しました", exc_info=True)

    # --- 推定数量計算 (等配分) ---
    n_buy = len(buy_rows)

    def _est_qty(price: float, sm: float) -> int | None:
        """等配分・size_multiplier 適用で推定数量を計算する。None は不明。"""
        if not portfolio_value or portfolio_value <= 0 or price <= 0 or n_buy == 0:
            return None
        slot = portfolio_value * _REPORT_MAX_UTILIZATION / n_buy
        qty = int(slot * sm / price / _REPORT_LOT_SIZE) * _REPORT_LOT_SIZE
        cap = (
            int(portfolio_value * _REPORT_MAX_POSITION_PCT / price / _REPORT_LOT_SIZE)
            * _REPORT_LOT_SIZE
        )
        return min(qty, cap)

    # --- 出力 ---
    sep = "=" * 66
    lines: list[str] = []
    lines.append(sep)
    lines.append(f"  [Signal Report] date={target_date}")
    pf_s = f"{portfolio_value:,.0f}円" if portfolio_value is not None else "N/A"
    lines.append(
        f"  PF={pf_s}"
        f"  max_util={_REPORT_MAX_UTILIZATION:.0%}"
        f"  max_pos={_REPORT_MAX_POSITION_PCT:.0%}"
        f"  lot={_REPORT_LOT_SIZE}"
    )
    lines.append(sep)

    # BUY
    lines.append(f"\n[BUY] {n_buy} 件")
    if buy_rows:
        lines.append(
            f"  {'Rk':>2}  {'Code':<6}  {'Name':<22}  {'Close':>8}  {'Est.Qty':>10}  {'Est.Amt':>12}"
        )
        lines.append("  " + "-" * 64)
        total_est = 0.0
        for code, name, rank, sm in buy_rows:
            price = prices.get(code, 0.0)
            rk_s = str(rank) if rank is not None else "-"
            qty = _est_qty(price, float(sm))
            price_s = f"{price:,.0f}" if price > 0 else "---"
            if qty is None:
                qty_s, amt_s = "N/A", "---"
            elif qty == 0:
                qty_s, amt_s = "0(<1 lot)", "---"
            else:
                est = qty * price
                total_est += est
                qty_s = f"{qty:,}"
                amt_s = f"{est:,.0f}"
            name_s = (name or "")[:20]
            lines.append(
                f"  {rk_s:>2}  {code:<6}  {name_s:<22}  {price_s:>8}  {qty_s:>10}  {amt_s:>12}"
            )
        if portfolio_value and total_est > 0:
            pct = total_est / portfolio_value * 100
            lines.append(f"\n  Est.Total: {total_est:,.0f}円 ({pct:.1f}% of PF)")
    else:
        lines.append("  (なし)")

    # SELL
    lines.append(f"\n[SELL] {len(sell_rows)} 件")
    if sell_rows:
        lines.append(f"  {'Code':<6}  {'Name':<26}  {'Close':>8}")
        lines.append("  " + "-" * 44)
        for code, name in sell_rows:
            price = prices.get(code, 0.0)
            price_s = f"{price:,.0f}" if price > 0 else "---"
            name_s = (name or "")[:24]
            lines.append(f"  {code:<6}  {name_s:<26}  {price_s:>8}")
    else:
        lines.append("  (なし)")

    lines.append("\n" + sep)
    lines.append(
        "  ※ Est.Qty は等配分/close price 基準の推定値。実際の発注量と異なる場合があります。"
    )

    report_text = "\n".join(lines)
    print(report_text)

    # --- ファイル保存 ---
    try:
        out_dir = Path("artifacts/signal_queue")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{target_date}_signal_report.txt"
        out_path.write_text(report_text + "\n", encoding="utf-8")
        logger.info("シグナルレポート保存: %s", out_path)
    except Exception:
        logger.warning("シグナルレポートのファイル保存に失敗しました", exc_info=True)


def main() -> None:
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    run_id: int | None = None
    try:
        run_id = register_process(_JOB_NAME, log_file=str(_run_log) if _run_log else None)
    except Exception:
        logger.warning("process_registry 登録に失敗しました", exc_info=True)
    conn = None
    _failed = False
    _errors: list[str] = []
    _updated_rows: dict[str, int] = {}

    sqlite_conn = None
    try:
        settings = Settings()
        conn = duckdb.connect(str(settings.duckdb_path))
        sqlite_conn = sqlite3.connect(str(settings.sqlite_path), timeout=30.0)
        sqlite_conn.row_factory = sqlite3.Row
        init_position_entries_db(sqlite_conn)
        init_monitoring_db(sqlite_conn)
        target_date = date.today()

        # --- ポートフォリオ DD 停止チェック ---
        mdb = MonitoringDB(sqlite_conn)
        dashboard = mdb.get_dashboard()
        pf_value: float | None = None
        if dashboard is not None:
            val = dashboard.get("portfolio_value")
            try:
                pf_value = float(val) if val is not None else None
            except Exception:
                logger.warning(
                    "dashboard.portfolio_value の変換に失敗しました: %r", val, exc_info=True
                )
        entry_blocked = False
        if dashboard is not None:
            drawdown_pct = float(dashboard["drawdown_pct"])
            blocked_since_str = dashboard["dd_stop_blocked_since"]
            blocked_since = date.fromisoformat(blocked_since_str) if blocked_since_str else None

            # タイムアウト解除チェック
            if blocked_since is not None:
                elapsed = (target_date - blocked_since).days
                if elapsed >= _DD_STOP_TIMEOUT_DAYS:
                    logger.info(
                        "DD 停止タイムアウト解除: blocked_since=%s elapsed=%d日",
                        blocked_since_str,
                        elapsed,
                    )
                    mdb.upsert_dashboard(
                        portfolio_value=float(dashboard["portfolio_value"]),
                        cash=float(dashboard["cash"]),
                        drawdown_pct=0.0,
                        open_order_count=int(dashboard["open_order_count"]),
                        position_count=int(dashboard["position_count"]),
                        peak_value=float(dashboard["portfolio_value"]),
                        clear_dd_stop=True,
                    )
                    blocked_since = None
                    drawdown_pct = 0.0

            # DD 停止判定
            if blocked_since is None and drawdown_pct > _DD_STOP_PCT:
                entry_blocked = True
                mdb.upsert_dashboard(
                    portfolio_value=float(dashboard["portfolio_value"]),
                    cash=float(dashboard["cash"]),
                    drawdown_pct=drawdown_pct,
                    open_order_count=int(dashboard["open_order_count"]),
                    position_count=int(dashboard["position_count"]),
                    dd_stop_blocked_since=target_date.isoformat(),
                )
                logger.warning(
                    "DD 停止発動: drawdown=%.1f%% > %.0f%% → BUY シグナル生成をスキップ",
                    drawdown_pct * 100,
                    _DD_STOP_PCT * 100,
                )
            elif blocked_since is not None:
                entry_blocked = True
                logger.info(
                    "DD 停止継続中: blocked_since=%s drawdown=%.1f%%",
                    blocked_since_str,
                    drawdown_pct * 100,
                )

        if entry_blocked:
            logger.info("DD Stop により BUY をスキップします（SELL は継続）date=%s", target_date)
        n = generate_signals(
            conn,
            target_date,
            use_ma200_filter=True,
            adaptive_threshold_vol_regime=True,
            topix_vol_low_threshold=0.12,
            dynamic_trailing_stop=True,
            trail_stage2_mult=1.8,
            trail_stage3_mult=1.5,
            entry_blocked=entry_blocked,
            block_entries_by_regime=False,
            sqlite_conn=sqlite_conn,
            # W1_08 IS パラメータ
            entry_3d_max_abs_return=0.08,
            quality_score_min=-0.30,
            score_drop_atr_gate=1.0,
        )
        _updated_rows["signals"] = n
        logger.info("シグナル生成完了: %d 件 (date=%s)", n, target_date)
        _print_signal_report(conn, target_date, pf_value)
    except Exception as exc:
        logger.exception("generate_signals が失敗しました")
        _errors.append(str(exc))
        _failed = True
    finally:
        if conn is not None:
            conn.close()
        if sqlite_conn is not None:
            sqlite_conn.close()

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
