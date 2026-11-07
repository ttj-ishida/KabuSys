"""日次成績の記録（portfolio_performance への UPSERT）。

Issue #427: 成績レポート・夜 LINE・Streamlit が読む portfolio_performance に
日次の資産額を書き込む。(date, env) 単位で冪等。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb


@dataclass(frozen=True)
class PerformanceRow:
    date: date
    env: str
    equity: float
    cash: float
    daily_return: float | None
    drawdown: float


def record_daily_performance(
    conn: duckdb.DuckDBPyConnection,
    *,
    as_of: date,
    env: str,
    equity: float,
    cash: float,
) -> PerformanceRow:
    """as_of の資産額を portfolio_performance に UPSERT して記録内容を返す。

    daily_return = equity / 同 env の as_of より前で最新の equity − 1（なければ None）。
    drawdown     = equity / 同 env の as_of 以前の最大 equity（当日を含む）− 1（0 以下）。
    as_of より後の行は参照しない（過去日の再計算で未来情報を使わない）。
    """
    prev = conn.execute(
        "SELECT equity FROM portfolio_performance WHERE env = ? AND date < ?"
        " ORDER BY date DESC LIMIT 1",
        [env, as_of],
    ).fetchone()
    daily_return: float | None = None
    if prev is not None and prev[0] is not None and float(prev[0]) != 0.0:
        daily_return = equity / float(prev[0]) - 1.0

    peak_row = conn.execute(
        "SELECT MAX(equity) FROM portfolio_performance WHERE env = ? AND date < ?",
        [env, as_of],
    ).fetchone()
    peak = equity
    if peak_row is not None and peak_row[0] is not None:
        peak = max(peak, float(peak_row[0]))
    drawdown = (equity / peak - 1.0) if peak > 0 else 0.0

    conn.execute(
        """
        INSERT INTO portfolio_performance (date, env, equity, cash, drawdown, daily_return)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (date, env) DO UPDATE SET
            equity = excluded.equity,
            cash = excluded.cash,
            drawdown = excluded.drawdown,
            daily_return = excluded.daily_return
        """,
        [as_of, env, equity, cash, drawdown, daily_return],
    )
    return PerformanceRow(
        date=as_of,
        env=env,
        equity=equity,
        cash=cash,
        daily_return=daily_return,
        drawdown=drawdown,
    )
