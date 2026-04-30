"""運用成績データ収集モジュール。

DuckDB（portfolio_performance, market_calendar）を read-only で参照し、
DailyRow / WeeklyRow / MonthlyRow を返す。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import groupby


@dataclass
class DailyRow:
    date: date
    env: str
    equity: float
    daily_return: float | None
    drawdown: float | None
    cumulative_return: float | None  # (equity / first_equity_in_period) - 1.0


@dataclass
class WeeklyRow:
    week_label: str  # "2026-W17"
    trading_days: int
    equity_start: float
    equity_end: float
    weekly_return: float | None  # (equity_end / equity_start) - 1.0
    max_drawdown: float | None  # 週内の drawdown 最小値
    win_days: int  # daily_return > 0 の日数


@dataclass
class MonthlyRow:
    month_label: str  # "2026-04"
    trading_days: int
    equity_start: float
    equity_end: float
    monthly_return: float | None
    max_drawdown: float | None
    win_days: int


def _iso_week_label(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _month_label(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def _count_trading_days(conn, from_date: date, to_date: date) -> int:
    """market_calendar で from_date〜to_date の JPX 営業日数を返す。"""
    row = conn.execute(
        "SELECT COUNT(*) FROM market_calendar"
        " WHERE date >= ? AND date <= ? AND is_trading_day = true",
        [from_date.isoformat(), to_date.isoformat()],
    ).fetchone()
    return int(row[0]) if row else 0


def collect_daily_rows(
    conn,
    env: str,
    from_date: date,
    to_date: date,
) -> list[DailyRow]:
    """portfolio_performance から env フィルタ済み日次行を昇順で返す。

    cumulative_return は期間内最初の equity を基準に計算する。
    """
    rows = conn.execute(
        "SELECT date, env, equity, daily_return, drawdown"
        " FROM portfolio_performance"
        " WHERE env = ? AND date >= ? AND date <= ?"
        " ORDER BY date ASC",
        [env, from_date.isoformat(), to_date.isoformat()],
    ).fetchall()
    if not rows:
        return []
    first_equity = float(rows[0][2])
    result: list[DailyRow] = []
    for r in rows:
        equity = float(r[2])
        cum = (equity / first_equity - 1.0) if first_equity != 0.0 else None
        d = r[0]
        if not isinstance(d, date):
            d = date.fromisoformat(str(d))
        result.append(
            DailyRow(
                date=d,
                env=r[1],
                equity=equity,
                daily_return=float(r[3]) if r[3] is not None else None,
                drawdown=float(r[4]) if r[4] is not None else None,
                cumulative_return=cum,
            )
        )
    return result


def collect_weekly_rows(
    conn,
    env: str,
    from_date: date,
    to_date: date,
) -> list[WeeklyRow]:
    """日次行を ISO 週番号でグループ化して WeeklyRow を返す。

    trading_days は portfolio_performance に記録がある最初〜最後の日付を範囲として
    market_calendar の営業日数を集計する（週全体の境界ではない）。
    """
    daily = collect_daily_rows(conn, env, from_date, to_date)
    if not daily:
        return []
    result: list[WeeklyRow] = []
    for week_label, group_iter in groupby(daily, key=lambda r: _iso_week_label(r.date)):
        group = list(group_iter)
        week_from = group[0].date
        week_to = group[-1].date
        trading_days = _count_trading_days(conn, week_from, week_to)
        eq_start = group[0].equity
        eq_end = group[-1].equity
        weekly_return = (eq_end / eq_start - 1.0) if eq_start != 0.0 else None
        drawdowns = [r.drawdown for r in group if r.drawdown is not None]
        max_dd = min(drawdowns) if drawdowns else None
        win_days = sum(
            1 for r in group if r.daily_return is not None and r.daily_return > 0
        )
        result.append(
            WeeklyRow(
                week_label=week_label,
                trading_days=trading_days,
                equity_start=eq_start,
                equity_end=eq_end,
                weekly_return=weekly_return,
                max_drawdown=max_dd,
                win_days=win_days,
            )
        )
    return result


def collect_monthly_rows(
    conn,
    env: str,
    from_date: date,
    to_date: date,
) -> list[MonthlyRow]:
    """日次行を年月でグループ化して MonthlyRow を返す。

    trading_days は portfolio_performance に記録がある最初〜最後の日付を範囲として
    market_calendar の営業日数を集計する（月全体の境界ではない）。
    """
    daily = collect_daily_rows(conn, env, from_date, to_date)
    if not daily:
        return []
    result: list[MonthlyRow] = []
    for month_label, group_iter in groupby(daily, key=lambda r: _month_label(r.date)):
        group = list(group_iter)
        month_from = group[0].date
        month_to = group[-1].date
        trading_days = _count_trading_days(conn, month_from, month_to)
        eq_start = group[0].equity
        eq_end = group[-1].equity
        monthly_return = (eq_end / eq_start - 1.0) if eq_start != 0.0 else None
        drawdowns = [r.drawdown for r in group if r.drawdown is not None]
        max_dd = min(drawdowns) if drawdowns else None
        win_days = sum(
            1 for r in group if r.daily_return is not None and r.daily_return > 0
        )
        result.append(
            MonthlyRow(
                month_label=month_label,
                trading_days=trading_days,
                equity_start=eq_start,
                equity_end=eq_end,
                monthly_return=monthly_return,
                max_drawdown=max_dd,
                win_days=win_days,
            )
        )
    return result
