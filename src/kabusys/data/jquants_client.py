"""
J-Quants API クライアント

J-Quants API から以下のデータを取得する。
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー（祝日・半日・SQ）

設計原則:
  - APIレート制限（120 req/min）を厳守する（RateLimiter による制御）
  - リトライロジック付き（指数バックオフ、最大 3 回）
  - Look-ahead Bias 防止: 取得日時（fetched_at）を記録し、
    「いつシステムがそのデータを知り得たか」をトレース可能にする
  - 冪等性: DuckDB への INSERT は INSERT OR REPLACE で重複を排除する
"""

from __future__ import annotations

import time
import logging
import urllib.request
import urllib.parse
import urllib.error
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb

from kabusys.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_BASE_URL = "https://api.jquants.com/v1"
_RATE_LIMIT_PER_MIN = 120          # J-Quants APIレート上限
_MIN_INTERVAL_SEC = 60.0 / _RATE_LIMIT_PER_MIN  # リクエスト間最小間隔
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0          # 指数バックオフ係数（秒）


# ---------------------------------------------------------------------------
# レート制限
# ---------------------------------------------------------------------------

class _RateLimiter:
    """トークンバケット方式でAPIレート制限を制御する。"""

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
    id_token: str | None = None,
) -> Any:
    """J-Quants API へ GET リクエストを送り、JSON を返す。

    Args:
        path: APIパス（例: "/prices/daily_quotes"）
        params: クエリパラメータ
        id_token: 認証トークン（省略時は refresh_token から自動取得）

    Returns:
        レスポンスの JSON データ。

    Raises:
        RuntimeError: 最大リトライ回数を超えた場合。
    """
    url = _BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if id_token:
        headers["Authorization"] = f"Bearer {id_token}"

    last_exc: Exception = RuntimeError("未初期化")
    for attempt in range(_MAX_RETRIES):
        _rate_limiter.wait()
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            status = e.code
            if status == 429 or status >= 500:
                wait = _RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    "HTTP %d on %s, retry %d/%d in %.1fs",
                    status, path, attempt + 1, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
                last_exc = e
                continue
            raise
        except (urllib.error.URLError, OSError) as e:
            wait = _RETRY_BACKOFF_BASE ** attempt
            logger.warning(
                "Network error on %s, retry %d/%d in %.1fs: %s",
                path, attempt + 1, _MAX_RETRIES, wait, e,
            )
            time.sleep(wait)
            last_exc = e

    raise RuntimeError(
        f"J-Quants API リクエスト失敗 ({_MAX_RETRIES} 回リトライ済み): {path}"
    ) from last_exc


# ---------------------------------------------------------------------------
# 認証
# ---------------------------------------------------------------------------

def get_id_token(refresh_token: str | None = None) -> str:
    """リフレッシュトークンから ID トークンを取得する。

    Args:
        refresh_token: J-Quants リフレッシュトークン。
                       省略時は settings.jquants_refresh_token を使用。

    Returns:
        ID トークン文字列。
    """
    token = refresh_token or settings.jquants_refresh_token
    url = _BASE_URL + "/token/auth_refresh"
    params = {"refreshtoken": token}
    data = _request("/token/auth_refresh", params=params)
    return data["idToken"]


# ---------------------------------------------------------------------------
# データ取得関数
# ---------------------------------------------------------------------------

