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

    with (
        patch.dict(
            os.environ,
            {
                "JQUANTS_REFRESH_TOKEN": "tok",
                "KABU_API_PASSWORD": "pass",
                "KABUSYS_ENV": "development",
                "LOG_LEVEL": "INFO",
            },
            clear=False,
        ),
        patch.object(vc, "_CONFIG_DIR", tmp_path),
    ):
        result = vc.main([])
    assert result == 0


def test_main_returns_1_on_error():
    """必須変数不足で main() が 1 を返すこと。"""
    from kabusys import validate_config as vc

    with (
        patch.dict(
            os.environ,
            {
                "JQUANTS_REFRESH_TOKEN": "",
                "KABU_API_PASSWORD": "pass",
            },
            clear=False,
        ),
        patch.object(vc, "_CONFIG_DIR", Path("/nonexistent")),
    ):
        result = vc.main([])
    assert result == 1


def test_strict_mode_fails_on_warning(tmp_path):
    """--strict モードで警告があるとき main() が 1 を返すこと。"""
    from kabusys import validate_config as vc

    # config/ が空なので missing yaml warnings が出る
    with (
        patch.dict(
            os.environ,
            {
                "JQUANTS_REFRESH_TOKEN": "tok",
                "KABU_API_PASSWORD": "pass",
                "KABUSYS_ENV": "development",
                "LOG_LEVEL": "INFO",
            },
            clear=False,
        ),
        patch.object(vc, "_CONFIG_DIR", tmp_path),
    ):
        result = vc.main(["--strict"])
    # tmp_path には YAML がないので warning → strict では fail
    assert result == 1


class TestRunChecks:
    def test_returns_validation_result_type(self, tmp_path, monkeypatch):
        from kabusys.validate_config import ValidationResult, run_checks

        monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "tok")
        monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
        monkeypatch.setenv("KABUSYS_ENV", "development")
        monkeypatch.chdir(tmp_path)
        result = run_checks()
        assert isinstance(result, ValidationResult)

    def test_status_ok_when_no_errors_no_warnings(self, tmp_path, monkeypatch):
        from kabusys.validate_config import run_checks

        monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "tok")
        monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
        monkeypatch.setenv("KABUSYS_ENV", "development")
        monkeypatch.chdir(tmp_path)
        result = run_checks()
        assert result.status in ("OK", "WARNING")  # warnings ok, errors not

    def test_status_error_when_required_var_missing(self, monkeypatch):
        from kabusys.validate_config import run_checks

        monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
        monkeypatch.delenv("KABU_API_PASSWORD", raising=False)
        result = run_checks()
        assert result.status == "ERROR"
        assert len(result.errors) >= 1

    def test_two_consecutive_calls_are_independent(self, monkeypatch):
        from kabusys.validate_config import run_checks

        monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
        monkeypatch.delenv("KABU_API_PASSWORD", raising=False)
        r1 = run_checks()
        monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "tok")
        monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
        monkeypatch.setenv("KABUSYS_ENV", "development")
        r2 = run_checks()
        assert r1.status == "ERROR"
        assert r2.status in ("OK", "WARNING")


class TestSandboxConfig:
    def test_no_warning_when_sandbox_disabled(self, tmp_path):
        _, warnings, _ = _run_validate(
            env_overrides={"KABU_USE_SANDBOX": "false"},
            config_dir=tmp_path,
        )
        assert not any("KABU_SANDBOX" in w for w in warnings)

    def test_warning_when_sandbox_enabled_without_password(self, tmp_path):
        _, warnings, _ = _run_validate(
            env_overrides={
                "KABU_USE_SANDBOX": "true",
                "KABU_SANDBOX_API_PASSWORD": "",
            },
            config_dir=tmp_path,
        )
        assert any("KABU_SANDBOX_API_PASSWORD" in w for w in warnings)

    def test_no_warning_when_sandbox_enabled_with_password(self, tmp_path):
        _, warnings, _ = _run_validate(
            env_overrides={
                "KABU_USE_SANDBOX": "true",
                "KABUSYS_ENV": "paper_trading",
                "KABU_SANDBOX_API_PASSWORD": "sandbox_pass",
            },
            config_dir=tmp_path,
        )
        assert not any("KABU_SANDBOX_API_PASSWORD" in w for w in warnings)

    def test_warning_when_sandbox_enabled_but_not_paper_env(self, tmp_path):
        _, warnings, _ = _run_validate(
            env_overrides={
                "KABU_USE_SANDBOX": "true",
                "KABUSYS_ENV": "development",
                "KABU_SANDBOX_API_PASSWORD": "sandbox_pass",
            },
            config_dir=tmp_path,
        )
        assert any("paper_trading" in w for w in warnings)


