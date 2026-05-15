"""tests/test_backfill_features.py — backfill_features.backfill() のテスト。"""

from __future__ import annotations

import importlib.util
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from kabusys.data.schema import init_schema

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "backfill_features.py"
_spec = importlib.util.spec_from_file_location("backfill_features", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
backfill = _mod.backfill
_check_rsi_lookback = _mod._check_rsi_lookback
_RSI_LOOKBACK_DAYS = _mod._RSI_LOOKBACK_DAYS


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def _insert_prices(conn, target_date: date) -> None:
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, '1001', 1000, 1050, 990, 1020, 10000, 500_000_000) ON CONFLICT DO NOTHING",
        [target_date],
    )


def _insert_features(conn, target_date: date) -> None:
    conn.execute(
        "INSERT INTO features (date, code, created_at) VALUES (?, '1001', current_timestamp) "
        "ON CONFLICT DO NOTHING",
        [target_date],
    )


def _insert_trading_day(conn, target_date: date) -> None:
    conn.execute(
        "INSERT INTO market_calendar (date, is_trading_day) VALUES (?, TRUE) ON CONFLICT DO NOTHING",
        [target_date],
    )


# ---------------------------------------------------------------------------
# テストケース
# ---------------------------------------------------------------------------

_D1 = date(2024, 1, 4)  # 木曜日（営業日として扱われる）
_D2 = date(2024, 1, 5)  # 金曜日


class TestBackfill:
    def test_processes_date_with_price_data(self, conn):
        """prices_daily にデータがある営業日は build_features が呼ばれる。"""
        _insert_trading_day(conn, _D1)
        _insert_prices(conn, _D1)

        with patch.object(_mod, "build_features", return_value=10) as mock_bf:
            processed, skipped, no_price = backfill(conn, _D1, _D1)

        assert processed == 1
        assert skipped == 0
        assert no_price == 0
        mock_bf.assert_called_once()

    def test_skips_existing_features_without_force(self, conn):
        """既存データがある日は --force なしでスキップされる。"""
        _insert_trading_day(conn, _D1)
        _insert_prices(conn, _D1)
        _insert_features(conn, _D1)

        with patch.object(_mod, "build_features") as mock_bf:
            processed, skipped, no_price = backfill(conn, _D1, _D1, force=False)

        assert processed == 0
        assert skipped == 1
        assert no_price == 0
        mock_bf.assert_not_called()

    def test_force_overwrites_existing_features(self, conn):
        """--force 指定時は既存データがある日も build_features が呼ばれる。"""
        _insert_trading_day(conn, _D1)
        _insert_prices(conn, _D1)
        _insert_features(conn, _D1)

        with patch.object(_mod, "build_features", return_value=5) as mock_bf:
            processed, skipped, no_price = backfill(conn, _D1, _D1, force=True)

        assert processed == 1
        assert skipped == 0
        mock_bf.assert_called_once()

    def test_skips_date_without_price_data(self, conn):
        """prices_daily にデータがない日は no_price カウントに記録されスキップされる。"""
        _insert_trading_day(conn, _D1)
        # prices_daily へのデータ投入なし

        with patch.object(_mod, "build_features") as mock_bf:
            processed, skipped, no_price = backfill(conn, _D1, _D1)

        assert processed == 0
        assert skipped == 0
        assert no_price == 1
        mock_bf.assert_not_called()

    def test_dry_run_does_not_call_build_features(self, conn):
        """--dry-run では build_features が呼ばれず processed のみカウントされる。"""
        _insert_trading_day(conn, _D1)
        _insert_prices(conn, _D1)

        with patch.object(_mod, "build_features") as mock_bf:
            processed, skipped, no_price = backfill(conn, _D1, _D1, dry_run=True)

        assert processed == 1
        assert skipped == 0
        mock_bf.assert_not_called()

    def test_multiple_days_mixed(self, conn):
        """複数日：処理・スキップ・価格なしが混在するケース。"""
        for d in [_D1, _D2]:
            _insert_trading_day(conn, d)

        _insert_prices(conn, _D1)  # _D1: 処理対象（既存なし・価格あり）
        _insert_features(conn, _D2)  # _D2: 既存あり・価格なし → skipped（既存チェックが先）

        with patch.object(_mod, "build_features", return_value=3):
            processed, skipped, no_price = backfill(conn, _D1, _D2, force=False)

        assert processed == 1  # _D1
        assert skipped == 1  # _D2（既存あり）
        assert no_price == 0

    def test_force_actually_overwrites_in_db(self, conn):
        """--force 時に build_features が DELETE+INSERT を行い重複なく上書きされること。

        build_features() 内部は DELETE FROM features WHERE date=? + INSERT のため冪等。
        モックではなく実テーブルで検証する。
        """
        from datetime import timedelta

        from kabusys.data.schema import init_schema as _init  # noqa: F401

        # 十分な価格データを投入（RSI の計算に必要な 15 件分）
        _insert_trading_day(conn, _D1)
        for i in range(20):
            d = _D1 - timedelta(days=i)
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
                "VALUES (?, '1001', ?, ?, ?, ?, 10000, 500_000_000) ON CONFLICT DO NOTHING",
                [d, 1000 + i, 1050 + i, 990 + i, 1020 + i],
            )

        # 事前に features を 1 行挿入
        _insert_features(conn, _D1)
        before = conn.execute("SELECT COUNT(*) FROM features WHERE date = ?", [_D1]).fetchone()[0]
        assert before == 1

        # --force で上書き実行
        processed, skipped, no_price = backfill(conn, _D1, _D1, force=True)

        after = conn.execute("SELECT COUNT(*) FROM features WHERE date = ?", [_D1]).fetchone()[0]
        assert processed == 1
        assert skipped == 0
        # 重複せず、build_features が生成した行数になっていること（1 以上）
        assert after >= 1

    def test_empty_range_returns_zeros(self, conn):
        """営業日が存在しない期間はすべて 0 を返す。"""
        sat = date(2024, 1, 6)
        sun = date(2024, 1, 7)
        conn.execute(
            "INSERT INTO market_calendar (date, is_trading_day) VALUES (?, FALSE), (?, FALSE)",
            [sat, sun],
        )

        with patch.object(_mod, "build_features") as mock_bf:
            processed, skipped, no_price = backfill(conn, sat, sun)

        assert processed == 0
        assert skipped == 0
        assert no_price == 0
        mock_bf.assert_not_called()


