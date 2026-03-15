
import os
from pathlib import Path
import warnings
from unittest import mock

import pytest

import kabusys.config as config


def test_parse_env_line_basic_and_comments():
    assert config._parse_env_line("") is None
    assert config._parse_env_line("   # comment") is None
    assert config._parse_env_line("NOSEP") is None
    assert config._parse_env_line("=value") is None

    assert config._parse_env_line("export FOO=bar") == ("FOO", "bar")
    assert config._parse_env_line("KEY=abc #comment") == ("KEY", "abc")
    assert config._parse_env_line("KEY=abc#notcomment") == ("KEY", "abc#notcomment")

    # single-quoted with escaped quote
    line = r"KEY='a\'b' #ignored"
    k, v = config._parse_env_line(line)
    assert k == "KEY"
    assert v == "a'b"

    # double-quoted with escaped quote
    line2 = r'KEY="a\"b"'
    k2, v2 = config._parse_env_line(line2)
    assert k2 == "KEY"
    assert v2 == 'a"b'


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("A=1\nB=2\nC=3\n")

    # setup existing environment to test protected behavior
    monkeypatch.setenv("B", "old")
    protected = frozenset({"B"})

    # override=True but B is protected -> B should remain "old"
    config._load_env_file(env_path, override=True, protected=protected)
    assert os.environ["A"] == "1"
    assert os.environ["B"] == "old"
    assert os.environ["C"] == "3"

    # override=False: values should not overwrite existing ones
    monkeypatch.setenv("D", "initial")
    env_path2 = tmp_path / ".env2"
    env_path2.write_text("D=new\nE=5\n")
    config._load_env_file(env_path2, override=False, protected=frozenset())
    assert os.environ["D"] == "initial"
    assert os.environ["E"] == "5"


def test_load_env_file_open_oserror_warns(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("A=1\n")
    # Patch builtins.open to raise OSError for this call
    with mock.patch("builtins.open", side_effect=OSError("boom")):
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            config._load_env_file(env_path, override=False, protected=frozenset())
            assert any("読み込みに失敗しました" in str(w.message) or "読み込みに失敗しました" in str(w.message) for w in rec)


def test_find_project_root_with_and_without_marker(tmp_path, monkeypatch):
    # create project structure: proj/.git + src/kabusys/config.py
    proj = tmp_path / "proj"
    src = proj / "src" / "kabusys"
    src.mkdir(parents=True)
    git_marker = proj / ".git"
    git_marker.mkdir()
    fake_file = src / "config.py"
    fake_file.write_text("# fake")

    # monkeypatch module __file__ to simulate being located under src/kabusys/config.py
    monkeypatch.setattr(config, "__file__", str(fake_file))
    root = config._find_project_root()
    assert root == proj

    # if no marker exist -> returns None
    # point to another path without markers
    noproj = tmp_path / "noproject" / "pkg"
    noproj.mkdir(parents=True)
    fake2 = noproj / "m.py"
    fake2.write_text("#")
    monkeypatch.setattr(config, "__file__", str(fake2))
    assert config._find_project_root() is None


def test_require_and_settings_env_handling(monkeypatch):
    # require should raise when missing
    monkeypatch.delenv("SOME_KEY", raising=False)
    with pytest.raises(ValueError) as ei:
        config._require("SOME_KEY")
    assert "SOME_KEY" in str(ei.value)

    # set required environment variables and check Settings properties
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "sbot")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "ch1")
    # KABU_API_BASE_URL default
    monkeypatch.delenv("KABU_API_BASE_URL", raising=False)

    s = config.Settings()
    assert s.jquants_refresh_token == "tok"
    assert s.kabu_api_password == "pwd"
    assert s.slack_bot_token == "sbot"
    assert s.slack_channel_id == "ch1"
    assert s.kabu_api_base_url == "http://localhost:18080/kabusapi"

    # duckdb_path default expands to a Path ending with expected file
    dp = s.duckdb_path
    assert isinstance(dp, Path)
    assert dp.name == "kabusys.duckdb"

    # env validation: invalid value -> ValueError
    monkeypatch.setenv("KABUSYS_ENV", "invalid_value")
    with pytest.raises(ValueError):
        _ = s.env

    # log_level invalid -> ValueError
    monkeypatch.setenv("LOG_LEVEL", "nope")
    with pytest.raises(ValueError):
        _ = s.log_level

    # check boolean helpers
    monkeypatch.setenv("KABUSYS_ENV", "LIVE")
    assert s.env == "live"
    assert s.is_live
    monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
    assert s.is_paper
    monkeypatch.setenv("KABUSYS_ENV", "development")
    assert s.is_dev
