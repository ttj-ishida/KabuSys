
import os
import tempfile
import sqlite3
import warnings

import pytest

from kabusys.config import _parse_env_line, Settings, _find_project_root, _load_env_file, _require


def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   # comment") is None
    # simple key=value
    assert _parse_env_line("FOO=bar") == ("FOO", "bar")
    # export prefix
    assert _parse_env_line("export FOO=bar") == ("FOO", "bar")
    # quoted with escapes
    assert _parse_env_line(r"QUOTED='a\'b\c'") == ("QUOTED", "a'bc")
    # double quoted escapes
    assert _parse_env_line(r'Q2="x\"y"') == ("Q2", 'x"y')
    # inline comment after space
    assert _parse_env_line("X=val # comment") == ("X", "val")
    # no separator
    assert _parse_env_line("BADLINE") is None
    # empty key
    assert _parse_env_line("=value") is None


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    p = tmp_path / ".env.test"
    p.write_text("A=1\nB=2\nC=3\n")
    # protected keys should not be overridden when override=True
    monkeypatch.setenv("B", "existing")
    protected = frozenset(os.environ.keys())
    # load without override: only missing keys set
    _load_env_file(p, override=False, protected=protected)
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "existing"
    # load with override: protected keys preserved
    p.write_text("B=over\nD=4\n")
    _load_env_file(p, override=True, protected=protected)
    assert os.environ.get("B") == "existing"
    assert os.environ.get("D") == "4"


def test_require_raises_and_returns(monkeypatch):
    monkeypatch.delenv("SOME_KEY", raising=False)
    with pytest.raises(ValueError):
        _require("SOME_KEY")
    monkeypatch.setenv("SOME_KEY", "value")
    assert _require("SOME_KEY") == "value"


def test_settings_env_and_paper_fill_mode(monkeypatch):
    # env default
    monkeypatch.delenv("KABUSYS_ENV", raising=False)
    s = Settings()
    assert s.env == "development"
    # valid env
    monkeypatch.setenv("KABUSYS_ENV", "LIVE")
    assert Settings().env == "live"
    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        Settings().env

    # paper fill mode valid
    monkeypatch.setenv("PAPER_FILL_MODE", "partial")
    assert Settings().paper_fill_mode == "partial"
    # invalid
    monkeypatch.setenv("PAPER_FILL_MODE", "BAD")
    with pytest.raises(ValueError):
        _ = Settings().paper_fill_mode
