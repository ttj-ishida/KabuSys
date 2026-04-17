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

    with patch("run_data_update.Settings") as mock_settings, \
         patch("run_data_update.duckdb.connect"), \
         patch("run_data_update.run_daily_etl", return_value=mock_result) as mock_etl:
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_data_update.main()

    mock_etl.assert_called_once()


def test_run_data_update_exits_1_on_error():
    import run_data_update

    with patch("run_data_update.Settings"), \
         patch("run_data_update.duckdb.connect"), \
         patch("run_data_update.run_daily_etl", side_effect=RuntimeError("fail")):
        with pytest.raises(SystemExit) as exc:
            run_data_update.main()
        assert exc.value.code == 1


# ---------- run_feature_gen ----------

def test_run_feature_gen_calls_build_features():
    import run_feature_gen

    with patch("run_feature_gen.Settings") as mock_settings, \
         patch("run_feature_gen.duckdb.connect"), \
         patch("run_feature_gen.build_features", return_value=5) as mock_fn:
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_feature_gen.main()

    mock_fn.assert_called_once()


# ---------- run_ai_analysis ----------

def test_run_ai_analysis_calls_both_functions():
    import run_ai_analysis

    with patch("run_ai_analysis.Settings") as mock_settings, \
         patch("run_ai_analysis.duckdb.connect"), \
         patch("run_ai_analysis.score_news", return_value=3) as mock_news, \
         patch("run_ai_analysis.score_regime", return_value=1) as mock_regime:
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        mock_settings.return_value.openai_api_key = "test-key"
        run_ai_analysis.main()

    mock_news.assert_called_once()
    mock_regime.assert_called_once()


# ---------- run_strategy_signal ----------

def test_run_strategy_signal_calls_generate_signals():
    import run_strategy_signal

    with patch("run_strategy_signal.Settings") as mock_settings, \
         patch("run_strategy_signal.duckdb.connect"), \
         patch("run_strategy_signal.generate_signals", return_value=10) as mock_fn:
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_strategy_signal.main()

    mock_fn.assert_called_once()


# ---------- run_portfolio_construction ----------

def test_portfolio_construction_writes_signal_queue():
    import run_portfolio_construction

    mock_conn = MagicMock()
    # signals テーブルから 2件のBUYシグナルを返す
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("7203", "buy", 0.8, 1),
        ("6758", "buy", 0.6, 2),
    ]
    mock_cursor.description = [
        ("code",), ("side",), ("score",), ("signal_rank",)
    ]
    # prices_daily クエリ
    price_cursor = MagicMock()
    price_cursor.fetchall.return_value = [("7203", 2500.0), ("6758", 5000.0)]
    price_cursor.description = [("code",), ("close",)]
    # positions クエリ
    pos_cursor = MagicMock()
    pos_cursor.fetchall.return_value = []
    pos_cursor.description = [("code",), ("size",)]

    mock_conn.execute.side_effect = [
        mock_cursor,   # signals query
        price_cursor,  # prices query
        pos_cursor,    # positions query
        MagicMock(),   # BEGIN
        MagicMock(),   # DELETE portfolio_targets
        MagicMock(),   # INSERT portfolio_targets (7203)
        MagicMock(),   # INSERT portfolio_targets (6758)
        MagicMock(),   # DELETE signal_queue
        MagicMock(),   # INSERT signal_queue (7203)
        MagicMock(),   # INSERT signal_queue (6758)
        MagicMock(),   # COMMIT
    ]

    with patch("run_portfolio_construction.Settings") as mock_settings, \
         patch("run_portfolio_construction.duckdb.connect", return_value=mock_conn):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_portfolio_construction.main()

    # signal_queue への INSERT が呼ばれたことを確認
    insert_calls = [
        str(c) for c in mock_conn.execute.call_args_list
        if "signal_queue" in str(c) and "INSERT" in str(c)
    ]
    assert len(insert_calls) >= 1


def test_portfolio_construction_no_signals_exits_0():
    """シグナルが 0 件のとき正常終了する（signal_queue は空のまま）。"""
    import run_portfolio_construction

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = [("code",), ("side",), ("score",), ("signal_rank",)]
    mock_conn.execute.return_value = mock_cursor

    with patch("run_portfolio_construction.Settings") as mock_settings, \
         patch("run_portfolio_construction.duckdb.connect", return_value=mock_conn):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_portfolio_construction.main()  # SystemExit が起きないこと
