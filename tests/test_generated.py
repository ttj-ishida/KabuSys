import os
from pathlib import Path

import pytest

from kabusys.config import _parse_env_line, _load_env_file, Settings


def test_parse_env_line_blank_and_comment():
    assert _parse_env_line("") is None
    assert _parse_env_line("   \n") is None
    assert _parse_env_line("# a comment") is None


def test_parse_env_line_export_and_simple():
    assert _parse_env_line("export KEY=val") == ("KEY", "val")
    assert _parse_env_line("KEY = value with spaces ") == ("KEY", "value with spaces")
    # missing '='
    assert _parse_env_line("INVALIDLINE") is None


def test_parse_env_line_quoted_and_escapes():
    # single quotes with escaped single quote inside (using backslash)
    line = "S='a\\'b#notcomment'  # trailing comment"
    k, v = _parse_env_line(line)
    assert k == "S"
    assert (
        v == "a'b#notcomment"
    )  # backslash unescaped and comment inside quotes preserved

    # double quotes and escape of double quote
    line2 = 'D="x\\"y"'
    k2, v2 = _parse_env_line(line2)
    assert k2 == "D"
    assert v2 == 'x"y'


def test_parse_env_line_unquoted_inline_comment():
    # '#' preceded by space is taken as comment
    assert _parse_env_line("A=foo # comment")[1] == "foo"
    # '#' not preceded by space is part of value
    assert _parse_env_line("B=foo#bar")[1] == "foo#bar"


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "\n".join(["A=1", "B=2", "C=override_me"]) + "\n", encoding="utf-8"
    )

    # prepare existing os.environ
    monkeypatch.delenv("A", raising=False)
    monkeypatch.setenv("B", "existing")
    # protected keys should not be overridden even when override=True
    protected = frozenset({"B"})

    # load with override=False: A set, B not overwritten
    _load_env_file(Path(env_file), override=False, protected=protected)
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "existing"

    # load with override=True but protected prevents B overwrite
    monkeypatch.setenv("B", "existing2")
    _load_env_file(Path(env_file), override=True, protected=protected)
    assert os.environ.get("B") == "existing2"
    # C should be set/overwritten
    assert os.environ.get("C") == "override_me"


def test_settings_paper_fill_mode_and_env(monkeypatch):
    s = Settings()
    # default PAPER_FILL_MODE is "instant"
    monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
    assert s.paper_fill_mode == "instant"

    monkeypatch.setenv("PAPER_FILL_MODE", "PARTIAL")
    assert s.paper_fill_mode == "partial"

    monkeypatch.setenv("PAPER_FILL_MODE", "invalid-mode")
    with pytest.raises(ValueError):
        _ = s.paper_fill_mode

    # env validation
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert s.env == "live"
    assert s.is_live is True
    monkeypatch.setenv("KABUSYS_ENV", "development")
    assert s.is_dev is True

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert s.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "nope")
    with pytest.raises(ValueError):
        _ = s.log_level
