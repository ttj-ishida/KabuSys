
import os
from pathlib import Path
import tempfile
import io

import pytest

from kabusys import config as config_mod


def test_parse_env_line_basic_and_comments():
    assert config_mod._parse_env_line("") is None
    assert config_mod._parse_env_line("   ") is None
    assert config_mod._parse_env_line("# comment") is None

    assert config_mod._parse_env_line("KEY=val") == ("KEY", "val")
    assert config_mod._parse_env_line(" export KEY2 =  another ") == ("KEY2", "another")

    # quoted with double quote and escape
    assert config_mod._parse_env_line('Q="a\\\"b c"') == ("Q", 'a"b c')
    # single quote with escape
    assert config_mod._parse_env_line("S='a\\'b'") == ("S", "a'b")

    # inline comment (space before #)
    assert config_mod._parse_env_line("FOO=bar # comment") == ("FOO", "bar")
    # hash inside value without preceding space should be kept
    assert config_mod._parse_env_line("FOO=bar#baz") == ("FOO", "bar#baz")

    # missing '='
    assert config_mod._parse_env_line("NOEQ") is None
    # empty key
    assert config_mod._parse_env_line("=value") is None


def test_load_env_file_override_and_protected(monkeypatch, tmp_path):
    target = tmp_path / ".env.test"
    target.write_text("A=1\nB=2\nC=3\n", encoding="utf-8")

    # start with B already set in os.environ
    monkeypatch.setenv("B", "exists")
    # protected contains current os.environ keys (B)
    protected = frozenset(os.environ.keys())

    # override=False should not overwrite existing B
    config_mod._load_env_file(path=target, override=False, protected=protected)
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "exists"
    assert os.environ.get("C") == "3"

    # now test override=True but protected prevents overwriting B
    target.write_text("A=9\nB=9\nD=4\n", encoding="utf-8")
    config_mod._load_env_file(path=target, override=True, protected=protected)
    assert os.environ.get("A") == "9"  # overwritten
    assert os.environ.get("B") == "exists"  # protected, not overwritten
    assert os.environ.get("D") == "4"


def test_require_raises_when_missing(monkeypatch):
    # ensure KEY not present
    monkeypatch.delenv("SOME_MISSING_KEY", raising=False)
    with pytest.raises(ValueError):
        config_mod._require("SOME_MISSING_KEY")


def test_settings_paper_fill_mode_and_env_log_level(monkeypatch):
    # valid fill mode
    monkeypatch.setenv("PAPER_FILL_MODE", "partial")
    s = config_mod.Settings()
    assert s.paper_fill_mode == "partial"

    # invalid fill mode raises
    monkeypatch.setenv("PAPER_FILL_MODE", "INVALID_MODE")
    with pytest.raises(ValueError):
        _ = s.paper_fill_mode

    # env valid
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert s.env == "live"
    assert s.is_live

    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "not_valid")
    with pytest.raises(ValueError):
        _ = s.env

    # log level valid/invalid
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert s.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "BAD_LEVEL")
    with pytest.raises(ValueError):
        _ = s.log_level
