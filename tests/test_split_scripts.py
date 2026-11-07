"""Issue #424: 分割補正の運用スクリプト（rebuild / backfill / detect）のテスト。"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

import pytest

from kabusys.data.schema import init_schema

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


rebuild_script = _load("rebuild_adjusted_prices")
backfill_script = _load("backfill_adj_factor")
detect_script = _load("detect_split_candidates")


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def _raw(conn, d, code, close, adj=None, volume=1000):
    conn.execute(
        "INSERT INTO raw_prices "
        "(date, code, open, high, low, close, volume, turnover, adj_factor) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)",
        [d, code, close, close, close, close, volume, adj],
    )


def _close(conn, d, code):
    row = conn.execute(
        "SELECT close FROM prices_daily WHERE date = ? AND code = ?", [d, code]
    ).fetchone()
    return None if row is None else float(row[0])


# ---------------------------------------------------------------------------
# scripts/rebuild_adjusted_prices.py
# ---------------------------------------------------------------------------


def _split_series(conn, code="83880"):
    _raw(conn, "2026-09-26", code, 11130.0)
    _raw(conn, "2026-09-29", code, 2185.0, adj=0.2)


def test_rebuild_script_rebuilds_all_codes_with_factors(conn):
    _split_series(conn)
    n = rebuild_script.run(conn, codes=None, dry_run=False)
    assert n == 2
    assert _close(conn, "2026-09-26", "83880") == pytest.approx(2226.0)


def test_rebuild_script_dry_run_does_not_write(conn):
    _split_series(conn)
    n = rebuild_script.run(conn, codes=None, dry_run=True)
    assert n == 0
    assert _close(conn, "2026-09-26", "83880") is None


def test_rebuild_script_limits_to_codes(conn):
    _split_series(conn, "83880")
    _split_series(conn, "485A0")
    rebuild_script.run(conn, codes=["485A0"], dry_run=False)
    assert _close(conn, "2026-09-26", "485A0") == pytest.approx(2226.0)
    assert _close(conn, "2026-09-26", "83880") is None


# ---------------------------------------------------------------------------
# scripts/backfill_adj_factor.py
# ---------------------------------------------------------------------------


def _quote(d: str, code: str, close: float, adj) -> dict:
    return {
        "Date": d,
        "Code": code,
        "O": close,
        "H": close,
        "L": close,
        "C": close,
        "Vo": 1000,
        "Va": 1_000_000,
        "AdjFactor": adj,
    }


def test_backfill_saves_factor_and_rebuilds_history(conn):
    _raw(conn, "2026-09-25", "83880", 11000.0)
    _raw(conn, "2026-09-28", "83880", 11130.0)
    _raw(conn, "2026-09-29", "83880", 2185.0)  # adj_factor 欠落
    _raw(conn, "2026-09-29", "7203", 3000.0)
    # 補正前のまま同期済み
    conn.execute(
        "INSERT INTO prices_daily SELECT date, code, open, high, low, close, volume, turnover "
        "FROM raw_prices"
    )
    calls: list[date] = []

    def fake_fetch(code=None, date_from=None, date_to=None):
        calls.append(date_from)
        assert date_from == date_to
        if date_from == date(2026, 9, 29):
            return [
                _quote("2026-09-29", "83880", 2185.0, 0.2),
                _quote("2026-09-29", "7203", 3000.0, 1.0),
            ]
        return [_quote(date_from.isoformat(), "7203", 3000.0, 1.0)]

    summary = backfill_script.backfill(conn, date(2026, 9, 28), date(2026, 9, 29), fetch=fake_fetch)

    assert calls == [date(2026, 9, 28), date(2026, 9, 29)]
    assert summary["codes"] == ["83880"]
    assert summary["skipped_dates"] == []
    adj = conn.execute(
        "SELECT adj_factor FROM raw_prices WHERE code='83880' AND date='2026-09-29'"
    ).fetchone()[0]
    assert float(adj) == pytest.approx(0.2)
    # 範囲外（2026-09-25）の過去行も作り直される
    assert _close(conn, "2026-09-25", "83880") == pytest.approx(2200.0)
    assert _close(conn, "2026-09-29", "83880") == pytest.approx(2185.0)
    assert _close(conn, "2026-09-29", "7203") == pytest.approx(3000.0)


def test_backfill_skips_unavailable_dates_with_warning(conn, caplog):
    def fake_fetch(code=None, date_from=None, date_to=None):
        if date_from == date(2026, 9, 28):
            raise RuntimeError("HTTP 403: plan does not cover this date")
        return []

    summary = backfill_script.backfill(conn, date(2026, 9, 28), date(2026, 9, 29), fetch=fake_fetch)

    assert summary["skipped_dates"] == [date(2026, 9, 28), date(2026, 9, 29)]
    assert summary["codes"] == []
    assert "スキップ" in caplog.text


def test_backfill_skips_weekends_without_calendar(conn):
    calls: list[date] = []

    def fake_fetch(code=None, date_from=None, date_to=None):
        calls.append(date_from)
        return []

    # 2026-10-02 (金) 〜 2026-10-05 (月)
    backfill_script.backfill(conn, date(2026, 10, 2), date(2026, 10, 5), fetch=fake_fetch)
    assert calls == [date(2026, 10, 2), date(2026, 10, 5)]


# ---------------------------------------------------------------------------
# scripts/detect_split_candidates.py
# ---------------------------------------------------------------------------


def _snapshot(conn):
    return conn.execute("SELECT * FROM raw_prices ORDER BY code, date").fetchall(), conn.execute(
        "SELECT * FROM prices_daily ORDER BY code, date"
    ).fetchall()


def test_detect_split_candidates_finds_ratio_days_without_writing(conn):
    _raw(conn, "2026-09-26", "83880", 11130.0)
    _raw(conn, "2026-09-29", "83880", 2185.0)  # 1:5 相当（係数なし）
    _raw(conn, "2026-09-26", "485A0", 1000.0)
    _raw(conn, "2026-09-29", "485A0", 2010.0)  # 2:1 併合相当
    _raw(conn, "2026-09-26", "7203", 3000.0)
    _raw(conn, "2026-09-29", "7203", 2400.0)  # -20%（候補ではない）
    _raw(conn, "2026-09-26", "1111", 1000.0)
    _raw(conn, "2026-09-29", "1111", 500.0, adj=0.5)  # 係数あり（対象外）
    before = _snapshot(conn)

    found = detect_script.detect_split_candidates(conn, date(2026, 9, 1), date(2026, 9, 30))

    assert [(c["code"], c["date"], c["label"]) for c in found] == [
        ("485A0", date(2026, 9, 29), "2:1 併合"),
        ("83880", date(2026, 9, 29), "1:5 分割"),
    ]
    assert _snapshot(conn) == before


def test_detect_split_candidates_uses_previous_close_before_range(conn):
    _raw(conn, "2026-09-30", "83880", 11130.0)
    _raw(conn, "2026-10-01", "83880", 3700.0)  # 1:3 相当
    found = detect_script.detect_split_candidates(conn, date(2026, 10, 1), date(2026, 10, 31))
    assert [(c["code"], c["label"]) for c in found] == [("83880", "1:3 分割")]