class TestCheckRsiLookback:
    def test_no_prior_prices_emits_warning(self, conn, caplog):
        """prices_daily に start 以前のデータが全くない場合は WARNING を出す。"""
        import logging

        with caplog.at_level(logging.WARNING):
            _check_rsi_lookback(conn, _D1)
        assert any("以前のデータが存在しません" in r.message for r in caplog.records)

    def test_sufficient_prior_prices_no_warning(self, conn, caplog):
        """start より十分前に価格データがあれば WARNING を出さない。"""
        import logging

        old_date = _D1 - timedelta(days=_RSI_LOOKBACK_DAYS + 10)
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
            "VALUES (?, '1001', 1000, 1000, 1000, 1000, 1000, 1000) ON CONFLICT DO NOTHING",
            [old_date],
        )
        with caplog.at_level(logging.WARNING):
            _check_rsi_lookback(conn, _D1)
        assert not any(r.levelno == logging.WARNING for r in caplog.records)

    def test_insufficient_prior_prices_emits_warning(self, conn, caplog):
        """start より古いデータがあるが RSI ルックバック日数に満たない場合は WARNING を出す。"""
        import logging

        # _RSI_LOOKBACK_DAYS - 5 日前のデータしかない（要求より新しい）
        insufficient_date = _D1 - timedelta(days=_RSI_LOOKBACK_DAYS - 5)
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
            "VALUES (?, '1001', 1000, 1000, 1000, 1000, 1000, 1000) ON CONFLICT DO NOTHING",
            [insufficient_date],
        )
        with caplog.at_level(logging.WARNING):
            _check_rsi_lookback(conn, _D1)
        assert any("最古データ" in r.message for r in caplog.records)
