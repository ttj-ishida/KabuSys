# tests/test_config_setup.py
"""src/kabusys/config_setup.py の単体テスト"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


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


def test_write_env_includes_toggles_with_defaults(tmp_path):
    """_write_env が拡張機能トグルをデフォルト値で書き出すこと。"""
    from kabusys.config_setup import _write_env

    env_file = tmp_path / ".env"
    _write_env(env_file, {})

    content = env_file.read_text(encoding="utf-8")
    assert "ENABLE_TDNET=false" in content
    assert "ENABLE_AI_SENTIMENT=false" in content
    assert "LINE_NOTIFY_ENABLED=false" in content


def test_write_env_respects_toggle_values(tmp_path):
    """_write_env がユーザー設定のトグル値を正しく書き出すこと。"""
    from kabusys.config_setup import _write_env

    env_file = tmp_path / ".env"
    _write_env(
        env_file,
        {
            "ENABLE_TDNET": "true",
            "ENABLE_AI_SENTIMENT": "true",
            "LINE_NOTIFY_ENABLED": "true",
        },
    )

    content = env_file.read_text(encoding="utf-8")
    assert "ENABLE_TDNET=true" in content
    assert "ENABLE_AI_SENTIMENT=true" in content
    assert "LINE_NOTIFY_ENABLED=true" in content


def test_write_env_toggle_keys_match_toggle_defaults(tmp_path):
    """_write_env が _TOGGLE_DEFAULTS のすべてのキーを書き出すこと（定数追加時のリグレッション防止）。"""
    from kabusys.config_setup import _TOGGLE_DEFAULTS, _write_env

    env_file = tmp_path / ".env"
    _write_env(env_file, {})

    content = env_file.read_text(encoding="utf-8")
    for key in _TOGGLE_DEFAULTS:
        assert key in content, f"{key} が .env に書き出されていない"


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

    # _ITEMS と同数の input() + 確認 1 回。
    # J-Quants ウィザードは空メール（Enter）→スキップのため 1 input() を消費。
    n_items = len(config_setup._ITEMS)
    env_file = tmp_path / ".env"
    inputs = iter(["development"] + [""] * (n_items - 1) + ["y"])
    with (
        patch("builtins.input", side_effect=inputs),
        patch.object(config_setup, "_ENV_PATH", env_file),
    ):
        result = config_setup.main(["--env-file", str(env_file)])

    assert result == 0
    assert env_file.exists()


def test_main_does_not_save_on_n(tmp_path):
    """main() でユーザーが n を入力したとき .env が保存されないこと。"""
    from kabusys import config_setup

    n_items = len(config_setup._ITEMS)
    env_file = tmp_path / ".env"
    inputs = iter(["development"] + [""] * (n_items - 1) + ["n"])
    with (
        patch("builtins.input", side_effect=inputs),
        patch.object(config_setup, "_ENV_PATH", env_file),
    ):
        result = config_setup.main(["--env-file", str(env_file)])

    assert result == 0
    assert not env_file.exists()


# ---------------------------------------------------------------------------
# _fetch_jquants_refresh_token テスト
# ---------------------------------------------------------------------------


def test_fetch_jquants_refresh_token_success():
    """正常レスポンスでリフレッシュトークンが返ること。"""
    from kabusys.config_setup import _fetch_jquants_refresh_token

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"refreshToken": "tok_abc123"}

    with patch("kabusys.config_setup.requests.post", return_value=mock_resp):
        result = _fetch_jquants_refresh_token("user@example.com", "pass")

    assert result == "tok_abc123"


def test_fetch_jquants_refresh_token_bad_request(capsys):
    """400 Bad Request のとき None が返りエラーメッセージが表示されること。"""
    from kabusys.config_setup import _fetch_jquants_refresh_token

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"message": "'mailaddress' or 'password' is incorrect."}

    with patch("kabusys.config_setup.requests.post", return_value=mock_resp):
        result = _fetch_jquants_refresh_token("bad@example.com", "wrong")

    assert result is None
    captured = capsys.readouterr()
    assert "400" in captured.out


def test_fetch_jquants_refresh_token_connection_error(capsys):
    """接続エラー発生時に None が返りエラーメッセージが表示されること。"""
    from kabusys.config_setup import _fetch_jquants_refresh_token

    with patch(
        "kabusys.config_setup.requests.post",
        side_effect=Exception("connection refused"),
    ):
        result = _fetch_jquants_refresh_token("user@example.com", "pass")

    assert result is None
    captured = capsys.readouterr()
    assert "接続エラー" in captured.out


# ---------------------------------------------------------------------------
# _prompt_jquants_auth テスト
# ---------------------------------------------------------------------------


def test_prompt_jquants_auth_no_token_skip(capsys):
    """既存トークンなし + 空メール入力でスキップし None が返ること。"""
    from kabusys.config_setup import _prompt_jquants_auth

    with patch("builtins.input", return_value=""):
        result = _prompt_jquants_auth({})

    assert result is None
    assert "スキップ" in capsys.readouterr().out


def test_prompt_jquants_auth_no_token_api_success():
    """既存トークンなし + メール+パスワード入力 → API 成功でトークンが返ること。"""
    from kabusys.config_setup import _prompt_jquants_auth

    inputs = iter(["user@example.com"])  # メールアドレス
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"refreshToken": "new_tok"}

    with (
        patch("builtins.input", side_effect=inputs),
        patch("getpass.getpass", return_value="mypassword"),
        patch("kabusys.config_setup.requests.post", return_value=mock_resp),
    ):
        result = _prompt_jquants_auth({})

    assert result == "new_tok"


def test_prompt_jquants_auth_no_token_api_failure_manual_fallback():
    """API 失敗後に手動入力したトークンが返ること。"""
    from kabusys.config_setup import _prompt_jquants_auth

    inputs = iter(["user@example.com", "manual_token_xyz"])
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"message": "'mailaddress' or 'password' is incorrect."}

    with (
        patch("builtins.input", side_effect=inputs),
        patch("getpass.getpass", return_value="wrongpass"),
        patch("kabusys.config_setup.requests.post", return_value=mock_resp),
    ):
        result = _prompt_jquants_auth({})

    assert result == "manual_token_xyz"


def test_prompt_jquants_auth_existing_token_keep():
    """既存トークンあり + Enter（N）で None が返り既存値が維持されること。"""
    from kabusys.config_setup import _prompt_jquants_auth

    with patch("builtins.input", return_value=""):  # "再取得しますか？" に Enter
        result = _prompt_jquants_auth({"JQUANTS_REFRESH_TOKEN": "old_tok"})

    assert result is None  # 呼び出し元が既存値を維持


def test_prompt_jquants_auth_existing_token_refresh():
    """既存トークンあり + y → API 成功で新トークンが返ること。"""
    from kabusys.config_setup import _prompt_jquants_auth

    inputs = iter(["y", "user@example.com"])  # 再取得確認, メール
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"refreshToken": "refreshed_tok"}

    with (
        patch("builtins.input", side_effect=inputs),
        patch("getpass.getpass", return_value="pass"),
        patch("kabusys.config_setup.requests.post", return_value=mock_resp),
    ):
        result = _prompt_jquants_auth({"JQUANTS_REFRESH_TOKEN": "old_tok"})

    assert result == "refreshed_tok"
