# tests/test_generate_config.py
"""scripts/generate_config.py の単体テスト"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import generate_config


def test_generate_creates_all_files(tmp_path):
    """generate() が 6 つの YAML ファイルをすべて生成すること。"""
    with patch.object(generate_config, "_CONFIG_DIR", tmp_path):
        count = generate_config.generate()

    files = list(tmp_path.glob("*.yaml"))
    assert count == 6
    assert len(files) == 6


def test_generate_skips_existing_by_default(tmp_path):
    """デフォルト動作では既存ファイルをスキップすること。"""
    existing = tmp_path / "system_config.yaml"
    existing.write_text("original", encoding="utf-8")

    with patch.object(generate_config, "_CONFIG_DIR", tmp_path):
        count = generate_config.generate(overwrite=False)

    # 既存の 1 ファイルはスキップ、残り 5 ファイルが生成される
    assert count == 5
    assert existing.read_text(encoding="utf-8") == "original"


def test_generate_overwrites_with_flag(tmp_path):
    """--overwrite 時は既存ファイルを上書きすること。"""
    existing = tmp_path / "system_config.yaml"
    existing.write_text("original", encoding="utf-8")

    with patch.object(generate_config, "_CONFIG_DIR", tmp_path):
        count = generate_config.generate(overwrite=True)

    assert count == 6
    assert existing.read_text(encoding="utf-8") != "original"


def test_generated_yaml_is_valid(tmp_path):
    """生成された YAML ファイルが有効な YAML であること。"""
    pytest.importorskip("yaml")
    import yaml

    with patch.object(generate_config, "_CONFIG_DIR", tmp_path):
        generate_config.generate()

    for yaml_file in tmp_path.glob("*.yaml"):
        content = yaml_file.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        assert parsed is not None, f"{yaml_file.name} のパースに失敗"


def test_risk_config_has_safe_defaults(tmp_path):
    """risk_config.yaml の max_drawdown が安全側（0.15 以下）であること。"""
    pytest.importorskip("yaml")
    import yaml

    with patch.object(generate_config, "_CONFIG_DIR", tmp_path):
        generate_config.generate()

    content = (tmp_path / "risk_config.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    assert data["risk"]["max_drawdown"] <= 0.15
    assert data["risk"]["max_position_size"] <= 0.10
