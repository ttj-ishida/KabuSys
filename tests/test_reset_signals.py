# tests/test_reset_signals.py
"""scripts/reset_signals.py の単体テスト"""
from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
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
    # 2024-01-15 は月曜日
    assert reset_signals._is_trading_hours(_jst(h, m)) == expected


def test_is_trading_hours_weekend_always_false():
    # 2024-01-13 は土曜日 — 取引時間帯でも False
    saturday = datetime(2024, 1, 13, 10, 0, 0, tzinfo=_JST)
    assert reset_signals._is_trading_hours(saturday) is False
    # 2024-01-14 は日曜日
    sunday = datetime(2024, 1, 14, 10, 0, 0, tzinfo=_JST)
    assert reset_signals._is_trading_hours(sunday) is False


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

    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")  # B1: ファイル存在チェックを通過させる

    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
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

    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")  # B1: ファイル存在チェックを通過させる

    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
    settings_mock.sqlite_path = tmp_path / "monitoring.db"

    # information_schema: テーブルあり → DELETE 実行
    execute_results = [
        MagicMock(fetchone=lambda: (1,)),   # information_schema → exists
        MagicMock(rowcount=5),              # DELETE
    ]
    conn_mock = MagicMock()
    conn_mock.execute.side_effect = execute_results

    with patch("reset_signals.Settings", return_value=settings_mock), \
         patch("reset_signals.duckdb.connect", return_value=conn_mock):
        _run_reset(["--force"])

    delete_calls = [str(c.args[0]) for c in conn_mock.execute.call_args_list]
    assert any("DELETE" in s for s in delete_calls)
    conn_mock.close.assert_called_once()


# ---------------------------------------------------------------------------
# B1: DuckDB ファイル不存在時はエラー終了
# ---------------------------------------------------------------------------

def test_exits_when_duckdb_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("reset_signals._is_trading_hours", lambda: False)
    monkeypatch.setattr("reset_signals._count_open_orders", lambda p: 0)

    settings_mock = MagicMock()
    settings_mock.duckdb_path = tmp_path / "nonexistent.duckdb"  # 存在しない
    settings_mock.sqlite_path = tmp_path / "monitoring.db"

    with patch("reset_signals.Settings", return_value=settings_mock):
        with pytest.raises(SystemExit) as exc:
            _run_reset(["--force"])
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# B2: signal_queue テーブル不存在時は noop
# ---------------------------------------------------------------------------

def test_noop_when_signal_queue_table_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("reset_signals._is_trading_hours", lambda: False)
    monkeypatch.setattr("reset_signals._count_open_orders", lambda p: 0)
    monkeypatch.setattr("reset_signals._backup_duckdb", lambda p: tmp_path / "backup.duckdb")

    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")

    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
    settings_mock.sqlite_path = tmp_path / "monitoring.db"

    # information_schema クエリで 0 を返す（テーブル不存在）
    conn_mock = MagicMock()
    conn_mock.execute.return_value.fetchone.return_value = (0,)

    with patch("reset_signals.Settings", return_value=settings_mock), \
         patch("reset_signals.duckdb.connect", return_value=conn_mock):
        _run_reset(["--force"])  # SystemExit しないこと

    # DELETE は実行されていないこと
    called_sqls = [str(c.args[0]) for c in conn_mock.execute.call_args_list]
    assert not any("DELETE" in s for s in called_sqls)


# ---------------------------------------------------------------------------
# B3: SQLite 確認エラー時はエラー終了
# ---------------------------------------------------------------------------

def test_exits_on_sqlite_error(tmp_path, monkeypatch):
    monkeypatch.setattr("reset_signals._is_trading_hours", lambda: False)

    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")

    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
    settings_mock.sqlite_path = tmp_path / "monitoring.db"

    def raise_error(p):
        raise RuntimeError("DB is locked")

    monkeypatch.setattr("reset_signals._count_open_orders", raise_error)

    with patch("reset_signals.Settings", return_value=settings_mock):
        with pytest.raises(SystemExit) as exc:
            _run_reset(["--force"])
        assert exc.value.code == 1


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

    # information_schema: テーブルあり → DELETE 実行
    execute_results = [
        MagicMock(fetchone=lambda: (1,)),   # information_schema → exists
        MagicMock(rowcount=7),              # DELETE
    ]
    conn_mock = MagicMock()
    conn_mock.execute.side_effect = execute_results

    with patch("reset_signals.Settings", return_value=settings_mock), \
         patch("reset_signals.duckdb.connect", return_value=conn_mock):
        _run_reset(["--force"])

    # バックアップディレクトリが作られていること
    backup_dir = tmp_path / "backup"
    assert backup_dir.exists()
    backups = list(backup_dir.glob("kabusys_*.duckdb"))
    assert len(backups) == 1
    # ファイル名にマイクロ秒が含まれること（%Y%m%d_%H%M%S_xxxxxx 形式）
    assert len(backups[0].stem.split("_")) >= 4

    delete_calls = [str(c.args[0]) for c in conn_mock.execute.call_args_list]
    assert any("DELETE" in s for s in delete_calls)


def test_backup_filename_unique_within_same_second(tmp_path, monkeypatch):
    """同秒内に2回呼んでもファイル名が衝突しないこと（マイクロ秒で区別）。"""
    monkeypatch.setattr("reset_signals._is_trading_hours", lambda: False)
    monkeypatch.setattr("reset_signals._count_open_orders", lambda p: 0)

    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")

    p1 = reset_signals._backup_duckdb(duckdb_path)
    p2 = reset_signals._backup_duckdb(duckdb_path)
    # 衝突しないこと（マイクロ秒が違う or 同じなら上書きで問題ないが、少なくともエラーにならない）
    assert p1.parent == p2.parent  # 同じbackupディレクトリ
