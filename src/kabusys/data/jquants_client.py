"""
J-Quants API クライアント（v2）

J-Quants API v2 から以下のデータを取得する。
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー（祝日・半日・SQ）

設計原則:
  - 認証は x-api-key ヘッダー（v2 移行後; 2025-12-22 以降登録ユーザーは API キーのみ対応）
  - APIレート制限（120 req/min）を厳守する（RateLimiter による制御）
  - リトライロジック付き（指数バックオフ、最大 3 回、対象: 408/429/5xx）
  - Look-ahead Bias 防止: 取得日時（fetched_at）を UTC で記録し、
    「いつシステムがそのデータを知り得たか」をトレース可能にする
  - 冪等性: DuckDB への INSERT は ON CONFLICT DO UPDATE で重複を排除する
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any

import duckdb

from kabusys.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_BASE_URL = "https://api.jquants.com/v2"
_RATE_LIMIT_PER_MIN = 120
_MIN_INTERVAL_SEC = 60.0 / _RATE_LIMIT_PER_MIN
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0  # 指数バックオフ係数（秒）
_RETRY_STATUS_CODES = {408, 429}  # ネットワーク起因の 4xx + 5xx 系


# ---------------------------------------------------------------------------
# レート制限（固定間隔スロットリング）
# ---------------------------------------------------------------------------


class _RateLimiter:
    """固定間隔スロットリングで API レート制限（120 req/min）を制御する。"""

    def __init__(self, min_interval: float = _MIN_INTERVAL_SEC) -> None:
        self._min_interval = min_interval
        self._last_called: float = 0.0

    def wait(self) -> None:
        """必要に応じてスリープし、レート制限を守る。"""
        elapsed = time.monotonic() - self._last_called
        wait_sec = self._min_interval - elapsed
        if wait_sec > 0:
            time.sleep(wait_sec)
        self._last_called = time.monotonic()


_rate_limiter = _RateLimiter()


# ---------------------------------------------------------------------------
# HTTP ユーティリティ
# ---------------------------------------------------------------------------


def _request(
    path: str,
    params: dict[str, str] | None = None,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
) -> Any:
    """J-Quants API へリクエストを送り、JSON を返す。

    Args:
        path: APIパス（例: "/equities/bars/daily"）
        params: クエリパラメータ
        method: HTTP メソッド（"GET" または "POST"）
        json_body: POST 時のリクエストボディ（dict）

    Returns:
        レスポンスの JSON データ。

    Raises:
        RuntimeError: 最大リトライ回数を超えた場合。
    """
    url = _BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers: dict[str, str] = {
        "Accept": "application/json",
        "x-api-key": settings.jquants_bulk_api_key,
    }
    data_bytes: bytes | None = None
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        data_bytes = json.dumps(json_body).encode("utf-8")

    def _do_call() -> Any:
        req = urllib.request.Request(url, headers=headers, method=method, data=data_bytes)
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"J-Quants API: JSON デコード失敗 ({path}): {raw[:200]!r}") from exc

    last_exc: Exception = RuntimeError("未初期化")
    for attempt in range(_MAX_RETRIES):
        _rate_limiter.wait()
        try:
            return _do_call()
        except urllib.error.HTTPError as e:
            status = e.code
            if status in _RETRY_STATUS_CODES or status >= 500:
                last_exc = e
                if attempt < _MAX_RETRIES - 1:  # 最終試行では sleep しない
                    # 429 は Retry-After ヘッダを優先、なければ指数バックオフ
                    wait = _RETRY_BACKOFF_BASE**attempt
                    if status == 429:
                        retry_after = e.headers.get("Retry-After") if e.headers else None
                        if retry_after:
                            try:
                                wait = float(retry_after)
                            except ValueError:
                                pass
                    logger.warning(
                        "HTTP %d on %s, retry %d/%d in %.1fs",
                        status,
                        path,
                        attempt + 1,
                        _MAX_RETRIES,
                        wait,
                    )
                    time.sleep(wait)
                continue
            # 4xx で再試行しないエラーはレスポンスボディをログに残して再 raise
            try:
                body = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                body = "(body読み取り失敗)"
            logger.error("HTTP %d on %s — response: %s", status, path, body)
            raise
        except (urllib.error.URLError, OSError) as e:
            last_exc = e
            if attempt < _MAX_RETRIES - 1:  # 最終試行では sleep しない
                wait = _RETRY_BACKOFF_BASE**attempt
                logger.warning(
                    "Network error on %s, retry %d/%d in %.1fs: %s",
                    path,
                    attempt + 1,
                    _MAX_RETRIES,
                    wait,
                    e,
                )
                time.sleep(wait)

    raise RuntimeError(
        f"J-Quants API リクエスト失敗 ({_MAX_RETRIES} 回リトライ済み): {path}"
    ) from last_exc


# ---------------------------------------------------------------------------
# データ取得関数
# ---------------------------------------------------------------------------


def fetch_daily_quotes(
    code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    """株価日足（OHLCV）を取得する（ページネーション対応）。

    v2 フィールド: O, H, L, C, Vo（出来高）, Va（売買代金）

    Args:
        code: 銘柄コード（省略時は全銘柄）。
        date_from: 取得開始日。
        date_to: 取得終了日。

    Returns:
        株価レコードのリスト。

    Note:
        J-Quants API は ``code`` 未指定時に ``date`` または ``code`` のどちらかを必須とする。
        ``code`` 未指定の場合は ``date`` パラメータで 1 日ずつ呼び出す。
    """
    result: list[dict[str, Any]] = []

    if code:
        # 銘柄コード指定: dateFrom/dateTo で範囲取得
        params: dict[str, str] = {"code": code}
        if date_from:
            params["dateFrom"] = date_from.strftime("%Y-%m-%d")
        if date_to:
            params["dateTo"] = date_to.strftime("%Y-%m-%d")
        seen_keys: set[str] = set()
        while True:
            data = _request("/equities/bars/daily", params=params)
            result.extend(data.get("data", []))
            pagination_key = data.get("pagination_key")
            if not pagination_key or pagination_key in seen_keys:
                break
            seen_keys.add(pagination_key)
            params["pagination_key"] = pagination_key
    else:
        # 全銘柄: API が date か code を必須とするため日付ごとに呼び出す
        d = date_from or date_to or date.today()
        end = date_to or d
        while d <= end:
            day_params: dict[str, str] = {"date": d.strftime("%Y-%m-%d")}
            seen_keys = set()
            while True:
                data = _request("/equities/bars/daily", params=day_params)
                result.extend(data.get("data", []))
                pagination_key = data.get("pagination_key")
                if not pagination_key or pagination_key in seen_keys:
                    break
                seen_keys.add(pagination_key)
                day_params["pagination_key"] = pagination_key
            d += timedelta(days=1)

    logger.info("fetch_daily_quotes: %d レコード取得", len(result))
    return result


def fetch_financial_statements(
    code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    """財務データ（四半期 BS/PL）を取得する（ページネーション対応）。

    Args:
        code: 銘柄コード（省略時は全銘柄）。
        date_from: 取得開始日。
        date_to: 取得終了日。

    Returns:
        財務レコードのリスト。

    Note:
        J-Quants API は ``code`` 未指定時に ``date`` または ``code`` のどちらかを必須とする。
        ``code`` 未指定の場合は ``date`` パラメータで 1 日ずつ呼び出す。
    """
    result: list[dict[str, Any]] = []

    if code:
        # 銘柄コード指定: dateFrom/dateTo で範囲取得
        params: dict[str, str] = {"code": code}
        if date_from:
            params["dateFrom"] = date_from.strftime("%Y-%m-%d")
        if date_to:
            params["dateTo"] = date_to.strftime("%Y-%m-%d")
        seen_keys: set[str] = set()
        while True:
            data = _request("/fins/summary", params=params)
            result.extend(data.get("data", []))
            pagination_key = data.get("pagination_key")
            if not pagination_key or pagination_key in seen_keys:
                break
            seen_keys.add(pagination_key)
            params["pagination_key"] = pagination_key
    else:
        # 全銘柄: API が date か code を必須とするため日付ごとに呼び出す
        d = date_from or date_to or date.today()
        end = date_to or d
        while d <= end:
            day_params: dict[str, str] = {"date": d.strftime("%Y-%m-%d")}
            seen_keys = set()
            while True:
                data = _request("/fins/summary", params=day_params)
                result.extend(data.get("data", []))
                pagination_key = data.get("pagination_key")
                if not pagination_key or pagination_key in seen_keys:
                    break
                seen_keys.add(pagination_key)
                day_params["pagination_key"] = pagination_key
            d += timedelta(days=1)

    logger.info("fetch_financial_statements: %d レコード取得", len(result))
    return result


def fetch_earnings_calendar(
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    """決算発表予定カレンダーを取得する（/equities/earnings-calendar）。

    Args:
        date_from: 取得開始日。
        date_to:   取得終了日。

    Returns:
        決算カレンダーレコードのリスト。各要素は {"Code": str, "Date": "YYYYMMDD"} を含む。
    """
    params: dict[str, str] = {}
    if date_from:
        params["dateFrom"] = date_from.strftime("%Y-%m-%d")
    if date_to:
        params["dateTo"] = date_to.strftime("%Y-%m-%d")
    # 注: /equities/earnings-calendar は 30日以内の窓であればページネーションなしで全件返す。
    # 30日超の範囲を指定する場合は pagination_key ループを追加すること。
    data = _request("/equities/earnings-calendar", params=params)
    records = data.get("data", [])
    logger.info("fetch_earnings_calendar: %d レコード取得", len(records))
    return records


def save_earnings_calendar(
    conn: duckdb.DuckDBPyConnection,
    records: list[dict[str, Any]],
) -> int:
    """決算カレンダーを earnings_calendar テーブルへ冪等保存する。

    Args:
        conn:    DuckDB 接続。
        records: fetch_earnings_calendar() の戻り値。

    Returns:
        保存を試みたレコード数（スキップ分を除く）。
    """
    rows: list[tuple] = []
    for r in records:
        code = r.get("Code", "")
        date_str = r.get("Date", "")
        if not code or not date_str:
            continue
        try:
            ann_date = date.fromisoformat(date_str[:10])
        except (ValueError, IndexError):
            logger.warning("save_earnings_calendar: 不正な日付フォーマット '%s'—スキップ", date_str)
            continue
        rows.append((code, ann_date))

    if not rows:
        return 0

    conn.executemany(
        """
        INSERT INTO earnings_calendar (code, announcement_date)
        VALUES (?, ?)
        ON CONFLICT DO NOTHING
        """,
        rows,
    )
    logger.info("save_earnings_calendar: %d 件を earnings_calendar に保存", len(rows))
    return len(rows)


def fetch_market_calendar(
    holiday_division: str | None = None,
) -> list[dict[str, Any]]:
    """JPX マーケットカレンダー（祝日・半日・SQ）を取得する。

    Args:
        holiday_division: 祝日区分フィルタ（省略時は全件）。

    Returns:
        カレンダーレコードのリスト。
    """
    params: dict[str, str] = {}
    if holiday_division:
        params["holidayDivision"] = holiday_division

    data = _request("/markets/calendar", params=params)
    records = data.get("data", [])
    logger.info("fetch_market_calendar: %d レコード取得", len(records))
    return records


# ---------------------------------------------------------------------------
# DuckDB への保存関数
# ---------------------------------------------------------------------------


def save_daily_quotes(
    conn: duckdb.DuckDBPyConnection,
    records: list[dict[str, Any]],
) -> int:
    """株価日足を raw_prices テーブルに保存する（冪等）。

    v2 フィールドマッピング: O→open, H→high, L→low, C→close, Vo→volume, Va→turnover

    Args:
        conn: DuckDB 接続。
        records: fetch_daily_quotes() の戻り値。

    Returns:
        挿入・更新したレコード数。
    """
    if not records:
        return 0

    fetched_at = datetime.now(tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    rows = [
        (
            r.get("Date"),
            str(r.get("Code", "") or ""),
            _to_float(r.get("O")),
            _to_float(r.get("H")),
            _to_float(r.get("L")),
            _to_float(r.get("C")),
            _to_int(r.get("Vo")),
            _to_int(r.get("Va")),
            fetched_at,
        )
        for r in records
        if r.get("Date") and r.get("Code")  # PK 欠損行はスキップ
    ]
    skipped = len(records) - len(rows)
    if skipped:
        logger.warning("save_daily_quotes: %d 件を PK 欠損によりスキップ", skipped)

    conn.executemany(
        """
        INSERT INTO raw_prices
            (date, code, open, high, low, close, volume, turnover, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (date, code) DO UPDATE SET
            open       = excluded.open,
            high       = excluded.high,
            low        = excluded.low,
            close      = excluded.close,
            volume     = excluded.volume,
            turnover   = excluded.turnover,
            fetched_at = excluded.fetched_at
        """,
        rows,
    )
    logger.info("save_daily_quotes: %d 件を raw_prices に保存", len(rows))
    return len(rows)


def save_financial_statements(
    conn: duckdb.DuckDBPyConnection,
    records: list[dict[str, Any]],
) -> int:
    """財務データを raw_financials テーブルに保存する（冪等）。

    Args:
        conn: DuckDB 接続。
        records: fetch_financial_statements() の戻り値。

    Returns:
        挿入・更新したレコード数。
    """
    if not records:
        return 0

    fetched_at = datetime.now(tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    rows = [
        (
            str(r.get("LocalCode", "") or ""),
            r.get("DisclosedDate"),
            r.get("TypeOfDocument", ""),
            _to_float(r.get("NetSales")),
            _to_float(r.get("OperatingProfit")),
            _to_float(r.get("Profit")),
            _to_float(r.get("EarningsPerShare")),
            _to_float(r.get("ROE")),
            _to_float(r.get("BookValuePerShare")),
            fetched_at,
        )
        for r in records
        if r.get("LocalCode")
        and r.get("DisclosedDate")
        and r.get("TypeOfDocument")  # PK 欠損行はスキップ
    ]
    skipped = len(records) - len(rows)
    if skipped:
        logger.warning("save_financial_statements: %d 件を PK 欠損によりスキップ", skipped)

    conn.executemany(
        """
        INSERT INTO raw_financials
            (code, report_date, period_type, revenue, operating_profit,
             net_income, eps, roe, bps, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (code, report_date, period_type) DO UPDATE SET
            revenue          = excluded.revenue,
            operating_profit = excluded.operating_profit,
            net_income       = excluded.net_income,
            eps              = excluded.eps,
            roe              = excluded.roe,
            bps              = excluded.bps,
            fetched_at       = excluded.fetched_at
        """,
        rows,
    )
    logger.info("save_financial_statements: %d 件を raw_financials に保存", len(rows))
    return len(rows)


def fetch_dividends(
    code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    """配当データを取得する（ページネーション対応）。

    Args:
        code:      銘柄コード（省略時は全銘柄）。
        date_from: 取得開始日。
        date_to:   取得終了日。

    Returns:
        配当レコードのリスト。
    """
    params: dict[str, str] = {}
    if code:
        params["code"] = code
    if date_from:
        params["dateFrom"] = date_from.strftime("%Y-%m-%d")
    if date_to:
        params["dateTo"] = date_to.strftime("%Y-%m-%d")

    result: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    while True:
        data = _request("/fins/dividend", params=params)
        result.extend(data.get("data", []))
        pagination_key = data.get("pagination_key")
        if not pagination_key or pagination_key in seen_keys:
            break
        seen_keys.add(pagination_key)
        params["pagination_key"] = pagination_key

    logger.info("fetch_dividends: %d レコード取得", len(result))
    return result


def save_dividends(
    conn: duckdb.DuckDBPyConnection,
    records: list[dict[str, Any]],
) -> int:
    """配当データを dividends テーブルに保存する（冪等）。

    Args:
        conn:    DuckDB 接続。
        records: fetch_dividends() の戻り値。
                 期待フィールド: Code, PubDate, RefNo, ExDate, RecDate, PayDate, DivRate

    Returns:
        挿入・更新したレコード数。
    """
    if not records:
        return 0

    fetched_at = datetime.now(tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    rows = [
        (
            str(r.get("Code", "") or ""),
            _to_date_str(r.get("PubDate")),
            str(r.get("RefNo", "") or ""),
            _to_date_str(r.get("ExDate")),
            _to_date_str(r.get("RecDate")),
            _to_date_str(r.get("PayDate")),
            _to_float(r.get("DivRate")),
            fetched_at,
        )
        for r in records
        if r.get("Code") and r.get("PubDate") and r.get("RefNo")
    ]
    skipped = len(records) - len(rows)
    if skipped:
        logger.warning("save_dividends: %d 件を PK 欠損によりスキップ", skipped)

    conn.executemany(
        """
        INSERT INTO dividends
            (code, pub_date, ref_no, ex_date, record_date, pay_date, div_rate, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (code, pub_date, ref_no) DO UPDATE SET
            ex_date     = excluded.ex_date,
            record_date = excluded.record_date,
            pay_date    = excluded.pay_date,
            div_rate    = excluded.div_rate,
            fetched_at  = excluded.fetched_at
        """,
        rows,
    )
    logger.info("save_dividends: %d 件を dividends に保存", len(rows))
    return len(rows)


def save_market_calendar(
    conn: duckdb.DuckDBPyConnection,
    records: list[dict[str, Any]],
) -> int:
    """カレンダーデータを market_calendar テーブルに保存する（冪等）。

    HolidayDivision の意味:
      "0" = 全日営業、"2" = SQ 日（全日取引あり）、"3" = 半日取引、
      その他 = 休場

    Args:
        conn: DuckDB 接続。
        records: fetch_market_calendar() の戻り値。

    Returns:
        挿入・更新したレコード数。
    """
    if not records:
        return 0

    rows = [
        (
            r.get("Date"),
            str(r.get("HolidayDivision", "")) in {"0", "2", "3"},  # 取引あり（型安全）
            str(r.get("HolidayDivision", "")) == "3",  # 半日
            str(r.get("HolidayDivision", "")) == "2",  # SQ 日
            r.get("HolidayName") or None,
        )
        for r in records
        if r.get("Date")  # PK 欠損行はスキップ
    ]
    skipped = len(records) - len(rows)
    if skipped:
        logger.warning("save_market_calendar: %d 件を PK 欠損によりスキップ", skipped)

    conn.executemany(
        """
        INSERT INTO market_calendar
            (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (date) DO UPDATE SET
            is_trading_day = excluded.is_trading_day,
            is_half_day    = excluded.is_half_day,
            is_sq_day      = excluded.is_sq_day,
            holiday_name   = excluded.holiday_name
        """,
        rows,
    )
    logger.info("save_market_calendar: %d 件を market_calendar に保存", len(rows))
    return len(rows)


def fetch_topix_daily(
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    """TOPIX 日足 OHLC を取得する（/indices/bars/daily/topix エンドポイント）。

    v2 フィールド: O, H, L, C

    Args:
        date_from: 取得開始日。
        date_to:   取得終了日。

    Returns:
        TOPIX 日足レコードのリスト。各要素は {"Date": "YYYYMMDD", "O": float, ...} を含む。
    """
    params: dict[str, str] = {}
    if date_from:
        params["dateFrom"] = date_from.strftime("%Y-%m-%d")
    if date_to:
        params["dateTo"] = date_to.strftime("%Y-%m-%d")
    data = _request("/indices/bars/daily/topix", params=params)
    records = data.get("data", [])
    logger.info("fetch_topix_daily: %d レコード取得", len(records))
    return records


def save_topix_daily(
    conn: duckdb.DuckDBPyConnection,
    records: list[dict[str, Any]],
) -> int:
    """TOPIX 日足データを topix_daily テーブルへ冪等保存する。

    v2 フィールドマッピング: O→open, H→high, L→low, C→close

    Args:
        conn:    DuckDB 接続。
        records: fetch_topix_daily() の戻り値。

    Returns:
        保存したレコード数。
    """
    rows: list[tuple] = []
    for r in records:
        date_str = r.get("Date", "")
        if not date_str:
            continue
        try:
            d = date.fromisoformat(date_str[:10])
        except (ValueError, IndexError):
            logger.warning("save_topix_daily: 不正な日付 '%s' — スキップ", date_str)
            continue
        o = _to_float(r.get("O"))
        h = _to_float(r.get("H"))
        lo = _to_float(r.get("L"))
        c = _to_float(r.get("C"))
        if None in (o, h, lo, c):
            logger.warning("save_topix_daily: OHLC 欠損行をスキップ: %s", r)
            continue
        rows.append((d, o, h, lo, c))
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT INTO topix_daily (date, open, high, low, close)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (date) DO UPDATE SET
            open=excluded.open, high=excluded.high, low=excluded.low, close=excluded.close
        """,
        rows,
    )
    logger.info("save_topix_daily: %d 件を topix_daily に保存", len(rows))
    return len(rows)


def fetch_listed_info(
    date_: date | None = None,
) -> list[dict[str, Any]]:
    """全上場銘柄情報を GET /equities/master から取得する。

    J-Quants API フィールドと stocks テーブルのマッピング:
        "Code"             → code
        "CompanyName"      → name
        "MarketCode"       → market（"0111"→"Prime", "0121"→"Standard", "0131"→"Growth", その他→"Other"）
        "Sector33CodeName" → sector

    Args:
        date_:    取得対象日（Look-ahead Bias 防止のため、取得日を明示することを推奨）。
                  省略時は当日のデータを返す。

    Returns:
        [{"code": str, "name": str, "market": str, "sector": str}, ...]
        Code が欠損するレコードはスキップ。

    Note:
        Look-ahead Bias 防止: バックテストで使用する場合は、バックテスト開始日
        以前に取得済みのデータを stocks テーブルに格納してから使用すること。
        本関数はデータ取得・ETL パイプライン専用であり、バックテストの内部ループから
        直接呼び出してはならない。
    """
    _MARKET_CODE_MAP: dict[str, str] = {
        "0111": "Prime",
        "0121": "Standard",
        "0131": "Growth",
    }

    params: dict[str, str] = {}
    if date_ is not None:
        params["date"] = date_.strftime("%Y-%m-%d")

    data = _request("/equities/master", params=params if params else None)
    records = data.get("data", [])

    result: list[dict[str, Any]] = []
    skipped = 0
    for r in records:
        code = str(r.get("Code") or "").strip()
        if not code:
            skipped += 1
            continue
        market_code = str(r.get("MarketCode") or "")
        result.append(
            {
                "code": code,
                "name": str(r.get("CompanyName") or ""),
                "market": _MARKET_CODE_MAP.get(market_code, "Other"),
                "sector": str(r.get("Sector33CodeName") or ""),
            }
        )

    if skipped:
        logger.warning("fetch_listed_info: %d 件を Code 欠損によりスキップ", skipped)
    logger.info("fetch_listed_info: %d 件取得", len(result))
    return result


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------


def _to_date_str(value: Any) -> str | None:
    """日付文字列を "YYYY-MM-DD" 形式に正規化する。

    J-Quants API は "YYYYMMDD" と "YYYY-MM-DD" の両形式を返すことがある。
    """
    if not value:
        return None
    s = str(value).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


def _to_float(value: Any) -> float | None:
    """値を float に変換する。変換失敗または空値は None を返す。"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_int(value: Any) -> int | None:
    """値を int に変換する。変換失敗または空値は None を返す。

    "1.0" のような float 文字列は float 経由で変換する。
    小数部が 0 以外（例: "1.9"）は意図しない切り捨てを防ぐため None を返す。
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        pass
    try:
        f = float(value)
        if f != int(f):  # 小数部が 0 以外は変換しない
            return None
        return int(f)
    except (ValueError, TypeError):
        return None
