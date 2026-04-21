
import os

# disable auto env load before importing module
os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"
import importlib

from kabusys import config as cfg
importlib.reload(cfg)


def test_parse_env_line_comment_or_empty():
    assert cfg._parse_env_line("") is None
    assert cfg._parse_env_line("   ") is None
    assert cfg._parse_env_line("# comment") is None


def test_parse_env_line_export_and_no_value():
    r = cfg._parse_env_line("export FOO=bar")
    assert r == ("FOO", "bar")
    assert cfg._parse_env_line("KEY_WITHOUT_EQ") is None


def test_parse_env_line_quoted_with_escape():
    s = r'FOO="a\"b\nc"'
    # The parser treats backslash escape and stops at matching quote.
    # It should unescape \" into "
    k, v = cfg._parse_env_line(s)
    assert k == "FOO"
    assert 'a"b' in v


def test_parse_env_line_inline_comment_and_unquoted():
    r = cfg._parse_env_line("FOO=hello # inline comment")
    assert r == ("FOO", "hello")
    # but when '#' is part of a token (no preceding space), it's preserved
    r2 = cfg._parse_env_line("BAR=abc#def")
    assert r2 == ("BAR", "abc#def")


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    envfile = tmp_path / ".env_test"
    envfile.write_text(
        '\n'.join(
            [
                "A=1",
                "B=2",
                "C='quoted\\'value'",
                'D="escaped\\\"x"',
            ]
        )
    )
    # ensure some existing environment variables
    monkeypatch.setenv("A", "orig")
    protected_keys = frozenset(os.environ.keys())
    # call loader with override=False: should not overwrite existing A
    cfg._load_env_file(envfile, override=False, protected=protected_keys)
    assert os.environ.get("A") == "orig"
    assert os.environ.get("B") == "2"
    # override True should overwrite non-protected; but protected prevents overwrite
    monkeypatch.setenv("B", "old_b")
    cfg._load_env_file(envfile, override=True, protected=protected_keys)
    # B was set AFTER protected_keys was captured → not in protected_keys
    # override=True なので B はファイルの値 "2" で上書きされる
    assert os.environ.get("B") == "2"
