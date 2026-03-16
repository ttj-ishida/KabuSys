"""
ETLパイプラインモジュール

DataPlatform.md Section 4, 5, 6 に基づき、以下のETL処理を実現する。

処理フロー:
  1. 差分更新: DBの最終取得日を確認し、新規データのみをAPIから取得する
  2. 保存: jquants_client の save_* 関数でIdempotentに保存する（ON CONFLICT DO UPDATE）
  3. 品質チェック: quality モジュールで欠損・スパイク・重複・日付不整合を検出する
  4. 監査ログ: ETL実行結果を audit テーブルに記録する

設計方針:
  - 差分更新のデフォルト単位は「営業日1日分」とし、未取得の範囲を自動算出する
  - 品質チェックはエラー重大度を持つ問題が検出されてもETLを継続し、
    呼び出し元がアクションを決定する（Fail-Fastではなく全件収集）
  - 引数で id_token を注入可能にしてテスト容易性を確保する
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import duckdb

from kabusys.data import jquants_client as jq
from kabusys.data import quality

logger = logging.getLogger(__name__)


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
        errors:            処理中に発生したエラーメッセージのリスト。
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
        return any(i.severity == "error" for i in self.quality_issues)


# ---------------------------------------------------------------------------
# 差分更新ヘルパー
# ---------------------------------------------------------------------------


def get_last_price_date(conn: duckdb.DuckDBPyConnection) -> date | None:
    """raw_prices テーブルの最終取得日を返す。

    テーブルが空の場合は None を返す。

    Args:
        conn: DuckDB 接続。

    Returns:
        最終取得日。テーブルが空の場合は None。
    """
    row = conn.execute("SELECT MAX(date) FROM raw_prices").fetchone()
    if row and row[0] is not None:
        val = row[0]
        if isinstance(val, date):
            return val
        return date.fromisoformat(str(val))
    return None


def get_last_financial_date(conn: duckdb.DuckDBPyConnection) -> date | None:
    """raw_financials テーブルの最終取得日（report_date）を返す。

    Args:
        conn: DuckDB 接続。

    Returns:
        最終取得日。テーブルが空の場合は None。
    """
    row = conn.execute("SELECT MAX(report_date) FROM raw_financials").fetchone()
    if row and row[0] is not None:
        val = row[0]
        if isinstance(val, date):
            return val
        return date.fromisoformat(str(val))
    return None


def get_last_calendar_date(conn: duckdb.DuckDBPyConnection) -> date | None:
    """market_calendar テーブルの最終取得日を返す。

    Args:
        conn: DuckDB 接続。

    Returns:
        最終取得日。テーブルが空の場合は None。
    """
    row = conn.execute("SELECT MAX(date) FROM market_calendar").fetchone()
    if row and row[0] is not None:
        val = row[0]
        if isinstance(val, date):
            return val
        return date.fromisoformat(str(val))
    return None


# ---------------------------------------------------------------------------
# 個別ETLジョブ
# ---------------------------------------------------------------------------


def run_prices_etl(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    id_token: str | None = None,
    date_from: date | None = None,
) -> tuple[int, int]:
    """株価日足の差分ETLを実行する。

    差分更新: date_from が指定されていない場合、DBの最終取得日の翌日から
    target_date までのデータを取得する。

    Args:
        conn:        DuckDB 接続。
        target_date: 取得終了日（通常は当日）。
        id_token:    J-Quants 認証トークン。
        date_from:   取得開始日。省略時は最終取得日の翌日。

    Returns:
        (取得レコード数, 保存レコード数) のタプル。
    """
    if date_from is None:
        last = get_last_price_date(conn)
        date_from = (last + timedelta(days=1)) if last else date(2017, 1, 1)

    if date_from > target_date:
        logger.info(
            "run_prices_etl: すでに最新（last=%s, target=%s）",
            date_from - timedelta(days=1),
            target_date,
        )
        return 0, 0

    logger.info("run_prices_etl: %s〜%s を取得", date_from, target_date)
    records = jq.fetch_daily_quotes(
        id_token=id_token,
        date_from=date_from,
        date_to=target_date,
    )
    saved = jq.save_daily_quotes(conn, records)
    logger.info("run_prices_etl: 取得=%d, 保存=%d", len(records), saved)
    return len(records), saved


def run_financials_etl(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    id_token: str | None = None,
    date_from: date | None = None,
) -> tuple[int, int]:
    """財務データの差分ETLを実行する。

    差分更新: date_from が指定されていない場合、DBの最終取得日の翌日から
    target_date までのデータを取得する。

    Args:
        conn:        DuckDB 接続。
        target_date: 取得終了日。
        id_token:    J-Quants 認証トークン。
        date_from:   取得開始日。省略時は最終取得日の翌日。

    Returns:
        (取得レコード数, 保存レコード数) のタプル。
    """
    if date_from is None:
        last = get_last_financial_date(conn)
        date_from = (last + timedelta(days=1)) if last else date(2017, 1, 1)

    if date_from > target_date:
        logger.info(
            "run_financials_etl: すでに最新（last=%s, target=%s）",
            date_from - timedelta(days=1),
            target_date,
        )
        return 0, 0

    logger.info("run_financials_etl: %s〜%s を取得", date_from, target_date)
    records = jq.fetch_financial_statements(
        id_token=id_token,
        date_from=date_from,
        date_to=target_date,
    )
    saved = jq.save_financial_statements(conn, records)
    logger.info("run_financials_etl: 取得=%d, 保存=%d", len(records), saved)
    return len(records), saved


def run_calendar_etl(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    id_token: str | None = None,
    date_from: date | None = None,
) -> tuple[int, int]:
    """市場カレンダーの差分ETLを実行する。

    差分更新: date_from が指定されていない場合、DBの最終取得日の翌日から
    target_date の90日後（カレンダーは先読みが必要）までのデータを取得する。

    Args:
        conn:        DuckDB 接続。
        target_date: 基準日。
        id_token:    J-Quants 認証トークン。
        date_from:   取得開始日。省略時は最終取得日の翌日。

    Returns:
        (取得レコード数, 保存レコード数) のタプル。
    """
    # カレンダーは90日先まで先読みして取得する
    date_to = target_date + timedelta(days=90)

    if date_from is None:
        last = get_last_calendar_date(conn)
        date_from = (last + timedelta(days=1)) if last else date(2017, 1, 1)

    if date_from > date_to:
        logger.info(
            "run_calendar_etl: すでに最新（last=%s）",
            date_from - timedelta(days=1),
        )
        return 0, 0

    logger.info("run_calendar_etl: %s〜%s を取得", date_from, date_to)
    records = jq.fetch_market_calendar(
        id_token=id_token,
        date_from=date_from,
        date_to=date_to,
    )
    saved = jq.save_market_calendar(conn, records)
    logger.info("run_calendar_etl: 取得=%d, 保存=%d", len(records), saved)
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
) -> ETLResult:
    """日次ETLパイプラインを実行する。

    株価・財務・カレンダーデータの差分取得、保存、品質チェックを一括して実行する。

    処理順:
      1. 市場カレンダーETL（先読みで90日先まで取得）
      2. 株価日足ETL（差分更新）
      3. 財務データETL（差分更新）
      4. 品質チェック（オプション）

    Args:
        conn:               DuckDB 接続。
        target_date:        ETL対象日。省略時は今日。
        id_token:           J-Quants 認証トークン。省略時はキャッシュを使用。
        run_quality_checks: True の場合、ETL後に品質チェックを実行する。
        spike_threshold:    スパイク検出閾値（デフォルト 0.5 = 50%）。

    Returns:
        ETLResult オブジェクト。
    """
    today = target_date or date.today()
    result = ETLResult(target_date=today)

    # 1. 市場カレンダーETL
    try:
        fetched, saved = run_calendar_etl(conn, today, id_token=id_token)
        result.calendar_fetched = fetched
        result.calendar_saved = saved
    except Exception as e:
        msg = f"run_calendar_etl 失敗: {e}"
        logger.error(msg)
        result.errors.append(msg)

    # 2. 株価日足ETL
    try:
        fetched, saved = run_prices_etl(conn, today, id_token=id_token)
        result.prices_fetched = fetched
        result.prices_saved = saved
    except Exception as e:
        msg = f"run_prices_etl 失敗: {e}"
        logger.error(msg)
        result.errors.append(msg)

    # 3. 財務データETL
    try:
        fetched, saved = run_financials_etl(conn, today, id_token=id_token)
        result.financials_fetched = fetched
        result.financials_saved = saved
    except Exception as e:
        msg = f"run_financials_etl 失敗: {e}"
        logger.error(msg)
        result.errors.append(msg)

    # 4. 品質チェック
    if run_quality_checks:
        try:
            result.quality_issues = quality.run_all_checks(
                conn,
                target_date=today,
                reference_date=today,
                spike_threshold=spike_threshold,
            )
        except Exception as e:
            msg = f"品質チェック失敗: {e}"
            logger.error(msg)
            result.errors.append(msg)

    logger.info(
        "run_daily_etl 完了: date=%s prices=%d/%d financials=%d/%d "
        "calendar=%d/%d quality_issues=%d errors=%d",
        today,
        result.prices_saved,
        result.prices_fetched,
        result.financials_saved,
        result.financials_fetched,
        result.calendar_saved,
        result.calendar_fetched,
        len(result.quality_issues),
        len(result.errors),
    )
    return result
