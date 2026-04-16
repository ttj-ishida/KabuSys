# tests/test_reset_signals.py
"""scripts/reset_signals.py の単体テスト"""
from __future__ import annotations

import sys
from datetime import datetime, time, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import reset_signals


def _run_reset(args: list[str] | None = None):
    import reset_signals as rs
    with patch.object(sys, "argv", ["reset_signals.py"] + (args or [])):
        return rs.main()


# ---------------------------------------------------------------------------
# _is_trading_hours
# ---------------------------------------------------------------------------

_JST = timezone(timedelta(hours=9))


def _jst(h: int, m: int) -> datetime:
    return datetime(2024, 1, 15, h, m, 0, tzinfo=_JST)


@pytest.mark.parametrize("h,m,expected", [
    (8, 59, False),   # 前場前
    (9, 0,  True),    # 前場開始
    (10, 0, True),    # 前場中
    (11, 29, True),   # 前場終了直前
    (11, 30, False),  # 昼休み
    (12, 0,  False),  # 昼休み中
    (12, 30, True),   # 後場開始
    (14, 59, True),   # 後場終了直前
    (15, 0,  False),  # 後場終了
    (20, 0,  False),  # 夜間
])
def test_is_trading_hours(h, m, expected):
    assert reset_signals._is_trading_hours(_jst(h, m)) == expected


# ---------------------------------------------------------------------------
# --force 必須
# ---------------------------------------------------------------------------

def test_requires_force_flag():
    with pytest.raises(SystemExit) as exc:
        _run_reset([])
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# 取引時間中は拒否
# ---------------------------------------------------------------------------

def test_rejects_during_trading_hours(tmp_path):
    with patch("reset_signals._is_trading_hours", return_value=True):
        with pytest.raises(SystemExit) as exc:
            _run_reset(["--force"])
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# 未処理注文がある場合の確認プロンプト
# ---------------------------------------------------------------------------

def test_aborts_on_open_orders_user_says_no(tmp_path, monkeypatch):
    monkeypatch.setattr("reset_signals._is_trading_hours", lambda: False)
    monkeypatch.setattr("reset_signals._count_open_orders", lambda p: 3)
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")

    settings_mock = MagicMock()
    settings_mock.duckdb_path = tmp_path / "kabusys.duckdb"
    settings_mock.sqlite_path = tmp_path / "monitoring.db"

    with patch("reset_signals.Settings", return_value=settings_mock):
        with pytest.raises(SystemExit) as exc:
            _run_reset(["--force"])
        assert exc.value.code == 0


def test_proceeds_on_open_orders_user_says_yes(tmp_path, monkeypatch):
    monkeypatch.setattr("reset_signals._is_trading_hours", lambda: False)
    monkeypatch.setattr("reset_signals._count_open_orders", lambda p: 2)
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    monkeypatch.setattr("reset_signals._backup_duckdb", lambda p: tmp_path / "backup.duckdb")

    settings_mock = MagicMock()
    settings_mock.duckdb_path = tmp_path / "kabusys.duckdb"
    settings_mock.sqlite_path = tmp_path / "monitoring.db"

    conn_mock = MagicMock()
    conn_mock.execute.return_value.rowcount = 5

    with patch("reset_signals.Settings", return_value=settings_mock), \
         patch("reset_signals.duckdb.connect", return_value=conn_mock):
        _run_reset(["--force"])

    conn_mock.execute.assert_called_once_with("DELETE FROM signal_queue")
    conn_mock.close.assert_called_once()


# ---------------------------------------------------------------------------
# 正常系: バックアップ作成 + 削除
# ---------------------------------------------------------------------------

def test_backup_created_and_delete_runs(tmp_path, monkeypatch):
    monkeypatch.setattr("reset_signals._is_trading_hours", lambda: False)
    monkeypatch.setattr("reset_signals._count_open_orders", lambda p: 0)

    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")

    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
    settings_mock.sqlite_path = tmp_path / "monitoring.db"

    conn_mock = MagicMock()
    conn_mock.execute.return_value.rowcount = 7

    with patch("reset_signals.Settings", return_value=settings_mock), \
         patch("reset_signals.duckdb.connect", return_value=conn_mock):
        _run_reset(["--force"])

    # バックアップディレクトリが作られていること
    backup_dir = tmp_path / "backup"
    assert backup_dir.exists()
    backups = list(backup_dir.glob("kabusys_*.duckdb"))
    assert len(backups) == 1

    conn_mock.execute.assert_called_once_with("DELETE FROM signal_queue")
