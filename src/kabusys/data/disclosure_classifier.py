"""
開示イベント分類モジュール

raw_disclosures の表題を正規表現キーワードルールで分類し、
disclosure_events テーブルへ UPSERT する。

設計方針:
  - 分類は表題の「最初にマッチしたルール」を採用（優先順位あり、先勝ち）
  - NLP なし・外部依存なし（stdlib re のみ）
  - UPSERT（ON CONFLICT DO UPDATE）で再分類を上書き可能
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from typing import TypedDict

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 型定義
# ---------------------------------------------------------------------------


class ClassificationResult(TypedDict):
    event_type: str
    event_score: float
    buy_caution: bool
    hold_caution: bool
    review_required: bool


# ---------------------------------------------------------------------------
# 分類ルール（優先順位あり、先勝ち）
# ---------------------------------------------------------------------------

_RULES: list[tuple[str, float, bool, bool, bool, re.Pattern[str]]] = [
    # earnings_report
    (
        "earnings_report",
        0.0,
        False,
        False,
        False,
        re.compile(r"決算短信|四半期報告", re.IGNORECASE),
    ),
    # earnings_revision_up
    (
        "earnings_revision_up",
        1.0,
        False,
        False,
        False,
        re.compile(r"業績予想.{0,10}(上方|増額)", re.IGNORECASE),
    ),
    # earnings_revision_down
    (
        "earnings_revision_down",
        -1.0,
        True,
        True,
        True,
        re.compile(r"業績予想.{0,10}(下方|減額)", re.IGNORECASE),
    ),
    # dividend_revision_up
    (
        "dividend_revision_up",
        1.0,
        False,
        False,
        False,
        re.compile(r"配当.{0,10}(増配|上方|引き上げ|引上げ)", re.IGNORECASE),
    ),
    # dividend_revision_down
    (
        "dividend_revision_down",
        -1.0,
        False,
        True,
        False,
        re.compile(r"配当.{0,10}(減配|下方|引き下げ|引下げ|無配)", re.IGNORECASE),
    ),
    # buyback
    (
        "buyback",
        0.5,
        False,
        False,
        False,
        re.compile(r"自己株式取得|自社株買|自己株の取得", re.IGNORECASE),
    ),
    # new_share_issuance
    (
        "new_share_issuance",
        -0.5,
        True,
        False,
        False,
        re.compile(
            r"(新株式発行|公募増資|第三者割当|新株予約権|公募|増資)", re.IGNORECASE
        ),
    ),
    # merger_acquisition
    (
        "merger_acquisition",
        0.0,
        True,
        False,
        True,
        re.compile(
            r"(合併|買収|子会社化|資本業務提携|株式交換|事業譲受|TOB|MBO)",
            re.IGNORECASE,
        ),
    ),
    # litigation_scandal
    (
        "litigation_scandal",
        -1.0,
        True,
        True,
        True,
        re.compile(
            r"(訴訟|不祥事|調査委員会|行政処分|監理銘柄|上場廃止|課徴金|粉飾|横領)",
            re.IGNORECASE,
        ),
    ),
]

_OTHER: ClassificationResult = {
    "event_type": "other",
    "event_score": 0.0,
    "buy_caution": False,
    "hold_caution": False,
    "review_required": False,
}


# ---------------------------------------------------------------------------
# 公開関数
# ---------------------------------------------------------------------------


def classify_title(title: str | None) -> ClassificationResult:
    """開示表題を分類ルールに照合してイベント分類結果を返す。

    先頭にマッチしたルールを採用する（先勝ちルール）。
    どのルールにもマッチしない場合は 'other' を返す。
    """
    if not title:
        return _OTHER

    for (
        event_type,
        event_score,
        buy_caution,
        hold_caution,
        review_required,
        pattern,
    ) in _RULES:
        if pattern.search(title):
            return ClassificationResult(
                event_type=event_type,
                event_score=event_score,
                buy_caution=buy_caution,
                hold_caution=hold_caution,
                review_required=review_required,
            )

    return _OTHER


def classify_disclosures(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> int:
    """指定日の raw_disclosures を分類して disclosure_events に UPSERT する。

    Returns:
        UPSERT した件数。
    """
    rows = conn.execute(
        "SELECT id, disclosed_at, code, title, source "
        "FROM raw_disclosures "
        "WHERE CAST(disclosed_at AS DATE) = ?",
        [target_date],
    ).fetchall()

    if not rows:
        logger.info("classify_disclosures: date=%s 対象なし", target_date)
        return 0

    classified_at = datetime.now(timezone.utc).replace(tzinfo=None)
    upsert_rows = []
    for row_id, disclosed_at, code, title, source in rows:
        result = classify_title(title)
        upsert_rows.append(
            (
                row_id,
                disclosed_at,
                code,
                result["event_type"],
                result["event_score"],
                result["buy_caution"],
                result["hold_caution"],
                result["review_required"],
                title,
                source,
                classified_at,
            )
        )

    saved = 0
    conn.begin()
    try:
        for i in range(0, len(upsert_rows), 500):
            chunk = upsert_rows[i : i + 500]
            placeholders = ", ".join("(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" for _ in chunk)
            flat = [v for row in chunk for v in row]
            conn.execute(
                "INSERT INTO disclosure_events "
                "(id, disclosed_at, code, event_type, event_score, "
                " buy_caution, hold_caution, review_required, title, source, classified_at) "
                f"VALUES {placeholders} "
                "ON CONFLICT (id) DO UPDATE SET "
                "  event_type = EXCLUDED.event_type, "
                "  event_score = EXCLUDED.event_score, "
                "  buy_caution = EXCLUDED.buy_caution, "
                "  hold_caution = EXCLUDED.hold_caution, "
                "  review_required = EXCLUDED.review_required, "
                "  classified_at = EXCLUDED.classified_at",
                flat,
            )
            saved += len(chunk)
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("classify_disclosures: トランザクション失敗、ロールバック")
        raise

    logger.info("classify_disclosures: date=%s classified=%d", target_date, saved)
    return saved


def run_disclosure_classification(
    conn: duckdb.DuckDBPyConnection,
    target_date: date | None = None,
) -> int:
    """開示イベント分類ジョブ（17:00 実行）。

    Returns:
        UPSERT した件数。
    """
    from datetime import date as date_cls

    if target_date is None:
        target_date = date_cls.today()

    saved = classify_disclosures(conn, target_date)
    logger.info("run_disclosure_classification: date=%s saved=%d", target_date, saved)
    return saved
