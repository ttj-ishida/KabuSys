# tests/test_strategy_config_load.py
"""_load_strategy_config() のユニットテスト。"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest


def _call_load(tmp_path: Path, yaml_content: str | None) -> dict:
    from kabusys.strategy.signal_generator import _load_strategy_config

    if yaml_content is None:
        target = tmp_path / "nonexistent.yaml"
    else:
        target = tmp_path / "strategy_config.yaml"
        target.write_text(yaml_content, encoding="utf-8")

    with patch("kabusys.strategy.signal_generator._STRATEGY_CONFIG_PATH", target):
        return _load_strategy_config()


class TestLoadStrategyConfigMissingFile:
    def test_returns_defaults_when_file_missing(self, tmp_path):
        from kabusys.strategy.signal_generator import _STRATEGY_CONFIG_DEFAULTS

        result = _call_load(tmp_path, None)
        assert result["weights"] == _STRATEGY_CONFIG_DEFAULTS["weights"]
        assert result["threshold"] == pytest.approx(_STRATEGY_CONFIG_DEFAULTS["threshold"])

    def test_returns_all_expected_keys(self, tmp_path):
        result = _call_load(tmp_path, None)
        expected_keys = {
            "weights",
            "threshold",
            "stop_loss_rate",
            "gap_up_threshold",
            "gap_down_threshold",
            "min_holding_days",
            "max_holding_days",
            "trailing_stop_atr_mult",
            "reentry_cooldown_days",
        }
        assert expected_keys <= result.keys()


class TestLoadStrategyConfigValidYaml:
    def test_reads_weights_from_yaml(self, tmp_path):
        content = """
strategy:
  weights:
    momentum: 0.50
    value: 0.25
    volatility: 0.10
    liquidity: 0.10
    news: 0.05
"""
        result = _call_load(tmp_path, content)
        assert result["weights"]["momentum"] == pytest.approx(0.50)
        assert result["weights"]["value"] == pytest.approx(0.25)

    def test_reads_threshold_from_yaml(self, tmp_path):
        content = "strategy:\n  threshold: 0.75\n"
        result = _call_load(tmp_path, content)
        assert result["threshold"] == pytest.approx(0.75)

    def test_reads_stop_loss_rate_from_yaml(self, tmp_path):
        content = "strategy:\n  stop_loss_rate: -0.10\n"
        result = _call_load(tmp_path, content)
        assert result["stop_loss_rate"] == pytest.approx(-0.10)

    def test_reads_min_holding_days_from_yaml(self, tmp_path):
        content = "strategy:\n  min_holding_days: 10\n"
        result = _call_load(tmp_path, content)
        assert result["min_holding_days"] == 10

    def test_reads_max_holding_days_from_yaml(self, tmp_path):
        content = "strategy:\n  max_holding_days: 30\n"
        result = _call_load(tmp_path, content)
        assert result["max_holding_days"] == 30

    def test_partial_weights_use_defaults_for_missing_keys(self, tmp_path):
        """weights に momentum だけ指定 → 他のキーはデフォルト値を使う。"""
        from kabusys.strategy.signal_generator import _STRATEGY_CONFIG_DEFAULTS

        content = "strategy:\n  weights:\n    momentum: 0.60\n"
        result = _call_load(tmp_path, content)
        assert result["weights"]["momentum"] == pytest.approx(0.60)
        assert result["weights"]["value"] == pytest.approx(
            _STRATEGY_CONFIG_DEFAULTS["weights"]["value"]
        )


class TestLoadStrategyConfigInvalidValues:
    def test_returns_default_weights_when_yaml_parse_fails(self, tmp_path):
        from kabusys.strategy.signal_generator import _STRATEGY_CONFIG_DEFAULTS

        result = _call_load(tmp_path, ": invalid: yaml: [[[")
        assert result["weights"] == _STRATEGY_CONFIG_DEFAULTS["weights"]

    def test_returns_default_weights_when_toplevel_not_dict(self, tmp_path):
        from kabusys.strategy.signal_generator import _STRATEGY_CONFIG_DEFAULTS

        result = _call_load(tmp_path, "- item1\n- item2\n")
        assert result["weights"] == _STRATEGY_CONFIG_DEFAULTS["weights"]

    def test_negative_weight_uses_default_for_that_key(self, tmp_path):
        """個別の weight が負値 → そのキーだけデフォルトを使い、合計が正なら他は適用される。"""
        from kabusys.strategy.signal_generator import _STRATEGY_CONFIG_DEFAULTS

        content = """
