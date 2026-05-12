# tests/test_cancel_signal_queue.py
"""scripts/cancel_signal_queue.py の単体テスト"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _run(args: list[str]):
    import cancel_signal_queue as m

    with patch.object(sys, "argv", ["cancel_signal_queue.py"] + args):
        return m.main()


# ---------------------------------------------------------------------------
# 引数バリデーション
# ---------------------------------------------------------------------------


def test_requires_date_or_all():
    with pytest.raises(SystemExit) as exc:
        _run([])
    assert exc.value.code == 2


def test_date_and_all_are_mutually_exclusive():
    with pytest.raises(SystemExit) as exc:
        _run(["--date", "2026-05-12", "--all"])
    assert exc.value.code == 2


def test_all_and_code_cannot_coexist(tmp_path):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")
    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
    with patch("cancel_signal_queue.Settings", return_value=settings_mock):
        with pytest.raises(SystemExit) as exc:
            _run(["--all", "--code", "7203"])
        assert exc.value.code == 2


def test_invalid_date_format_exits(tmp_path):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")
    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
    with patch("cancel_signal_queue.Settings", return_value=settings_mock):
        with pytest.raises(SystemExit) as exc:
            _run(["--date", "2026/05/12"])
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# DuckDB ファイル不存在
# ---------------------------------------------------------------------------


def test_exits_when_duckdb_missing(tmp_path):
    settings_mock = MagicMock()
    settings_mock.duckdb_path = tmp_path / "nonexistent.duckdb"
    with patch("cancel_signal_queue.Settings", return_value=settings_mock):
        with pytest.raises(SystemExit) as exc:
            _run(["--date", "2026-05-12"])
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# 対象 0 件 → 正常終了（exit 0）
# ---------------------------------------------------------------------------


def test_exits_zero_when_no_targets(tmp_path):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")
    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
    conn_mock = MagicMock()
    conn_mock.execute.return_value.fetchall.return_value = []
    with (
        patch("cancel_signal_queue.Settings", return_value=settings_mock),
        patch("cancel_signal_queue.duckdb.connect", return_value=conn_mock),
    ):
        with pytest.raises(SystemExit) as exc:
            _run(["--date", "2026-05-12"])
        assert exc.value.code == 0


# ---------------------------------------------------------------------------
# SELECT クエリが status='pending' のみを対象にしていること
# ---------------------------------------------------------------------------


def test_selects_pending_only(tmp_path):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")
    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
    conn_mock = MagicMock()
    conn_mock.execute.return_value.fetchall.return_value = []
    with (
        patch("cancel_signal_queue.Settings", return_value=settings_mock),
        patch("cancel_signal_queue.duckdb.connect", return_value=conn_mock),
    ):
        with pytest.raises(SystemExit):
            _run(["--date", "2026-05-12"])

    select_sql = str(conn_mock.execute.call_args_list[0].args[0])
    assert "pending" in select_sql
    assert "processing" not in select_sql
    assert "filled" not in select_sql


# ---------------------------------------------------------------------------
# ユーザーが "n" → UPDATE 実行なし・exit 0
# ---------------------------------------------------------------------------


def test_cancel_on_user_no(tmp_path, monkeypatch):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")
    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
    conn_mock = MagicMock()
    conn_mock.execute.return_value.fetchall.return_value = [
        ("sig-001", "7203", "2026-05-12", "pending", "buy", 100)
    ]
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    with (
        patch("cancel_signal_queue.Settings", return_value=settings_mock),
        patch("cancel_signal_queue.duckdb.connect", return_value=conn_mock),
    ):
        with pytest.raises(SystemExit) as exc:
            _run(["--date", "2026-05-12"])
        assert exc.value.code == 0

    sql_calls = [str(c.args[0]) for c in conn_mock.execute.call_args_list]
    assert not any("UPDATE" in s for s in sql_calls)


# ---------------------------------------------------------------------------
# 正常系: y 入力 → UPDATE cancelled が実行される
# ---------------------------------------------------------------------------


def test_updates_cancelled_on_yes(tmp_path, monkeypatch):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")
    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path

    select_result = MagicMock()
    select_result.fetchall.return_value = [
        ("sig-001", "7203", "2026-05-12", "pending", "buy", 100),
        ("sig-002", "9984", "2026-05-12", "pending", "sell", 50),
    ]
    update_result = MagicMock()
    update_result.fetchall.return_value = [("sig-001",), ("sig-002",)]
    conn_mock = MagicMock()
    conn_mock.execute.side_effect = [select_result, update_result]

    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    with (
        patch("cancel_signal_queue.Settings", return_value=settings_mock),
        patch("cancel_signal_queue.duckdb.connect", return_value=conn_mock),
    ):
        _run(["--date", "2026-05-12"])

    sql_calls = [(str(c.args[0]), c.args[1] if len(c.args) > 1 else [])
                 for c in conn_mock.execute.call_args_list]
    update_call = next(c for c in sql_calls if "UPDATE" in c[0])
    assert "cancelled" in update_call[0]
    assert "pending" in update_call[0]
    assert "RETURNING" in update_call[0]
    assert "sig-001" in update_call[1] and "sig-002" in update_call[1]
    conn_mock.close.assert_called_once()


# ---------------------------------------------------------------------------
# --date + --code の絞り込みクエリにコードが含まれること
# ---------------------------------------------------------------------------


def test_date_and_code_filter(tmp_path):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")
    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
    conn_mock = MagicMock()
    conn_mock.execute.return_value.fetchall.return_value = []
    with (
        patch("cancel_signal_queue.Settings", return_value=settings_mock),
        patch("cancel_signal_queue.duckdb.connect", return_value=conn_mock),
    ):
        with pytest.raises(SystemExit):
            _run(["--date", "2026-05-12", "--code", "7203"])

    call_args = conn_mock.execute.call_args_list[0].args
    assert "7203" in call_args[1]
    assert "2026-05-12" in call_args[1]


# ---------------------------------------------------------------------------
# --all は日付条件なしで全 pending を対象にすること
# ---------------------------------------------------------------------------


def test_all_flag_no_date_filter(tmp_path):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")
    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path
    conn_mock = MagicMock()
    conn_mock.execute.return_value.fetchall.return_value = []
    with (
        patch("cancel_signal_queue.Settings", return_value=settings_mock),
        patch("cancel_signal_queue.duckdb.connect", return_value=conn_mock),
    ):
        with pytest.raises(SystemExit):
            _run(["--all"])

    call_args = conn_mock.execute.call_args_list[0]
    params = call_args.args[1] if len(call_args.args) > 1 else []
    assert len(params) == 0
