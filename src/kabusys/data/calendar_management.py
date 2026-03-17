"""
マーケットカレンダー管理モジュール

DataPlatform.md Section 4.2 に基づき、JPX カレンダー（祝日・半日取引・SQ日）の
夜間バッチ更新と営業日判定ロジックを提供する。

処理フロー（calendar_update_job）:
  1. market_calendar テーブルの最終取得日を確認
  2. J-Quants API からカレンダーデータを差分取得
  3. market_calendar テーブルへ冪等保存（ON CONFLICT DO UPDATE）

営業日判定ロジック:
  - is_trading_day(conn, d)        : 指定日が営業日か判定
  - next_trading_day(conn, d)      : 翌営業日を返す
  - prev_trading_day(conn, d)      : 前営業日を返す
  - get_trading_days(conn, s, e)   : 期間内の営業日リストを返す
  - is_sq_day(conn, d)             : 指定日が SQ 日か判定

設計方針:
  - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を非営業日扱い）
  - 最大探索範囲は _MAX_SEARCH_DAYS 日以内とし無限ループを防ぐ
  - 全ての日付は date オブジェクトで扱い、timezone の混入を防ぐ
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import duckdb

from kabusys.data import jquants_client as jq

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

# 営業日探索の最大範囲（祝日連続でも現実的にこの日数を超えない）
_MAX_SEARCH_DAYS = 60

# カレンダー先読み日数（今日から何日先まで取得するか）
_CALENDAR_LOOKAHEAD_DAYS = 90

# ---------------------------------------------------------------------------
# 内部ユーティリティ
# ---------------------------------------------------------------------------


def _table_exists(conn: duckdb.DuckDBPyConnection, table: str) -> bool:
    """指定テーブルが存在するか確認する。"""
    row = conn.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE lower(table_name) = lower(?)
          AND table_schema NOT IN ('information_schema')
        """,
        [table],
    ).fetchone()
    return bool(row and row[0] > 0)


def _has_calendar_data(conn: duckdb.DuckDBPyConnection) -> bool:
    """market_calendar テーブルが存在しデータがあるか確認する。"""
    if not _table_exists(conn, "market_calendar"):
        return False
    row = conn.execute("SELECT 1 FROM market_calendar LIMIT 1").fetchone()
    return row is not None


def _is_weekend(d: date) -> bool:
    """土日かどうかを返す（フォールバック用）。"""
    return d.weekday() >= 5  # 5=Saturday, 6=Sunday


def _fetch_is_trading(conn: duckdb.DuckDBPyConnection, d: date) -> bool | None:
    """market_calendar から is_trading_day を取得する。

    Returns:
        テーブルに該当日が存在する場合は bool（NULL 値は None）、
        行自体が存在しない場合は None。
    """
    row = conn.execute(
        "SELECT is_trading_day FROM market_calendar WHERE date = ?",
        [d],
    ).fetchone()
    if not row:
        return None
    val = row[0]
    return None if val is None else bool(val)


def _to_date(val: object) -> date | None:
    """DuckDB から返る日付値を date オブジェクトに変換する。"""
    if val is None:
        return None
    return val if isinstance(val, date) else date.fromisoformat(str(val))


# ---------------------------------------------------------------------------
# 営業日判定ロジック
# ---------------------------------------------------------------------------


def is_trading_day(conn: duckdb.DuckDBPyConnection, d: date) -> bool:
    """指定日が営業日かどうかを返す。

    market_calendar に該当日がある場合はその値を使用する。
    データがない場合は土日を非営業日とするフォールバックを使用する。

    Args:
        conn: DuckDB 接続。
        d:    判定対象の日付。

    Returns:
        営業日なら True、休業日なら False。
    """
    if _has_calendar_data(conn):
        result = _fetch_is_trading(conn, d)
        if result is not None:
            return result
        # カレンダーにない日（取得範囲外）: フォールバック
        logger.debug("is_trading_day: %s はカレンダー範囲外、曜日ベースで判定", d)
    return not _is_weekend(d)


