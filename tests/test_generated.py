
import os
import builtins
import warnings
from pathlib import Path

import pytest
from unittest import mock

import kabusys.config as config


def test_parse_env_line_basic_and_comments():
    assert config._parse_env_line("") is None
    assert config._parse_env_line("   # comment") is None
    assert config._parse_env_line("KEY=value") == ("KEY", "value")
    assert config._parse_env_line(" export KEY2 =  123 ") == ("KEY2", "123")
    # no '='
    assert config._parse_env_line("INVALIDLINE") is None


def test_parse_env_line_quoted_and_escapes():
    # simple quoted
    assert config._parse_env_line("Q='a b c'") == ("Q", "a b c")
    # double quoted with escapes
    assert config._parse_env_line(r'Q2="a\"b\\c"') == ("Q2", 'a"b\\c')
    # missing key
    assert config._parse_env_line("=value") is None


def test_parse_env_line_inline_comment_behavior():
    # '#' immediately after token (no space) is part of value
    assert config._parse_env_line("K=foo#bar") == ("K", "foo#bar")
    # '#' preceded by space is comment
    assert config._parse_env_line("K2=foo #comment") == ("K2", "foo")


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text("A=1\nB=2\nC='x y'\n#comment\nINVALID\n")
    # ensure environment initially empty for those keys
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    monkeypatch.delenv("C", raising=False)

    # load with override=False sets only missing keys
    config._load_env_file(p, override=False, protected=frozenset())
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "2"
    assert os.environ.get("C") == "x y"

    # change env and protected behavior
    monkeypatch.setenv("A", "orig")
    # protected contains existing OS keys: A should not be overwritten when override=True
    protected = frozenset(os.environ.keys())
    config._load_env_file(p, override=True, protected=protected)
    assert os.environ.get("A") == "orig"


def test_load_env_file_missing_and_open_error(tmp_path, monkeypatch):
    # missing file: should be no-op
    config._load_env_file(tmp_path / "noexist", override=False, protected=frozenset())

    # simulate open raising OSError -> should warn but not raise
    p = tmp_path / ".envbad"
    p.write_text("A=1")
    with mock.patch("builtins.open", side_effect=OSError("boom")):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config._load_env_file(p, override=False, protected=frozenset())
            assert any(".env ファイルの読み込みに失敗しました" in str(x.message) for x in w)


def test_find_project_root(monkeypatch, tmp_path):
    # create a fake project structure
    root = tmp_path / "proj"
    sub = root / "pkg" / "subpkg"
    sub.mkdir(parents=True)
    # create a fake __file__ inside sub
    fake_file = sub / "config.py"
    fake_file.write_text("# dummy")
    # create pyproject.toml in root
    (root / "pyproject.toml").write_text("[tool]")
    # monkeypatch config.__file__ to our fake file
    monkeypatch.setattr(config, "__file__", str(fake_file))
    found = config._find_project_root()
    assert found is not None
    assert Path(found) == root


def test_require_and_settings(monkeypatch, tmp_path):
    # _require: missing -> ValueError
    monkeypatch.delenv("SOME_MISSING", raising=False)
    with pytest.raises(ValueError):
        config._require("SOME_MISSING")

    # settings properties: set env and check retrieval
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "rtok")
    assert config.settings.jquants_refresh_token == "rtok"

    monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
    assert config.settings.kabu_api_password == "pwd"

    # base url default
    monkeypatch.delenv("KABU_API_BASE_URL", raising=False)
    assert config.settings.kabu_api_base_url.startswith("http")

    # slack required
    monkeypatch.setenv("SLACK_BOT_TOKEN", "b")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "c")
    assert config.settings.slack_bot_token == "b"
    assert config.settings.slack_channel_id == "c"

    # duckdb/sqlite paths default
    monkeypatch.delenv("DUCKDB_PATH", raising=False)
    p = config.settings.duckdb_path
    assert isinstance(p, Path)

    # env validation
    monkeypatch.setenv("KABUSYS_ENV", "development")
    assert config.settings.env == "development"
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert config.settings.is_live
    monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
    assert config.settings.is_paper

    # invalid env should raise
    monkeypatch.setenv("KABUSYS_ENV", "INVALID_ENV")
    with pytest.raises(ValueError):
        _ = config.settings.env

    # log level valid/invalid
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert config.settings.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "BAD")
    with pytest.raises(ValueError):
        _ = config.settings.log_level
