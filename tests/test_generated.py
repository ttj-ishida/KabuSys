import os

import pytest

# --- config._parse_env_line, Settings, _load_env_file, _require tests ---
from kabusys.config import (
    _parse_env_line,
    _load_env_file,
    Settings,
    _require,
)


def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   # comment") is None
    assert _parse_env_line("KEYWITHOUTEQ") is None

    assert _parse_env_line("export FOO=bar") == ("FOO", "bar")
    assert _parse_env_line("KEY= value  ") == ("KEY", "value")
    # inline comment is trimmed only if preceded by space/tab
    assert _parse_env_line("K=val #comment") == ("K", "val")
    assert _parse_env_line("K=val#notcomment") == ("K", "val#notcomment")


def test_parse_env_line_quoted_and_escaped():
    # single quotes with escaped quote
    assert _parse_env_line("A='a\\'b'") == ("A", "a'b")
    # double quotes with escape
    assert _parse_env_line('B="x\\"y"') == ("B", 'x"y')
    # empty value in quotes
    assert _parse_env_line("C=''") == ("C", "")
    # quoted with trailing comment ignored
    assert _parse_env_line("D='foo'  # comment") == ("D", "foo")


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    p = tmp_path / ".env.test"
    p.write_text("A=1\nB=2\nC=3\n", encoding="utf-8")

    # ensure environment starts empty for these keys
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    monkeypatch.delenv("C", raising=False)

    # load without override -> set missing keys only
    _load_env_file(p, override=False, protected=frozenset())
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "2"

    # set B to something else, then load with override but protected contains B
    os.environ["B"] = "orig"
    _load_env_file(p, override=True, protected=frozenset({"B"}))
    # B should remain orig because it's protected
    assert os.environ["B"] == "orig"


def test_require_raises_when_missing(monkeypatch):
    monkeypatch.delenv("SOME_NONEXISTENT_KEY", raising=False)
    with pytest.raises(ValueError):
        _require("SOME_NONEXISTENT_KEY")


def test_settings_env_and_fill_mode(monkeypatch):
    s = Settings()
    # default env is development
    monkeypatch.setenv("KABUSYS_ENV", "development")
    assert s.env == "development"
    # invalid env should raise
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env_value")
    with pytest.raises(ValueError):
        _ = s.env

    # PAPER_FILL_MODE valid/invalid
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    assert s.paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "PARTIAL")
    assert s.paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "invalid_mode")
    with pytest.raises(ValueError):
        _ = s.paper_fill_mode
