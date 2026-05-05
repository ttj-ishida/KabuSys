"""disclosure_classifier モジュールのユニットテスト"""
from __future__ import annotations

from datetime import datetime

import duckdb
import pytest

from kabusys.data.disclosure_classifier import (
    classify_title,
    classify_disclosures,
    run_disclosure_classification,
)

# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

_DISC_DDL = [
    """
    CREATE TABLE IF NOT EXISTS raw_disclosures (
        id              VARCHAR   NOT NULL PRIMARY KEY,
        disclosed_at    TIMESTAMP NOT NULL,
        code            VARCHAR,
        company_name    VARCHAR,
        title           VARCHAR,
        document_url    VARCHAR,
        document_type   VARCHAR,
        source          VARCHAR   NOT NULL,
        fetched_at      TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS disclosure_events (
        id               VARCHAR   NOT NULL PRIMARY KEY,
        disclosed_at     TIMESTAMP NOT NULL,
        code             VARCHAR,
        event_type       VARCHAR   NOT NULL,
        event_score      DOUBLE    NOT NULL,
        buy_caution      BOOLEAN   NOT NULL DEFAULT false,
        hold_caution     BOOLEAN   NOT NULL DEFAULT false,
        review_required  BOOLEAN   NOT NULL DEFAULT false,
        title            VARCHAR,
        source           VARCHAR   NOT NULL,
        classified_at    TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,
]


@pytest.fixture
def cdb():
    conn = duckdb.connect(":memory:")
    for ddl in _DISC_DDL:
        conn.execute(ddl)
    yield conn
    conn.close()


def _insert_raw(conn, id, title, code="7203", source="tdnet"):
    conn.execute(
        "INSERT INTO raw_disclosures (id, disclosed_at, code, title, source) VALUES (?, ?, ?, ?, ?)",
        [id, datetime(2024, 9, 1, 9, 0), code, title, source],
    )


# ---------------------------------------------------------------------------
# 分類ルールテスト
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title, expected_type, expected_score, expected_buy_caution",
    [
        # earnings_report
        ("決算短信（連結）", "earnings_report", 0.0, False),
        ("第2四半期決算短信", "earnings_report", 0.0, False),
        # earnings_revision_up
        ("業績予想の修正（上方修正）に関するお知らせ", "earnings_revision_up", 1.0, False),
        ("通期業績予想を上方修正", "earnings_revision_up", 1.0, False),
        # earnings_revision_down
        ("業績予想の修正（下方修正）に関するお知らせ", "earnings_revision_down", -1.0, True),
        ("業績予想を下方修正", "earnings_revision_down", -1.0, True),
        # dividend_revision_up
        ("配当予想の修正（増配）に関するお知らせ", "dividend_revision_up", 1.0, False),
        # dividend_revision_down
        ("配当予想の修正（減配）に関するお知らせ", "dividend_revision_down", -1.0, False),
        # buyback
        ("自己株式取得に関するお知らせ", "buyback", 0.5, False),
        ("自社株買いの実施について", "buyback", 0.5, False),
        # new_share_issuance
        ("第三者割当による新株式発行に関するお知らせ", "new_share_issuance", -0.5, True),
        ("公募増資について", "new_share_issuance", -0.5, True),
        # merger_acquisition
        ("株式取得（子会社化）に関するお知らせ", "merger_acquisition", 0.0, True),
        ("資本業務提携に関するお知らせ", "merger_acquisition", 0.0, True),
        # litigation_scandal
        ("訴訟の提起に関するお知らせ", "litigation_scandal", -1.0, True),
        ("不祥事に関する調査結果について", "litigation_scandal", -1.0, True),
        # other
        ("代表取締役の異動に関するお知らせ", "other", 0.0, False),
        ("定時株主総会招集ご通知", "other", 0.0, False),
    ],
)
def test_classify_title(title, expected_type, expected_score, expected_buy_caution):
    """classify_title が各イベントタイプを正しく判定することを確認する。"""
    result = classify_title(title)
    assert result["event_type"] == expected_type, f"title={title!r}"
    assert result["event_score"] == expected_score, f"title={title!r}"
    assert result["buy_caution"] == expected_buy_caution, f"title={title!r}"


def test_classify_title_none_returns_other():
    """None タイトルは 'other' を返すことを確認する。"""
    result = classify_title(None)
    assert result["event_type"] == "other"
    assert result["event_score"] == 0.0


def test_classify_disclosures_writes_events(cdb):
    """classify_disclosures が raw_disclosures を読んで disclosure_events に書くことを確認する。"""
    from datetime import date
    _insert_raw(cdb, "TDN001", "業績予想の修正（上方修正）に関するお知らせ")
    _insert_raw(cdb, "TDN002", "自己株式取得に関するお知らせ")
    saved = classify_disclosures(cdb, target_date=date(2024, 9, 1))
    assert saved == 2
    rows = cdb.execute(
        "SELECT id, event_type, event_score FROM disclosure_events ORDER BY id"
    ).fetchall()
    assert rows[0] == ("TDN001", "earnings_revision_up", 1.0)
    assert rows[1] == ("TDN002", "buyback", 0.5)


def test_classify_disclosures_upsert(cdb):
    """同じ開示を再分類しても重複しないことを確認する（UPSERT 動作）。"""
    from datetime import date
    _insert_raw(cdb, "TDN001", "決算短信（連結）")
    classify_disclosures(cdb, target_date=date(2024, 9, 1))
    classify_disclosures(cdb, target_date=date(2024, 9, 1))
    count = cdb.execute("SELECT COUNT(*) FROM disclosure_events").fetchone()[0]
    assert count == 1


def test_run_disclosure_classification(cdb):
    """run_disclosure_classification がジョブとして動くことを確認する。"""
    from datetime import date
    _insert_raw(cdb, "TDN001", "業績予想を下方修正")
    saved = run_disclosure_classification(cdb, target_date=date(2024, 9, 1))
    assert saved == 1
    row = cdb.execute(
        "SELECT event_type, buy_caution, review_required FROM disclosure_events WHERE id = 'TDN001'"
    ).fetchone()
    assert row[0] == "earnings_revision_down"
    assert row[1] is True   # buy_caution
    assert row[2] is True   # review_required
