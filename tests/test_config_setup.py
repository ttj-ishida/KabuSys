# tests/test_config_setup.py
"""src/kabusys/config_setup.py の単体テスト"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


def test_read_env_parses_existing_file(tmp_path):
    """_read_env が既存の .env ファイルを正しく読み込むこと。"""
    from kabusys.config_setup import _read_env

    env_file = tmp_path / ".env"
    env_file.write_text(
        "# コメント\nJQUANTS_REFRESH_TOKEN=abc123\nKABUSYS_ENV=development\n",
        encoding="utf-8",
    )
    result = _read_env(env_file)
    assert result["JQUANTS_REFRESH_TOKEN"] == "abc123"
    assert result["KABUSYS_ENV"] == "development"


def test_read_env_returns_empty_for_missing_file(tmp_path):
    """_read_env が存在しないファイルに対して空 dict を返すこと。"""
    from kabusys.config_setup import _read_env

    result = _read_env(tmp_path / ".env")
    assert result == {}


def test_write_env_creates_file(tmp_path):
    """_write_env が .env ファイルを作成すること。"""
    from kabusys.config_setup import _write_env

    env_file = tmp_path / ".env"
    values = {
        "JQUANTS_REFRESH_TOKEN": "mytoken",
        "KABU_API_PASSWORD": "mypass",
        "KABUSYS_ENV": "development",
    }
    _write_env(env_file, values)

    assert env_file.exists()
    content = env_file.read_text(encoding="utf-8")
    assert "JQUANTS_REFRESH_TOKEN=mytoken" in content
    assert "KABU_API_PASSWORD=mypass" in content
    assert "KABUSYS_ENV=development" in content


def test_write_env_roundtrip(tmp_path):
    """_write_env → _read_env でラウンドトリップできること。"""
    from kabusys.config_setup import _read_env, _write_env

    values = {
        "JQUANTS_REFRESH_TOKEN": "tok",
        "KABU_API_PASSWORD": "pass",
        "KABUSYS_ENV": "paper_trading",
        "LOG_LEVEL": "DEBUG",
        "DUCKDB_PATH": "data/test.duckdb",
        "SQLITE_PATH": "data/test.db",
        "KABU_API_BASE_URL": "http://localhost:18080/kabusapi",
        "LINE_CHANNEL_ACCESS_TOKEN": "",
        "LINE_USER_ID": "",
        "KILL_FLAG_CLEAR_ON_START": "0",
    }
    env_file = tmp_path / ".env"
    _write_env(env_file, values)
    read_back = _read_env(env_file)

    assert read_back["KABUSYS_ENV"] == "paper_trading"
    assert read_back["LOG_LEVEL"] == "DEBUG"
    assert read_back["DUCKDB_PATH"] == "data/test.duckdb"


def test_run_wizard_uses_existing_on_empty_input(tmp_path):
    """Enter のみ（空入力）のとき既存値が使われること。"""
    from kabusys.config_setup import run_wizard

    env_file = tmp_path / ".env"
    env_file.write_text("KABUSYS_ENV=paper_trading\n", encoding="utf-8")

    # すべての入力を空（Enter）にする
    with patch("builtins.input", return_value=""):
        result = run_wizard(env_path=env_file)

    assert result["KABUSYS_ENV"] == "paper_trading"


def test_run_wizard_accepts_new_value(tmp_path):
    """ユーザーが新しい値を入力したとき、その値が使われること。"""
    from kabusys.config_setup import run_wizard

    env_file = tmp_path / ".env"
    inputs = iter(
        ["live"] + [""] * 100  # 最初の質問に "live"、残りは Enter
    )
    with patch("builtins.input", side_effect=inputs):
        result = run_wizard(env_path=env_file)

    assert result["KABUSYS_ENV"] == "live"


def test_main_saves_file_on_y(tmp_path):
    """main() でユーザーが y を入力したとき .env が保存されること。"""
    from kabusys import config_setup

    # _ITEMS は 10 項目 + 確認 1 回 = 11 回の input()
    n_items = len(config_setup._ITEMS)
    env_file = tmp_path / ".env"
    inputs = iter(["development"] + [""] * (n_items - 1) + ["y"])
    with patch("builtins.input", side_effect=inputs), \
         patch.object(config_setup, "_ENV_PATH", env_file):
        result = config_setup.main(["--env-file", str(env_file)])

    assert result == 0
    assert env_file.exists()


def test_main_does_not_save_on_n(tmp_path):
    """main() でユーザーが n を入力したとき .env が保存されないこと。"""
    from kabusys import config_setup

    n_items = len(config_setup._ITEMS)
    env_file = tmp_path / ".env"
    inputs = iter(["development"] + [""] * (n_items - 1) + ["n"])
    with patch("builtins.input", side_effect=inputs), \
         patch.object(config_setup, "_ENV_PATH", env_file):
        result = config_setup.main(["--env-file", str(env_file)])

    assert result == 0
    assert not env_file.exists()
