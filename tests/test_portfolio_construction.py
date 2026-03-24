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


# ---------------------------------------------------------------------------
# Task 3: position_sizing.py
# ---------------------------------------------------------------------------


def test_calc_position_sizes_risk_based_basic():
    """risk_based: 0.5% リスク・8% 損切りで株数が計算される。

    portfolio_value=10_000_000, price=1000
    → raw = floor(10M*0.005 / (1000*0.08)) = floor(50000/80) = floor(625) = 625 株
    → 100株単位切り捨て: (625 // 100) * 100 = 600 株
    """
    from kabusys.portfolio.position_sizing import calc_position_sizes

    result = calc_position_sizes(
        weights={},
        candidates=[{"code": "1234", "score": 0.8, "signal_rank": 1}],
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={},
        open_prices={"1234": 1000.0},
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    assert "1234" in result
    shares = result["1234"]
    assert shares == 600


def test_calc_position_sizes_max_position_pct_cap():
    """max_position_pct=0.10 が守られる（1銘柄上限 = 総資産の10%）。

    portfolio_value=1_000_000, price=1000 → 上限 = floor(1M * 0.10 / 1000) = 100 株
    """
    from kabusys.portfolio.position_sizing import calc_position_sizes

    result = calc_position_sizes(
        weights={},
        candidates=[{"code": "1234", "score": 0.8, "signal_rank": 1}],
        portfolio_value=1_000_000,
        available_cash=1_000_000,
        current_positions={},
        open_prices={"1234": 1000.0},
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    assert result.get("1234", 0) <= 100


def test_calc_position_sizes_lot_size_truncation():
    """100株単位に切り捨てられる。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    # 10M * 0.005 / (1100 * 0.08) = 568.18... → (568 // 100) * 100 = 500 株
    result = calc_position_sizes(
        weights={},
        candidates=[{"code": "1234", "score": 0.8, "signal_rank": 1}],
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={},
        open_prices={"1234": 1100.0},
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    shares = result.get("1234", 0)
    assert shares % 100 == 0


def test_calc_position_sizes_max_utilization_aggregate_cap():
    """available_cash を超える場合にスケールダウンされる。

    3銘柄 × risk_based → 投資合計が available_cash 以内に収まる。
    """
    from kabusys.portfolio.position_sizing import calc_position_sizes

    candidates = [
        {"code": "A", "score": 0.9, "signal_rank": 1},
        {"code": "B", "score": 0.8, "signal_rank": 2},
        {"code": "C", "score": 0.7, "signal_rank": 3},
    ]
    open_prices = {"A": 500.0, "B": 500.0, "C": 500.0}
    result = calc_position_sizes(
        weights={},
        candidates=candidates,
        portfolio_value=1_000_000,
        available_cash=1_000_000,
        current_positions={},
        open_prices=open_prices,
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    total_invested = sum(result.get(c["code"], 0) * open_prices[c["code"]] for c in candidates)
    assert total_invested <= 1_000_000 * 1.001  # 0.1% の誤差許容


def test_calc_position_sizes_equal_method():
    """allocation_method="equal" → 等金額配分で株数を計算。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    candidates = [
        {"code": "A", "score": 0.9, "signal_rank": 1},
        {"code": "B", "score": 0.5, "signal_rank": 2},
    ]
    weights = {"A": 0.5, "B": 0.5}

    result = calc_position_sizes(
        weights=weights,
        candidates=candidates,
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={},
        open_prices={"A": 1000.0, "B": 1000.0},
        allocation_method="equal",
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    # alloc_A = 10M * 0.5 * 0.70 = 3_500_000 → floor(3500000 / 1000) = 3500 → 上限 1000 株
    assert result.get("A", 0) == 1000
    assert result.get("B", 0) == 1000


def test_calc_position_sizes_score_method():
    """allocation_method="score" → スコア比例配分。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    candidates = [
        {"code": "A", "score": 0.6, "signal_rank": 1},
        {"code": "B", "score": 0.4, "signal_rank": 2},
    ]
    weights = {"A": 0.6, "B": 0.4}

    result = calc_position_sizes(
        weights=weights,
        candidates=candidates,
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={},
        open_prices={"A": 1000.0, "B": 1000.0},
        allocation_method="score",
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    # A: 10M * 0.6 * 0.70 = 4_200_000 → floor(4200000/1000) = 4200 → 上限 1000
    # B: 10M * 0.4 * 0.70 = 2_800_000 → floor(2800000/1000) = 2800 → 上限 1000
    assert result.get("A", 0) == 1000
    assert result.get("B", 0) == 1000


def test_calc_position_sizes_no_price_skipped():
    """open_prices に価格がない銘柄はスキップ（0株）。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    result = calc_position_sizes(
        weights={},
        candidates=[{"code": "9999", "score": 0.9, "signal_rank": 1}],
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={},
        open_prices={},  # 価格なし
        allocation_method="risk_based",
    )
    assert result.get("9999", 0) == 0


def test_calc_position_sizes_existing_position_excluded():
    """既存保有分は追加購入しない（追加分 = max(0, target - current)）。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    # target=600, current=600 → 追加分=0
    result = calc_position_sizes(
        weights={},
        candidates=[{"code": "1234", "score": 0.9, "signal_rank": 1}],
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={"1234": 600},  # 既に 600 株保有
        open_prices={"1234": 1000.0},
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    assert result.get("1234", 0) == 0


# ---------------------------------------------------------------------------
# Task 4: risk_adjustment.py
# ---------------------------------------------------------------------------

def test_apply_sector_cap_removes_overweight_sector():
    """同一セクターが 30% 超なら新規候補を除外。

    既存保有: 電気機器 A = 1000株 × 1000円 = 1,000,000円
    portfolio_value = 3,000,000 → セクター比 = 33.3% > 30%
    → 電気機器の新規候補 B を除外
    """
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    candidates = [
        {"code": "B", "score": 0.9, "signal_rank": 1},  # 電気機器
        {"code": "C", "score": 0.8, "signal_rank": 2},  # 機械
    ]
    sector_map = {"A": "電気機器", "B": "電気機器", "C": "機械"}
    current_positions = {"A": 1000}
    open_prices = {"A": 1000.0, "B": 900.0, "C": 800.0}

    result = apply_sector_cap(
        candidates=candidates,
        sector_map=sector_map,
        portfolio_value=3_000_000,
        current_positions=current_positions,
        open_prices=open_prices,
        max_sector_pct=0.30,
    )

    codes = {c["code"] for c in result}
    assert "B" not in codes   # 除外
    assert "C" in codes       # 通過


def test_apply_sector_cap_allows_under_limit():
    """セクター比が 30% 未満なら除外しない。"""
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    candidates = [
        {"code": "B", "score": 0.9, "signal_rank": 1},
    ]
    sector_map = {"A": "電気機器", "B": "電気機器"}
    current_positions = {"A": 100}
    open_prices = {"A": 1000.0, "B": 900.0}

    result = apply_sector_cap(
        candidates=candidates,
        sector_map=sector_map,
        portfolio_value=5_000_000,  # A = 100_000 / 5M = 2% < 30%
        current_positions=current_positions,
        open_prices=open_prices,
        max_sector_pct=0.30,
    )

    assert len(result) == 1
    assert result[0]["code"] == "B"


def test_apply_sector_cap_unknown_sector_passes():
    """sector_map にないコード（セクター不明）は制限なく通過する。"""
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    candidates = [
        {"code": "X", "score": 0.9, "signal_rank": 1},
    ]
    sector_map = {}  # X のセクターなし
    result = apply_sector_cap(
        candidates=candidates,
        sector_map=sector_map,
        portfolio_value=1_000_000,
        current_positions={},
        open_prices={"X": 1000.0},
        max_sector_pct=0.30,
    )
    assert len(result) == 1
    assert result[0]["code"] == "X"


def test_apply_sector_cap_preserves_fields():
    """apply_sector_cap は {code, score, signal_rank} 形式を保持して返す。"""
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    candidates = [
        {"code": "A", "score": 0.9, "signal_rank": 1},
        {"code": "B", "score": 0.7, "signal_rank": 2},
    ]
    sector_map = {"A": "電気機器", "B": "機械"}
    result = apply_sector_cap(
        candidates=candidates,
        sector_map=sector_map,
        portfolio_value=10_000_000,
        current_positions={},
        open_prices={"A": 1000.0, "B": 1000.0},
        max_sector_pct=0.30,
    )
    assert len(result) == 2
    assert result[0]["code"] == "A"
    assert "score" in result[0]
    assert "signal_rank" in result[0]


def test_calc_regime_multiplier_values():
    """calc_regime_multiplier: bull=1.0, neutral=0.7, bear=0.3, 未知=1.0。"""
    from kabusys.portfolio.risk_adjustment import calc_regime_multiplier

    assert calc_regime_multiplier("bull") == 1.0
    assert calc_regime_multiplier("neutral") == 0.7
    assert calc_regime_multiplier("bear") == 0.3
    assert calc_regime_multiplier("unknown_regime") == 1.0


def test_calc_regime_multiplier_case_sensitive():
    """大文字の 'Bull' は未知とみなし 1.0 にフォールバック（DB は小文字で格納）。"""
    from kabusys.portfolio.risk_adjustment import calc_regime_multiplier

    assert calc_regime_multiplier("Bull") == 1.0


# ---------------------------------------------------------------------------
# Task 4: 統合テスト（portfolio_builder + position_sizing + risk_adjustment）
# ---------------------------------------------------------------------------

def test_integration_neutral_regime_reduces_available_cash():
    """`neutral` レジームで available_cash が 70% に抑制される。

    portfolio_value=10M, multiplier=0.7 → available_cash=7M
    risk_based: 10M * 0.005 / (1000 * 0.08) = 625 → 600 株 × 1000 = 600_000
    total_cost=600_000 < available_cash=7_000_000 → スケールダウンなし → 600 株
    """
    from kabusys.portfolio.portfolio_builder import select_candidates
    from kabusys.portfolio.position_sizing import calc_position_sizes
    from kabusys.portfolio.risk_adjustment import calc_regime_multiplier

    portfolio_value = 10_000_000
    multiplier = calc_regime_multiplier("neutral")
    assert multiplier == 0.7
    available_cash = portfolio_value * multiplier  # 7_000_000

    candidates = select_candidates(
        [{"code": "1234", "signal_rank": 1, "score": 0.9}]
    )
    result = calc_position_sizes(
        weights={},
        candidates=candidates,
        portfolio_value=portfolio_value,
        available_cash=available_cash,
        current_positions={},
        open_prices={"1234": 1000.0},
        allocation_method="risk_based",
    )
    assert result.get("1234", 0) == 600


def test_integration_sector_cap_then_size():
    """セクター上限フィルタ後に position_sizing が動作する。"""
    from kabusys.portfolio.portfolio_builder import select_candidates, calc_equal_weights
    from kabusys.portfolio.position_sizing import calc_position_sizes
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    signals = [
        {"code": "A", "signal_rank": 1, "score": 0.9},  # 電気機器（除外される）
        {"code": "B", "signal_rank": 2, "score": 0.7},  # 機械（通過）
    ]
    sector_map = {"existing_A": "電気機器", "A": "電気機器", "B": "機械"}
    current_positions = {"existing_A": 1000}  # 電気機器に 1000 株保有
    open_prices = {"existing_A": 1200.0, "A": 1000.0, "B": 900.0}
    portfolio_value = 3_500_000  # existing_A = 1.2M / 3.5M = 34.3% > 30%

    candidates = select_candidates(signals)
    filtered = apply_sector_cap(
        candidates, sector_map, portfolio_value, current_positions, open_prices
    )

    assert len(filtered) == 1
    assert filtered[0]["code"] == "B"

    weights = calc_equal_weights(filtered)
    result = calc_position_sizes(
        weights=weights,
        candidates=filtered,
        portfolio_value=portfolio_value,
        available_cash=portfolio_value,
        current_positions=current_positions,
        open_prices=open_prices,
        allocation_method="equal",
        max_position_pct=0.10,
        max_utilization=0.70,
    )
    assert result.get("A", 0) == 0   # セクター除外
    assert result.get("B", 0) > 0    # 購入あり


# ---------------------------------------------------------------------------
# レビュー対応: 追加テスト
# ---------------------------------------------------------------------------

def test_apply_sector_cap_sell_codes_excluded_from_exposure():
    """sell_codes に含まれる銘柄はセクターエクスポージャーから除外される。

    既存保有: 電気機器 A = 1000株 × 1000円 = 1,000,000円  (33.3% > 30%)
    sell_codes に A が含まれる → エクスポージャー = 0 → ブロックされない
    → 電気機器の新規候補 B が通過する
    """
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    candidates = [{"code": "B", "score": 0.9, "signal_rank": 1}]
    sector_map = {"A": "電気機器", "B": "電気機器"}
    current_positions = {"A": 1000}
    open_prices = {"A": 1000.0, "B": 900.0}

    result = apply_sector_cap(
        candidates=candidates,
        sector_map=sector_map,
        portfolio_value=3_000_000,
        current_positions=current_positions,
        open_prices=open_prices,
        max_sector_pct=0.30,
        sell_codes={"A"},
    )

    assert len(result) == 1
    assert result[0]["code"] == "B"


def test_apply_sector_cap_without_sell_codes_blocks_sector():
    """sell_codes なしの場合は従来通りセクター上限で除外される（後退防止）。"""
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    candidates = [{"code": "B", "score": 0.9, "signal_rank": 1}]
    sector_map = {"A": "電気機器", "B": "電気機器"}
    current_positions = {"A": 1000}
    open_prices = {"A": 1000.0, "B": 900.0}

    result = apply_sector_cap(
        candidates=candidates,
        sector_map=sector_map,
        portfolio_value=3_000_000,
        current_positions=current_positions,
        open_prices=open_prices,
        max_sector_pct=0.30,
    )

    assert len(result) == 0


def test_calc_position_sizes_scale_down_greedy_no_zeroing():
    """スケールダウン後、残差貪欲配分により全銘柄ゼロ化が防止される。

    2銘柄 × raw=100株 × 1000円 = 200_000円, available_cash=130_000円
    scale=0.65 → floor(100*0.65)=65 → (65//100)*100=0 → 両方ゼロになる恐れ
    貪欲配分により少なくとも 100 株が割り当てられること。
    """
    from kabusys.portfolio.position_sizing import calc_position_sizes

    candidates = [
        {"code": "A", "score": 0.9, "signal_rank": 1},
        {"code": "B", "score": 0.8, "signal_rank": 2},
    ]
    result = calc_position_sizes(
        weights={"A": 0.5, "B": 0.5},
        candidates=candidates,
        portfolio_value=1_000_000,
        available_cash=130_000,
        current_positions={},
        open_prices={"A": 1000.0, "B": 1000.0},
        allocation_method="equal",
        max_position_pct=0.10,
        max_utilization=0.20,
        lot_size=100,
    )

    total_shares = sum(result.values())
    assert total_shares > 0, "スケールダウン後に全銘柄ゼロになってはならない"
    total_cost = sum(result.get(c["code"], 0) * 1000.0 for c in candidates)
    assert total_cost <= 130_000 * 1.001


def test_calc_position_sizes_scale_down_stays_within_budget():
    """スケールダウン後の投資合計が available_cash を超えない（貪欲配分含む）。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    candidates = [
        {"code": "A", "score": 0.6, "signal_rank": 1},
        {"code": "B", "score": 0.4, "signal_rank": 2},
        {"code": "C", "score": 0.3, "signal_rank": 3},
    ]
    available_cash = 250_000.0
    open_prices = {"A": 1000.0, "B": 800.0, "C": 600.0}

    result = calc_position_sizes(
        weights={},
        candidates=candidates,
        portfolio_value=5_000_000,
        available_cash=available_cash,
        current_positions={},
        open_prices=open_prices,
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        lot_size=100,
    )

    total_cost = sum(result.get(c["code"], 0) * open_prices[c["code"]] for c in candidates)
    assert total_cost <= available_cash * 1.001


def test_calc_position_sizes_cost_buffer_reduces_total():
    """cost_buffer を指定すると aggregate cap 判定が保守的になる。

    cost_buffer=0.1 は 10% のマージンを見込んで total_cost を計算するため、
    スケールダウン後の株式実取得コスト（cost_buffer なし）が available_cash 以内に収まる。
    """
    from kabusys.portfolio.position_sizing import calc_position_sizes

    candidates = [
        {"code": "A", "score": 0.9, "signal_rank": 1},
        {"code": "B", "score": 0.8, "signal_rank": 2},
    ]
    open_prices = {"A": 1000.0, "B": 1000.0}
    available_cash = 200_000.0

    result_with_buffer = calc_position_sizes(
        weights={},
        candidates=candidates,
        portfolio_value=5_000_000,
        available_cash=available_cash,
        current_positions={},
        open_prices=open_prices,
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        lot_size=100,
        cost_buffer=0.1,
    )

    # cost_buffer あり: 実取得コスト（buffer なし）は available_cash 以内
    raw_cost = sum(result_with_buffer.get(c["code"], 0) * open_prices[c["code"]] for c in candidates)
    assert raw_cost <= available_cash


def test_calc_position_sizes_greedy_does_not_exceed_raw_shares():
    """貪欲配分が raw_shares を超えないこと（安全弁の確認）。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    candidates = [{"code": "A", "score": 0.9, "signal_rank": 1}]
    open_prices = {"A": 1000.0}
    # raw_shares = 200株 (risk_based で計算される量), available_cash は潤沢
    result = calc_position_sizes(
        weights={},
        candidates=candidates,
        portfolio_value=10_000_000,
        available_cash=500_000,  # 十分ある
        current_positions={},
        open_prices=open_prices,
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        lot_size=100,
    )

    # 結果は raw_shares（≒600株）以内であること
    assert result.get("A", 0) <= 600
