"""EDINET 法定開示収集モジュールのユニットテスト"""

from __future__ import annotations

import json
from datetime import date, datetime

import duckdb
import pytest

from kabusys.data.edinet_collector import (
    _parse_edinet_response,
    _parse_submit_datetime,
    fetch_edinet_disclosures,
    run_edinet_collection,
)

# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

_DISCLOSURE_DDL = """
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
"""


@pytest.fixture
def disc_db():
    conn = duckdb.connect(":memory:")
    conn.execute(_DISCLOSURE_DDL)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# _parse_submit_datetime テスト
# ---------------------------------------------------------------------------


def test_parse_submit_datetime_minutes():
    """ "%Y-%m-%d %H:%M" フォーマットを正しくパースする。"""
    result = _parse_submit_datetime("2024-09-01 15:30", date(2024, 9, 1))
    assert result == datetime(2024, 9, 1, 15, 30)


def test_parse_submit_datetime_seconds():
    """ "%Y-%m-%d %H:%M:%S" フォーマットを正しくパースする。"""
    result = _parse_submit_datetime("2024-09-01 15:30:45", date(2024, 9, 1))
    assert result == datetime(2024, 9, 1, 15, 30, 45)


def test_parse_submit_datetime_iso():
    """ISO 8601 形式を正しくパースする。"""
    result = _parse_submit_datetime("2024-09-01T15:30:00", date(2024, 9, 1))
    assert result == datetime(2024, 9, 1, 15, 30, 0)


def test_parse_submit_datetime_fallback():
    """不正フォーマットの場合、target_date の 0:00 にフォールバックする。"""
    result = _parse_submit_datetime("invalid-datetime", date(2024, 9, 1))
    assert result == datetime(2024, 9, 1, 0, 0, 0)


# ---------------------------------------------------------------------------
# _parse_edinet_response テスト
# ---------------------------------------------------------------------------

_SAMPLE_RESPONSE = {
    "metadata": {"status": "200", "processDateTime": "2024-09-01 18:00"},
    "results": [
        {
            "docID": "S100ABCD",
            "edinetCode": "E00001",
            "docTypeCode": "120",
            "filerName": "トヨタ自動車株式会社",
            "submitDateTime": "2024-09-01 15:30",
            "docDescription": "有価証券報告書－第85期",
            "pdfFlag": "1",
            "xbrlFlag": "1",
            "withdrawalStatus": "0",
        },
        {
            "docID": "S100WXYZ",
            "edinetCode": "E00002",
            "docTypeCode": "170",
            "filerName": "大量保有者テスト",
            "submitDateTime": "2024-09-01 16:00",
            "docDescription": "大量保有報告書",
            "pdfFlag": "0",
            "xbrlFlag": "0",
            "withdrawalStatus": "0",
        },
        {
            "docID": "S100SKIP",
            "edinetCode": "E00003",
            "docTypeCode": "120",
            "filerName": "取り下げ会社",
            "submitDateTime": "2024-09-01 10:00",
            "docDescription": "有価証券報告書",
            "pdfFlag": "0",
            "xbrlFlag": "0",
            "withdrawalStatus": "1",  # 取り下げ済み
        },
        {
            "docID": "S100TYPE",
            "edinetCode": "E00004",
            "docTypeCode": "999",  # 対象外書類種別
            "filerName": "対象外会社",
            "submitDateTime": "2024-09-01 11:00",
            "docDescription": "対象外書類",
            "pdfFlag": "0",
            "xbrlFlag": "0",
            "withdrawalStatus": "0",
        },
    ],
}


def test_parse_edinet_response_returns_disclosures():
    """正常レスポンスから対象書類のみを RawDisclosure リストで返すことを確認する。"""
    raw = json.dumps(_SAMPLE_RESPONSE).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))

    # 取り下げ済み(S100SKIP)と対象外種別(S100TYPE)は除外 → 2件
    assert len(result) == 2
    ids = {d["id"] for d in result}
    assert "S100ABCD" in ids
    assert "S100WXYZ" in ids
    assert "S100SKIP" not in ids
    assert "S100TYPE" not in ids


