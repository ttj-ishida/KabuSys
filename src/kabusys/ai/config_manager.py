"""config_manager.py — strategy_config.yaml のバックアップ・書き換え・ロールバック。"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import yaml

BACKUP_DIR = Path("config/backups")

_STRATEGY_KEYS = frozenset({
    "threshold",
    "stop_loss_rate",
    "trailing_stop_atr_mult",
    "min_holding_days",
    "max_holding_days",
    "gap_up_threshold",
    "gap_down_threshold",
})

_SECTOR_KEY_MAP = {
    "sector_boost": "boost",
    "sector_quartile": "quartile",
}

_REGIME_KEYS = frozenset({
    "topix_drawdown_threshold",
    "topix_size_multiplier_bear",
})


def backup_config(config_path: Path, backup_dir: Path = BACKUP_DIR) -> Path:
    """strategy_config.yaml を config/backups/strategy_config_YYYYMMDD_HHMMSS.yaml にコピー。

    Returns:
        作成したバックアップファイルの Path。
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"strategy_config_{timestamp}.yaml"
    shutil.copy2(config_path, backup_path)
    return backup_path


def apply_params(config_path: Path, params: dict) -> None:
    """params の各キーを strategy_config.yaml の該当セクションに上書き保存。

    セクションマッピング:
    - weights.*                                 → strategy.weights.*（他は保持）
    - threshold, stop_loss_rate 等               → strategy.*
    - sector_boost, sector_quartile             → sector.boost, sector.quartile
    - topix_drawdown_threshold 等               → regime.*

    YAML 全体を読み込み→パッチ→書き戻す。コメントは失われる。
    """
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    for key, value in params.items():
        if key == "weights":
            if not isinstance(value, dict):
                continue
            if not isinstance(data.get("strategy"), dict):
                data["strategy"] = {}
            if not isinstance(data["strategy"].get("weights"), dict):
                data["strategy"]["weights"] = {}
            data["strategy"]["weights"].update(value)

        elif key in _STRATEGY_KEYS:
            if not isinstance(data.get("strategy"), dict):
                data["strategy"] = {}
            data["strategy"][key] = value

        elif key in _SECTOR_KEY_MAP:
            if not isinstance(data.get("sector"), dict):
                data["sector"] = {}
            data["sector"][_SECTOR_KEY_MAP[key]] = value

        elif key in _REGIME_KEYS:
            if not isinstance(data.get("regime"), dict):
                data["regime"] = {}
            data["regime"][key] = value

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def list_backups(backup_dir: Path = BACKUP_DIR) -> list[Path]:
    """タイムスタンプ降順でバックアップ Path 一覧を返す。"""
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob("strategy_config_*.yaml"), reverse=True)


def restore_backup(backup_path: Path, config_path: Path) -> None:
    """指定バックアップを config_path に上書き復元。"""
    shutil.copy2(backup_path, config_path)
