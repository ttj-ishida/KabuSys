"""
J-Quants API クライアント

J-Quants API から以下のデータを取得する。
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー（祝日・半日・SQ）

設計原則:
  - APIレート制限（120 req/min）を厳守する（RateLimiter による制御）
  - リトライロジック付き（指数バックオフ、最大 3 回、対象: 408/429/5xx）
  - 401 受信時はトークンを自動リフレッシュして 1 回リトライ
  - Look-ahead Bias 防止: 取得日時（fetched_at）を UTC で記録し、
    「いつシステムがそのデータを知り得たか」をトレース可能にする
  - 冪等性: DuckDB への INSERT は ON CONFLICT DO UPDATE で重複を排除する
"""

from __future__ import annotations

import time
import logging
import urllib.request
import urllib.parse
import urllib.error
import json
from datetime import datetime, timezone
from datetime import date
from typing import Any

import duckdb

from kabusys.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_BASE_URL = "https://api.jquants.com/v1"
_RATE_LIMIT_PER_MIN = 120
_MIN_INTERVAL_SEC = 60.0 / _RATE_LIMIT_PER_MIN
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0          # 指数バックオフ係数（秒）
_RETRY_STATUS_CODES = {408, 429}   # ネットワーク起因の 4xx + 5xx 系


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

# モジュールレベルの ID トークンキャッシュ（ページネーション間でトークンを共有）
_ID_TOKEN_CACHE: str | None = None


def _get_cached_token(force_refresh: bool = False) -> str:
    """キャッシュ済み ID トークンを返す。未取得または force_refresh=True 時は再取得する。"""
    global _ID_TOKEN_CACHE
    if force_refresh or not _ID_TOKEN_CACHE:
        _ID_TOKEN_CACHE = get_id_token()
    return _ID_TOKEN_CACHE


# ---------------------------------------------------------------------------
# HTTP ユーティリティ
# ---------------------------------------------------------------------------

def _request(
    path: str,
    params: dict[str, str] | None = None,
    id_token: str | None = None,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
    allow_refresh: bool = True,
) -> Any:
    """J-Quants API へリクエストを送り、JSON を返す。

    Args:
        path: APIパス（例: "/prices/daily_quotes"）
        params: クエリパラメータ
        id_token: 認証トークン
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

    headers: dict[str, str] = {"Accept": "application/json"}
    data_bytes: bytes | None = None
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        data_bytes = json.dumps(json_body).encode("utf-8")

    def _do_call(token: str | None) -> Any:
        h = dict(headers)
        if token:
            h["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(
            url, headers=h, method=method, data=data_bytes
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"J-Quants API: JSON デコード失敗 ({path}): {raw[:200]!r}"
            ) from exc

    last_exc: Exception = RuntimeError("未初期化")
    # id_token 未指定時はキャッシュを使用（ページネーション間でトークンを共有）
    token = id_token or (_get_cached_token() if allow_refresh else None)
    _token_refreshed = False  # 401 リフレッシュは 1 回のみ保証
    for attempt in range(_MAX_RETRIES):
        _rate_limiter.wait()
        try:
            return _do_call(token)
        except urllib.error.HTTPError as e:
            status = e.code
            # 401: トークン期限切れ → 1 回だけリフレッシュしてリトライ
            # allow_refresh=False の場合（get_id_token からの呼び出し等）は無限再帰を防ぐ
            if status == 401 and allow_refresh and not _token_refreshed:
                logger.warning("401 Unauthorized on %s, refreshing id_token", path)
                try:
                    token = _get_cached_token(force_refresh=True)  # キャッシュも更新
                    _token_refreshed = True
                    continue
                except Exception as refresh_exc:
                    raise RuntimeError(
                        "id_token のリフレッシュに失敗しました"
                    ) from refresh_exc
            if status == 401:
                raise  # リフレッシュ済みで再度 401 → 即座に失敗
            if status in _RETRY_STATUS_CODES or status >= 500:
                last_exc = e
                if attempt < _MAX_RETRIES - 1:  # 最終試行では sleep しない
                    # 429 は Retry-After ヘッダを優先、なければ指数バックオフ
                    wait = _RETRY_BACKOFF_BASE ** attempt
                    if status == 429:
                        retry_after = e.headers.get("Retry-After") if e.headers else None
                        if retry_after:
                            try:
                                wait = float(retry_after)
                            except ValueError:
                                pass
                    logger.warning(
                        "HTTP %d on %s, retry %d/%d in %.1fs",
                        status, path, attempt + 1, _MAX_RETRIES, wait,
                    )
                    time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, OSError) as e:
            last_exc = e
            if attempt < _MAX_RETRIES - 1:  # 最終試行では sleep しない
                wait = _RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    "Network error on %s, retry %d/%d in %.1fs: %s",
                    path, attempt + 1, _MAX_RETRIES, wait, e,
                )
                time.sleep(wait)

    raise RuntimeError(
        f"J-Quants API リクエスト失敗 ({_MAX_RETRIES} 回リトライ済み): {path}"
    ) from last_exc


# ---------------------------------------------------------------------------
# 認証
# ---------------------------------------------------------------------------

def get_id_token(refresh_token: str | None = None) -> str:
    """リフレッシュトークンから ID トークンを取得する（POST）。

    Args:
        refresh_token: J-Quants リフレッシュトークン。
                       省略時は settings.jquants_refresh_token を使用。

    Returns:
        ID トークン文字列。
    """
    token = refresh_token or settings.jquants_refresh_token
    if not token:
        raise ValueError("refresh_token が指定されていません")
    data = _request(
        "/token/auth_refresh",
        method="POST",
        json_body={"refreshtoken": token},
        allow_refresh=False,  # 無限再帰防止
    )
    return data["idToken"]


# ---------------------------------------------------------------------------
# データ取得関数
# ---------------------------------------------------------------------------

def fetch_daily_quotes(
    id_token: str | None = None,
    code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    """株価日足（OHLCV）を取得する（ページネーション対応）。

    Args:
        id_token: 認証トークン。省略時はモジュールキャッシュを使用（自動リフレッシュ対応）。
        code: 銘柄コード（省略時は全銘柄）。
        date_from: 取得開始日。
        date_to: 取得終了日。

    Returns:
        株価レコードのリスト。
    """
    params: dict[str, str] = {}
    if code:
        params["code"] = code
    if date_from:
        params["dateFrom"] = date_from.strftime("%Y%m%d")
    if date_to:
        params["dateTo"] = date_to.strftime("%Y%m%d")

    result: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    while True:
        data = _request("/prices/daily_quotes", params=params, id_token=id_token)
        result.extend(data.get("daily_quotes", []))
        pagination_key = data.get("pagination_key")
        if not pagination_key or pagination_key in seen_keys:
            break
        seen_keys.add(pagination_key)
        params["pagination_key"] = pagination_key

    logger.info("fetch_daily_quotes: %d レコード取得", len(result))
    return result


def fetch_financial_statements(
    id_token: str | None = None,
    code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    """財務データ（四半期 BS/PL）を取得する（ページネーション対応）。

    Args:
        id_token: 認証トークン。省略時はモジュールキャッシュを使用（自動リフレッシュ対応）。
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
    seen_keys: set[str] = set()
    while True:
        data = _request("/fins/statements", params=params, id_token=id_token)
        result.extend(data.get("statements", []))
        pagination_key = data.get("pagination_key")
        if not pagination_key or pagination_key in seen_keys:
            break
        seen_keys.add(pagination_key)
        params["pagination_key"] = pagination_key

    logger.info("fetch_financial_statements: %d レコード取得", len(result))
    return result


