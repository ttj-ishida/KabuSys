# tests/test_scripts_batch.py
"""Night batch スクリプトの単体テスト"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


# ---------- run_data_update ----------


def test_run_data_update_calls_run_daily_etl():
    import run_data_update

    mock_result = MagicMock()
    mock_result.errors = []

    with (
        patch("run_data_update.Settings") as mock_settings,
        patch("run_data_update.duckdb.connect"),
        patch("run_data_update.run_daily_etl", return_value=mock_result) as mock_etl,
    ):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_data_update.main()

    mock_etl.assert_called_once()


def test_run_data_update_exits_1_on_error():
    import run_data_update

    with (
        patch("run_data_update.Settings"),
        patch("run_data_update.duckdb.connect"),
        patch("run_data_update.run_daily_etl", side_effect=RuntimeError("fail")),
    ):
        with pytest.raises(SystemExit) as exc:
            run_data_update.main()
        assert exc.value.code == 1


# ---------- run_feature_gen ----------


def test_run_feature_gen_calls_build_features():
    import run_feature_gen

    with (
        patch("run_feature_gen.Settings") as mock_settings,
        patch("run_feature_gen.duckdb.connect"),
        patch("run_feature_gen.build_features", return_value=5) as mock_fn,
    ):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_feature_gen.main()

    mock_fn.assert_called_once()


# ---------- run_ai_analysis ----------


def test_run_ai_analysis_calls_both_functions():
    import run_ai_analysis

    with (
        patch("run_ai_analysis.Settings") as mock_settings,
        patch("run_ai_analysis.duckdb.connect"),
        patch("run_ai_analysis.score_news", return_value=3) as mock_news,
        patch("run_ai_analysis.score_regime", return_value=1) as mock_regime,
    ):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        mock_settings.return_value.openai_api_key = "test-key"
        run_ai_analysis.main()

    mock_news.assert_called_once()
    mock_regime.assert_called_once()


# ---------- run_strategy_signal ----------


def test_run_strategy_signal_calls_generate_signals():
    import run_strategy_signal

    with (
        patch("run_strategy_signal.Settings") as mock_settings,
        patch("run_strategy_signal.duckdb.connect"),
        patch("run_strategy_signal.sqlite3.connect"),
        patch("run_strategy_signal.init_position_entries_db"),
        patch("run_strategy_signal.generate_signals", return_value=10) as mock_fn,
    ):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        mock_settings.return_value.sqlite_path = Path("/fake.db")
        run_strategy_signal.main()

    mock_fn.assert_called_once()


# ---------- run_portfolio_construction ----------


def _mock_paper_settings(mock_settings: MagicMock, tmp_path: Path) -> None:
    """portfolio_construction テスト用の Paper モード settings を設定する。"""
    mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
    mock_settings.return_value.is_live = False
    mock_settings.return_value.is_paper = True
    mock_settings.return_value.is_dev = False
    mock_settings.return_value.paper_trading_initial_cash = 10_000_000.0
    mock_settings.return_value.paper_sqlite_path = tmp_path / "nonexistent.db"


def test_portfolio_construction_writes_signal_queue(tmp_path: Path):
    import run_portfolio_construction

    mock_conn = MagicMock()
    # signals テーブルから 2件のBUYシグナルを返す
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("7203", "buy", 0.8, 1),
        ("6758", "buy", 0.6, 2),
    ]
    mock_cursor.description = [("code",), ("side",), ("score",), ("signal_rank",)]
    # prices_daily クエリ
    price_cursor = MagicMock()
    price_cursor.fetchall.return_value = [("7203", 2500.0), ("6758", 5000.0)]
    price_cursor.description = [("code",), ("close",)]
    # positions クエリ
    pos_cursor = MagicMock()
    pos_cursor.fetchall.return_value = []
    pos_cursor.description = [("code",), ("size",)]

    mock_conn.execute.side_effect = [
        mock_cursor,  # signals query
        price_cursor,  # prices query
        pos_cursor,  # positions query
        MagicMock(),  # BEGIN
        MagicMock(),  # DELETE portfolio_targets
        MagicMock(),  # INSERT portfolio_targets (7203)
        MagicMock(),  # INSERT portfolio_targets (6758)
        MagicMock(),  # DELETE signal_queue
        MagicMock(),  # INSERT signal_queue (7203)
        MagicMock(),  # INSERT signal_queue (6758)
        MagicMock(),  # COMMIT
    ]

    with (
        patch("run_portfolio_construction.Settings") as mock_settings,
        patch("run_portfolio_construction.duckdb.connect", return_value=mock_conn),
    ):
        _mock_paper_settings(mock_settings, tmp_path)
        run_portfolio_construction.main()

    # signal_queue への INSERT が呼ばれたことを確認
    insert_calls = [
        str(c)
        for c in mock_conn.execute.call_args_list
        if "signal_queue" in str(c) and "INSERT" in str(c)
    ]
    assert len(insert_calls) >= 1


def test_portfolio_construction_no_signals_exits_0(tmp_path: Path):
    """シグナルが 0 件のとき正常終了する（signal_queue は空のまま）。"""
    import run_portfolio_construction

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = [("code",), ("side",), ("score",), ("signal_rank",)]
    mock_conn.execute.return_value = mock_cursor

    with (
        patch("run_portfolio_construction.Settings") as mock_settings,
        patch("run_portfolio_construction.duckdb.connect", return_value=mock_conn),
    ):
        _mock_paper_settings(mock_settings, tmp_path)
        run_portfolio_construction.main()  # SystemExit が起きないこと


# ---------- run_tdnet_collection ----------


def test_run_tdnet_collection_skipped_when_disabled():
    """ENABLE_TDNET=false のとき run_tdnet_collection を呼ばずにリターンする。"""
    import run_tdnet_collection

    with (
        patch("run_tdnet_collection.Settings") as mock_settings,
        patch("run_tdnet_collection.run_tdnet_collection") as mock_fn,
    ):
        mock_settings.return_value.enable_tdnet = False
        run_tdnet_collection.main()

    mock_fn.assert_not_called()


def test_run_tdnet_collection_runs_when_enabled():
    """ENABLE_TDNET=true のとき run_tdnet_collection が実行される。"""
    import run_tdnet_collection

    with (
        patch("run_tdnet_collection.Settings") as mock_settings,
        patch("run_tdnet_collection.duckdb.connect"),
        patch("run_tdnet_collection.run_tdnet_collection", return_value=3) as mock_fn,
    ):
        mock_settings.return_value.enable_tdnet = True
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_tdnet_collection.main()

    mock_fn.assert_called_once()


# ---------- run_disclosure_classification ----------


def test_run_disclosure_classification_skipped_when_disabled():
    """ENABLE_TDNET=false のとき run_disclosure_classification を呼ばずにリターンする。"""
    import run_disclosure_classification

    with (
        patch("run_disclosure_classification.Settings") as mock_settings,
        patch("run_disclosure_classification.run_disclosure_classification") as mock_fn,
    ):
        mock_settings.return_value.enable_tdnet = False
        run_disclosure_classification.main()

    mock_fn.assert_not_called()


def test_run_disclosure_classification_runs_when_enabled():
    """ENABLE_TDNET=true のとき run_disclosure_classification が実行される。"""
    import run_disclosure_classification

    with (
        patch("run_disclosure_classification.Settings") as mock_settings,
        patch("run_disclosure_classification.duckdb.connect"),
        patch(
            "run_disclosure_classification.run_disclosure_classification",
            return_value=2,
        ) as mock_fn,
    ):
        mock_settings.return_value.enable_tdnet = True
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_disclosure_classification.main()

    mock_fn.assert_called_once()


# ---------- run_edinet_collection ----------


def test_run_edinet_collection_skipped_when_disabled():
    """ENABLE_EDINET=false のとき run_edinet_collection を呼ばずにリターンする。"""
    import run_edinet_collection

    with (
        patch("run_edinet_collection.Settings") as mock_settings,
        patch("run_edinet_collection.run_edinet_collection") as mock_fn,
    ):
        mock_settings.return_value.enable_edinet = False
        run_edinet_collection.main()

    mock_fn.assert_not_called()


def test_run_edinet_collection_runs_when_enabled():
    """ENABLE_EDINET=true のとき run_edinet_collection が実行される。"""
    import run_edinet_collection

    with (
        patch("run_edinet_collection.Settings") as mock_settings,
        patch("run_edinet_collection.duckdb.connect"),
        patch("run_edinet_collection.run_edinet_collection", return_value=5) as mock_fn,
    ):
        mock_settings.return_value.enable_edinet = True
        mock_settings.return_value.edinet_api_key = "test-key"
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_edinet_collection.main()

    mock_fn.assert_called_once()


def test_run_edinet_collection_exits_when_api_key_missing():
    """ENABLE_EDINET=true かつ EDINET_API_KEY 未設定のとき sys.exit(1) すること。"""
    import run_edinet_collection

    with (
        patch("run_edinet_collection.Settings") as mock_settings,
        patch("run_edinet_collection.run_edinet_collection") as mock_fn,
        pytest.raises(SystemExit) as exc_info,
    ):
        mock_settings.return_value.enable_edinet = True
        mock_settings.return_value.edinet_api_key = ""
        run_edinet_collection.main()

    assert exc_info.value.code == 1
    mock_fn.assert_not_called()
