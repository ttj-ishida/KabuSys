"""Paper モードの資産算出（portfolio_construction / performance_record で共用）。

Issue #427: scripts/run_portfolio_construction.py から移設（ロジックは変更なし）。
"""

from __future__ import annotations

import contextlib
import logging
import sqlite3
from datetime import date

import duckdb

from kabusys.config import Settings

logger = logging.getLogger(__name__)


def fetch_close_prices(
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


def calc_paper_portfolio_value(
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
            prices = fetch_close_prices(duckdb_conn, list(positions.keys()), as_of)
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
