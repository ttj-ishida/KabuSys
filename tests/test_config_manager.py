"""config_manager 単体テスト（Issue #279）"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """テスト用 strategy_config.yaml を tmp_path に作成する。"""
    cfg = tmp_path / "strategy_config.yaml"
    content = {
        "strategy": {
            "weights": {
                "momentum": 0.40,
                "value": 0.20,
                "volatility": 0.15,
                "liquidity": 0.15,
                "news": 0.10,
            },
            "threshold": 0.60,
            "stop_loss_rate": -0.08,
            "trailing_stop_atr_mult": 2.0,
            "min_holding_days": 5,
            "max_holding_days": 60,
            "gap_up_threshold": 0.05,
            "gap_down_threshold": -0.03,
        },
        "sector": {"boost": 0.03, "quartile": 0.25},
        "regime": {
            "topix_drawdown_threshold": -0.15,
            "topix_size_multiplier_bear": 0.5,
        },
    }
    cfg.write_text(yaml.dump(content, allow_unicode=True), encoding="utf-8")
    return cfg


@pytest.fixture
def backup_dir(tmp_path: Path) -> Path:
    return tmp_path / "backups"


class TestBackupConfig:
    def test_backup_file_created(self, config_file, backup_dir):
        from kabusys.ai.config_manager import backup_config

        result = backup_config(config_file, backup_dir)
        assert result.exists()

    def test_backup_filename_pattern(self, config_file, backup_dir):
        from kabusys.ai.config_manager import backup_config

        result = backup_config(config_file, backup_dir)
        assert re.match(
            r"strategy_config_\d{8}_\d{6}\.yaml", result.name
        )

    def test_backup_content_matches_original(self, config_file, backup_dir):
        from kabusys.ai.config_manager import backup_config

        result = backup_config(config_file, backup_dir)
        assert result.read_text(encoding="utf-8") == config_file.read_text(encoding="utf-8")

    def test_backup_dir_created_if_not_exists(self, config_file, backup_dir):
        from kabusys.ai.config_manager import backup_config

        assert not backup_dir.exists()
        backup_config(config_file, backup_dir)
        assert backup_dir.exists()


class TestApplyParams:
    def test_strategy_key_updated(self, config_file):
        from kabusys.ai.config_manager import apply_params

        apply_params(config_file, {"threshold": 0.70})
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data["strategy"]["threshold"] == pytest.approx(0.70)

    def test_weights_partial_update_preserves_other_factors(self, config_file):
        from kabusys.ai.config_manager import apply_params

        apply_params(config_file, {"weights": {"momentum": 0.50}})
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        w = data["strategy"]["weights"]
        assert w["momentum"] == pytest.approx(0.50)
        assert w["value"] == pytest.approx(0.20)   # 変更なし
        assert w["volatility"] == pytest.approx(0.15)  # 変更なし

    def test_sector_boost_mapped_correctly(self, config_file):
        from kabusys.ai.config_manager import apply_params

        apply_params(config_file, {"sector_boost": 0.05})
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data["sector"]["boost"] == pytest.approx(0.05)

    def test_sector_quartile_mapped_correctly(self, config_file):
        from kabusys.ai.config_manager import apply_params

        apply_params(config_file, {"sector_quartile": 0.30})
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data["sector"]["quartile"] == pytest.approx(0.30)

    def test_regime_keys_mapped_correctly(self, config_file):
        from kabusys.ai.config_manager import apply_params

        apply_params(
            config_file,
            {
                "topix_drawdown_threshold": -0.20,
                "topix_size_multiplier_bear": 0.3,
            },
        )
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data["regime"]["topix_drawdown_threshold"] == pytest.approx(-0.20)
        assert data["regime"]["topix_size_multiplier_bear"] == pytest.approx(0.3)

    def test_trailing_stop_updated(self, config_file):
        from kabusys.ai.config_manager import apply_params

        apply_params(config_file, {"trailing_stop_atr_mult": 2.5})
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data["strategy"]["trailing_stop_atr_mult"] == pytest.approx(2.5)


class TestListBackups:
    def test_returns_empty_when_dir_missing(self, tmp_path):
        from kabusys.ai.config_manager import list_backups

        result = list_backups(tmp_path / "nonexistent")
        assert result == []

    def test_returns_paths_in_descending_order(self, config_file, backup_dir):
        from kabusys.ai.config_manager import backup_config, list_backups
        import time

        p1 = backup_config(config_file, backup_dir)
        time.sleep(1.1)  # ファイル名のタイムスタンプが変わるのを待つ
        p2 = backup_config(config_file, backup_dir)

        result = list_backups(backup_dir)
        assert result[0] == p2
        assert result[1] == p1


class TestRestoreBackup:
    def test_restore_overwrites_config(self, config_file, backup_dir):
        from kabusys.ai.config_manager import apply_params, backup_config, restore_backup

        backup_path = backup_config(config_file, backup_dir)
        apply_params(config_file, {"threshold": 0.99})  # config を変更
        data_after = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data_after["strategy"]["threshold"] == pytest.approx(0.99)

        restore_backup(backup_path, config_file)  # 復元

        data_restored = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data_restored["strategy"]["threshold"] == pytest.approx(0.60)
