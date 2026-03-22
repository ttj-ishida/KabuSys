"""Phase 5 ポートフォリオ構築エンジン テスト"""
from __future__ import annotations

import pytest
from kabusys.data.schema import init_schema


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Task 1: schema.py — stocks テーブル
# ---------------------------------------------------------------------------

def test_stocks_table_exists(conn):
    """stocks テーブルが init_schema で作成される。"""
    row = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'stocks'"
    ).fetchone()
    assert row[0] == 1


def test_stocks_table_insert(conn):
    """stocks テーブルに INSERT できる。"""
    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["1234", "テスト株式会社", "Prime", "電気機器"],
    )
    row = conn.execute("SELECT code, sector FROM stocks WHERE code = '1234'").fetchone()
    assert row is not None
    assert row[0] == "1234"
    assert row[1] == "電気機器"


def test_stocks_table_upsert(conn):
    """stocks テーブルは PRIMARY KEY (code) で UPSERT できる（冪等）。"""
    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["1234", "旧名称", "Prime", "電気機器"],
    )
    conn.execute(
        """
        INSERT INTO stocks (code, name, market, sector)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (code) DO UPDATE SET
            name   = excluded.name,
            market = excluded.market,
            sector = excluded.sector
        """,
        ["1234", "新名称", "Standard", "機械"],
    )
    row = conn.execute("SELECT name, market, sector FROM stocks WHERE code = '1234'").fetchone()
    assert row[0] == "新名称"
    assert row[1] == "Standard"
    assert row[2] == "機械"


# ---------------------------------------------------------------------------
# Task 1: jquants_client.py — fetch_listed_info のマッピングテスト
# ---------------------------------------------------------------------------

def test_fetch_listed_info_field_mapping():
    """fetch_listed_info が J-Quants API レスポンスを stocks スキーマにマッピングする。"""
    from unittest.mock import patch
    from kabusys.data.jquants_client import fetch_listed_info

    mock_response = {
        "info": [
            {
                "Code": "13010",
                "CompanyName": "テスト会社",
                "MarketCode": "0111",
                "Sector33CodeName": "電気機器",
            },
            {
                "Code": "20050",
                "CompanyName": "サンプル工業",
                "MarketCode": "0121",
                "Sector33CodeName": "機械",
            },
            {
                "Code": "30090",
                "CompanyName": "グロース社",
                "MarketCode": "0131",
                "Sector33CodeName": "情報通信業",
            },
            {
                "Code": "99999",
                "CompanyName": "その他",
                "MarketCode": "9999",
                "Sector33CodeName": "その他",
            },
        ]
    }

    with patch("kabusys.data.jquants_client._request", return_value=mock_response):
        result = fetch_listed_info(date_=None)

    assert len(result) == 4
    # MarketCode → market 変換確認
    by_code = {r["code"]: r for r in result}
    assert by_code["13010"]["market"] == "Prime"
    assert by_code["20050"]["market"] == "Standard"
    assert by_code["30090"]["market"] == "Growth"
    assert by_code["99999"]["market"] == "Other"
    # name, sector
    assert by_code["13010"]["name"] == "テスト会社"
    assert by_code["13010"]["sector"] == "電気機器"


def test_fetch_listed_info_missing_fields_skipped():
    """Code が欠損するレコードはスキップされる。"""
    from unittest.mock import patch
    from kabusys.data.jquants_client import fetch_listed_info

    mock_response = {
        "info": [
            {"Code": "1234", "CompanyName": "正常", "MarketCode": "0111", "Sector33CodeName": "電気機器"},
            {"Code": "", "CompanyName": "コード欠損", "MarketCode": "0111", "Sector33CodeName": ""},
            {"CompanyName": "コードなし", "MarketCode": "0111", "Sector33CodeName": ""},
        ]
    }

    with patch("kabusys.data.jquants_client._request", return_value=mock_response):
        result = fetch_listed_info(date_=None)

    assert len(result) == 1
    assert result[0]["code"] == "1234"
