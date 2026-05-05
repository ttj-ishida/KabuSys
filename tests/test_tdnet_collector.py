"""TDnet 開示収集モジュールのユニットテスト"""

from __future__ import annotations

from datetime import date, datetime

import duckdb
import pytest

from kabusys.data.tdnet_collector import (
    RawDisclosure,
    _extract_disclosure_id,
    _parse_tdnet_html,
    save_raw_disclosures,
    run_tdnet_collection,
)
from kabusys.data.disclosure_classifier import run_disclosure_classification


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


# ---------------------------------------------------------------------------
# Task 2: TDnet パーサーテスト
# ---------------------------------------------------------------------------

# 実際の TDnet HTML 構造に準拠したサンプル:
#   - id="main-list-table" の 7列テーブル
#   - タイトルと PDF href は同一セル（kjTitle の <a href>）
#   - CSS クラス名: kjTime / kjCode / kjName / kjTitle / kjXbrl / kjPlace / kjHistroy
_SAMPLE_HTML = """\
<html><body>
<table id="main-list-table">
<tr>
  <td class="oddnew-L kjTime" noWrap>09:00</td>
  <td class="oddnew-M kjCode" noWrap>7203</td>
  <td class="oddnew-M kjName" noWrap>トヨタ自動車株式会社</td>
  <td class="oddnew-M kjTitle" align="left"><a href="140120240901400001.pdf" target="_blank">業績予想の修正に関するお知らせ</a></td>
  <td class="oddnew-M kjXbrl" noWrap align="center"> </td>
  <td class="oddnew-M kjPlace" noWrap align="left">東</td>
  <td class="oddnew-R kjHistroy" align="left">　</td>
</tr>
<tr>
  <td class="evennew-L kjTime" noWrap>09:10</td>
  <td class="evennew-M kjCode" noWrap>6758</td>
  <td class="evennew-M kjName" noWrap>ソニーグループ株式会社</td>
  <td class="evennew-M kjTitle" align="left"><a href="140120240901400002.pdf" target="_blank">自己株式取得結果に関するお知らせ</a></td>
  <td class="evennew-M kjXbrl" noWrap align="center"> </td>
  <td class="evennew-M kjPlace" noWrap align="left">東</td>
  <td class="evennew-R kjHistroy" align="left">　</td>
</tr>
</table>
</body></html>
"""


def test_parse_tdnet_html_returns_disclosures():
    """_parse_tdnet_html が HTML テーブルから開示リストを返すことを確認する。"""
    disclosures = _parse_tdnet_html(_SAMPLE_HTML, target_date=date(2024, 9, 1))
    assert len(disclosures) == 2
    assert disclosures[0]["id"] == "140120240901400001"
    assert disclosures[0]["code"] == "7203"
    assert disclosures[0]["company_name"] == "トヨタ自動車株式会社"
    assert "業績予想" in disclosures[0]["title"]
    assert disclosures[0]["source"] == "tdnet"


def test_parse_tdnet_html_empty_table():
    """id="main-list-table" に有効なデータ行がない場合、空リストを返すことを確認する。"""
    html = '<html><body><table id="main-list-table"></table></body></html>'
    result = _parse_tdnet_html(html, target_date=date(2024, 9, 1))
    assert result == []


def test_parse_tdnet_html_ignores_other_tables():
    """id="main-list-table" 以外のテーブルを無視することを確認する。"""
    html = """\
<html><body>
<table id="list-head">
  <tr>
    <td class="kjCode">9999</td>
    <td class="kjTitle"><a href="SHOULD_NOT_APPEAR.pdf">無視されるべき行</a></td>
  </tr>
</table>
<table id="main-list-table">
</table>
</body></html>
"""
    result = _parse_tdnet_html(html, target_date=date(2024, 9, 1))
    assert result == []


def test_extract_disclosure_id_from_href():
    """PDF href から開示IDを抽出できることを確認する。"""
    assert _extract_disclosure_id("140120241031413060.pdf") == "140120241031413060"
    assert (
        _extract_disclosure_id("/inbs/140120241031413060.pdf") == "140120241031413060"
    )
    assert _extract_disclosure_id("") is None
    # クエリ文字列付き href でも正しく抽出できること
    assert (
        _extract_disclosure_id("140120241031413060.pdf?foo=bar") == "140120241031413060"
    )


def test_save_raw_disclosures_idempotent(disc_db):
    """同じ開示を2回 save しても重複しないことを確認する。"""
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


# ---------------------------------------------------------------------------
# Task 5: 統合テスト（パイプライン全体確認）
# ---------------------------------------------------------------------------

_PIPELINE_HTML = """\
<html><body>
<table id="main-list-table">
<tr>
  <td class="oddnew-L kjTime" noWrap>09:00</td>
  <td class="oddnew-M kjCode" noWrap>7203</td>
  <td class="oddnew-M kjName" noWrap>トヨタ自動車</td>
  <td class="oddnew-M kjTitle" align="left"><a href="140120240901400001.pdf" target="_blank">業績予想の修正（上方修正）に関するお知らせ</a></td>
  <td class="oddnew-M kjXbrl" noWrap align="center"> </td>
  <td class="oddnew-M kjPlace" noWrap align="left">東</td>
  <td class="oddnew-R kjHistroy" align="left">　</td>
</tr>
<tr>
  <td class="evennew-L kjTime" noWrap>10:00</td>
  <td class="evennew-M kjCode" noWrap>6758</td>
  <td class="evennew-M kjName" noWrap>ソニーグループ</td>
  <td class="evennew-M kjTitle" align="left"><a href="140120240901400002.pdf" target="_blank">訴訟の提起に関するお知らせ</a></td>
  <td class="evennew-M kjXbrl" noWrap align="center"> </td>
  <td class="evennew-M kjPlace" noWrap align="left">東</td>
  <td class="evennew-R kjHistroy" align="left">　</td>
</tr>
</table>
</body></html>
"""


def test_full_pipeline_collection_to_classification(monkeypatch):
    """収集 → 保存 → 分類の一連フローが正しく動くことを確認する。"""
    from kabusys.data.schema import init_schema
    from kabusys.data import tdnet_collector

    conn = init_schema(":memory:")

    def mock_fetch_page(url, timeout=30):
        if "I_list_001" in url:
            return _PIPELINE_HTML
        return "<html><body><table></table></body></html>"

    monkeypatch.setattr(tdnet_collector, "_fetch_page", mock_fetch_page)

    target = date(2024, 9, 1)
    saved_raw = run_tdnet_collection(conn, target_date=target)
    assert saved_raw == 2

    count = conn.execute("SELECT COUNT(*) FROM raw_disclosures").fetchone()[0]
    assert count == 2

    saved_events = run_disclosure_classification(conn, target_date=target)
    assert saved_events == 2

    rows = conn.execute(
        "SELECT id, event_type, event_score, buy_caution FROM disclosure_events ORDER BY id"
    ).fetchall()
    assert rows[0] == ("140120240901400001", "earnings_revision_up", 1.0, False)
    assert rows[1] == ("140120240901400002", "litigation_scandal", -1.0, True)

    conn.close()
