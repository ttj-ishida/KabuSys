# tests/test_scripts_batch.py
"""Night batch スクリプトの単体テスト"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import date
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