def test_parse_edinet_response_source_is_edinet():
    """パース結果の source が 'edinet' であることを確認する。"""
    raw = json.dumps(_SAMPLE_RESPONSE).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))
    assert all(d["source"] == "edinet" for d in result)


def test_parse_edinet_response_code_is_none():
    """EDINET API は銘柄コードを返さないので code=None であることを確認する。"""
    raw = json.dumps(_SAMPLE_RESPONSE).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))
    assert all(d["code"] is None for d in result)


def test_parse_edinet_response_pdf_url_type2():
    """pdfFlag=1 の書類の document_url に ?type=2 が付くことを確認する。"""
    raw = json.dumps(_SAMPLE_RESPONSE).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))
    abcd = next(d for d in result if d["id"] == "S100ABCD")
    assert "?type=2" in abcd["document_url"]


def test_parse_edinet_response_no_pdf_url_type1():
    """pdfFlag=0 の書類の document_url に ?type=1 が付くことを確認する。"""
    raw = json.dumps(_SAMPLE_RESPONSE).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))
    wxyz = next(d for d in result if d["id"] == "S100WXYZ")
    assert "?type=1" in wxyz["document_url"]


def test_parse_edinet_response_api_status_not_200():
    """API ステータスが 200 以外の場合、空リストを返すことを確認する。"""
    payload = {"metadata": {"status": "500"}, "results": []}
    raw = json.dumps(payload).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))
    assert result == []


def test_parse_edinet_response_api_status_int_200():
    """API ステータスが int 200 を返した場合も正常処理されることを確認する。"""
    payload = {
        "metadata": {"status": 200},
        "results": [
            {
                "docID": "S100INT",
                "edinetCode": "E00001",
                "docTypeCode": "120",
                "filerName": "テスト会社",
                "submitDateTime": "2024-09-01 15:00",
                "docDescription": "有価証券報告書",
                "pdfFlag": "0",
                "xbrlFlag": "0",
                "withdrawalStatus": "0",
            }
        ],
    }
    raw = json.dumps(payload).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))
    assert len(result) == 1
    assert result[0]["id"] == "S100INT"


def test_parse_edinet_response_invalid_json():
    """不正な JSON バイトの場合、空リストを返すことを確認する。"""
    result = _parse_edinet_response(b"not-json", target_date=date(2024, 9, 1))
    assert result == []


def test_parse_edinet_response_fallback_datetime():
    """submitDateTime が不正フォーマットの場合、target_date の 0:00 にフォールバックすることを確認する。"""
    payload = {
        "metadata": {"status": "200"},
        "results": [
            {
                "docID": "S100FB",
                "edinetCode": "E00001",
                "docTypeCode": "120",
                "filerName": "フォールバック会社",
                "submitDateTime": "invalid-datetime",
                "docDescription": "有価証券報告書",
                "pdfFlag": "0",
                "xbrlFlag": "0",
                "withdrawalStatus": "0",
            }
        ],
    }
    raw = json.dumps(payload).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))
    assert len(result) == 1
    assert result[0]["disclosed_at"] == datetime(2024, 9, 1, 0, 0, 0)


def test_parse_edinet_response_submit_datetime_with_seconds():
    """submitDateTime に秒が含まれる場合も正しくパースされることを確認する。"""
    payload = {
        "metadata": {"status": "200"},
        "results": [
            {
                "docID": "S100SEC",
                "edinetCode": "E00001",
                "docTypeCode": "150",
                "filerName": "テスト会社",
                "submitDateTime": "2024-09-01 09:15:30",
                "docDescription": "訂正臨時報告書",
                "pdfFlag": "0",
                "xbrlFlag": "0",
                "withdrawalStatus": "0",
            }
        ],
    }
    raw = json.dumps(payload).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))
    assert len(result) == 1
    assert result[0]["disclosed_at"] == datetime(2024, 9, 1, 9, 15, 30)


