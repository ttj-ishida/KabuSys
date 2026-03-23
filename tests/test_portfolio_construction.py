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


# ---------------------------------------------------------------------------
# Task 2: portfolio_builder.py
# ---------------------------------------------------------------------------


def test_select_candidates_top_n():
    """select_candidates → スコア降順で上位 max_positions 件を返す。"""
    from kabusys.portfolio.portfolio_builder import select_candidates

    signals = [
        {"code": "A", "signal_rank": 3, "score": 0.5},
        {"code": "B", "signal_rank": 1, "score": 0.9},
        {"code": "C", "signal_rank": 2, "score": 0.7},
        {"code": "D", "signal_rank": 4, "score": 0.3},
    ]
    result = select_candidates(signals, max_positions=2)
    assert len(result) == 2
    assert result[0]["code"] == "B"
    assert result[1]["code"] == "C"


def test_select_candidates_fewer_than_max():
    """候補数 ≤ max_positions なら全件返す。"""
    from kabusys.portfolio.portfolio_builder import select_candidates

    signals = [
        {"code": "A", "signal_rank": 1, "score": 0.8},
        {"code": "B", "signal_rank": 2, "score": 0.6},
    ]
    result = select_candidates(signals, max_positions=10)
    assert len(result) == 2


def test_select_candidates_empty():
    """空リスト → 空リスト。"""
    from kabusys.portfolio.portfolio_builder import select_candidates

    assert select_candidates([], max_positions=10) == []


def test_calc_equal_weights_sums_to_one():
    """calc_equal_weights → 重みの合計が 1.0。"""
    from kabusys.portfolio.portfolio_builder import calc_equal_weights

    candidates = [
        {"code": "A", "score": 0.9, "signal_rank": 1},
        {"code": "B", "score": 0.7, "signal_rank": 2},
        {"code": "C", "score": 0.5, "signal_rank": 3},
    ]
    weights = calc_equal_weights(candidates)
    assert set(weights.keys()) == {"A", "B", "C"}
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    # 等分
    assert abs(weights["A"] - 1 / 3) < 1e-9


def test_calc_equal_weights_empty():
    """candidates が空なら {}。"""
    from kabusys.portfolio.portfolio_builder import calc_equal_weights

    assert calc_equal_weights([]) == {}


def test_calc_score_weights_proportional():
    """calc_score_weights → score に比例した重み。"""
    from kabusys.portfolio.portfolio_builder import calc_score_weights

    candidates = [
        {"code": "A", "score": 0.6, "signal_rank": 1},
        {"code": "B", "score": 0.4, "signal_rank": 2},
    ]
    weights = calc_score_weights(candidates)
    assert abs(weights["A"] - 0.6) < 1e-9
    assert abs(weights["B"] - 0.4) < 1e-9


def test_calc_score_weights_fallback_on_all_zero():
    """全スコアが 0.0 のとき等金額配分にフォールバックする。"""
    from kabusys.portfolio.portfolio_builder import calc_score_weights

    candidates = [
        {"code": "A", "score": 0.0, "signal_rank": 1},
        {"code": "B", "score": 0.0, "signal_rank": 2},
    ]
    weights = calc_score_weights(candidates)
    assert abs(weights["A"] - 0.5) < 1e-9
    assert abs(weights["B"] - 0.5) < 1e-9


def test_calc_score_weights_empty():
    """candidates が空なら {}。"""
    from kabusys.portfolio.portfolio_builder import calc_score_weights

    assert calc_score_weights([]) == {}