strategy:
  weights:
    momentum: -0.50
    value: 0.25
    volatility: 0.15
    liquidity: 0.10
    news: 0.10
"""
        result = _call_load(tmp_path, content)
        # momentum は負なのでデフォルトを使う
        assert result["weights"]["momentum"] == pytest.approx(
            _STRATEGY_CONFIG_DEFAULTS["weights"]["momentum"]
        )
        # value は有効なのでそちらを使う
        assert result["weights"]["value"] == pytest.approx(0.25)

    def test_all_zero_weights_uses_defaults(self, tmp_path):
        from kabusys.strategy.signal_generator import _STRATEGY_CONFIG_DEFAULTS

        content = """
strategy:
  weights:
    momentum: 0.0
    value: 0.0
    volatility: 0.0
    liquidity: 0.0
    news: 0.0
"""
        result = _call_load(tmp_path, content)
        assert result["weights"] == _STRATEGY_CONFIG_DEFAULTS["weights"]

    def test_bool_value_for_threshold_uses_default(self, tmp_path):
        from kabusys.strategy.signal_generator import _STRATEGY_CONFIG_DEFAULTS

        content = "strategy:\n  threshold: true\n"
        result = _call_load(tmp_path, content)
        assert result["threshold"] == pytest.approx(_STRATEGY_CONFIG_DEFAULTS["threshold"])

    def test_no_strategy_section_returns_defaults(self, tmp_path):
        from kabusys.strategy.signal_generator import _STRATEGY_CONFIG_DEFAULTS

        content = "value_score:\n  weights:\n    per: 0.5\n"
        result = _call_load(tmp_path, content)
        assert result["weights"] == _STRATEGY_CONFIG_DEFAULTS["weights"]
        assert result["threshold"] == pytest.approx(_STRATEGY_CONFIG_DEFAULTS["threshold"])


class TestLoadValueConfigFromStrategyYaml:
    def test_reads_value_score_from_strategy_config_yaml(self, tmp_path):
        content = """
strategy:
  threshold: 0.60
value_score:
  weights:
    per: 0.40
    pbr: 0.40
    div_yield: 0.20
  normalization:
    per_mid: 25.0
    pbr_mid: 2.0
    div_yield_max: 4.0
"""
        from kabusys.strategy.signal_generator import _load_value_config

        target = tmp_path / "strategy_config.yaml"
        target.write_text(content, encoding="utf-8")
        with patch("kabusys.strategy.signal_generator._STRATEGY_CONFIG_PATH", target):
            result = _load_value_config()
        assert result["weights"]["per"] == pytest.approx(0.40)
        assert result["normalization"]["per_mid"] == pytest.approx(25.0)

    def test_falls_back_to_defaults_when_no_value_score_section(self, tmp_path):
        """value_score セクションなし + strategy.toml もなし → デフォルト。"""
        content = "strategy:\n  threshold: 0.60\n"
        from kabusys.strategy.signal_generator import (
            _load_value_config,
        )

        target = tmp_path / "strategy_config.yaml"
        target.write_text(content, encoding="utf-8")

        # strategy.toml の検索パスも tmp_path 内の存在しないファイルに向ける
        fake_toml = tmp_path / "strategy.toml"  # 存在しない

        with (
            patch("kabusys.strategy.signal_generator._STRATEGY_CONFIG_PATH", target),
            patch(
                "kabusys.strategy.signal_generator.Path",
                side_effect=lambda *a: fake_toml if "strategy.toml" in str(a) else Path(*a),
            ),
        ):
            result = _load_value_config()

        # 少なくとも必須キーが存在することを確認
        assert "weights" in result
        assert "normalization" in result

    def test_value_score_invalid_weights_falls_back_to_defaults(self, tmp_path):
        """value_score.weights が不正（負値）→ デフォルトを使用。"""
        from kabusys.strategy.signal_generator import (
            _VALUE_CONFIG_DEFAULTS,
            _load_value_config,
        )

        content = """
