# tests/test_validate_config.py
"""src/kabusys/validate_config.py の単体テスト"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest


def _run_validate(env_overrides: dict | None = None, config_dir: Path | None = None):
    """validate() を実行するヘルパー。環境変数と config_dir をオーバーライド可能。"""
    from kabusys import validate_config as vc

    base_env = {
        "JQUANTS_REFRESH_TOKEN": "test_token",
        "KABU_API_PASSWORD": "test_pass",
        "KABUSYS_ENV": "development",
        "DUCKDB_PATH": "data/kabusys.duckdb",
        "SQLITE_PATH": "data/monitoring.db",
        "LOG_LEVEL": "INFO",
    }
    if env_overrides:
        base_env.update(env_overrides)

    patches = {k: v for k, v in base_env.items()}

    with patch.dict(os.environ, patches, clear=False):
        if config_dir is not None:
            with patch.object(vc, "_CONFIG_DIR", config_dir):
                return vc.validate()
        else:
            return vc.validate()


def test_valid_config_returns_no_errors(tmp_path):
    """必要な設定がすべて揃っているとき errors が空であること。"""
    errors, warnings, _ = _run_validate(config_dir=tmp_path)
    assert errors == []


def test_missing_required_var_returns_error():
    """必須環境変数が未設定のとき errors に含まれること。"""
    errors, _, _ = _run_validate(
        env_overrides={"JQUANTS_REFRESH_TOKEN": ""},
        config_dir=Path("/nonexistent"),
    )
    assert any("JQUANTS_REFRESH_TOKEN" in e for e in errors)


def test_placeholder_value_returns_warning():
    """プレースホルダ値のとき warnings に含まれること。"""
    _, warnings, _ = _run_validate(
        env_overrides={"JQUANTS_REFRESH_TOKEN": "your_jquants_refresh_token_here"},
        config_dir=Path("/nonexistent"),
    )
    assert any("JQUANTS_REFRESH_TOKEN" in w for w in warnings)


def test_invalid_kabusys_env_returns_error():
    """KABUSYS_ENV が無効値のとき errors に含まれること。"""
    errors, _, _ = _run_validate(
        env_overrides={"KABUSYS_ENV": "staging"},
        config_dir=Path("/nonexistent"),
    )
    assert any("KABUSYS_ENV" in e for e in errors)


def test_live_env_returns_warning():
    """KABUSYS_ENV=live のとき warnings に含まれること。"""
    _, warnings, _ = _run_validate(
        env_overrides={"KABUSYS_ENV": "live"},
        config_dir=Path("/nonexistent"),
    )
    assert any("live" in w for w in warnings)


def test_invalid_log_level_returns_warning():
    """LOG_LEVEL が無効値のとき warnings に含まれること。"""
    _, warnings, _ = _run_validate(
        env_overrides={"LOG_LEVEL": "VERBOSE"},
        config_dir=Path("/nonexistent"),
    )
    assert any("LOG_LEVEL" in w for w in warnings)


def test_missing_yaml_files_return_warnings(tmp_path):
    """config/ に YAML がないとき warnings に含まれること。"""
    _, warnings, _ = _run_validate(config_dir=tmp_path)
    assert any("yaml" in w.lower() or ".yaml" in w for w in warnings)


def test_valid_yaml_files_return_no_error(tmp_path):
    """有効な YAML ファイルが揃っているとき errors が増えないこと。"""
    pytest.importorskip("yaml")
    sys_path = Path(__file__).resolve().parents[1] / "scripts"
    import sys
    sys.path.insert(0, str(sys_path))
    import generate_config
    with patch.object(generate_config, "_CONFIG_DIR", tmp_path):
        generate_config.generate()

    errors, _, _ = _run_validate(config_dir=tmp_path)
    assert errors == []


def test_main_returns_0_on_success(tmp_path):
    """正常設定で main() が 0 を返すこと。"""
    from kabusys import validate_config as vc

    with patch.dict(os.environ, {
        "JQUANTS_REFRESH_TOKEN": "tok",
        "KABU_API_PASSWORD": "pass",
        "KABUSYS_ENV": "development",
        "LOG_LEVEL": "INFO",
    }, clear=False), patch.object(vc, "_CONFIG_DIR", tmp_path):
        result = vc.main([])
    assert result == 0


def test_main_returns_1_on_error():
    """必須変数不足で main() が 1 を返すこと。"""
    from kabusys import validate_config as vc

    with patch.dict(os.environ, {
        "JQUANTS_REFRESH_TOKEN": "",
        "KABU_API_PASSWORD": "pass",
    }, clear=False), patch.object(vc, "_CONFIG_DIR", Path("/nonexistent")):
        result = vc.main([])
    assert result == 1


def test_strict_mode_fails_on_warning(tmp_path):
    """--strict モードで警告があるとき main() が 1 を返すこと。"""
    from kabusys import validate_config as vc

    # config/ が空なので missing yaml warnings が出る
    with patch.dict(os.environ, {
        "JQUANTS_REFRESH_TOKEN": "tok",
        "KABU_API_PASSWORD": "pass",
        "KABUSYS_ENV": "development",
        "LOG_LEVEL": "INFO",
    }, clear=False), patch.object(vc, "_CONFIG_DIR", tmp_path):
        result = vc.main(["--strict"])
    # tmp_path には YAML がないので warning → strict では fail
    assert result == 1
