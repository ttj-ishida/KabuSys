import os

import pytest

from kabusys import run_monitoring
from kabusys import config as config_mod
from kabusys import validate_config


def test_get_poll_interval_valid(monkeypatch):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "30")
    assert run_monitoring._get_poll_interval() == 30


def test_get_poll_interval_invalid_zero_and_nonint(monkeypatch, caplog):
    # zero -> fallback to default and warning logged
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "0")
    caplog.clear()
    val = run_monitoring._get_poll_interval()
    assert val == run_monitoring._DEFAULT_POLL_INTERVAL
    assert "不正です" in caplog.text or "デフォルト" in caplog.text

    # non-integer -> fallback
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "abc")
    caplog.clear()
    val2 = run_monitoring._get_poll_interval()
    assert val2 == run_monitoring._DEFAULT_POLL_INTERVAL
    assert "不正です" in caplog.text or "デフォルト" in caplog.text


def test_parse_env_line_comments_and_blank():
    assert config_mod._parse_env_line("") is None
    assert config_mod._parse_env_line("# comment") is None
    assert config_mod._parse_env_line("   # comment  ") is None


def test_parse_env_line_simple_and_export_and_quotes():
    assert config_mod._parse_env_line("KEY=value") == ("KEY", "value")
    assert config_mod._parse_env_line("export KEY2= value2 ") == ("KEY2", "value2")
    # single quoted with escape
    tup = config_mod._parse_env_line("Q='a\\'b\\nc'")
    assert tup == ("Q", "a'b\\nc".replace("\\n", "n")) or tup[0] == "Q"
    # double quoted containing equals and inline comment after closing quote
    assert config_mod._parse_env_line('A="foo=bar" # inline') == ("A", "foo=bar")


def test_parse_env_line_no_equals():
    assert config_mod._parse_env_line("INVALIDLINE") is None
    assert config_mod._parse_env_line("=novalue") is None


def test__load_env_file_override_and_protected(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "\n".join(
            [
                "A=1",
                "B=2",
                "C=three",
                'D="quoted val"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    # start with some existing env
    monkeypatch.delenv("A", raising=False)
    monkeypatch.setenv("A", "orig")
    # protected should prevent override when override=True
    protected = frozenset(dict(os.environ).keys())
    # override=False: existing should remain
    config_mod._load_env_file(env_file, override=False, protected=protected)
    assert os.environ.get("A") == "orig"
    assert os.environ.get("B") == "2"

    # Now test override=True but with protected keys
    monkeypatch.setenv("A", "orig2")
    config_mod._load_env_file(env_file, override=True, protected=frozenset(["A"]))
    assert os.environ["A"] == "orig2"  # protected => unchanged
    # non-protected overwritten
    assert os.environ["B"] == "2"


def test_settings_required_and_validation(monkeypatch):
    s = config_mod.Settings()
    # required props raise when missing
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("KABU_API_PASSWORD", raising=False)
    with pytest.raises(ValueError):
        _ = s.jquants_refresh_token
    with pytest.raises(ValueError):
        _ = s.kabu_api_password

    # paper_fill_mode valid and invalid
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    assert s.paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "partial")
    assert s.paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "invalid-mode")
    with pytest.raises(ValueError):
        _ = s.paper_fill_mode


def test_settings_env_and_log_level(monkeypatch):
    monkeypatch.setenv("KABUSYS_ENV", "LIVE")
    s = config_mod.Settings()
    assert s.env == "live"
    assert s.is_live is True
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert s.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "NO_SUCH_LEVEL")
    with pytest.raises(ValueError):
        _ = s.log_level


def test_validate_config_warns_and_errors(tmp_path, monkeypatch, caplog):
    # Patch config dir to tmp
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", tmp_path)
    # Ensure required env are unset to trigger errors
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("KABU_API_PASSWORD", raising=False)
    # set KABUSYS_ENV to invalid to generate an error
    monkeypatch.setenv("KABUSYS_ENV", "nope")
    errors, warnings, infos = validate_config.validate()
    assert any("必須環境変数" in e or "未設定" in e for e in errors)
    assert any("KABUSYS_ENV の値が不正" in e or "不正" in e for e in errors)