def fetch_market_calendar(
    id_token: str | None = None,
    holiday_division: str | None = None,
) -> list[dict[str, Any]]:
    """JPX マーケットカレンダー（祝日・半日・SQ）を取得する。

    Args:
        id_token: 認証トークン。省略時はモジュールキャッシュを使用（自動リフレッシュ対応）。
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

    fetched_at = datetime.now(tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    rows = [
        (
            r.get("Date"),
            str(r.get("Code", "") or ""),
            _to_float(r.get("Open")),
            _to_float(r.get("High")),
            _to_float(r.get("Low")),
            _to_float(r.get("Close")),
            _to_int(r.get("Volume")),
            _to_int(r.get("TurnoverValue")),
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
            fetched_at,
        )
        for r in records
        if r.get("LocalCode") and r.get("DisclosedDate") and r.get("TypeOfDocument")  # PK 欠損行はスキップ
    ]
    skipped = len(records) - len(rows)
    if skipped:
        logger.warning("save_financial_statements: %d 件を PK 欠損によりスキップ", skipped)

    conn.executemany(
        """
        INSERT INTO raw_financials
            (code, report_date, period_type, revenue, operating_profit,
             net_income, eps, roe, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (code, report_date, period_type) DO UPDATE SET
            revenue          = excluded.revenue,
            operating_profit = excluded.operating_profit,
            net_income       = excluded.net_income,
            eps              = excluded.eps,
            roe              = excluded.roe,
            fetched_at       = excluded.fetched_at
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
            str(r.get("HolidayDivision", "")) == "3",               # 半日
            str(r.get("HolidayDivision", "")) == "2",               # SQ 日
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


def fetch_listed_info(
    id_token: str | None = None,
    date_: date | None = None,
) -> list[dict[str, Any]]:
    """全上場銘柄情報を GET /listed/info から取得する。

    J-Quants API フィールドと stocks テーブルのマッピング:
        "Code"             → code
        "CompanyName"      → name
        "MarketCode"       → market（"0111"→"Prime", "0121"→"Standard", "0131"→"Growth", その他→"Other"）
        "Sector33CodeName" → sector

    Args:
        id_token: 認証トークン。省略時はモジュールキャッシュを使用。
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
        params["date"] = date_.strftime("%Y%m%d")

    data = _request("/listed/info", params=params if params else None, id_token=id_token)
    records = data.get("info", [])

    result: list[dict[str, Any]] = []
    skipped = 0
    for r in records:
        code = str(r.get("Code") or "").strip()
        if not code:
            skipped += 1
            continue
        market_code = str(r.get("MarketCode") or "")
        result.append({
            "code": code,
            "name": str(r.get("CompanyName") or ""),
            "market": _MARKET_CODE_MAP.get(market_code, "Other"),
            "sector": str(r.get("Sector33CodeName") or ""),
        })

    if skipped:
        logger.warning("fetch_listed_info: %d 件を Code 欠損によりスキップ", skipped)
    logger.info("fetch_listed_info: %d 件取得", len(result))
    return result


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

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