def is_sq_day(conn: duckdb.DuckDBPyConnection, d: date) -> bool:
    """指定日が SQ（特別清算指数算出）日かどうかを返す。

    market_calendar に該当日がない場合は False を返す。

    Args:
        conn: DuckDB 接続。
        d:    判定対象の日付。

    Returns:
        SQ 日なら True、そうでなければ False。
    """
    if not _has_calendar_data(conn):
        return False
    row = conn.execute(
        "SELECT is_sq_day FROM market_calendar WHERE date = ?",
        [d],
    ).fetchone()
    if not row:
        return False
    val = row[0]
    return False if val is None else bool(val)


def next_trading_day(conn: duckdb.DuckDBPyConnection, d: date) -> date:
    """指定日の翌営業日を返す。

    d 自身は含めず、d + 1 日以降で最初の営業日を返す。
    カレンダーデータがある場合は SQL で O(1) 取得する。
    カレンダー範囲外または未取得時は曜日ベースフォールバックで探索する。
    _MAX_SEARCH_DAYS 日以内に営業日が見つからない場合は ValueError を送出する。

    Args:
        conn: DuckDB 接続。
        d:    基準日。

    Returns:
        d の翌営業日。

    Raises:
        ValueError: _MAX_SEARCH_DAYS 以内に営業日が見つからない場合。
    """
    if _has_calendar_data(conn):
        row = conn.execute(
            "SELECT MIN(date) FROM market_calendar WHERE date > ? AND is_trading_day = true",
            [d],
        ).fetchone()
        db_result = _to_date(row[0]) if row else None
        if db_result is not None:
            return db_result
        # DB の範囲外（d 以降にカレンダーデータなし）→ フォールバック
        db_max_row = conn.execute("SELECT MAX(date) FROM market_calendar").fetchone()
        fallback_start = max(d + timedelta(days=1), (_to_date(db_max_row[0]) or d) + timedelta(days=1))
    else:
        fallback_start = d + timedelta(days=1)

    candidate = fallback_start
    for _ in range(_MAX_SEARCH_DAYS):
        if not _is_weekend(candidate):
            return candidate
        candidate += timedelta(days=1)
    raise ValueError(
        f"next_trading_day: {d} から {_MAX_SEARCH_DAYS} 日以内に営業日が見つかりません"
    )


def prev_trading_day(conn: duckdb.DuckDBPyConnection, d: date) -> date:
    """指定日の前営業日を返す。

    d 自身は含めず、d - 1 日以前で最も近い営業日を返す。
    カレンダーデータがある場合は SQL で O(1) 取得する。
    カレンダー範囲外または未取得時は曜日ベースフォールバックで探索する。
    _MAX_SEARCH_DAYS 日以内に営業日が見つからない場合は ValueError を送出する。

    Args:
        conn: DuckDB 接続。
        d:    基準日。

    Returns:
        d の前営業日。

    Raises:
        ValueError: _MAX_SEARCH_DAYS 以内に営業日が見つからない場合。
    """
    if _has_calendar_data(conn):
        row = conn.execute(
            "SELECT MAX(date) FROM market_calendar WHERE date < ? AND is_trading_day = true",
            [d],
        ).fetchone()
        db_result = _to_date(row[0]) if row else None
        if db_result is not None:
            return db_result
        # DB の範囲外（d 以前にカレンダーデータなし）→ フォールバック
        db_min_row = conn.execute("SELECT MIN(date) FROM market_calendar").fetchone()
        fallback_start = min(d - timedelta(days=1), (_to_date(db_min_row[0]) or d) - timedelta(days=1))
    else:
        fallback_start = d - timedelta(days=1)

    candidate = fallback_start
    for _ in range(_MAX_SEARCH_DAYS):
        if not _is_weekend(candidate):
            return candidate
        candidate -= timedelta(days=1)
    raise ValueError(
        f"prev_trading_day: {d} から {_MAX_SEARCH_DAYS} 日以内に営業日が見つかりません"
    )


