"""pre_market_collector のテスト（モックで IO を差し替え）"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch

from kabusys.operations.pre_market_collector import (
    PreMarketData,
    check_data_freshness,
    check_position_count,
    check_signal_queue,
    check_stop_flag,
    check_task_scheduler,
    collect,
)

# --- check_data_freshness ---


def test_data_freshness_ok(tmp_path):
    """prices_daily の最終日が today-1 以下 3 日以内なら OK。"""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (date(2026, 4, 25),)
    result = check_data_freshness(mock_conn, today=date(2026, 4, 27))
    assert result is True


def test_data_freshness_stale(tmp_path):
    """prices_daily の最終日が 4 日以上前なら False。"""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (date(2026, 4, 20),)
    result = check_data_freshness(mock_conn, today=date(2026, 4, 27))
    assert result is False


def test_data_freshness_no_data():
    """prices_daily にデータがなければ False。"""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (None,)
    result = check_data_freshness(mock_conn, today=date(2026, 4, 27))
    assert result is False


def test_data_freshness_datetime_type():
    """DuckDB が datetime で返しても正しく処理できる。"""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (
        datetime(2026, 4, 25, 15, 30, 0),
    )
    result = check_data_freshness(mock_conn, today=date(2026, 4, 27))
    assert result is True


def test_data_freshness_future_date():
    """未来日が返った場合は False（データ異常とみなす）。"""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (date(2026, 4, 30),)
    result = check_data_freshness(mock_conn, today=date(2026, 4, 27))
    assert result is False


def test_data_freshness_iso8601_t_separator():
    """T 区切りの ISO 8601 文字列（例: "2026-04-25T00:00:00"）を正しく処理できる。"""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = ("2026-04-25T00:00:00",)
    result = check_data_freshness(mock_conn, today=date(2026, 4, 27))
    assert result is True


# --- check_signal_queue ---


def test_signal_queue_pending_count():
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (7,)
    result = check_signal_queue(mock_conn, today=date(2026, 4, 27))
    assert result == 7


def test_signal_queue_zero():
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (0,)
    result = check_signal_queue(mock_conn, today=date(2026, 4, 27))
    assert result == 0


# --- check_position_count ---


def test_position_count():
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (4,)
    result = check_position_count(mock_conn)
    assert result == 4


def test_position_count_none():
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (None,)
    result = check_position_count(mock_conn)
    assert result == 0


# --- check_stop_flag ---


def test_stop_flag_exists(tmp_path):
    flag = tmp_path / "stop_requested.flag"
    flag.touch()
    assert check_stop_flag(flag) is True


def test_stop_flag_not_exists(tmp_path):
    flag = tmp_path / "stop_requested.flag"
    assert check_stop_flag(flag) is False


# --- check_task_scheduler ---


def test_task_scheduler_ready():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = (
        '"\\\\KabuSys_ExecutionStart","4/28/2026 8:30:00 AM","Ready"\r\n'
    )
    with patch(
        "kabusys.operations.pre_market_collector.subprocess.run",
        return_value=mock_result,
    ):
        assert check_task_scheduler("KabuSys_ExecutionStart") is True


def test_task_scheduler_not_ready():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = '"\\\\KabuSys_ExecutionStart","N/A","Disabled"\r\n'
    with patch(
        "kabusys.operations.pre_market_collector.subprocess.run",
        return_value=mock_result,
    ):
        assert check_task_scheduler("KabuSys_ExecutionStart") is False


def test_task_scheduler_error():
    """schtasks が失敗した場合は False を返す（タスクが存在しない等）。"""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    with patch(
        "kabusys.operations.pre_market_collector.subprocess.run",
        return_value=mock_result,
    ):
        assert check_task_scheduler("KabuSys_ExecutionStart") is False


def test_task_scheduler_ready_japanese_locale():
    """日本語 OS で "準備完了" が返った場合も True になる。"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = (
        '"\\\\KabuSys_ExecutionStart","2026/04/28 8:30:00","準備完了"\r\n'
    )
    with patch(
        "kabusys.operations.pre_market_collector.subprocess.run",
        return_value=mock_result,
    ):
        assert check_task_scheduler("KabuSys_ExecutionStart") is True


# --- collect ---


def test_collect_returns_pre_market_data(tmp_path):
    mock_duckdb = MagicMock()
    mock_duckdb.execute.return_value.fetchone.return_value = (date(2026, 4, 25),)

    mock_sqlite = MagicMock()
    mock_sqlite.execute.return_value.fetchone.return_value = (5,)

    stop_flag = tmp_path / "stop_requested.flag"

    with patch(
        "kabusys.operations.pre_market_collector.check_task_scheduler",
        return_value=True,
    ):
        data = collect(
            duckdb_conn=mock_duckdb,
            sqlite_conn=mock_sqlite,
            stop_flag_path=stop_flag,
            task_name="KabuSys_ExecutionStart",
            today=date(2026, 4, 27),
        )

    assert isinstance(data, PreMarketData)
    assert data.data_freshness_ok is True
    assert data.signal_queue_pending == 5
    assert data.stop_flag_exists is False
    assert data.task_scheduler_ready is True