def fetch_daily_quotes(
    id_token: str,
    code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    """株価日足（OHLCV）を取得する。

    Args:
        id_token: 認証トークン。
        code: 銘柄コード（省略時は全銘柄）。
        date_from: 取得開始日（省略時は当日）。
        date_to: 取得終了日（省略時は当日）。

    Returns:
        株価レコードのリスト。各レコードは dict。
    """
    params: dict[str, str] = {}
    if code:
        params["code"] = code
    if date_from:
        params["dateFrom"] = date_from.strftime("%Y%m%d")
    if date_to:
        params["dateTo"] = date_to.strftime("%Y%m%d")

    result: list[dict[str, Any]] = []
    while True:
        data = _request("/prices/daily_quotes", params=params, id_token=id_token)
        result.extend(data.get("daily_quotes", []))
        pagination_key = data.get("pagination_key")
        if not pagination_key:
            break
        params["pagination_key"] = pagination_key

    logger.info("fetch_daily_quotes: %d レコード取得", len(result))
    return result


def fetch_financial_statements(
    id_token: str,
    code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    """財務データ（四半期 BS/PL）を取得する。

    Args:
        id_token: 認証トークン。
        code: 銘柄コード（省略時は全銘柄）。
        date_from: 取得開始日。
        date_to: 取得終了日。

    Returns:
        財務レコードのリスト。
    """
    params: dict[str, str] = {}
    if code:
        params["code"] = code
    if date_from:
        params["dateFrom"] = date_from.strftime("%Y%m%d")
    if date_to:
        params["dateTo"] = date_to.strftime("%Y%m%d")

    result: list[dict[str, Any]] = []
    while True:
        data = _request("/fins/statements", params=params, id_token=id_token)
        result.extend(data.get("statements", []))
        pagination_key = data.get("pagination_key")
        if not pagination_key:
            break
        params["pagination_key"] = pagination_key

    logger.info("fetch_financial_statements: %d レコード取得", len(result))
    return result


def fetch_market_calendar(
    id_token: str,
    holiday_division: str | None = None,
) -> list[dict[str, Any]]:
    """JPX マーケットカレンダー（祝日・半日・SQ）を取得する。

    Args:
        id_token: 認証トークン。
        holiday_division: 祝日区分フィルタ（省略時は全件）。

    Returns:
        カレンダーレコードのリスト。
    """
    params: dict[str, str] = {}
    if holiday_division:
        params["holidayDivision"] = holiday_division

    data = _request("/markets/trading_calendar", params=params, id_token=id_token)
    records = data.get("trading_calendar", [])
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

    Args:
        conn: DuckDB 接続。
        records: fetch_daily_quotes() の戻り値。

    Returns:
        挿入・更新したレコード数。
    """
    if not records:
        return 0

    fetched_at = datetime.utcnow().isoformat(timespec="seconds")
    rows = [
        (
            r.get("Date"),
            str(r.get("Code", "")),
            _to_float(r.get("Open")),
            _to_float(r.get("High")),
            _to_float(r.get("Low")),
            _to_float(r.get("Close")),
            _to_float(r.get("Volume")),
            _to_float(r.get("TurnoverValue")),
            fetched_at,
        )
        for r in records
    ]

    conn.executemany(
        """
        INSERT OR REPLACE INTO raw_prices
            (date, code, open, high, low, close, volume, turnover, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    fetched_at = datetime.utcnow().isoformat(timespec="seconds")
    rows = [
        (
            str(r.get("LocalCode", "")),
            r.get("DisclosedDate"),
            r.get("TypeOfDocument", ""),
            _to_float(r.get("NetSales")),
            _to_float(r.get("OperatingProfit")),
            _to_float(r.get("Profit")),
            _to_float(r.get("EarningsPerShare")),
            _to_float(r.get("ROE")),
            fetched_at,
        )
        for r in records
    ]

    conn.executemany(
        """
        INSERT OR REPLACE INTO raw_financials
            (code, report_date, period_type, revenue, operating_profit,
             net_income, eps, roe, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    logger.info("save_financial_statements: %d 件を raw_financials に保存", len(rows))
    return len(rows)


def save_market_calendar(
    conn: duckdb.DuckDBPyConnection,
    records: list[dict[str, Any]],
) -> int:
    """カレンダーデータを market_calendar テーブルに保存する（冪等）。

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
            r.get("HolidayDivision") == "0",     # "0" = 営業日
            r.get("HolidayDivision") == "3",     # "3" = 半日
            r.get("HolidayDivision") == "2",     # "2" = SQ日
            r.get("HolidayName") or None,
        )
        for r in records
    ]

    conn.executemany(
        """
        INSERT OR REPLACE INTO market_calendar
            (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    logger.info("save_market_calendar: %d 件を market_calendar に保存", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def _to_float(value: Any) -> float | None:
    """文字列または None を float に変換する。変換失敗時は None を返す。"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