def test_parse_edinet_response_target_doc_types_171_172():
    """対象種別 171/172 が収集されることを確認する。"""
    payload = {
        "metadata": {"status": "200"},
        "results": [
            {
                "docID": "S100171",
                "edinetCode": "E00001",
                "docTypeCode": "171",
                "filerName": "会社A",
                "submitDateTime": "2024-09-01 10:00",
                "docDescription": "大量保有報告書（特例対象）",
                "pdfFlag": "0",
                "xbrlFlag": "0",
                "withdrawalStatus": "0",
            },
            {
                "docID": "S100172",
                "edinetCode": "E00002",
                "docTypeCode": "172",
                "filerName": "会社B",
                "submitDateTime": "2024-09-01 11:00",
                "docDescription": "変更報告書",
                "pdfFlag": "0",
                "xbrlFlag": "0",
                "withdrawalStatus": "0",
            },
        ],
    }
    raw = json.dumps(payload).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))
    assert len(result) == 2
    ids = {d["id"] for d in result}
    assert "S100171" in ids
    assert "S100172" in ids


def test_parse_edinet_response_empty_results():
    """results が空配列の場合、空リストを返すことを確認する。"""
    payload = {"metadata": {"status": "200"}, "results": []}
    raw = json.dumps(payload).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))
    assert result == []


def test_parse_edinet_response_all_withdrawal_statuses():
    """withdrawalStatus が '0' 以外の書類がすべて除外されることを確認する。"""
    payload = {
        "metadata": {"status": "200"},
        "results": [
            {
                "docID": "S100W1",
                "edinetCode": "E00001",
                "docTypeCode": "120",
                "filerName": "会社A",
                "submitDateTime": "2024-09-01 10:00",
                "docDescription": "有価証券報告書",
                "pdfFlag": "0",
                "xbrlFlag": "0",
                "withdrawalStatus": "1",
            },
            {
                "docID": "S100W2",
                "edinetCode": "E00002",
                "docTypeCode": "130",
                "filerName": "会社B",
                "submitDateTime": "2024-09-01 11:00",
                "docDescription": "四半期報告書",
                "pdfFlag": "0",
                "xbrlFlag": "0",
                "withdrawalStatus": "2",
            },
        ],
    }
    raw = json.dumps(payload).encode("utf-8")
    result = _parse_edinet_response(raw, target_date=date(2024, 9, 1))
    assert result == []


# ---------------------------------------------------------------------------
# fetch_edinet_disclosures テスト
# ---------------------------------------------------------------------------


def test_fetch_edinet_disclosures_returns_list(monkeypatch):
    """fetch_edinet_disclosures がパース済みリストを返すことを確認する。"""
    from kabusys.data import edinet_collector

    raw = json.dumps(_SAMPLE_RESPONSE).encode("utf-8")
    monkeypatch.setattr(edinet_collector, "_fetch_edinet_json", lambda url, timeout=30: raw)

    result = fetch_edinet_disclosures(date(2024, 9, 1), api_key="test-key")
    assert len(result) == 2
    assert all(d["source"] == "edinet" for d in result)


def test_fetch_edinet_disclosures_subscription_key_in_url(monkeypatch):
    """fetch_edinet_disclosures が Subscription-Key をクエリパラメータに含めることを確認する。"""
    from kabusys.data import edinet_collector

    captured_urls: list[str] = []

    def fake_fetch(url, timeout=30):
        captured_urls.append(url)
        return json.dumps({"metadata": {"status": "200"}, "results": []}).encode("utf-8")

    monkeypatch.setattr(edinet_collector, "_fetch_edinet_json", fake_fetch)
    fetch_edinet_disclosures(date(2024, 9, 1), api_key="my-secret-key")

    assert len(captured_urls) == 1
    assert "Subscription-Key=my-secret-key" in captured_urls[0]


def test_fetch_edinet_disclosures_no_api_key_no_subscription_param(monkeypatch):
    """api_key が空のとき Subscription-Key クエリパラメータが含まれないことを確認する。"""
    from kabusys.data import edinet_collector

    captured_urls: list[str] = []

    def fake_fetch(url, timeout=30):
        captured_urls.append(url)
        return json.dumps({"metadata": {"status": "200"}, "results": []}).encode("utf-8")

    monkeypatch.setattr(edinet_collector, "_fetch_edinet_json", fake_fetch)
    fetch_edinet_disclosures(date(2024, 9, 1), api_key="")

    assert "Subscription-Key" not in captured_urls[0]


