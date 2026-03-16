"""
データ品質チェックモジュール

DataPlatform.md Section 9 に基づき、以下の品質チェックを実施する。

チェック項目:
  - 欠損データ検出: 必須カラムが NULL のレコードを検出
  - 異常値検出:     株価のスパイク（前日比 ±X% 超）を検出
  - 重複チェック:   主キー重複を検出
  - 日付不整合検出: 将来日付・営業日外のデータを検出

設計方針:
  - 各チェックは QualityIssue のリストを返す（Fail-Fast ではなく全件収集）
  - 呼び出し元が重大度に応じて ETL 停止／警告ログ出力を判断する
  - DuckDB 接続を受け取り SQL クエリで効率的に処理する
  - SQL はパラメータバインド（?）を使用し、インジェクションリスクを排除する
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

# 株価スパイク判定閾値（前日比の絶対値がこの値を超えたら異常とみなす）
_SPIKE_THRESHOLD = 0.5   # 50% 超の変動をスパイクとみなす

# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------


@dataclass
class QualityIssue:
    """品質チェックで検出された問題を表すデータクラス。

    Attributes:
        check_name: チェック名（例: "missing_data", "spike"）
        table:      対象テーブル名
        severity:   重大度（"error" | "warning"）
        detail:     詳細メッセージ
        rows:       問題レコードのサンプル（最大 10 件）
    """

    check_name: str
    table: str
    severity: Literal["error", "warning"]
    detail: str
    rows: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 欠損データ検出
# ---------------------------------------------------------------------------


def check_missing_data(
    conn: duckdb.DuckDBPyConnection,
    target_date: date | None = None,
) -> list[QualityIssue]:
    """raw_prices テーブルの必須カラム欠損を検出する。

    open/high/low/close のいずれかが NULL のレコードを検出する。
    volume は欠損が許容されるため対象外。

    Args:
        conn:        DuckDB 接続。
        target_date: 検査対象日（省略時は全件）。

    Returns:
        QualityIssue のリスト。問題がなければ空リスト。
    """
    params = [target_date, target_date]
    sample_rows = conn.execute(
        """
        SELECT date, code, open, high, low, close
        FROM raw_prices
        WHERE (open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL)
          AND (? IS NULL OR date = ?)
        LIMIT 10
        """,
        params,
    ).fetchall()

    issues: list[QualityIssue] = []
    if sample_rows:
        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM raw_prices
            WHERE (open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL)
              AND (? IS NULL OR date = ?)
            """,
            params,
        ).fetchone()[0]
        cols = ["date", "code", "open", "high", "low", "close"]
        issues.append(
            QualityIssue(
                check_name="missing_data",
                table="raw_prices",
                severity="error",
                detail=f"OHLC 欠損レコードが {count} 件あります",
                rows=[dict(zip(cols, row)) for row in sample_rows],
            )
        )
        logger.error("check_missing_data: raw_prices に OHLC 欠損 %d 件", count)

    return issues


# ---------------------------------------------------------------------------
# 異常値検出（スパイク判定）
# ---------------------------------------------------------------------------


def check_spike(
    conn: duckdb.DuckDBPyConnection,
    target_date: date | None = None,
    threshold: float = _SPIKE_THRESHOLD,
) -> list[QualityIssue]:
    """株価の前日比スパイク（急騰・急落）を検出する。

    LAG ウィンドウ関数で前日の close を取得し、変動率の絶対値が
    threshold を超えるレコードを検出する。

    Args:
        conn:        DuckDB 接続。
        target_date: 検査対象日（省略時は全件）。
        threshold:   スパイク判定閾値（デフォルト 0.5 = 50%）。

    Returns:
        QualityIssue のリスト。問題がなければ空リスト。
    """
    params = [threshold, target_date, target_date]
    spike_cte = """
        WITH lagged AS (
            SELECT
                date,
                code,
                close,
                LAG(close) OVER (PARTITION BY code ORDER BY date) AS prev_close
            FROM raw_prices
        ),
        spikes AS (
            SELECT
                date,
                code,
                prev_close,
                close AS curr_close,
                (close - prev_close) / prev_close AS change_rate
            FROM lagged
            WHERE prev_close > 0
              AND ABS((close - prev_close) / prev_close) > ?
              AND (? IS NULL OR date = ?)
        )
    """

    sample_rows = conn.execute(
        spike_cte + """
        SELECT date, code, prev_close, curr_close, change_rate
        FROM spikes
        ORDER BY ABS(change_rate) DESC
        LIMIT 10
        """,
        params,
    ).fetchall()

    issues: list[QualityIssue] = []
    if sample_rows:
        count = conn.execute(
            spike_cte + "SELECT COUNT(*) FROM spikes",
            params,
        ).fetchone()[0]
        cols = ["date", "code", "prev_close", "curr_close", "change_rate"]
        issues.append(
            QualityIssue(
                check_name="spike",
                table="raw_prices",
                severity="warning",
                detail=(
                    f"前日比 {threshold * 100:.0f}% 超のスパイクが {count} 件あります"
                ),
                rows=[dict(zip(cols, row)) for row in sample_rows],
            )
        )
        logger.warning("check_spike: raw_prices にスパイク %d 件", count)

    return issues


# ---------------------------------------------------------------------------
# 重複チェック
# ---------------------------------------------------------------------------