class TestPaperTradingCashValidation:
    def test_no_error_when_not_set(self, tmp_path):
        errors, _, _ = _run_validate(
            env_overrides={"PAPER_TRADING_INITIAL_CASH": ""},
            config_dir=tmp_path,
        )
        assert not any("PAPER_TRADING_INITIAL_CASH" in e for e in errors)

    def test_error_when_zero(self, tmp_path):
        errors, _, _ = _run_validate(
            env_overrides={"PAPER_TRADING_INITIAL_CASH": "0"},
            config_dir=tmp_path,
        )
        assert any("PAPER_TRADING_INITIAL_CASH" in e for e in errors)

    def test_error_when_negative(self, tmp_path):
        errors, _, _ = _run_validate(
            env_overrides={"PAPER_TRADING_INITIAL_CASH": "-500000"},
            config_dir=tmp_path,
        )
        assert any("PAPER_TRADING_INITIAL_CASH" in e for e in errors)

    def test_error_when_invalid_string(self, tmp_path):
        errors, _, _ = _run_validate(
            env_overrides={"PAPER_TRADING_INITIAL_CASH": "abc"},
            config_dir=tmp_path,
        )
        assert any("PAPER_TRADING_INITIAL_CASH" in e for e in errors)

    def test_no_error_when_valid(self, tmp_path):
        errors, _, _ = _run_validate(
            env_overrides={"PAPER_TRADING_INITIAL_CASH": "5000000"},
            config_dir=tmp_path,
        )
        assert not any("PAPER_TRADING_INITIAL_CASH" in e for e in errors)