def get_trading_days(
    conn: duckdb.DuckDBPyConnection,
    start: date,
    end: date,
) -> list[date]:
    """start から end（両端含む）の期間内の営業日リストを返す。

    market_calendar データがある場合は DB クエリで一括取得し効率的に処理する。
    データがない場合は曜日ベースフォールバックで土日を除いた日を返す。

    Args:
        conn:  DuckDB 接続。
        start: 期間の開始日（含む）。
        end:   期間の終了日（含む）。

    Returns:
        期間内の営業日の日付リスト（昇順）。
    """
    if start > end:
        return []

    if _has_calendar_data(conn):
        rows = conn.execute(
            """
            SELECT date FROM market_calendar
            WHERE date >= ? AND date <= ? AND is_trading_day = true
            ORDER BY date
            """,
            [start, end],
        ).fetchall()
        result = [
            _to_date(row[0]) for row in rows if _to_date(row[0]) is not None
        ]

        # カレンダー範囲外の日付を曜日ベースで補完（MIN/MAX を 1 クエリで取得）
        minmax = conn.execute("SELECT MIN(date), MAX(date) FROM market_calendar").fetchone()
        db_min = _to_date(minmax[0]) if minmax else None
        db_max = _to_date(minmax[1]) if minmax else None

        extra: list[date] = []
        if db_min and start < db_min:
            cur = start
            while cur < db_min and cur <= end:
                if not _is_weekend(cur):
                    extra.append(cur)
                cur += timedelta(days=1)
        if db_max and end > db_max:
            cur = max(start, db_max + timedelta(days=1))
            while cur <= end:
                if not _is_weekend(cur):
                    extra.append(cur)
                cur += timedelta(days=1)

        return sorted(set(result + extra))

    # フォールバック: 土日を除く
    result = []
    cur = start
    while cur <= end:
        if not _is_weekend(cur):
            result.append(cur)
        cur += timedelta(days=1)
    return result


# ---------------------------------------------------------------------------
# 夜間バッチ更新ジョブ
# ---------------------------------------------------------------------------


def calendar_update_job(
    conn: duckdb.DuckDBPyConnection,
    lookahead_days: int = _CALENDAR_LOOKAHEAD_DAYS,
) -> int:
    """JPX カレンダーを J-Quants API から差分取得し market_calendar テーブルを更新する。

    DataPlatform.md Section 4.2 の calendar_update_job に対応する夜間バッチ処理。
    market_calendar の最終取得日を確認し、今日から lookahead_days 先までを取得する。
    取得済み範囲は上書き（ON CONFLICT DO UPDATE）して最新状態に保つ。

    Args:
        conn:           DuckDB 接続。
        lookahead_days: 今日から何日先まで取得するか（デフォルト 90 日）。

    Returns:
        保存したレコード数。API エラー時は 0 を返す。
    """
    today = date.today()
    date_to = today + timedelta(days=lookahead_days)

    # 未取得範囲の開始日を算出（最終取得日の翌日、または基準日）
    if _has_calendar_data(conn):
        row = conn.execute("SELECT MAX(date) FROM market_calendar").fetchone()
        last_date = _to_date(row[0]) if row else None
        if last_date:
            if last_date >= date_to:
                logger.info(
                    "calendar_update_job: カレンダーは最新 last=%s date_to=%s",
                    last_date,
                    date_to,
                )
                return 0
            date_from = last_date + timedelta(days=1)
        else:
            date_from = today
    else:
        date_from = today

    logger.info(
        "calendar_update_job: J-Quants からカレンダー取得 date_from=%s date_to=%s",
        date_from,
        date_to,
    )

    try:
        records = jq.fetch_market_calendar(
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
        )
    except Exception:
        logger.exception("calendar_update_job: fetch_market_calendar 失敗")
        return 0

    if not records:
        logger.info("calendar_update_job: 取得レコードなし")
        return 0

    try:
        saved = jq.save_market_calendar(conn, records)
    except Exception:
        logger.exception("calendar_update_job: save_market_calendar 失敗")
        return 0

    logger.info(
        "calendar_update_job: fetched=%d saved=%d", len(records), saved
    )
    return saved