value_score:
  weights:
    per: -0.50
    pbr: -0.30
    div_yield: -0.20
  normalization:
    per_mid: 20.0
    pbr_mid: 1.5
    div_yield_max: 3.0
"""
        target = tmp_path / "strategy_config.yaml"
        target.write_text(content, encoding="utf-8")
        with patch("kabusys.strategy.signal_generator._STRATEGY_CONFIG_PATH", target):
            result = _load_value_config()
        assert result["weights"] == _VALUE_CONFIG_DEFAULTS["weights"]

    def test_value_score_invalid_normalization_falls_back_to_defaults(self, tmp_path):
        """value_score.normalization に 0 以下 → デフォルトを使用。"""
        from kabusys.strategy.signal_generator import (
            _VALUE_CONFIG_DEFAULTS,
            _load_value_config,
        )

        content = """
value_score:
  weights:
    per: 0.50
    pbr: 0.30
    div_yield: 0.20
  normalization:
    per_mid: 0.0
    pbr_mid: 1.5
    div_yield_max: 3.0
"""
        target = tmp_path / "strategy_config.yaml"
        target.write_text(content, encoding="utf-8")
        with patch("kabusys.strategy.signal_generator._STRATEGY_CONFIG_PATH", target):
            result = _load_value_config()
        assert result["normalization"] == _VALUE_CONFIG_DEFAULTS["normalization"]


class TestLoadStrategyConfigCache:
    """mtime キャッシュのテスト。"""

    def _reset_cache(self, sg):
        sg._strategy_config_cache = None
        sg._strategy_config_mtime = -1.0

    def test_second_call_returns_same_result(self, tmp_path):
        """同一ファイルの二回目の呼び出しはキャッシュから返す。"""
        yaml_content = textwrap.dedent("""\
            strategy:
              weights:
                momentum: 0.40
                value: 0.20
                volatility: 0.15
                liquidity: 0.15
                news: 0.10
              threshold: 0.65
              stop_loss_rate: -0.08
              min_holding_days: 5
              max_holding_days: 60
              trailing_stop_atr_mult: 2.0
              reentry_cooldown_days: 5
              gap_up_threshold: 0.05
              gap_down_threshold: -0.03
        """)
        cfg_path = tmp_path / "strategy_config.yaml"
        cfg_path.write_text(yaml_content, encoding="utf-8")

        from kabusys.strategy import signal_generator as sg

        self._reset_cache(sg)
        with patch("kabusys.strategy.signal_generator._STRATEGY_CONFIG_PATH", cfg_path):
            result1 = sg._load_strategy_config()
            result2 = sg._load_strategy_config()
        assert result1 == result2
        assert result1["threshold"] == pytest.approx(0.65)

    def test_cache_invalidated_on_file_change(self, tmp_path):
        """ファイル更新後は新しい値が返る（キャッシュ無効化）。"""
        import os

        cfg_path = tmp_path / "strategy_config.yaml"
        cfg_path.write_text(
            textwrap.dedent("""\
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
        """),
            encoding="utf-8",
        )

        from kabusys.strategy import signal_generator as sg

        self._reset_cache(sg)
        with patch("kabusys.strategy.signal_generator._STRATEGY_CONFIG_PATH", cfg_path):
            result1 = sg._load_strategy_config()
            assert result1["threshold"] == pytest.approx(0.60)

            # ファイルを更新し mtime を変える
            new_mtime = cfg_path.stat().st_mtime + 1.0
            cfg_path.write_text(
                textwrap.dedent("""\
                strategy:
                  weights:
                    momentum: 0.40
                    value: 0.20
                    volatility: 0.15
                    liquidity: 0.15
                    news: 0.10
                  threshold: 0.75
                  stop_loss_rate: -0.08
                  min_holding_days: 5
                  max_holding_days: 60
                  trailing_stop_atr_mult: 2.0
                  reentry_cooldown_days: 5
                  gap_up_threshold: 0.05
                  gap_down_threshold: -0.03
            """),
                encoding="utf-8",
            )
            os.utime(str(cfg_path), (new_mtime, new_mtime))

            result2 = sg._load_strategy_config()
        assert result2["threshold"] == pytest.approx(0.75)