class TestCheckStrategyConfigContent:
    """_check_strategy_config_content() のセマンティック検証テスト。"""

    def _run_with_yaml(self, yaml_content: str, tmp_path):
        """strategy_config.yaml に yaml_content を書いて validate() を実行する。"""
        cfg_path = tmp_path / "strategy_config.yaml"
        cfg_path.write_text(yaml_content, encoding="utf-8")
        errors, warnings, _ = _run_validate(config_dir=tmp_path)
        return errors, warnings

    def test_valid_strategy_config_no_errors(self, tmp_path):
        content = """\
strategy:
  weights:
    momentum: 0.40
    value: 0.20
    volatility: 0.15
    liquidity: 0.15
    news: 0.10
  threshold: 0.60
  stop_loss_rate: -0.08
  min_holding_days: 5
  max_holding_days: 60
  trailing_stop_atr_mult: 2.0
  reentry_cooldown_days: 5
  gap_up_threshold: 0.05
  gap_down_threshold: -0.03
value_score:
  weights:
    per: 0.50
    pbr: 0.30
    div_yield: 0.20
  normalization:
    per_mid: 20.0
    pbr_mid: 1.5
    div_yield_max: 3.0
"""
        errors, warnings = self._run_with_yaml(content, tmp_path)
        strategy_errors = [e for e in errors if "strategy_config" in e]
        assert strategy_errors == []

    def test_missing_strategy_section_errors(self, tmp_path):
        content = "other_key: value\n"
        errors, _ = self._run_with_yaml(content, tmp_path)
        assert any("strategy_config" in e and "strategy" in e for e in errors)

    def test_negative_weight_errors(self, tmp_path):
        content = """\
strategy:
  weights:
    momentum: -0.10
    value: 0.20
    volatility: 0.15
    liquidity: 0.15
    news: 0.10
  threshold: 0.60
  stop_loss_rate: -0.08
  min_holding_days: 5
  max_holding_days: 60
  trailing_stop_atr_mult: 2.0
  reentry_cooldown_days: 5
  gap_up_threshold: 0.05
  gap_down_threshold: -0.03
"""
        errors, _ = self._run_with_yaml(content, tmp_path)
        assert any("strategy_config" in e and "momentum" in e for e in errors)

    def test_stop_loss_rate_non_negative_errors(self, tmp_path):
        content = """\
strategy:
  weights:
    momentum: 0.40
    value: 0.20
    volatility: 0.15
    liquidity: 0.15
    news: 0.10
  threshold: 0.60
  stop_loss_rate: 0.05
  min_holding_days: 5
  max_holding_days: 60
  trailing_stop_atr_mult: 2.0
  reentry_cooldown_days: 5
  gap_up_threshold: 0.05
  gap_down_threshold: -0.03
"""
        errors, _ = self._run_with_yaml(content, tmp_path)
        assert any("strategy_config" in e and "stop_loss_rate" in e for e in errors)

    def test_trailing_stop_non_positive_errors(self, tmp_path):
        content = """\
strategy:
  weights:
    momentum: 0.40
    value: 0.20
    volatility: 0.15
    liquidity: 0.15
    news: 0.10
  threshold: 0.60
  stop_loss_rate: -0.08
  min_holding_days: 5
  max_holding_days: 60
  trailing_stop_atr_mult: -1.0
  reentry_cooldown_days: 5
  gap_up_threshold: 0.05
  gap_down_threshold: -0.03
"""
        errors, _ = self._run_with_yaml(content, tmp_path)
        assert any(
            "strategy_config" in e and "trailing_stop_atr_mult" in e for e in errors
        )

    def test_max_holding_days_zero_errors(self, tmp_path):
        content = """\
strategy:
  weights:
    momentum: 0.40
    value: 0.20
    volatility: 0.15
    liquidity: 0.15
    news: 0.10
  threshold: 0.60
  stop_loss_rate: -0.08
  min_holding_days: 5
  max_holding_days: 0
  trailing_stop_atr_mult: 2.0
  reentry_cooldown_days: 5
  gap_up_threshold: 0.05
  gap_down_threshold: -0.03
"""
        errors, _ = self._run_with_yaml(content, tmp_path)
        assert any("strategy_config" in e and "max_holding_days" in e for e in errors)

    def test_negative_reentry_cooldown_errors(self, tmp_path):
        content = """\
strategy:
  weights:
    momentum: 0.40
    value: 0.20
    volatility: 0.15
    liquidity: 0.15
    news: 0.10
  threshold: 0.60
  stop_loss_rate: -0.08
  min_holding_days: 5
  max_holding_days: 60
  trailing_stop_atr_mult: 2.0
  reentry_cooldown_days: -1
  gap_up_threshold: 0.05
  gap_down_threshold: -0.03
"""
        errors, _ = self._run_with_yaml(content, tmp_path)
        assert any(
            "strategy_config" in e and "reentry_cooldown_days" in e for e in errors
        )

    def test_min_holding_days_gte_max_warns(self, tmp_path):
        content = """\
strategy:
  weights:
    momentum: 0.40
    value: 0.20
    volatility: 0.15
    liquidity: 0.15
    news: 0.10
  threshold: 0.60
  stop_loss_rate: -0.08
  min_holding_days: 60
  max_holding_days: 5
  trailing_stop_atr_mult: 2.0
  reentry_cooldown_days: 5
  gap_up_threshold: 0.05
  gap_down_threshold: -0.03
"""
        _, warnings = self._run_with_yaml(content, tmp_path)
        assert any(
            "strategy_config" in w
            and "min_holding_days" in w
            and "max_holding_days" in w
            for w in warnings
        )
