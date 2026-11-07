"""Issue #424: prices_daily の分割補正（後方補正）のテスト。"""

from __future__ import annotations

from datetime import date

import pytest

from kabusys.data import jquants_client as jquants
from kabusys.data.pipeline import sync_raw_prices_to_prices_daily
from kabusys.data.price_adjustment import rebuild_adjusted_prices
from kabusys.data.schema import init_schema


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def _raw(
    conn,
    d: str,
    code: str,
    close: float,
    volume: int = 1000,
    adj: float | None = None,
    turnover: float | None = 1_000_000.0,
) -> None:
    conn.execute(
        "INSERT INTO raw_prices "
        "(date, code, open, high, low, close, volume, turnover, adj_factor) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [d, code, close, close, close, close, volume, turnover, adj],
    )


def _pd(conn, code: str) -> dict[str, tuple[float, float, int, float | None]]:
    rows = conn.execute(
        "SELECT date, open, close, volume, turnover FROM prices_daily WHERE code = ? ORDER BY date",
        [code],
    ).fetchall()
    return {
        r[0].isoformat(): (
            float(r[1]),
            float(r[2]),
            int(r[3]),
            None if r[4] is None else float(r[4]),
        )
        for r in rows
    }


def _split_series(conn, code: str = "83880") -> None:
    """1:5 分割（2026-09-29 権利落ち）を含む系列。"""
    _raw(conn, "2026-09-25", code, 11000.0, volume=100)
    _raw(conn, "2026-09-26", code, 11130.0, volume=200, adj=1.0)
    _raw(conn, "2026-09-29", code, 2185.0, volume=1500, adj=0.2)
    _raw(conn, "2026-09-30", code, 2200.0, volume=1000)


# ---------------------------------------------------------------------------
# save_daily_quotes: AdjFactor の保存（spec §2.1）
# ---------------------------------------------------------------------------


def _rec(adj=None, *, with_key=True):
    r = {
        "Date": "2026-09-29",
        "Code": "83880",
        "O": 2185.0,
        "H": 2200.0,
        "L": 2150.0,
        "C": 2185.0,
        "Vo": 1500,
        "Va": 3_000_000,
    }
    if with_key:
        r["AdjFactor"] = adj
    return r


def _adj(conn):
    return conn.execute("SELECT adj_factor FROM raw_prices WHERE code='83880'").fetchone()[0]


def test_save_daily_quotes_saves_adj_factor(conn):
    jquants.save_daily_quotes(conn, [_rec(0.2)])
    assert float(_adj(conn)) == pytest.approx(0.2)


def test_save_daily_quotes_adj_factor_missing_key_is_null(conn):
    jquants.save_daily_quotes(conn, [_rec(with_key=False)])
    assert _adj(conn) is None


def test_save_daily_quotes_adj_factor_invalid_is_null(conn):
    jquants.save_daily_quotes(conn, [_rec("abc")])
    assert _adj(conn) is None


def test_save_daily_quotes_adj_factor_updated_on_conflict(conn):
    jquants.save_daily_quotes(conn, [_rec(None)])
    jquants.save_daily_quotes(conn, [_rec("0.2")])
    assert float(_adj(conn)) == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# rebuild_adjusted_prices（spec §2.2）
# ---------------------------------------------------------------------------


def test_rebuild_adjusts_pre_split_prices_and_volume(conn):
    _split_series(conn)
    n = rebuild_adjusted_prices(conn, ["83880"])
    pd = _pd(conn, "83880")
    assert n == 4
    # 分割前: 価格 × 0.2、出来高 × 5、売買代金は不変
    assert pd["2026-09-25"][1] == pytest.approx(2200.0)
    assert pd["2026-09-25"][2] == 500
    assert pd["2026-09-25"][3] == pytest.approx(1_000_000.0)
    assert pd["2026-09-26"][1] == pytest.approx(2226.0)
    assert pd["2026-09-26"][2] == 1000
    # 権利落ち日以降は不変（最新日は実際の株価と一致）
    assert pd["2026-09-29"][1] == pytest.approx(2185.0)
    assert pd["2026-09-29"][2] == 1500
    assert pd["2026-09-30"][1] == pytest.approx(2200.0)
    assert pd["2026-09-30"][2] == 1000


def test_rebuild_is_idempotent(conn):
    _split_series(conn)
    rebuild_adjusted_prices(conn, ["83880"])
    first = _pd(conn, "83880")
    rebuild_adjusted_prices(conn, ["83880"])
    assert _pd(conn, "83880") == first


def test_rebuild_overwrites_existing_unadjusted_rows(conn):
    _split_series(conn)
    sync_raw_prices_to_prices_daily(conn, date(2026, 9, 25), date(2026, 9, 26))  # 補正前
    rebuild_adjusted_prices(conn, ["83880"])
    assert _pd(conn, "83880")["2026-09-25"][1] == pytest.approx(2200.0)


