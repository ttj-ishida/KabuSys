
import builtins
import os
from pathlib import Path
from unittest import mock

import pytest

from kabusys.config import _parse_env_line, _load_env_file, Settings


def test_parse_env_line_blank_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   ") is None
    assert _parse_env_line("# comment") is None


def test_parse_env_line_export_and_unquoted_comment():
    assert _parse_env_line("export KEY=val") == ("KEY", "val")
    # inline comment recognized only if preceded by space/tab
    assert _parse_env_line("KEY=val #inline") == ("KEY", "val")
    # if '#' is not preceded by space, it is part of value
    assert _parse_env_line("KEY=val#notcomment") == ("KEY", "val#notcomment")


def test_parse_env_line_quoted_with_escape():
    # value: a'b  (backslash-escaped quote inside single quotes)
    line = r"KEY='a\'b'  #comment"
    k, v = _parse_env_line(line)
    assert k == "KEY"
    assert v == "a'b"


def test_parse_env_line_invalid():
    assert _parse_env_line("NO_EQUALS") is None
    assert _parse_env_line("=novalue") is None


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    envfile = tmp_path / ".env.test"
    envfile.write_text("A=1\nB=2\nC=3\n")
    # set existing OS env to simulate protected keys
    monkeypatch.setenv("B", "orig")
    # override=False -> A set, B untouched
    _load_env_file(envfile, override=False, protected=frozenset())
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "orig"
    # override=True with protected containing B -> B preserved, C overwritten
    monkeypatch.setenv("B", "orig2")
    _load_env_file(envfile, override=True, protected=frozenset({"B"}))
    assert os.environ.get("B") == "orig2"
    assert os.environ.get("C") == "3"


def test_load_env_file_open_oserror(tmp_path, monkeypatch):
    # simulate open() raising OSError
    path = tmp_path / "doesnotmatter"
    with mock.patch("builtins.open", side_effect=OSError("boom")):
        # should not raise
        _load_env_file(path, override=False, protected=frozenset())
