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


# ---------- _calc_paper_portfolio_value ----------


def test_calc_paper_portfolio_value_db_not_exists(tmp_path: Path):
    """paper_trading.db が未存在のとき (initial_cash, initial_cash) を返す（_MAX_UTILIZATION 非適用）。"""
    import run_portfolio_construction

    settings = MagicMock()
    settings.paper_trading_initial_cash = 5_000_000.0
    settings.paper_sqlite_path = tmp_path / "nonexistent.db"
    mock_conn = MagicMock()

    pv, ac = run_portfolio_construction._calc_paper_portfolio_value(settings, mock_conn)

    assert pv == pytest.approx(5_000_000.0)
    assert ac == pytest.approx(5_000_000.0)


def test_calc_paper_portfolio_value_with_positions(tmp_path: Path):
    """買いポジションあり: portfolio_value = 現金残高 + 時価。"""
    import sqlite3

    import run_portfolio_construction

    db_path = tmp_path / "paper_trading.db"
    with sqlite3.connect(str(db_path)) as db:
        db.execute(
            "CREATE TABLE orders (side TEXT, code TEXT, filled_qty INTEGER, avg_fill_price REAL)"
        )
        db.execute("INSERT INTO orders VALUES ('buy', '7203', 100, 2000.0)")

    settings = MagicMock()
    settings.paper_trading_initial_cash = 1_000_000.0
    settings.paper_sqlite_path = db_path

    price_cursor = MagicMock()
    price_cursor.fetchall.return_value = [("7203", 2500.0)]
    mock_conn = MagicMock()
    mock_conn.execute.return_value = price_cursor

    pv, ac = run_portfolio_construction._calc_paper_portfolio_value(settings, mock_conn)

    # net_cash = 1,000,000 - 100*2000 = 800,000
    # market_value = 100 * 2500 = 250,000
    assert pv == pytest.approx(1_050_000.0)
    assert ac == pytest.approx(800_000.0)


def test_calc_paper_portfolio_value_negative_cash_clipped(tmp_path: Path):
    """net_cash が負のとき available_cash は 0 に補正される。"""
    import sqlite3

    import run_portfolio_construction

    db_path = tmp_path / "paper_trading.db"
    with sqlite3.connect(str(db_path)) as db:
        db.execute(
            "CREATE TABLE orders (side TEXT, code TEXT, filled_qty INTEGER, avg_fill_price REAL)"
        )
        # 1,000株買い (cost=2,000,000 > initial_cash=1,000,000)
        db.execute("INSERT INTO orders VALUES ('buy', '7203', 1000, 2000.0)")

    settings = MagicMock()
    settings.paper_trading_initial_cash = 1_000_000.0
    settings.paper_sqlite_path = db_path

    price_cursor = MagicMock()
    price_cursor.fetchall.return_value = [("7203", 2000.0)]
    mock_conn = MagicMock()
    mock_conn.execute.return_value = price_cursor

    pv, ac = run_portfolio_construction._calc_paper_portfolio_value(settings, mock_conn)

    # net_cash = 1,000,000 - 2,000,000 = -1,000,000 → available_cash=0
    assert ac == pytest.approx(0.0)
    # portfolio_value = max(-1,000,000 + 2,000,000, 0) = 1,000,000
    assert pv == pytest.approx(1_000_000.0)


def test_calc_paper_portfolio_value_price_fetch_fails(tmp_path: Path):
    """DuckDB 価格取得失敗時に market_value=0 でフォールバック。"""
    import sqlite3

    import run_portfolio_construction

    db_path = tmp_path / "paper_trading.db"
    with sqlite3.connect(str(db_path)) as db:
        db.execute(
            "CREATE TABLE orders (side TEXT, code TEXT, filled_qty INTEGER, avg_fill_price REAL)"
        )
        db.execute("INSERT INTO orders VALUES ('buy', '7203', 100, 2000.0)")

    settings = MagicMock()
    settings.paper_trading_initial_cash = 1_000_000.0
    settings.paper_sqlite_path = db_path

    mock_conn = MagicMock()
    mock_conn.execute.side_effect = Exception("DuckDB connection error")

    pv, ac = run_portfolio_construction._calc_paper_portfolio_value(settings, mock_conn)

    # net_cash = 1,000,000 - 200,000 = 800,000; market_value = 0 (failed)
    assert pv == pytest.approx(800_000.0)
    assert ac == pytest.approx(800_000.0)


# ---------- _calc_live_portfolio_value ----------


def _make_live_settings() -> MagicMock:
    s = MagicMock()
    s.portfolio_value = 10_000_000.0
    s.kabu_api_password = "pass"
    s.kabu_trade_password = None
    s.kabu_api_base_url = "http://localhost:18080/kabusapi"
    return s


