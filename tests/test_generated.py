
import os
import tempfile
import sqlite3
import warnings

import pytest

from kabusys.config import (
    _parse_env_line,
    _load_env_file,
    _require,
    Settings,
)


def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   # comment") is None
    assert _parse_env_line("KEY=val") == ("KEY", "val")
    # export prefix
    assert _parse_env_line("export KEY2 =  some ") == ("KEY2", "some")
    # no separator
    assert _parse_env_line("NOSEP") is None
    # inline comment recognized when preceded by space
    assert _parse_env_line("K=1 #comment") == ("K", "1")
    # inline '#' not comment when attached to token
    assert _parse_env_line("K2=abc#not_comment") == ("K2", "abc#not_comment")
    # quoted with escapes
    s = "QUOTED='a\\'b\\\\c'"
    res = _parse_env_line(s)
    assert res == ("QUOTED", "a'b\\c")


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    envfile = tmp_path / ".env.test"
    envfile.write_text("A=1\nB=two\nC='x y'\n")
    # clear env
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    monkeypatch.delenv("C", raising=False)

    # override=False should set only missing keys
    _load_env_file(envfile, override=False, protected=frozenset())
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "two"
    assert os.environ.get("C") == "x y"

    # override=True should overwrite unless protected
    envfile.write_text("A=9\nD=4\n")
    protected = frozenset({"A"})
    _load_env_file(envfile, override=True, protected=protected)
    # A protected -> unchanged
    assert os.environ.get("A") == "1"
    assert os.environ.get("D") == "4"


def test_require_and_settings_env(monkeypatch):
    # _require raises if not present
    monkeypatch.delenv("FOO", raising=False)
    with pytest.raises(ValueError):
        _require("FOO")

    # Settings.env validation: invalid value
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    s = Settings()
    with pytest.raises(ValueError):
        _ = s.env

    # valid envs
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert Settings().env == "live"

    # paper fill mode validation
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    assert Settings().paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "INSTANT")
    assert Settings().paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "badmode")
    with pytest.raises(ValueError):
        _ = Settings().paper_fill_mode