def test_fetch_edinet_disclosures_http_401_logs_error(monkeypatch, caplog):
    """HTTP 401 が発生した場合、認証エラーログを出して空リストを返すことを確認する。"""
    import logging
    import urllib.error

    from kabusys.data import edinet_collector

    def raise_401(url, timeout=30):
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(edinet_collector, "_fetch_edinet_json", raise_401)
    with caplog.at_level(logging.ERROR):
        result = fetch_edinet_disclosures(date(2024, 9, 1), api_key="bad-key")

    assert result == []
    assert "認証エラー" in caplog.text


def test_fetch_edinet_disclosures_http_403_logs_error(monkeypatch, caplog):
    """HTTP 403 が発生した場合、認証エラーログを出して空リストを返すことを確認する。"""
    import logging
    import urllib.error

    from kabusys.data import edinet_collector

    def raise_403(url, timeout=30):
        raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(edinet_collector, "_fetch_edinet_json", raise_403)
    with caplog.at_level(logging.ERROR):
        result = fetch_edinet_disclosures(date(2024, 9, 1))

    assert result == []
    assert "認証エラー" in caplog.text


def test_fetch_edinet_disclosures_generic_error_returns_empty(monkeypatch):
    """一般的な例外が発生した場合、空リストを返すことを確認する。"""
    from kabusys.data import edinet_collector

    def raise_error(url, timeout=30):
        raise RuntimeError("network error")

    monkeypatch.setattr(edinet_collector, "_fetch_edinet_json", raise_error)
    result = fetch_edinet_disclosures(date(2024, 9, 1))
    assert result == []


# ---------------------------------------------------------------------------
# run_edinet_collection テスト
# ---------------------------------------------------------------------------


def test_run_edinet_collection_saves_disclosures(disc_db, monkeypatch):
    """run_edinet_collection が開示を収集して DB に保存することを確認する。"""
    from kabusys.data import edinet_collector

    raw = json.dumps(_SAMPLE_RESPONSE).encode("utf-8")
    monkeypatch.setattr(edinet_collector, "_fetch_edinet_json", lambda url, timeout=30: raw)

    saved = run_edinet_collection(disc_db, target_date=date(2024, 9, 1))
    assert saved == 2
    count = disc_db.execute("SELECT COUNT(*) FROM raw_disclosures").fetchone()[0]
    assert count == 2


def test_run_edinet_collection_idempotent(disc_db, monkeypatch):
    """同じ日を2回収集しても重複しないことを確認する（ON CONFLICT DO NOTHING）。"""
    from kabusys.data import edinet_collector

    raw = json.dumps(_SAMPLE_RESPONSE).encode("utf-8")
    monkeypatch.setattr(edinet_collector, "_fetch_edinet_json", lambda url, timeout=30: raw)

    first = run_edinet_collection(disc_db, target_date=date(2024, 9, 1))
    second = run_edinet_collection(disc_db, target_date=date(2024, 9, 1))
    assert first == 2
    assert second == 0
    count = disc_db.execute("SELECT COUNT(*) FROM raw_disclosures").fetchone()[0]
    assert count == 2


def test_run_edinet_collection_default_date(disc_db, monkeypatch):
    """target_date=None のとき today が使われることを確認する。"""
    from kabusys.data import edinet_collector

    captured_urls: list[str] = []

    def fake_fetch(url, timeout=30):
        captured_urls.append(url)
        return json.dumps({"metadata": {"status": "200"}, "results": []}).encode("utf-8")

    monkeypatch.setattr(edinet_collector, "_fetch_edinet_json", fake_fetch)
    run_edinet_collection(disc_db, target_date=None)

    today_str = date.today().strftime("%Y-%m-%d")
    assert any(today_str in url for url in captured_urls)


def test_run_edinet_collection_source_edinet_in_db(disc_db, monkeypatch):
    """保存されたレコードの source が 'edinet' であることを確認する。"""
    from kabusys.data import edinet_collector

    raw = json.dumps(_SAMPLE_RESPONSE).encode("utf-8")
    monkeypatch.setattr(edinet_collector, "_fetch_edinet_json", lambda url, timeout=30: raw)

    run_edinet_collection(disc_db, target_date=date(2024, 9, 1))
    rows = disc_db.execute("SELECT DISTINCT source FROM raw_disclosures").fetchall()
    assert rows == [("edinet",)]