def test_calc_live_portfolio_value_api_and_duckdb_success():
    """Kabu API 成功 → available_cash = API 値。portfolio_value = DuckDB 値。"""
    import run_portfolio_construction

    settings = _make_live_settings()
    db_cursor = MagicMock()
    db_cursor.fetchone.return_value = (12_000_000.0,)
    mock_conn = MagicMock()
    mock_conn.execute.return_value = db_cursor

    mock_kabu_module = MagicMock()
    mock_client = MagicMock()
    mock_client.get_available_cash.return_value = 8_000_000.0
    mock_kabu_module.KabuStationClient.return_value = mock_client

    with patch.dict("sys.modules", {"kabusys.execution.kabu_client": mock_kabu_module}):
        pv, ac = run_portfolio_construction._calc_live_portfolio_value(settings, mock_conn)

    assert pv == pytest.approx(12_000_000.0)
    assert ac == pytest.approx(8_000_000.0)


def test_calc_live_portfolio_value_api_fails_duckdb_success():
    """Kabu API 失敗 + DuckDB 成功 → available_cash = pv × 0.7。"""
    import run_portfolio_construction

    settings = _make_live_settings()
    db_cursor = MagicMock()
    db_cursor.fetchone.return_value = (12_000_000.0,)
    mock_conn = MagicMock()
    mock_conn.execute.return_value = db_cursor

    mock_kabu_module = MagicMock()
    mock_client = MagicMock()
    mock_client.get_available_cash.side_effect = RuntimeError("API error")
    mock_kabu_module.KabuStationClient.return_value = mock_client

    with patch.dict("sys.modules", {"kabusys.execution.kabu_client": mock_kabu_module}):
        pv, ac = run_portfolio_construction._calc_live_portfolio_value(settings, mock_conn)

    assert pv == pytest.approx(12_000_000.0)
    assert ac == pytest.approx(12_000_000.0 * 0.70)


def test_calc_live_portfolio_value_both_fail():
    """Kabu API 失敗 + DuckDB 失敗 → portfolio_value = ENV 値, available_cash = pv × 0.7。"""
    import run_portfolio_construction

    settings = _make_live_settings()
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = Exception("DuckDB error")

    mock_kabu_module = MagicMock()
    mock_client = MagicMock()
    mock_client.get_available_cash.side_effect = RuntimeError("API error")
    mock_kabu_module.KabuStationClient.return_value = mock_client

    with patch.dict("sys.modules", {"kabusys.execution.kabu_client": mock_kabu_module}):
        pv, ac = run_portfolio_construction._calc_live_portfolio_value(settings, mock_conn)

    assert pv == pytest.approx(10_000_000.0)
    assert ac == pytest.approx(10_000_000.0 * 0.70)


def test_calc_live_portfolio_value_api_returns_invalid():
    """Kabu API が不正値（負値）を返したとき pv×max_utilization にフォールバックする。"""
    import run_portfolio_construction

    settings = _make_live_settings()
    db_cursor = MagicMock()
    db_cursor.fetchone.return_value = (10_000_000.0,)
    mock_conn = MagicMock()
    mock_conn.execute.return_value = db_cursor

    mock_kabu_module = MagicMock()
    mock_client = MagicMock()
    mock_client.get_available_cash.return_value = -1.0  # 不正値
    mock_kabu_module.KabuStationClient.return_value = mock_client

    with patch.dict("sys.modules", {"kabusys.execution.kabu_client": mock_kabu_module}):
        pv, ac = run_portfolio_construction._calc_live_portfolio_value(settings, mock_conn)

    assert pv == pytest.approx(10_000_000.0)
    assert ac == pytest.approx(10_000_000.0 * 0.70)


# ---------- Settings.portfolio_value ----------


def test_settings_portfolio_value_negative(monkeypatch):
    """PORTFOLIO_VALUE が負値のとき ValueError を送出する。"""
    from kabusys.config import Settings

    monkeypatch.setenv("PORTFOLIO_VALUE", "-1")
    with pytest.raises(ValueError, match="正の値"):
        Settings().portfolio_value


def test_settings_portfolio_value_zero(monkeypatch):
    """PORTFOLIO_VALUE が 0 のとき ValueError を送出する。"""
    from kabusys.config import Settings

    monkeypatch.setenv("PORTFOLIO_VALUE", "0")
    with pytest.raises(ValueError, match="正の値"):
        Settings().portfolio_value


def test_settings_portfolio_value_non_numeric(monkeypatch):
    """PORTFOLIO_VALUE が数値でないとき ValueError を送出する。"""
    from kabusys.config import Settings

    monkeypatch.setenv("PORTFOLIO_VALUE", "abc")
    with pytest.raises(ValueError, match="不正"):
        Settings().portfolio_value


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
