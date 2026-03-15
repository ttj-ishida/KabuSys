
import os
from pathlib import Path
import builtins
import warnings
from unittest import mock

import pytest

# 変更が必要ならモジュール名を適宜調整してください
from kabusys import config


def test_parse_env_line_basic():
    assert config._parse_env_line("") is None
    assert config._parse_env_line("# comment") is None
    assert config._parse_env_line("KEY=val") == ("KEY", "val")
    assert config._parse_env_line("  export KEY2 =  value2  ") == ("KEY2", "value2")


def test_parse_env_line_quotes_and_escapes():
    # single quotes with escaped single quote
    line = "A='a\\'b'"
    assert config._parse_env_line(line) == ("A", "a'b")

    # double quotes with escaped double quote and backslash
    line = 'B="x\\\"y\\\\z"'
    assert config._parse_env_line(line) == ("B", 'x"y\\z')


def test_parse_env_line_inline_comment_rules():
    # '#' should be preserved when not preceded by space/tab
    assert config._parse_env_line("K=foo#bar") == ("K", "foo#bar")
    # '#' treated as comment if preceded by space
    assert config._parse_env_line("K=foo #comment") == ("K", "foo")


def test_parse_env_line_invalid():
    assert config._parse_env_line("noequals") is None
    assert config._parse_env_line("=novar") is None
    # key empty after export
    assert config._parse_env_line("export =value") is None


def test_load_env_file_basic(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("\nA=1\nB=two #ignored\nexport C='x\\'y'\n")

    # ensure B already exists so override=False doesn't change it
    monkeypatch.setenv("B", "orig")
    # clear others if present
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("C", raising=False)

    config._load_env_file(env_file, override=False, protected=frozenset())

    assert os.environ.get("A") == "1"
    # B should remain unchanged
    assert os.environ.get("B") == "orig"
    assert os.environ.get("C") == "x'y"


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("X=fromfile\nY=2\n")

    # set existing env X which is considered OS env (protected)
    monkeypatch.setenv("X", "osval")
    monkeypatch.delenv("Y", raising=False)

    # override=True but protected contains X -> X should not be overwritten
    config._load_env_file(env_file, override=True, protected=frozenset({"X"}))

    assert os.environ["X"] == "osval"
    assert os.environ["Y"] == "2"


def test_load_env_file_unreadable_warns(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("A=1\n")

    # Patch builtins.open to raise OSError when called
    with mock.patch("builtins.open", side_effect=OSError("fail")) as m_open:
        with mock.patch("warnings.warn") as m_warn:
            config._load_env_file(env_path, override=False, protected=frozenset())
            m_warn.assert_called_once()
            # ensure open was attempted
            assert m_open.called


def test_find_project_root(tmp_path, monkeypatch):
    # create nested dir structure and a fake module file location
    project = tmp_path / "myproj"
    sub = project / "pkg" / "subpkg"
    sub.mkdir(parents=True)
    (project / ".git").write_text("")  # mark project root

    fake_module = sub / "module.py"
    fake_module.write_text("# dummy")

    # monkeypatch the module's __file__ to point into our fake tree
    monkeypatch.setattr(config, "__file__", str(fake_module))

    found = config._find_project_root()
    assert found is not None
    assert Path(found) == project


def test_require_and_settings_properties(monkeypatch, tmp_path):
    # _require raises when not set
    monkeypatch.delenv("MUST", raising=False)
    with pytest.raises(ValueError):
        config._require("MUST")

    # when set, returns value
    monkeypatch.setenv("MUST", "ok")
    assert config._require("MUST") == "ok"

    # test Settings properties for defaults and overrides
    s = config.Settings()

    # KABUSYS_ENV default is development
    monkeypatch.delenv("KABUSYS_ENV", raising=False)
    assert s.env == "development"
    assert s.is_dev is True
    assert s.is_live is False
    assert s.is_paper is False

    # valid envs
    monkeypatch.setenv("KABUSYS_ENV", "LIVE")
    assert s.env == "live"
    assert s.is_live is True

    monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
    assert s.env == "paper_trading"
    assert s.is_paper is True

    # invalid env raises
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = s.env

    # LOG_LEVEL default and validation
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert s.log_level == "INFO"
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert s.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "NOPE")
    with pytest.raises(ValueError):
        _ = s.log_level

    # duckdb/sqlite path defaults and expansion
    monkeypatch.delenv("DUCKDB_PATH", raising=False)
    monkeypatch.delenv("SQLITE_PATH", raising=False)
    dp = s.duckdb_path
    sp = s.sqlite_path
    assert isinstance(dp, Path)
    assert isinstance(sp, Path)

    # expanduser test
    monkeypatch.setenv("DUCKDB_PATH", "~/mydb.duckdb")
    assert str(s.duckdb_path).endswith("mydb.duckdb")
