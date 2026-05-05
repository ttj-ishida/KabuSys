"""TDnet 開示収集モジュールのユニットテスト"""
from __future__ import annotations

import duckdb
import pytest


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

_DISCLOSURE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS raw_disclosures (
        id              VARCHAR   NOT NULL PRIMARY KEY,
        disclosed_at    TIMESTAMP NOT NULL,
        code            VARCHAR,
        company_name    VARCHAR,
        title           VARCHAR,
        document_url    VARCHAR,
        document_type   VARCHAR,
        source          VARCHAR   NOT NULL CHECK (source IN ('tdnet', 'edinet')),
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
        source           VARCHAR   NOT NULL CHECK (source IN ('tdnet', 'edinet')),
        classified_at    TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,
]


@pytest.fixture
def disc_db():
    conn = duckdb.connect(":memory:")
    for ddl in _DISCLOSURE_DDL:
        conn.execute(ddl)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Task 1: スキーマテスト
# ---------------------------------------------------------------------------


def test_raw_disclosures_table_exists(disc_db):
    """raw_disclosures テーブルが正しく作成されることを確認する。"""
    result = disc_db.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'raw_disclosures' "
        "ORDER BY column_name"
    ).fetchall()
    columns = {row[0] for row in result}
    assert "id" in columns
    assert "disclosed_at" in columns
    assert "code" in columns
    assert "source" in columns
    assert "fetched_at" in columns


def test_disclosure_events_table_exists(disc_db):
    """disclosure_events テーブルが正しく作成されることを確認する。"""
    result = disc_db.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'disclosure_events' "
        "ORDER BY column_name"
    ).fetchall()
    columns = {row[0] for row in result}
    assert "id" in columns
    assert "event_type" in columns
    assert "event_score" in columns
    assert "buy_caution" in columns
    assert "review_required" in columns


from kabusys.data.tdnet_collector import (
    RawDisclosure,
    _extract_disclosure_id,
    _parse_tdnet_html,
    save_raw_disclosures,
    run_tdnet_collection,
)


# ---------------------------------------------------------------------------
# Task 2: TDnet パーサーテスト
# ---------------------------------------------------------------------------

_SAMPLE_HTML = """\
<html><body>
<table>
<tr><th>時刻</th><th>コード</th><th>会社名</th><th>表題</th><th>PDF</th></tr>
<tr>
  <td>09:00</td>
  <td>7203</td>
  <td>トヨタ自動車株式会社</td>
  <td>業績予想の修正に関するお知らせ</td>
  <td><a href="140120240901400001.pdf">PDF</a></td>
</tr>
<tr>
  <td>09:10</td>
  <td>6758</td>
  <td>ソニーグループ株式会社</td>
  <td>自己株式取得結果に関するお知らせ</td>
  <td><a href="140120240901400002.pdf">PDF</a></td>
</tr>
</table>
</body></html>
"""


def test_parse_tdnet_html_returns_disclosures():
    """_parse_tdnet_html が HTML テーブルから開示リストを返すことを確認する。"""
    from datetime import date
    disclosures = _parse_tdnet_html(_SAMPLE_HTML, target_date=date(2024, 9, 1))
    assert len(disclosures) == 2
    assert disclosures[0]["id"] == "140120240901400001"
    assert disclosures[0]["code"] == "7203"
    assert disclosures[0]["company_name"] == "トヨタ自動車株式会社"
    assert "業績予想" in disclosures[0]["title"]
    assert disclosures[0]["source"] == "tdnet"


def test_parse_tdnet_html_empty_table():
    """行がない HTML テーブルで空リストを返すことを確認する。"""
    html = "<html><body><table><tr><th>時刻</th></tr></table></body></html>"
    from datetime import date
    result = _parse_tdnet_html(html, target_date=date(2024, 9, 1))
    assert result == []


def test_extract_disclosure_id_from_href():
    """PDF href から開示IDを抽出できることを確認する。"""
    assert _extract_disclosure_id("140120241031413060.pdf") == "140120241031413060"
    assert _extract_disclosure_id("/inbs/140120241031413060.pdf") == "140120241031413060"
    assert _extract_disclosure_id("") is None


def test_save_raw_disclosures_idempotent(disc_db):
    """同じ開示を2回 save しても重複しないことを確認する。"""
    from datetime import datetime
    disclosures = [
        RawDisclosure(
            id="TDN001",
            disclosed_at=datetime(2024, 9, 1, 9, 0, 0),
            code="7203",
            company_name="トヨタ自動車",
            title="業績予想修正",
            document_url="https://example.com/TDN001.pdf",
            document_type="業績予想の修正",
            source="tdnet",
        )
    ]
    first = save_raw_disclosures(disc_db, disclosures)
    second = save_raw_disclosures(disc_db, disclosures)
    assert first == 1
    assert second == 0
    count = disc_db.execute("SELECT COUNT(*) FROM raw_disclosures").fetchone()[0]
    assert count == 1


def test_run_tdnet_collection_mocked(disc_db, monkeypatch):
    """run_tdnet_collection が HTTP をモックして保存件数を返すことを確認する。"""
    from datetime import date
    from kabusys.data import tdnet_collector

    def mock_fetch_page(url, timeout=30):
        if "I_list_001" in url:
            return _SAMPLE_HTML
        return "<html><body><table></table></body></html>"

    monkeypatch.setattr(tdnet_collector, "_fetch_page", mock_fetch_page)
    saved = run_tdnet_collection(disc_db, target_date=date(2024, 9, 1))
    assert saved == 2
    rows = disc_db.execute("SELECT COUNT(*) FROM raw_disclosures").fetchone()[0]
    assert rows == 2
