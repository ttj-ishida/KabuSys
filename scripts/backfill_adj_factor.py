# scripts/backfill_adj_factor.py
"""欠けている raw_prices.adj_factor を J-Quants から再取得して補う（Issue #424）。

2026-06 以降の日次更新は AdjFactor を保存していなかったため、指定期間を日付ごとに
再取得して raw_prices に保存し、raw → prices_daily の同期（分割補正込み）をやり直す。
係数が見つかった銘柄は全期間の prices_daily が作り直される。

J-Quants のプランで取得できない日付（エラー・空応答）は警告を出してスキップする。
DuckDB に書き込むため、スケジューラーと Execution を停止してから実行すること。

使い方:
    python scripts/backfill_adj_factor.py --from 2026-06-01 --to 2026-11-06
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.data import jquants_client as jq
from kabusys.data.pipeline import sync_raw_prices_to_prices_daily
from kabusys.data.price_adjustment import codes_with_factors

logger = logging.getLogger(__name__)

FetchFn = Callable[..., list[dict[str, Any]]]


def _target_dates(conn: duckdb.DuckDBPyConnection, date_from: date, date_to: date) -> list[date]:
    """期間内の営業日。market_calendar に期間のデータがなければ平日で代用する。"""
    rows = conn.execute(
        "SELECT date, is_trading_day FROM market_calendar WHERE date BETWEEN ? AND ? ORDER BY date",
        [date_from, date_to],
    ).fetchall()
    if rows:
        return [r[0] for r in rows if r[1]]
    days: list[date] = []
    d = date_from
    while d <= date_to:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def backfill(
    conn: duckdb.DuckDBPyConnection,
    date_from: date,
    date_to: date,
    fetch: FetchFn | None = None,
) -> dict[str, Any]:
    """期間の株価を日付ごとに再取得して adj_factor を保存し、prices_daily を同期し直す。

    Returns:
        {"saved": 保存件数, "codes": 期間内に 1 以外の係数を持つ銘柄, "skipped_dates": [...]}
    """
    fetch_fn = fetch or jq.fetch_daily_quotes
    saved = 0
    skipped: list[date] = []
    for d in _target_dates(conn, date_from, date_to):
        try:
            records = fetch_fn(date_from=d, date_to=d)
        except Exception as exc:
            logger.warning("%s: 取得できないためスキップします（%s）", d, exc)
            skipped.append(d)
            continue
        if not records:
            logger.warning("%s: データがないためスキップします（プラン外の可能性）", d)
            skipped.append(d)
            continue
        saved += jq.save_daily_quotes(conn, records)

    # 範囲の同期で、係数が出た銘柄は全期間を作り直す
    sync_raw_prices_to_prices_daily(conn, date_from, date_to)
    codes = codes_with_factors(conn, date_from, date_to)
    logger.info(
        "backfill_adj_factor: saved=%d codes=%d skipped_dates=%d",
        saved,
        len(codes),
        len(skipped),
    )
    return {"saved": saved, "codes": codes, "skipped_dates": skipped}


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="欠けている adj_factor を再取得して補います。")
    parser.add_argument("--from", dest="date_from", required=True, type=_parse_date)
    parser.add_argument("--to", dest="date_to", required=True, type=_parse_date)
    args = parser.parse_args(argv)
    if args.date_from > args.date_to:
        parser.error("--from は --to 以前の日付を指定してください")

    from kabusys.config import Settings

    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        summary = backfill(conn, args.date_from, args.date_to)
        print(f"保存: {summary['saved']:,} 件")
        print(f"分割・併合の係数がある銘柄: {', '.join(summary['codes']) or '(なし)'}")
        if summary["skipped_dates"]:
            days = ", ".join(d.isoformat() for d in summary["skipped_dates"])
            print(f"スキップした日付: {days}")
        return 0
    except Exception:
        logger.exception("backfill_adj_factor が失敗しました")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
