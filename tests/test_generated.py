
import importlib
import sys
from pathlib import Path
from unittest import mock

import pytest


def _reload_config_module():
    """
    pathlib.Path.exists が False を返すようにパッチしてから
    kabusys.config モジュールを強制的に再読み込みして返す。
    これによりモジュールインポート時の .env 自動ロードの副作用を防ぐ。
    """
    module_name = "kabusys.config"
    # Ensure fresh import
    sys.modules.pop(module_name, None)
    with mock.patch("pathlib.Path.exists", return_value=False):
        # import_module will execute module code with Path.exists patched
        module = importlib.import_module(module_name)
    return module


def test_load_env_file_parses_and_sets_env(tmp_path, monkeypatch):
    # Arrange: create temp .env-like file
    env_file = tmp_path / ".env_test"
    contents = """
    # this is a comment
    KEY1 = value1

    KEY2="value with quotes"
    KEY3='single quoted'
    INVALID_LINE_NO_EQUALS
    SPACED_KEY =  spaced_value
    EMPTY_VALUE =
    """
    env_file.write_text(contents, encoding="utf-8")

    # Ensure existing env var is not overwritten
    monkeypatch.setenv("KEY2", "preexisting")

    # Import module fresh (prevent module-level .env load)
    cfg = _reload_config_module()

    # Act
    cfg._load_env_file(env_file)

    # Assert
    assert cfg.os.environ.get("KEY1") == "value1"
    # KEY2 existed before; should not be overwritten by file
    assert cfg.os.environ.get("KEY2") == "preexisting"
    # Quotes should be stripped
    assert cfg.os.environ.get("KEY3") == "single quoted"
    assert cfg.os.environ.get("SPACED_KEY") == "spaced_value"
    # EMPTY_VALUE has no RHS; treated as empty string -> still set
    assert cfg.os.environ.get("EMPTY_VALUE") == ""
    # INVALID_LINE_NO_EQUALS should be ignored
    assert "INVALID_LINE_NO_EQUALS" not in cfg.os.environ


def test_load_env_file_nonexistent_does_nothing(tmp_path):
    nonexist = tmp_path / "no_such_file.env"
    cfg = _reload_config_module()

    # Should not raise
    cfg._load_env_file(nonexist)


def test_require_returns_value_and_raises_when_missing(monkeypatch):
    cfg = _reload_config_module()

    # If env not set -> raises ValueError mentioning the key
    monkeypatch.delenv("SOME_REQUIRED_KEY", raising=False)
    with pytest.raises(ValueError) as exc:
        cfg._require("SOME_REQUIRED_KEY")
    assert "SOME_REQUIRED_KEY" in str(exc.value)

    # When set -> returns value
    monkeypatch.setenv("SOME_REQUIRED_KEY", "secret123")
    assert cfg._require("SOME_REQUIRED_KEY") == "secret123"


def test_settings_properties_and_defaults(monkeypatch):
    cfg = _reload_config_module()
    Settings = cfg.Settings

    # Create fresh Settings instance to test properties
    s = Settings()

    # Defaults for base URLs and paths when env vars not set
    monkeypatch.delenv("KABU_API_BASE_URL", raising=False)
    monkeypatch.delenv("DUCKDB_PATH", raising=False)
    monkeypatch.delenv("SQLITE_PATH", raising=False)
    monkeypatch.delenv("KABUSYS_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    assert s.kabu_api_base_url == "http://localhost:18080/kabusapi"
    assert s.duckdb_path == Path("data/kabusys.duckdb")
    assert s.sqlite_path == Path("data/monitoring.db")
    assert s.env == "development"
    assert s.log_level == "INFO"
    assert s.is_live is False

    # When env vars set, values should reflect them
    monkeypatch.setenv("KABU_API_BASE_URL", "https://api.example")
    monkeypatch.setenv("DUCKDB_PATH", "/tmp/db.duckdb")
    monkeypatch.setenv("SQLITE_PATH", "/tmp/monitor.db")
    monkeypatch.setenv("KABUSYS_ENV", "live")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    # New instance to pick up changed os.environ
    s2 = Settings()
    assert s2.kabu_api_base_url == "https://api.example"
    assert s2.duckdb_path == Path("/tmp/db.duckdb")
    assert s2.sqlite_path == Path("/tmp/monitor.db")
    assert s2.env == "live"
    assert s2.log_level == "DEBUG"
    assert s2.is_live is True


def test_settings_required_tokens_and_password(monkeypatch):
    cfg = _reload_config_module()
    Settings = cfg.Settings
    s = Settings()

    # Ensure required keys raise when missing
    for key, prop in [
        ("JQUANTS_REFRESH_TOKEN", "jquants_refresh_token"),
        ("KABU_API_PASSWORD", "kabu_api_password"),
        ("SLACK_BOT_TOKEN", "slack_bot_token"),
        ("SLACK_CHANNEL_ID", "slack_channel_id"),
    ]:
        monkeypatch.delenv(key, raising=False)
        with pytest.raises(ValueError):
            getattr(s, prop)

    # When set, the properties should return the values
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "jq_token")
    monkeypatch.setenv("KABU_API_PASSWORD", "kabu_pass")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "slack_token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C12345")

    s2 = Settings()
    assert s2.jquants_refresh_token == "jq_token"
    assert s2.kabu_api_password == "kabu_pass"
    assert s2.slack_bot_token == "slack_token"
    assert s2.slack_channel_id == "C12345"


def test_settings_singleton_instance_and_type(monkeypatch):
    # Reload module and check that `settings` instance exists and is Settings
    cfg = _reload_config_module()
    assert hasattr(cfg, "settings")
    assert isinstance(cfg.settings, cfg.Settings)