def check_duplicates(
    conn: duckdb.DuckDBPyConnection,
    target_date: date | None = None,
) -> list[QualityIssue]:
    """raw_prices の主キー重複（date, code）を検出する。

    ON CONFLICT DO UPDATE で通常は排除されるが、ETL 外からの挿入など
    スキーマ変更時に生じる可能性があるため念のため検査する。

    Args:
        conn:        DuckDB 接続。
        target_date: 検査対象日（省略時は全件）。

    Returns:
        QualityIssue のリスト。問題がなければ空リスト。
    """
    params = [target_date, target_date]
    sample_rows = conn.execute(
        """
        SELECT date, code, COUNT(*) AS cnt
        FROM raw_prices
        WHERE (? IS NULL OR date = ?)
        GROUP BY date, code
        HAVING COUNT(*) > 1
        ORDER BY date, code
        LIMIT 10
        """,
        params,
    ).fetchall()

    issues: list[QualityIssue] = []
    if sample_rows:
        total = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT 1
                FROM raw_prices
                WHERE (? IS NULL OR date = ?)
                GROUP BY date, code
                HAVING COUNT(*) > 1
            )
            """,
            params,
        ).fetchone()[0]
        cols = ["date", "code", "count"]
        issues.append(
            QualityIssue(
                check_name="duplicates",
                table="raw_prices",
                severity="error",
                detail=f"主キー重複が {total} グループ検出されました",
                rows=[dict(zip(cols, row)) for row in sample_rows],
            )
        )
        logger.error("check_duplicates: raw_prices に主キー重複 %d グループ", total)

    return issues


# ---------------------------------------------------------------------------
# 日付不整合検出
# ---------------------------------------------------------------------------


def check_date_consistency(
    conn: duckdb.DuckDBPyConnection,
    reference_date: date | None = None,
) -> list[QualityIssue]:
    """日付不整合（将来日付・非営業日データ）を検出する。

    以下の2項目を検査する:
    1. reference_date より後の日付のレコード（未来データ）
    2. market_calendar で非営業日とされる日の株価データ（テーブルが存在する場合のみ）

    Args:
        conn:           DuckDB 接続。
        reference_date: 基準日（省略時は CURRENT_DATE）。

    Returns:
        QualityIssue のリスト。問題がなければ空リスト。
    """
    ref = reference_date or date.today()
    issues: list[QualityIssue] = []

    # 1) 将来日付チェック
    future_sample = conn.execute(
        """
        SELECT date, code, close
        FROM raw_prices
        WHERE date > ?
        ORDER BY date DESC
        LIMIT 10
        """,
        [ref],
    ).fetchall()

    if future_sample:
        count = conn.execute(
            "SELECT COUNT(*) FROM raw_prices WHERE date > ?",
            [ref],
        ).fetchone()[0]
        cols = ["date", "code", "close"]
        issues.append(
            QualityIssue(
                check_name="future_date",
                table="raw_prices",
                severity="error",
                detail=f"基準日 {ref} より後の未来日付レコードが {count} 件あります",
                rows=[dict(zip(cols, row)) for row in future_sample],
            )
        )
        logger.error("check_date_consistency: 未来日付レコード %d 件", count)

    # 2) market_calendar との整合性チェック（テーブルが存在する場合）
    try:
        non_trading_sample = conn.execute(
            """
            SELECT rp.date, COUNT(*) AS cnt
            FROM raw_prices rp
            JOIN market_calendar mc ON rp.date = mc.date
            WHERE mc.is_trading_day = false
            GROUP BY rp.date
            ORDER BY rp.date
            LIMIT 10
            """
        ).fetchall()

        if non_trading_sample:
            total_days = conn.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT rp.date
                    FROM raw_prices rp
                    JOIN market_calendar mc ON rp.date = mc.date
                    WHERE mc.is_trading_day = false
                    GROUP BY rp.date
                )
                """
            ).fetchone()[0]
            cols = ["date", "record_count"]
            issues.append(
                QualityIssue(
                    check_name="non_trading_day",
                    table="raw_prices",
                    severity="warning",
                    detail=(
                        f"market_calendar で非営業日とされる日に "
                        f"{total_days} 日分の株価データがあります"
                    ),
                    rows=[dict(zip(cols, row)) for row in non_trading_sample],
                )
            )
            logger.warning(
                "check_date_consistency: 非営業日の株価データ %d 日分",
                total_days,
            )
    except duckdb.Error:
        # market_calendar テーブル未存在・カラム不一致等の場合はスキップ
        pass

    return issues


# ---------------------------------------------------------------------------
# 公開 API: 全チェック実行
# ---------------------------------------------------------------------------


def run_all_checks(
    conn: duckdb.DuckDBPyConnection,
    target_date: date | None = None,
    reference_date: date | None = None,
    spike_threshold: float = _SPIKE_THRESHOLD,
) -> list[QualityIssue]:
    """すべての品質チェックを実行し、検出した問題をまとめて返す。

    Args:
        conn:            DuckDB 接続。
        target_date:     チェック対象日（省略時は全件）。
        reference_date:  日付不整合チェックの基準日（省略時は今日）。
        spike_threshold: スパイク判定閾値（デフォルト 0.5 = 50%）。

    Returns:
        QualityIssue のリスト。問題がなければ空リスト。
    """
    issues: list[QualityIssue] = []
    issues.extend(check_missing_data(conn, target_date))
    issues.extend(check_duplicates(conn, target_date))
    issues.extend(check_spike(conn, target_date, spike_threshold))
    issues.extend(check_date_consistency(conn, reference_date))

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    logger.info(
        "run_all_checks: error=%d, warning=%d", len(errors), len(warnings)
    )
    return issues
