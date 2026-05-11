# tests/test_mark_signal_failed.py
"""scripts/mark_signal_failed.py の単体テスト"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _run(args: list[str]):
    import mark_signal_failed as m

    with patch.object(sys, "argv", ["mark_signal_failed.py"] + args):
        return m.main()


# ---------------------------------------------------------------------------
# --code 必須
# ---------------------------------------------------------------------------


def test_requires_code():
    with pytest.raises(SystemExit) as exc:
        _run([])
    # argparse exits with code 2 when required arg is missing
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# --date バリデーション
# ---------------------------------------------------------------------------


def test_invalid_date_format_exits(tmp_path):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")
    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path

    with patch("mark_signal_failed.Settings", return_value=settings_mock):
        with pytest.raises(SystemExit) as exc:
            _run(["--code", "7203", "--date", "2026/04/17"])  # スラッシュ区切りは不正
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# DuckDB ファイル不存在
# ---------------------------------------------------------------------------


def test_exits_when_duckdb_missing(tmp_path):
    settings_mock = MagicMock()
    settings_mock.duckdb_path = tmp_path / "nonexistent.duckdb"

    with patch("mark_signal_failed.Settings", return_value=settings_mock):
        with pytest.raises(SystemExit) as exc:
            _run(["--code", "7203"])
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# 対象 0 件のときエラー終了
# ---------------------------------------------------------------------------


def test_exits_when_no_targets(tmp_path):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")

    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path

    conn_mock = MagicMock()
    conn_mock.execute.return_value.fetchall.return_value = []  # 0件

    with (
        patch("mark_signal_failed.Settings", return_value=settings_mock),
        patch("mark_signal_failed.duckdb.connect", return_value=conn_mock),
    ):
        with pytest.raises(SystemExit) as exc:
            _run(["--code", "7203", "--date", "2026-04-17"])
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# status='pending'/'processing' のみが対象になること
# ---------------------------------------------------------------------------


def test_selects_pending_and_processing_only(tmp_path, monkeypatch):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")

    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path

    conn_mock = MagicMock()
    conn_mock.execute.return_value.fetchall.return_value = []

    with (
        patch("mark_signal_failed.Settings", return_value=settings_mock),
        patch("mark_signal_failed.duckdb.connect", return_value=conn_mock),
    ):
        with pytest.raises(SystemExit):
            _run(["--code", "7203", "--date", "2026-04-17"])

    select_sql = str(conn_mock.execute.call_args_list[0].args[0])
    assert "pending" in select_sql and "processing" in select_sql
    assert "sent" not in select_sql
    assert "signal_id" in select_sql  # 正しいカラム名


# ---------------------------------------------------------------------------
# ユーザーが "n" を入力 → キャンセル
# ---------------------------------------------------------------------------


def test_cancel_on_user_no(tmp_path, monkeypatch):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")

    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path

    conn_mock = MagicMock()
    conn_mock.execute.return_value.fetchall.return_value = [
        ("sig-001", "7203", "2026-04-17", "pending", "buy", 100)
    ]
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")

    with (
        patch("mark_signal_failed.Settings", return_value=settings_mock),
        patch("mark_signal_failed.duckdb.connect", return_value=conn_mock),
    ):
        with pytest.raises(SystemExit) as exc:
            _run(["--code", "7203", "--date", "2026-04-17"])
        assert exc.value.code == 0

    # UPDATE は実行されていないこと
    sql_calls = [str(c.args[0]) for c in conn_mock.execute.call_args_list]
    assert not any("UPDATE" in s for s in sql_calls)


# ---------------------------------------------------------------------------
# 正常系: y を入力 → UPDATE が実行される
# ---------------------------------------------------------------------------


def test_updates_on_user_yes(tmp_path, monkeypatch):
    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")

    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path

    # SELECT returns 2 records (実際のスキーマに沿ったカラム順: signal_id, code, date, status, side, size)
    select_result = MagicMock()
    select_result.fetchall.return_value = [
        ("sig-001", "7203", "2026-04-17", "pending", "buy", 100),
        ("sig-002", "7203", "2026-04-17", "processing", "buy", 200),
    ]
    # UPDATE ... RETURNING signal_id の結果
    update_result = MagicMock()
    update_result.fetchall.return_value = [("sig-001",), ("sig-002",)]
    conn_mock = MagicMock()
    conn_mock.execute.side_effect = [select_result, update_result]

    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    with (
        patch("mark_signal_failed.Settings", return_value=settings_mock),
        patch("mark_signal_failed.duckdb.connect", return_value=conn_mock),
    ):
        _run(["--code", "7203", "--date", "2026-04-17"])

    # UPDATE が呼ばれ、status='failed' と signal_id が含まれること
    sql_calls = [
        (str(c.args[0]), c.args[1] if len(c.args) > 1 else [])
        for c in conn_mock.execute.call_args_list
    ]
    update_call = next(c for c in sql_calls if "UPDATE" in c[0])
    assert "failed" in update_call[0]
    assert "RETURNING" in update_call[0]
    assert "sig-001" in update_call[1] and "sig-002" in update_call[1]
    conn_mock.close.assert_called_once()


# ---------------------------------------------------------------------------
# --date 省略時は当日 JST が使われる
# ---------------------------------------------------------------------------


def test_default_date_is_today_jst(tmp_path, monkeypatch):
    """--date 省略時は JST 当日が使われること。datetime をモックして環境依存を排除。"""
    from datetime import datetime, timedelta, timezone

    fixed_jst = datetime(2026, 4, 17, 10, 0, 0, tzinfo=timezone(timedelta(hours=9)))
    expected_date = fixed_jst.date()  # 2026-04-17

    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")

    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path

    captured_date = []

    def fake_execute(sql, params=None):
        if params:
            captured_date.append(params)
        m = MagicMock()
        m.fetchall.return_value = []
        return m

    conn_mock = MagicMock()
    conn_mock.execute.side_effect = fake_execute

    mock_dt = MagicMock()
    mock_dt.now.return_value = fixed_jst
    mock_dt.fromisoformat = datetime.fromisoformat  # --date 指定パスは通常通り

    with (
        patch("mark_signal_failed.Settings", return_value=settings_mock),
        patch("mark_signal_failed.duckdb.connect", return_value=conn_mock),
        patch("mark_signal_failed.datetime", mock_dt),
    ):
        with pytest.raises(SystemExit):  # 0件でexit(1)
            _run(["--code", "7203"])

    # 固定 JST 日付がクエリパラメータに渡されていること
    assert any(len(p) >= 2 and str(expected_date) in str(p[1]) for p in captured_date)
