"""
ETLパイプラインモジュール

DataPlatform.md Section 4, 5, 6 に基づき、以下のETL処理を実現する。

処理フロー:
  1. 差分更新: DBの最終取得日を確認し、新規データのみをAPIから取得する
  2. 保存: jquants_client の save_* 関数でIdempotentに保存する（ON CONFLICT DO UPDATE）
  3. 品質チェック: quality モジュールで欠損・スパイク・重複・日付不整合を検出する

設計方針:
  - 差分更新のデフォルト単位は「営業日1日分」とし、未取得の範囲を自動算出する
  - backfill_days により最終取得日の数日前から再取得し、API 後出し修正を吸収する
  - 品質チェックはエラー重大度を持つ問題が検出されてもETLを継続し、
    呼び出し元がアクションを決定する（Fail-Fastではなく全件収集）
  - 引数で id_token を注入可能にしてテスト容易性を確保する
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

import duckdb

from kabusys.data import jquants_client as jq
from kabusys.data import quality

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

# J-Quants が提供する株価データの開始日（初回ロード時に使用）
_MIN_DATA_DATE = date(2017, 1, 1)

# 市場カレンダーの先読み日数（当日より未来のカレンダーを事前に取得する）
_CALENDAR_LOOKAHEAD_DAYS = 90

# デフォルトのバックフィル日数（最終取得日の数日前から再取得して後出し修正を吸収）
_DEFAULT_BACKFILL_DAYS = 3

# 品質チェックの重大度定数（quality.QualityIssue.severity と一致させる）
_SEVERITY_ERROR = "error"


# ---------------------------------------------------------------------------
# 結果データクラス
# ---------------------------------------------------------------------------


@dataclass
class ETLResult:
    """ETL実行結果を格納するデータクラス。

    Attributes:
        target_date:       ETL対象日。
        prices_fetched:    取得した株価レコード数。
        prices_saved:      DBに保存した株価レコード数。
        financials_fetched: 取得した財務レコード数。
        financials_saved:  DBに保存した財務レコード数。
        calendar_fetched:  取得したカレンダーレコード数。
        calendar_saved:    DBに保存したカレンダーレコード数。
        quality_issues:    品質チェックで検出された問題のリスト。
        errors:            処理中に発生したエラーの概要メッセージのリスト。
    """

    target_date: date
    prices_fetched: int = 0
    prices_saved: int = 0
    financials_fetched: int = 0
    financials_saved: int = 0
    calendar_fetched: int = 0
    calendar_saved: int = 0
    quality_issues: list[quality.QualityIssue] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """ETL処理中に致命的なエラーが発生したかどうか。"""
        return bool(self.errors)

    @property
    def has_quality_errors(self) -> bool:
        """品質チェックでエラー重大度の問題が検出されたかどうか。"""
        return any(i.severity == _SEVERITY_ERROR for i in self.quality_issues)

    def to_dict(self) -> dict[str, Any]:
        """ETLResult を辞書に変換する（監査ログ書き込みやデバッグに利用）。

        quality_issues は (check_name, severity, message) のタプルリストに変換する。

        Returns:
            ETLResult の全フィールドを含む辞書。
        """
        d = asdict(self)
        d["quality_issues"] = [
            {"check_name": i.check_name, "severity": i.severity, "message": i.message}
            for i in self.quality_issues
        ]
        return d


# ---------------------------------------------------------------------------
# 内部ユーティリティ
# ---------------------------------------------------------------------------


def _table_exists(conn: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    """指定テーブルが DuckDB に存在するかを確認する。

    Args:
        conn:       DuckDB 接続。
        table_name: テーブル名。

    Returns:
        テーブルが存在する場合 True。
    """
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return row is not None


def _get_max_date(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    date_column: str,
) -> date | None:
    """テーブルの指定カラムの最大日付を返す。

    テーブルが存在しない、またはテーブルが空の場合は None を返す。

    Args:
        conn:        DuckDB 接続。
        table_name:  テーブル名。
        date_column: 日付カラム名。

    Returns:
        最大日付。テーブル未作成または空の場合は None。
    """
    if not _table_exists(conn, table_name):
        return None
    row = conn.execute(
        f"SELECT MAX({date_column}) FROM {table_name}"  # noqa: S608
    ).fetchone()
    if row and row[0] is not None:
        val = row[0]
        if isinstance(val, date):
            return val
        return date.fromisoformat(str(val))
    return None


# ---------------------------------------------------------------------------
# 市場カレンダーヘルパー
# ---------------------------------------------------------------------------


def _adjust_to_trading_day(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> date:
    """target_date が非営業日なら、直近の営業日（過去方向）に調整して返す。

    market_calendar テーブルが存在しない、またはカレンダーデータがない場合は
    target_date をそのまま返す（カレンダー未取得時のフォールバック）。

    Args:
        conn:        DuckDB 接続。
        target_date: 調整対象の日付。

    Returns:
        target_date またはそれ以前で最も近い営業日。
    """
    if not _table_exists(conn, "market_calendar"):
        return target_date

    # target_date 以前で最も新しい営業日を取得（最大 30 日遡る）
    look_back = target_date - timedelta(days=30)
    row = conn.execute(
        """
        SELECT MAX(date) FROM market_calendar
        WHERE date <= ? AND date >= ? AND is_trading_day = true
        """,
        [target_date, look_back],
    ).fetchone()

    if row and row[0] is not None:
        val = row[0]
        adjusted = val if isinstance(val, date) else date.fromisoformat(str(val))
        if adjusted != target_date:
            logger.info(
                "_adjust_to_trading_day: %s は非営業日のため %s に調整",
                target_date,
                adjusted,
            )
        return adjusted

    return target_date


# ---------------------------------------------------------------------------
# 差分更新ヘルパー
# ---------------------------------------------------------------------------


def get_last_price_date(conn: duckdb.DuckDBPyConnection) -> date | None:
    """raw_prices テーブルの最終取得日を返す。

    テーブルが存在しない、または空の場合は None を返す。

    Args:
        conn: DuckDB 接続。

    Returns:
        最終取得日。テーブル未作成または空の場合は None。
    """
    return _get_max_date(conn, "raw_prices", "date")


def get_last_financial_date(conn: duckdb.DuckDBPyConnection) -> date | None:
    """raw_financials テーブルの最終取得日（report_date）を返す。

    Args:
        conn: DuckDB 接続。

    Returns:
        最終取得日。テーブル未作成または空の場合は None。
    """
    return _get_max_date(conn, "raw_financials", "report_date")


def get_last_calendar_date(conn: duckdb.DuckDBPyConnection) -> date | None:
    """market_calendar テーブルの最終取得日を返す。

    Args:
        conn: DuckDB 接続。

    Returns:
        最終取得日。テーブル未作成または空の場合は None。
    """
    return _get_max_date(conn, "market_calendar", "date")


# ---------------------------------------------------------------------------
# 個別ETLジョブ
# ---------------------------------------------------------------------------


def run_prices_etl(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    id_token: str | None = None,
    date_from: date | None = None,
    backfill_days: int = _DEFAULT_BACKFILL_DAYS,
) -> tuple[int, int]:
    """株価日足の差分ETLを実行する。

    差分更新: date_from が指定されていない場合、DBの最終取得日から
    backfill_days 日前を date_from として再取得する（API 後出し修正の吸収）。

    Args:
        conn:          DuckDB 接続。
        target_date:   取得終了日（通常は当日）。
        id_token:      J-Quants 認証トークン。
        date_from:     取得開始日。省略時は最終取得日 - backfill_days + 1。
        backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3 日）。

    Returns:
        (取得レコード数, 保存レコード数) のタプル。
    """
    if date_from is None:
        last = get_last_price_date(conn)
        if last is not None:
            date_from = max(_MIN_DATA_DATE, last - timedelta(days=backfill_days - 1))
        else:
            date_from = _MIN_DATA_DATE

    if date_from > target_date:
        logger.info(
            "run_prices_etl: すでに最新 date_from=%s target=%s",
            date_from,
            target_date,
        )
        return 0, 0

    logger.info("run_prices_etl: date_from=%s date_to=%s", date_from, target_date)
    records = jq.fetch_daily_quotes(
        id_token=id_token,
        date_from=date_from,
        date_to=target_date,
    )
    saved = jq.save_daily_quotes(conn, records)
    logger.info("run_prices_etl: fetched=%d saved=%d", len(records), saved)
    return len(records), saved


def run_financials_etl(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    id_token: str | None = None,
    date_from: date | None = None,
    backfill_days: int = _DEFAULT_BACKFILL_DAYS,
) -> tuple[int, int]:
    """財務データの差分ETLを実行する。

    差分更新: date_from が指定されていない場合、DBの最終取得日から
    backfill_days 日前を date_from として再取得する（API 後出し修正の吸収）。

    Args:
        conn:          DuckDB 接続。
        target_date:   取得終了日。
        id_token:      J-Quants 認証トークン。
        date_from:     取得開始日。省略時は最終取得日 - backfill_days + 1。
        backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3 日）。

    Returns:
        (取得レコード数, 保存レコード数) のタプル。
    """
    if date_from is None:
        last = get_last_financial_date(conn)
        if last is not None:
            date_from = max(_MIN_DATA_DATE, last - timedelta(days=backfill_days - 1))
        else:
            date_from = _MIN_DATA_DATE

    if date_from > target_date:
        logger.info(
            "run_financials_etl: すでに最新 date_from=%s target=%s",
            date_from,
            target_date,
        )
        return 0, 0

    logger.info("run_financials_etl: date_from=%s date_to=%s", date_from, target_date)
    records = jq.fetch_financial_statements(
        id_token=id_token,
        date_from=date_from,
        date_to=target_date,
    )
    saved = jq.save_financial_statements(conn, records)
    logger.info("run_financials_etl: fetched=%d saved=%d", len(records), saved)
    return len(records), saved


def run_calendar_etl(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    id_token: str | None = None,
    date_from: date | None = None,
    lookahead_days: int = _CALENDAR_LOOKAHEAD_DAYS,
) -> tuple[int, int]:
    """市場カレンダーの差分ETLを実行する。

    差分更新: date_from が指定されていない場合、DBの最終取得日の翌日から
    target_date + lookahead_days までのデータを取得する。

    Args:
        conn:           DuckDB 接続。
        target_date:    基準日。
        id_token:       J-Quants 認証トークン。
        date_from:      取得開始日。省略時は最終取得日の翌日。
        lookahead_days: 基準日から何日先まで取得するか（デフォルト 90 日）。

    Returns:
        (取得レコード数, 保存レコード数) のタプル。
    """
    date_to = target_date + timedelta(days=lookahead_days)

    if date_from is None:
        last = get_last_calendar_date(conn)
        date_from = (last + timedelta(days=1)) if last is not None else _MIN_DATA_DATE

    if date_from > date_to:
        logger.info(
            "run_calendar_etl: すでに最新 date_from=%s date_to=%s",
            date_from,
            date_to,
        )
        return 0, 0

    logger.info("run_calendar_etl: date_from=%s date_to=%s", date_from, date_to)
    records = jq.fetch_market_calendar(
        id_token=id_token,
        date_from=date_from,
        date_to=date_to,
    )
    saved = jq.save_market_calendar(conn, records)
    logger.info("run_calendar_etl: fetched=%d saved=%d", len(records), saved)
    return len(records), saved


# ---------------------------------------------------------------------------
# メインETLエントリポイント
# ---------------------------------------------------------------------------


def run_daily_etl(
    conn: duckdb.DuckDBPyConnection,
    target_date: date | None = None,
    id_token: str | None = None,
    run_quality_checks: bool = True,
    spike_threshold: float = 0.5,
    backfill_days: int = _DEFAULT_BACKFILL_DAYS,
    calendar_lookahead_days: int = _CALENDAR_LOOKAHEAD_DAYS,
) -> ETLResult:
    """日次ETLパイプラインを実行する。

    株価・財務・カレンダーデータの差分取得、保存、品質チェックを一括して実行する。
    各ステップは独立してエラーハンドリングされ、1ステップ失敗でも他ステップは継続する。

    処理順:
      1. 市場カレンダーETL（lookahead_days 先まで取得）
      2. 株価日足ETL（差分更新 + backfill）
      3. 財務データETL（差分更新 + backfill）
      4. 品質チェック（オプション）

    Args:
        conn:                    DuckDB 接続。
        target_date:             ETL対象日。省略時は今日。
        id_token:                J-Quants 認証トークン。省略時はキャッシュを使用。
        run_quality_checks:      True の場合、ETL後に品質チェックを実行する。
        spike_threshold:         スパイク検出閾値（デフォルト 0.5 = 50%）。
        backfill_days:           株価・財務ETLのバックフィル日数（デフォルト 3 日）。
        calendar_lookahead_days: カレンダーの先読み日数（デフォルト 90 日）。

    Returns:
        ETLResult オブジェクト。
    """
    today = target_date or date.today()
    result = ETLResult(target_date=today)

    # 1. 市場カレンダーETL（先に取得して営業日調整に使用できるようにする）
    try:
        fetched, saved = run_calendar_etl(
            conn, today, id_token=id_token, lookahead_days=calendar_lookahead_days
        )
        result.calendar_fetched = fetched
        result.calendar_saved = saved
    except Exception:
        logger.exception("run_calendar_etl 失敗")
        result.errors.append("run_calendar_etl 失敗")

    # カレンダー取得後に対象日を営業日に調整する
    trading_day = _adjust_to_trading_day(conn, today)

    # 2. 株価日足ETL
    try:
        fetched, saved = run_prices_etl(
            conn, trading_day, id_token=id_token, backfill_days=backfill_days
        )
        result.prices_fetched = fetched
        result.prices_saved = saved
    except Exception:
        logger.exception("run_prices_etl 失敗")
        result.errors.append("run_prices_etl 失敗")

    # 3. 財務データETL
    try:
        fetched, saved = run_financials_etl(
            conn, trading_day, id_token=id_token, backfill_days=backfill_days
        )
        result.financials_fetched = fetched
        result.financials_saved = saved
    except Exception:
        logger.exception("run_financials_etl 失敗")
        result.errors.append("run_financials_etl 失敗")

    # 4. 品質チェック
    if run_quality_checks:
        try:
            result.quality_issues = quality.run_all_checks(
                conn,
                target_date=trading_day,
                reference_date=trading_day,
                spike_threshold=spike_threshold,
            )
        except Exception:
            logger.exception("品質チェック失敗")
            result.errors.append("品質チェック失敗")

    logger.info(
        "run_daily_etl 完了: date=%s "
        "prices fetched=%d saved=%d "
        "financials fetched=%d saved=%d "
        "calendar fetched=%d saved=%d "
        "quality_issues=%d errors=%d",
        today,
        result.prices_fetched,
        result.prices_saved,
        result.financials_fetched,
        result.financials_saved,
        result.calendar_fetched,
        result.calendar_saved,
        len(result.quality_issues),
        len(result.errors),
    )
    return result