def test_rebuild_multiple_splits_use_product(conn):
    _raw(conn, "2026-01-05", "1111", 1000.0, volume=10)
    _raw(conn, "2026-01-06", "1111", 500.0, volume=20, adj=0.5)  # 1:2
    _raw(conn, "2026-01-07", "1111", 100.0, volume=100, adj=0.2)  # 1:5
    _raw(conn, "2026-01-08", "1111", 101.0, volume=100)
    rebuild_adjusted_prices(conn, ["1111"])
    pd = _pd(conn, "1111")
    assert pd["2026-01-05"][1] == pytest.approx(100.0)  # 1000 × 0.5 × 0.2
    assert pd["2026-01-05"][2] == 100  # 10 ÷ 0.1
    assert pd["2026-01-06"][1] == pytest.approx(100.0)  # 500 × 0.2
    assert pd["2026-01-06"][2] == 100
    assert pd["2026-01-08"][1] == pytest.approx(101.0)


def test_rebuild_reverse_split(conn):
    """併合（2:1 → adj_factor 2.0）は過去の株価を引き上げる。"""
    _raw(conn, "2026-01-05", "2222", 100.0, volume=1000)
    _raw(conn, "2026-01-06", "2222", 200.0, volume=500, adj=2.0)
    rebuild_adjusted_prices(conn, ["2222"])
    pd = _pd(conn, "2222")
    assert pd["2026-01-05"][1] == pytest.approx(200.0)
    assert pd["2026-01-05"][2] == 500


def test_rebuild_treats_null_and_invalid_factors_as_one(conn):
    _raw(conn, "2026-01-05", "3333", 100.0, adj=None)
    _raw(conn, "2026-01-06", "3333", 100.0, adj=0.0)  # 不正値（0）は 1 とみなす
    _raw(conn, "2026-01-07", "3333", 100.0, adj=None)
    rebuild_adjusted_prices(conn, ["3333"])
    pd = _pd(conn, "3333")
    assert [v[1] for v in pd.values()] == [100.0, 100.0, 100.0]


def test_rebuild_applies_quality_filter_and_keeps_factor_of_filtered_rows(conn):
    _raw(conn, "2026-01-05", "4444", 1000.0)
    # 権利落ち日に売買がなく OHLC が NULL でも、係数は過去分に反映される
    conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, adj_factor)"
        " VALUES ('2026-01-06', '4444', NULL, NULL, NULL, NULL, 0, NULL, 0.5)"
    )
    _raw(conn, "2026-01-07", "4444", 500.0)
    rebuild_adjusted_prices(conn, ["4444"])
    pd = _pd(conn, "4444")
    assert "2026-01-06" not in pd
    assert pd["2026-01-05"][1] == pytest.approx(500.0)


def test_rebuild_none_targets_codes_with_factors_only(conn):
    _split_series(conn, "83880")
    _raw(conn, "2026-09-25", "7203", 3000.0)
    n = rebuild_adjusted_prices(conn)
    assert n == 4
    assert _pd(conn, "7203") == {}
    assert _pd(conn, "83880")["2026-09-25"][1] == pytest.approx(2200.0)


def test_rebuild_does_not_touch_other_codes(conn):
    _split_series(conn, "83880")
    _split_series(conn, "99990")
    rebuild_adjusted_prices(conn, ["83880"])
    assert _pd(conn, "99990") == {}


def test_rebuild_empty_code_list_is_noop(conn):
    _split_series(conn)
    assert rebuild_adjusted_prices(conn, []) == 0
    assert _pd(conn, "83880") == {}


# ---------------------------------------------------------------------------
# 日次の同期（spec §2.2）
# ---------------------------------------------------------------------------


def test_sync_rebuilds_history_of_code_with_new_factor(conn):
    # 過去分は補正前のまま同期済み
    _raw(conn, "2026-09-24", "83880", 11000.0, volume=100)
    _raw(conn, "2026-09-25", "83880", 11100.0, volume=100)
    sync_raw_prices_to_prices_daily(conn, date(2026, 9, 24), date(2026, 9, 25))
    # 係数のない銘柄
    _raw(conn, "2026-09-25", "7203", 3000.0)
    _raw(conn, "2026-09-29", "7203", 3010.0)
    # 新しい日付に分割の係数が出る
    _raw(conn, "2026-09-26", "83880", 11130.0, volume=200)
    _raw(conn, "2026-09-29", "83880", 2185.0, volume=1500, adj=0.2)

    synced = sync_raw_prices_to_prices_daily(conn, date(2026, 9, 26), date(2026, 9, 29))

    assert synced == 3
    pd = _pd(conn, "83880")
    # 同期範囲外の過去行も作り直される
    assert pd["2026-09-24"][1] == pytest.approx(2200.0)
    assert pd["2026-09-24"][2] == 500
    assert pd["2026-09-26"][1] == pytest.approx(2226.0)
    assert pd["2026-09-29"][1] == pytest.approx(2185.0)
    # 係数のない銘柄は従来どおり
    pd7203 = _pd(conn, "7203")
    assert pd7203["2026-09-29"][1] == pytest.approx(3010.0)
    assert "2026-09-25" not in pd7203  # 同期範囲外は書かない（従来どおり）


