# tests/test_run_yahoonews_collection.py
"""run_yahoonews_collection スクリプトのユニットテスト。"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import run_yahoonews_collection as script_mod


class TestMainSkipsWhenDisabled:
    def test_skips_when_enable_yahoonews_false(self, caplog):
        """ENABLE_YAHOONEWS=false のときは収集せずに正常終了する。"""
        mock_settings = MagicMock()
        mock_settings.enable_yahoonews = False

        with (
            patch.object(script_mod, "Settings", return_value=mock_settings),
            patch.object(script_mod, "duckdb") as mock_duckdb,
        ):
            script_mod.main()
            mock_duckdb.connect.assert_not_called()

    def test_runs_when_enable_yahoonews_true(self):
        """ENABLE_YAHOONEWS=true のときは run_news_collection を呼ぶ。"""
        mock_settings = MagicMock()
        mock_settings.enable_yahoonews = True
        mock_settings.duckdb_path = Path("/tmp/test.duckdb")

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [("1301",), ("1302",)]

        with (
            patch.object(script_mod, "Settings", return_value=mock_settings),
            patch.object(script_mod.duckdb, "connect", return_value=mock_conn),
            patch.object(
                script_mod, "run_news_collection", return_value=5
            ) as mock_collect,
        ):
            script_mod.main()
            mock_collect.assert_called_once()
            call_kwargs = mock_collect.call_args
            assert call_kwargs[1]["known_codes"] == ["1301", "1302"]

    def test_exits_on_collection_error(self):
        """run_news_collection が例外を投げると sys.exit(1) する。"""
        mock_settings = MagicMock()
        mock_settings.enable_yahoonews = True
        mock_settings.duckdb_path = Path("/tmp/test.duckdb")

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []

        with (
            patch.object(script_mod, "Settings", return_value=mock_settings),
            patch.object(script_mod.duckdb, "connect", return_value=mock_conn),
            patch.object(
                script_mod, "run_news_collection", side_effect=RuntimeError("fail")
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                script_mod.main()
            assert exc_info.value.code == 1

    def test_conn_closed_on_collection_error(self):
        """run_news_collection が失敗しても conn.close() が呼ばれる。"""
        mock_settings = MagicMock()
        mock_settings.enable_yahoonews = True
        mock_settings.duckdb_path = Path("/tmp/test.duckdb")

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []

        with (
            patch.object(script_mod, "Settings", return_value=mock_settings),
            patch.object(script_mod.duckdb, "connect", return_value=mock_conn),
            patch.object(
                script_mod, "run_news_collection", side_effect=RuntimeError("fail")
            ),
        ):
            with pytest.raises(SystemExit):
                script_mod.main()
            mock_conn.close.assert_called_once()

    def test_exits_on_connect_error(self):
        """duckdb.connect が例外を投げると sys.exit(1) する。"""
        mock_settings = MagicMock()
        mock_settings.enable_yahoonews = True
        mock_settings.duckdb_path = Path("/tmp/test.duckdb")

        with (
            patch.object(script_mod, "Settings", return_value=mock_settings),
            patch.object(
                script_mod.duckdb, "connect", side_effect=RuntimeError("cannot open")
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                script_mod.main()
            assert exc_info.value.code == 1

    def test_known_codes_none_when_stocks_unavailable(self):
        """stocks テーブルが存在しないとき known_codes=None で呼ぶ。"""
        mock_settings = MagicMock()
        mock_settings.enable_yahoonews = True
        mock_settings.duckdb_path = Path("/tmp/test.duckdb")

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("no such table: stocks")

        with (
            patch.object(script_mod, "Settings", return_value=mock_settings),
            patch.object(script_mod.duckdb, "connect", return_value=mock_conn),
            patch.object(
                script_mod, "run_news_collection", return_value=0
            ) as mock_collect,
        ):
            script_mod.main()
            call_kwargs = mock_collect.call_args
            assert call_kwargs[1]["known_codes"] is None


class TestFetchKnownCodes:
    def test_returns_codes_from_stocks(self):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [("7203",), ("6758",)]
        result = script_mod._fetch_known_codes(mock_conn)
        assert result == ["7203", "6758"]

    def test_coerces_int_codes_to_str(self):
        """stocks.code が INT 型の場合でも str に正規化する。"""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [(7203,), (6758,)]
        result = script_mod._fetch_known_codes(mock_conn)
        assert result == ["7203", "6758"]

    def test_uses_distinct_query(self):
        """SELECT DISTINCT を使用していることを確認する。"""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        script_mod._fetch_known_codes(mock_conn)
        called_sql = mock_conn.execute.call_args[0][0]
        assert "DISTINCT" in called_sql.upper()

    def test_returns_empty_list_on_error(self):
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("fail")
        result = script_mod._fetch_known_codes(mock_conn)
        assert result == []