def test_sync_range_applies_factor_after_range(conn):
    """同期範囲より後に係数がある場合も M(d) が掛かる（raw にある後日分を使う）。"""
    _raw(conn, "2026-09-26", "83880", 11130.0, volume=200)
    _raw(conn, "2026-09-29", "83880", 2185.0, volume=1500, adj=0.2)
    sync_raw_prices_to_prices_daily(conn, date(2026, 9, 26), date(2026, 9, 26))
    assert _pd(conn, "83880")["2026-09-26"][1] == pytest.approx(2226.0)


def test_sync_is_idempotent_with_factor(conn):
    _split_series(conn)
    sync_raw_prices_to_prices_daily(conn, date(2026, 9, 25), date(2026, 9, 30))
    first = _pd(conn, "83880")
    sync_raw_prices_to_prices_daily(conn, date(2026, 9, 25), date(2026, 9, 30))
    assert _pd(conn, "83880") == first
    assert first["2026-09-25"][1] == pytest.approx(2200.0)


def test_rebuild_removes_rows_whose_raw_fails_quality_filter(conn):
    _split_series(conn)
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
        "VALUES ('2026-09-24', '83880', 0, 0, 0, 0, 0, NULL)"
    )
    conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover) "
        "VALUES ('2026-09-24', '83880', 0, 0, 0, 0, 0, NULL)"
    )
    # raw_prices に対応行がない prices_daily 行は触らない
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
        "VALUES ('2026-09-01', '83880', 9000, 9000, 9000, 9000, 10, NULL)"
    )
    rebuild_adjusted_prices(conn, ["83880"])
    pd = _pd(conn, "83880")
    assert "2026-09-24" not in pd
    assert pd["2026-09-01"][1] == pytest.approx(9000.0)


# ---------------------------------------------------------------------------
# Fix round 1 / I1: ETL 停止後、同期範囲より前に取得した raw 行も同期・補正する
# ---------------------------------------------------------------------------


def test_daily_etl_syncs_all_fetched_dates_after_outage(conn, monkeypatch):
    from unittest import mock

    from kabusys.data import pipeline

    # 最後に取得した日は 2026-09-22（その後 ETL が止まっていた）
    _raw(conn, "2026-09-22", "83880", 11000.0, volume=100)
    sync_raw_prices_to_prices_daily(conn, date(2026, 9, 22), date(2026, 9, 22))

    def fake_fetch(code=None, date_from=None, date_to=None):
        assert date_from == date(2026, 9, 20)  # last(9/22) - (backfill 3 - 1)
        return [
            {
                "Date": "2026-09-28",
                "Code": "83880",
                "O": 11130,
                "H": 11130,
                "L": 11130,
                "C": 11130,
                "Vo": 200,
                "Va": 1,
                "AdjFactor": 1.0,
            },
            # 分割の係数は trading_day - 2 より前の日付にある
            {
                "Date": "2026-09-29",
                "Code": "83880",
                "O": 2185,
                "H": 2185,
                "L": 2185,
                "C": 2185,
                "Vo": 1500,
                "Va": 1,
                "AdjFactor": 0.2,
            },
            {
                "Date": "2026-10-09",
                "Code": "83880",
                "O": 2300,
                "H": 2300,
                "L": 2300,
                "C": 2300,
                "Vo": 1000,
                "Va": 1,
                "AdjFactor": 1.0,
            },
        ]

    monkeypatch.setattr(pipeline.jq, "fetch_daily_quotes", fake_fetch)
    with (
        mock.patch.object(pipeline, "run_calendar_etl", return_value=(0, 0)),
        mock.patch.object(pipeline, "run_financials_etl", return_value=(0, 0)),
        mock.patch.object(pipeline, "run_topix_etl", return_value=(0, 0)),
        mock.patch.object(pipeline, "run_dividends_etl", return_value=(0, 0)),
        mock.patch.object(pipeline.jq, "fetch_earnings_calendar", return_value=[]),
    ):
        result = pipeline.run_daily_etl(
            conn, target_date=date(2026, 10, 9), run_quality_checks=False
        )

    pd = _pd(conn, "83880")
    assert result.prices_daily_synced == 4  # 9/22（backfill 再取得範囲）を含む
    assert pd["2026-09-28"][1] == pytest.approx(2226.0)  # 範囲外の古い行も同期・補正
    assert pd["2026-09-29"][1] == pytest.approx(2185.0)
    assert pd["2026-09-22"][1] == pytest.approx(2200.0)  # 係数で過去分も作り直し
    assert pd["2026-10-09"][1] == pytest.approx(2300.0)
