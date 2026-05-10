# AI Co-Pilot Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI Co-Pilot の提案パラメータを UI で確認→ `strategy_config.yaml` に適用→バックテスト再実行→変更前後の比較表示まで Co-Pilot タブ内で完結させる。

**Architecture:** `param_extractor.py`（JSON 抽出・検証）、`config_manager.py`（YAML バックアップ・適用）、`param_review.py`（Streamlit UI + subprocess）の 3 モジュールに分割。`ai_wizard.py` がチャット後に `param_extractor` を呼び出し、提案が存在すれば `param_review` を表示する。`10_Strategy_Lab.py` は `render_wizard()` に `duckdb_path` と `config_path` を追加するだけ。

**Tech Stack:** Python 3.10+, PyYAML, Streamlit, DuckDB, subprocess, unittest.mock

---

## ファイル構成

| ファイル | 操作 | 内容 |
|---|---|---|
| `src/kabusys/ai/param_extractor.py` | 新規 | AI 返答から JSON ブロック抽出・ホワイトリスト検証 |
| `src/kabusys/ai/config_manager.py` | 新規 | YAML バックアップ・適用・ロールバック |
| `src/kabusys/monitoring/components/param_review.py` | 新規 | Streamlit: 確認→適用→subprocess→比較 |
| `src/kabusys/monitoring/components/ai_wizard.py` | 変更 | システムプロンプト更新・シグネチャ拡張・param_review 呼び出し |
| `src/kabusys/monitoring/pages/10_Strategy_Lab.py` | 変更 | render_wizard() 引数追加 |
| `tests/test_param_extractor.py` | 新規 | param_extractor 単体テスト |
| `tests/test_config_manager.py` | 新規 | config_manager 単体テスト |
| `tests/test_param_review.py` | 新規 | param_review 単体テスト（st mock） |

---

## Task 1: `param_extractor.py` — JSON 抽出・ホワイトリスト検証

**Files:**
- Create: `src/kabusys/ai/param_extractor.py`
- Test: `tests/test_param_extractor.py`

- [ ] **Step 1: テストファイルを作成し、失敗を確認する**

`tests/test_param_extractor.py` を以下の内容で作成する:

```python
"""param_extractor 単体テスト（Issue #279）"""

from __future__ import annotations

import pytest

from kabusys.ai.param_extractor import extract_params


class TestExtractParams:
    def test_valid_json_block_returns_dict(self):
        text = 'おすすめです。\n```json\n{"threshold": 0.65}\n```'
        result = extract_params(text)
        assert result == {"threshold": 0.65}

    def test_no_json_block_returns_none(self):
        assert extract_params("パラメータは据え置きで良いです。") is None

    def test_invalid_json_returns_none(self):
        text = "```json\n{invalid}\n```"
        assert extract_params(text) is None

    def test_whitelist_only_violation_returns_none(self):
        text = '```json\n{"db_path": "/data/db"}\n```'
        assert extract_params(text) is None

    def test_mixed_keys_removes_violation_keeps_valid(self):
        text = '```json\n{"threshold": 0.65, "db_path": "/data/db"}\n```'
        result = extract_params(text)
        assert result == {"threshold": 0.65}
        assert "db_path" not in result

    def test_unknown_weight_key_excluded(self):
        text = '```json\n{"weights": {"unknown_factor": 0.5, "momentum": 0.45}}\n```'
        result = extract_params(text)
        assert result == {"weights": {"momentum": 0.45}}

    def test_value_out_of_range_excluded(self):
        # threshold must be 0.0〜1.0; 1.5 is out of range
        text = '```json\n{"threshold": 1.5, "sector_boost": 0.03}\n```'
        result = extract_params(text)
        assert result == {"sector_boost": 0.03}
        assert "threshold" not in result

    def test_last_block_used_when_multiple_blocks(self):
        text = (
            "```json\n{\"threshold\": 0.55}\n```\n"
            "詳細は以下の通りです。\n"
            "```json\n{\"threshold\": 0.65}\n```"
        )
        result = extract_params(text)
        assert result == {"threshold": 0.65}

    def test_negative_stop_loss_rate_valid(self):
        text = '```json\n{"stop_loss_rate": -0.08}\n```'
        result = extract_params(text)
        assert result == {"stop_loss_rate": -0.08}

    def test_positive_stop_loss_rate_excluded(self):
        text = '```json\n{"stop_loss_rate": 0.08}\n```'
        assert extract_params(text) is None

    def test_weights_dict_parsed_correctly(self):
        text = '```json\n{"weights": {"momentum": 0.45, "value": 0.25}}\n```'
        result = extract_params(text)
        assert result == {"weights": {"momentum": 0.45, "value": 0.25}}

    def test_empty_weights_dict_excluded(self):
        text = '```json\n{"weights": {}}\n```'
        assert extract_params(text) is None

    def test_int_values_for_holding_days(self):
        text = '```json\n{"min_holding_days": 3, "max_holding_days": 30}\n```'
        result = extract_params(text)
        assert result == {"min_holding_days": 3, "max_holding_days": 30}
        assert isinstance(result["min_holding_days"], int)
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_param_extractor.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'kabusys.ai.param_extractor'`

- [ ] **Step 3: `param_extractor.py` を実装する**

`src/kabusys/ai/param_extractor.py` を以下の内容で作成する:

```python
"""param_extractor.py — AI 返答テキストから JSON ブロックを抽出・ホワイトリスト検証する。"""

from __future__ import annotations

import json
import logging
import re

_logger = logging.getLogger(__name__)

ALLOWED_KEYS = frozenset({
    "weights",
    "threshold",
    "sector_boost",
    "sector_quartile",
    "stop_loss_rate",
    "trailing_stop_atr_mult",
    "gap_up_threshold",
    "gap_down_threshold",
    "min_holding_days",
    "max_holding_days",
    "topix_drawdown_threshold",
    "topix_size_multiplier_bear",
})

ALLOWED_WEIGHT_KEYS = frozenset({
    "momentum", "value", "volatility", "liquidity", "news",
})

_VALUE_RANGES: dict[str, tuple[float, float]] = {
    "threshold": (0.0, 1.0),
    "sector_boost": (0.0, 1.0),
    "sector_quartile": (0.01, 0.99),
    "stop_loss_rate": (-1.0, -0.001),
    "trailing_stop_atr_mult": (0.1, 10.0),
    "gap_up_threshold": (0.0, 1.0),
    "gap_down_threshold": (-1.0, 0.0),
    "min_holding_days": (0.0, 365.0),
    "max_holding_days": (1.0, 365.0),
    "topix_drawdown_threshold": (-1.0, -0.001),
    "topix_size_multiplier_bear": (0.01, 1.0),
}

_INT_KEYS = frozenset({"min_holding_days", "max_holding_days"})


def extract_params(text: str) -> dict | None:
    """AI 返答テキストの ```json ... ``` ブロックを抽出し、ホワイトリスト検証済み dict を返す。

    - JSON ブロックが存在しない場合は None。
    - 複数ブロックがある場合は最後のブロックを使用する。
    - ホワイトリスト外キーはそのキーのみ除外し警告ログを出す。
    - weights は ALLOWED_WEIGHT_KEYS のキーのみ許可。
    - 値域外の値はそのキーを除外し警告ログを出す。
    - 有効なキーが 1 つも残らない場合は None。
    """
    blocks = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not blocks:
        return None

    try:
        data = json.loads(blocks[-1])
    except (json.JSONDecodeError, TypeError):
        _logger.warning("extract_params: JSON パースに失敗しました")
        return None

    if not isinstance(data, dict):
        _logger.warning("extract_params: JSON がオブジェクトではありません")
        return None

    result: dict = {}

    for key, value in data.items():
        if key not in ALLOWED_KEYS:
            _logger.warning("extract_params: ホワイトリスト外キーを除外: %s", key)
            continue

        if key == "weights":
            if not isinstance(value, dict):
                _logger.warning("extract_params: weights の値が dict ではありません")
                continue
            filtered: dict = {}
            for wk, wv in value.items():
                if wk not in ALLOWED_WEIGHT_KEYS:
                    _logger.warning("extract_params: 未知の weight キーを除外: %s", wk)
                    continue
                if not isinstance(wv, (int, float)) or not (0.0 <= float(wv) <= 1.0):
                    _logger.warning(
                        "extract_params: weight 値が値域外: %s=%s", wk, wv
                    )
                    continue
                filtered[wk] = float(wv)
            if filtered:
                result["weights"] = filtered
            continue

        lo, hi = _VALUE_RANGES[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            _logger.warning("extract_params: 数値でない値を除外: %s=%s", key, value)
            continue

        v: int | float = int(value) if key in _INT_KEYS else float(value)
        if not (lo <= float(v) <= hi):
            _logger.warning(
                "extract_params: 値域外の値を除外: %s=%s (範囲: %s〜%s)", key, v, lo, hi
            )
            continue
        result[key] = v

    return result if result else None
```

- [ ] **Step 4: テストがすべてパスすることを確認する**

```bash
pytest tests/test_param_extractor.py -v
```

Expected: 13 tests PASSED

- [ ] **Step 5: コミットする**

```bash
git add src/kabusys/ai/param_extractor.py tests/test_param_extractor.py
git commit -m "feat: param_extractor — AI 返答から JSON ブロック抽出・ホワイトリスト検証 (Issue #279)"
```

---

## Task 2: `config_manager.py` — YAML バックアップ・適用・ロールバック

**Files:**
- Create: `src/kabusys/ai/config_manager.py`
- Test: `tests/test_config_manager.py`

- [ ] **Step 1: テストファイルを作成する**

`tests/test_config_manager.py` を以下の内容で作成する:

```python
"""config_manager 単体テスト（Issue #279）"""

from __future__ import annotations

import re
from datetime import datetime
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
    def test_strategy_key_updated(self, config_file, backup_dir):
        from kabusys.ai.config_manager import apply_params

        apply_params(config_file, {"threshold": 0.70})
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data["strategy"]["threshold"] == pytest.approx(0.70)

    def test_weights_partial_update_preserves_other_factors(self, config_file, backup_dir):
        from kabusys.ai.config_manager import apply_params

        apply_params(config_file, {"weights": {"momentum": 0.50}})
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        w = data["strategy"]["weights"]
        assert w["momentum"] == pytest.approx(0.50)
        assert w["value"] == pytest.approx(0.20)   # 変更なし
        assert w["volatility"] == pytest.approx(0.15)  # 変更なし

    def test_sector_boost_mapped_correctly(self, config_file, backup_dir):
        from kabusys.ai.config_manager import apply_params

        apply_params(config_file, {"sector_boost": 0.05})
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data["sector"]["boost"] == pytest.approx(0.05)

    def test_sector_quartile_mapped_correctly(self, config_file, backup_dir):
        from kabusys.ai.config_manager import apply_params

        apply_params(config_file, {"sector_quartile": 0.30})
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data["sector"]["quartile"] == pytest.approx(0.30)

    def test_regime_keys_mapped_correctly(self, config_file, backup_dir):
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

    def test_trailing_stop_updated(self, config_file, backup_dir):
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_config_manager.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'kabusys.ai.config_manager'`

- [ ] **Step 3: `config_manager.py` を実装する**

`src/kabusys/ai/config_manager.py` を以下の内容で作成する:

```python
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
```

- [ ] **Step 4: テストがすべてパスすることを確認する**

```bash
pytest tests/test_config_manager.py -v
```

Expected: 12 tests PASSED（`TestListBackups::test_returns_paths_in_descending_order` は time.sleep(1.1) で約1秒かかる）

- [ ] **Step 5: コミットする**

```bash
git add src/kabusys/ai/config_manager.py tests/test_config_manager.py
git commit -m "feat: config_manager — strategy_config.yaml バックアップ・適用・ロールバック (Issue #279)"
```

---

## Task 3: `param_review.py` — Streamlit レビュー・適用・再実行・比較 UI

**Files:**
- Create: `src/kabusys/monitoring/components/param_review.py`
- Test: `tests/test_param_review.py`

- [ ] **Step 1: テストファイルを作成する**

`tests/test_param_review.py` を以下の内容で作成する:

```python
"""param_review コンポーネント単体テスト（Issue #279）"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import yaml


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    cfg = tmp_path / "strategy_config.yaml"
    content = {
        "strategy": {
            "weights": {"momentum": 0.40, "value": 0.20, "volatility": 0.15,
                        "liquidity": 0.15, "news": 0.10},
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


def _make_st_mock(session_state=None):
    mock_st = MagicMock()
    mock_st.session_state = session_state if session_state is not None else {}
    mock_st.columns.return_value = [MagicMock(), MagicMock()]
    mock_st.button.return_value = False
    return mock_st


class TestRenderParamReviewEmpty:
    def test_empty_params_and_no_state_returns_immediately(self, config_file, tmp_path):
        import kabusys.monitoring.components.param_review as mod

        mock_st = _make_st_mock()
        with patch.object(mod, "st", mock_st):
            mod.render_param_review(
                suggested_params={},
                config_path=config_file,
                duckdb_path=tmp_path / "test.duckdb",
                prev_run_id=None,
            )

        mock_st.subheader.assert_not_called()
        mock_st.dataframe.assert_not_called()


class TestApplyButton:
    def test_apply_sets_session_state(self, config_file, tmp_path):
        import kabusys.monitoring.components.param_review as mod

        state: dict = {}
        mock_st = _make_st_mock(session_state=state)

        # 適用ボタンのみ True を返すよう設定
        def button_side_effect(label, **kwargs):
            return kwargs.get("key") == "param_review_apply"

        mock_st.button.side_effect = button_side_effect
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        backup_path = tmp_path / "backups" / "strategy_config_20260510_120000.yaml"
        backup_path.parent.mkdir(parents=True)
        import shutil
        shutil.copy2(config_file, backup_path)

        with patch.object(mod, "st", mock_st):
            with patch(
                "kabusys.monitoring.components.param_review.backup_config",
                return_value=backup_path,
            ) as mock_backup:
                with patch(
                    "kabusys.monitoring.components.param_review.apply_params"
                ) as mock_apply:
                    mod.render_param_review(
                        suggested_params={"threshold": 0.65},
                        config_path=config_file,
                        duckdb_path=tmp_path / "test.duckdb",
                        prev_run_id="prev-run-001",
                    )

        assert state.get("param_review_applied") is True
        assert state.get("param_review_backup_path") == str(backup_path)
        assert state.get("param_review_prev_run_id") == "prev-run-001"
        mock_backup.assert_called_once_with(config_file)
        mock_apply.assert_called_once_with(config_file, {"threshold": 0.65})


class TestCancelButton:
    def test_cancel_clears_suggested_from_session_state(self, config_file, tmp_path):
        import kabusys.monitoring.components.param_review as mod

        state: dict = {"param_review_suggested": {"threshold": 0.65}}
        mock_st = _make_st_mock(session_state=state)

        def button_side_effect(label, **kwargs):
            return kwargs.get("key") == "param_review_cancel"

        mock_st.button.side_effect = button_side_effect
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        with patch.object(mod, "st", mock_st):
            mod.render_param_review(
                suggested_params={"threshold": 0.65},
                config_path=config_file,
                duckdb_path=tmp_path / "test.duckdb",
                prev_run_id=None,
            )

        assert "param_review_suggested" not in state
        mock_st.rerun.assert_called()


class TestSubprocessRun:
    def test_successful_subprocess_sets_new_run_id(self, config_file, tmp_path):
        import kabusys.monitoring.components.param_review as mod

        state: dict = {
            "param_review_applied": True,
            "param_review_backup_path": str(tmp_path / "backup.yaml"),
            "param_review_prev_run_id": "prev-001",
        }
        mock_st = _make_st_mock(session_state=state)
        mock_st.date_input.side_effect = [
            __import__("datetime").date(2023, 1, 1),
            __import__("datetime").date(2024, 12, 31),
        ]

        def button_side_effect(label, **kwargs):
            return kwargs.get("key") == "param_review_run"

        mock_st.button.side_effect = button_side_effect
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        status_ctx = MagicMock()
        status_ctx.__enter__ = MagicMock(return_value=status_ctx)
        status_ctx.__exit__ = MagicMock(return_value=False)
        mock_st.status.return_value = status_ctx

        report_json = json.dumps({
            "meta": {"run_id": "new-run-001"},
            "headline": {},
        })
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = report_json

        with patch.object(mod, "st", mock_st):
            with patch(
                "kabusys.monitoring.components.param_review._load_default_dates",
                return_value=("2023-01-01", "2024-12-31"),
            ):
                with patch(
                    "kabusys.monitoring.components.param_review.subprocess.run",
                    return_value=mock_result,
                ):
                    mod.render_param_review(
                        suggested_params={},
                        config_path=config_file,
                        duckdb_path=tmp_path / "test.duckdb",
                        prev_run_id=None,
                    )

        assert state.get("param_review_new_run_id") == "new-run-001"
        mock_st.rerun.assert_called()

    def test_failed_subprocess_calls_error(self, config_file, tmp_path):
        import kabusys.monitoring.components.param_review as mod

        state: dict = {
            "param_review_applied": True,
            "param_review_backup_path": str(tmp_path / "backup.yaml"),
        }
        mock_st = _make_st_mock(session_state=state)
        mock_st.date_input.side_effect = [
            __import__("datetime").date(2023, 1, 1),
            __import__("datetime").date(2024, 12, 31),
        ]

        def button_side_effect(label, **kwargs):
            return kwargs.get("key") == "param_review_run"

        mock_st.button.side_effect = button_side_effect
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        status_ctx = MagicMock()
        status_ctx.__enter__ = MagicMock(return_value=status_ctx)
        status_ctx.__exit__ = MagicMock(return_value=False)
        mock_st.status.return_value = status_ctx

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "DuckDB file not found"

        with patch.object(mod, "st", mock_st):
            with patch(
                "kabusys.monitoring.components.param_review._load_default_dates",
                return_value=(None, None),
            ):
                with patch(
                    "kabusys.monitoring.components.param_review.subprocess.run",
                    return_value=mock_result,
                ):
                    mod.render_param_review(
                        suggested_params={},
                        config_path=config_file,
                        duckdb_path=tmp_path / "test.duckdb",
                        prev_run_id=None,
                    )

        mock_st.error.assert_called()


class TestRollbackButton:
    def test_rollback_calls_restore_and_resets_state(self, config_file, tmp_path):
        import kabusys.monitoring.components.param_review as mod

        backup_path = tmp_path / "backup.yaml"
        state: dict = {
            "param_review_applied": True,
            "param_review_backup_path": str(backup_path),
            "param_review_prev_run_id": "prev-001",
            "param_review_new_run_id": "new-001",
            "param_review_suggested": {"threshold": 0.65},
        }
        mock_st = _make_st_mock(session_state=state)
        mock_st.date_input.side_effect = [
            __import__("datetime").date(2023, 1, 1),
            __import__("datetime").date(2024, 12, 31),
        ]

        def button_side_effect(label, **kwargs):
            return kwargs.get("key") == "param_review_rollback"

        mock_st.button.side_effect = button_side_effect
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        with patch.object(mod, "st", mock_st):
            with patch(
                "kabusys.monitoring.components.param_review._load_default_dates",
                return_value=("2023-01-01", "2024-12-31"),
            ):
                with patch(
                    "kabusys.monitoring.components.param_review.restore_backup"
                ) as mock_restore:
                    mod.render_param_review(
                        suggested_params={},
                        config_path=config_file,
                        duckdb_path=tmp_path / "test.duckdb",
                        prev_run_id=None,
                    )

        mock_restore.assert_called_once_with(backup_path, config_file)
        assert "param_review_applied" not in state
        assert "param_review_backup_path" not in state
        assert "param_review_suggested" not in state
        mock_st.rerun.assert_called()
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_param_review.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'kabusys.monitoring.components.param_review'`

- [ ] **Step 3: `param_review.py` を実装する**

`src/kabusys/monitoring/components/param_review.py` を以下の内容で作成する:

```python
"""param_review.py — AI 提案パラメータのレビュー・適用・バックテスト再実行・比較表示コンポーネント。"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import date
from pathlib import Path

import duckdb
import streamlit as st
import yaml

from kabusys.ai.config_manager import apply_params, backup_config, restore_backup

_logger = logging.getLogger(__name__)

_DISPLAY_NAMES: dict[str, str] = {
    "threshold": "threshold（BUY 閾値）",
    "stop_loss_rate": "stop_loss_rate（損切り率）",
    "trailing_stop_atr_mult": "trailing_stop_atr_mult（ATR 乗数）",
    "min_holding_days": "min_holding_days（最低保有日数）",
    "max_holding_days": "max_holding_days（最大保有日数）",
    "gap_up_threshold": "gap_up_threshold（ギャップアップ閾値）",
    "gap_down_threshold": "gap_down_threshold（ギャップダウン閾値）",
    "sector_boost": "sector_boost（セクターブースト）",
    "sector_quartile": "sector_quartile（セクター区切り）",
    "topix_drawdown_threshold": "topix_drawdown_threshold（TOPIX 下落閾値）",
    "topix_size_multiplier_bear": "topix_size_multiplier_bear（弱気相場サイズ係数）",
}


def _read_current_params(config_path: Path) -> dict:
    """strategy_config.yaml から現在の変更可能パラメータを読み取る。"""
    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}

    result: dict = {}
    s = data.get("strategy", {}) or {}
    for key in (
        "threshold", "stop_loss_rate", "trailing_stop_atr_mult",
        "min_holding_days", "max_holding_days",
        "gap_up_threshold", "gap_down_threshold",
    ):
        if key in s:
            result[key] = s[key]
    if isinstance(s.get("weights"), dict):
        result["weights"] = s["weights"]

    sec = data.get("sector", {}) or {}
    if "boost" in sec:
        result["sector_boost"] = sec["boost"]
    if "quartile" in sec:
        result["sector_quartile"] = sec["quartile"]

    reg = data.get("regime", {}) or {}
    for key in ("topix_drawdown_threshold", "topix_size_multiplier_bear"):
        if key in reg:
            result[key] = reg[key]

    return result


def _load_default_dates(duckdb_path: Path) -> tuple[str | None, str | None]:
    """backtest_runs の最新行の start_date / end_date を文字列で返す。"""
    try:
        conn = duckdb.connect(str(duckdb_path), read_only=True)
        try:
            row = conn.execute(
                "SELECT start_date, end_date FROM backtest_runs"
                " ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        return None, None

    if row is None:
        return None, None
    return str(row[0]), str(row[1])


def _load_run_metrics(duckdb_path: Path, run_id: str) -> dict | None:
    """DuckDB から指定 run_id の指標 dict を返す。見つからない場合は None。"""
    try:
        conn = duckdb.connect(str(duckdb_path), read_only=True)
        try:
            row = conn.execute(
                "SELECT cagr, sharpe, max_drawdown, win_rate, total_trades"
                " FROM backtest_runs WHERE run_id = ?",
                [run_id],
            ).fetchone()
        finally:
            conn.close()
    except Exception as e:
        _logger.warning("_load_run_metrics: %s", e)
        return None

    if row is None:
        return None
    return {
        "cagr": row[0],
        "sharpe": row[1],
        "max_drawdown": row[2],
        "win_rate": row[3],
        "total_trades": row[4],
    }


def render_param_review(
    suggested_params: dict,
    config_path: Path,
    duckdb_path: Path,
    prev_run_id: str | None,
) -> None:
    """AI 提案パラメータのレビュー・適用・バックテスト再実行・比較表示 UI を描画する。

    Args:
        suggested_params: param_extractor.extract_params() が返した提案 dict。
        config_path:      strategy_config.yaml の Path。
        duckdb_path:      subprocess に渡す DuckDB ファイルパス。
        prev_run_id:      変更前の backtest_runs.run_id（比較用）。None の場合は比較なし。
    """
    applied = st.session_state.get("param_review_applied", False)

    if not suggested_params and not applied:
        return

    st.divider()
    st.subheader("📋 AI 提案パラメータ")

    if not applied:
        current = _read_current_params(config_path)
        rows = []
        for key, proposed in suggested_params.items():
            if key == "weights":
                for wk, wv in proposed.items():
                    curr_w = current.get("weights", {}).get(wk, "N/A")
                    rows.append({
                        "パラメータ": f"weights.{wk}",
                        "現在値": curr_w,
                        "提案値": wv,
                    })
            else:
                rows.append({
                    "パラメータ": _DISPLAY_NAMES.get(key, key),
                    "現在値": current.get(key, "N/A"),
                    "提案値": proposed,
                })
        if rows:
            st.dataframe(rows, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 適用する", key="param_review_apply"):
                try:
                    backup_path = backup_config(config_path)
                    apply_params(config_path, suggested_params)
                    st.session_state["param_review_applied"] = True
                    st.session_state["param_review_backup_path"] = str(backup_path)
                    st.session_state["param_review_prev_run_id"] = prev_run_id
                    st.rerun()
                except Exception as e:
                    st.error(f"適用に失敗しました: {e}")
        with col2:
            if st.button("❌ キャンセル", key="param_review_cancel"):
                st.session_state.pop("param_review_suggested", None)
                st.rerun()
        return

    # --- 適用済み: バックテスト実行フォーム ---
    st.success("✅ パラメータを適用しました。バックテストを再実行して効果を確認できます。")

    default_start, default_end = _load_default_dates(duckdb_path)

    start_val = (
        date.fromisoformat(default_start)
        if default_start
        else date(date.today().year - 2, 1, 1)
    )
    end_val = (
        date.fromisoformat(default_end) if default_end else date.today()
    )

    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input("開始日", value=start_val, key="param_review_start")
    with col_e:
        end_date = st.date_input("終了日", value=end_val, key="param_review_end")

    col_run, col_roll = st.columns(2)
    with col_run:
        if st.button("▶ バックテスト実行", key="param_review_run"):
            with st.status("バックテスト実行中...", expanded=True) as status:
                st.write(f"期間: {start_date} 〜 {end_date}")
                proc = subprocess.run(
                    [
                        sys.executable, "-m", "kabusys.backtest.run",
                        "--start", start_date.isoformat(),
                        "--end", end_date.isoformat(),
                        "--db", str(duckdb_path),
                        "--output-format", "json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if proc.returncode != 0:
                    status.update(label="❌ バックテスト失敗", state="error")
                    st.error(f"エラー:\n{proc.stderr}")
                    return
                try:
                    report_data = json.loads(proc.stdout)
                    new_run_id: str = report_data["meta"]["run_id"]
                except (json.JSONDecodeError, KeyError) as e:
                    status.update(label="❌ 結果の解析に失敗", state="error")
                    st.error(f"stdout パース失敗: {e}")
                    return
                status.update(label="✅ バックテスト完了", state="complete")
                st.session_state["param_review_new_run_id"] = new_run_id
            st.rerun()

    with col_roll:
        backup_path_str: str = st.session_state.get("param_review_backup_path", "")
        if backup_path_str and st.button("⏪ ロールバック", key="param_review_rollback"):
            try:
                restore_backup(Path(backup_path_str), config_path)
                for k in (
                    "param_review_applied",
                    "param_review_backup_path",
                    "param_review_prev_run_id",
                    "param_review_new_run_id",
                    "param_review_suggested",
                ):
                    st.session_state.pop(k, None)
                st.rerun()
            except Exception as e:
                st.error(f"ロールバックに失敗しました: {e}")

    # --- 比較表示 ---
    new_run_id_state: str | None = st.session_state.get("param_review_new_run_id")
    prev_run_id_state: str | None = st.session_state.get("param_review_prev_run_id")
    if not new_run_id_state:
        return

    st.subheader("📊 変更前後の比較")
    new_m = _load_run_metrics(duckdb_path, new_run_id_state)
    prev_m = (
        _load_run_metrics(duckdb_path, prev_run_id_state)
        if prev_run_id_state
        else None
    )

    def _pct(v: float | None) -> str:
        return f"{v:+.2%}" if v is not None else "N/A"

    def _f(v: float | None, prec: int = 3) -> str:
        return f"{v:.{prec}f}" if v is not None else "N/A"

    metrics = [
        ("CAGR", "cagr", _pct, True),
        ("Sharpe Ratio", "sharpe", _f, True),
        ("Max Drawdown", "max_drawdown", _pct, True),
        ("Win Rate", "win_rate", _pct, True),
        ("Total Trades", "total_trades",
         lambda v: str(int(v)) if v is not None else "N/A", False),
    ]

    h1, h2, h3, h4 = st.columns(4)
    h1.markdown("**指標**")
    h2.markdown("**変更前**")
    h3.markdown("**変更後**")
    h4.markdown("**差分**")

    for label, mk, fmt, show_diff in metrics:
        nv = new_m.get(mk) if new_m else None
        pv = prev_m.get(mk) if prev_m else None
        c1, c2, c3, c4 = st.columns(4)
        c1.write(label)
        c2.write(fmt(pv))
        c3.write(fmt(nv))
        if show_diff and nv is not None and pv is not None:
            diff = nv - pv
            icon = "🟢" if diff > 0 else "🔴"
            c4.markdown(f"{icon} {diff:+.4f}")
        else:
            c4.write("—")
```

- [ ] **Step 4: テストがすべてパスすることを確認する**

```bash
pytest tests/test_param_review.py -v
```

Expected: 7 tests PASSED

- [ ] **Step 5: コミットする**

```bash
git add src/kabusys/monitoring/components/param_review.py tests/test_param_review.py
git commit -m "feat: param_review — AI 提案パラメータ確認・適用・バックテスト再実行 UI (Issue #279)"
```

---

## Task 4: `ai_wizard.py` 変更 — システムプロンプト更新・シグネチャ拡張・param_review 呼び出し

**Files:**
- Modify: `src/kabusys/monitoring/components/ai_wizard.py`
- Modify: `tests/test_ai_wizard.py`（シグネチャ変更に伴う既存テスト更新 + 新規テスト追加）

- [ ] **Step 1: 既存テストが現在パスしていることを確認する**

```bash
pytest tests/test_ai_wizard.py -v
```

Expected: 8 tests PASSED

- [ ] **Step 2: `ai_wizard.py` を全面的に書き換える**

`src/kabusys/monitoring/components/ai_wizard.py` を以下の内容に置き換える:

```python
"""ai_wizard.py — AI Co-Pilot チャットコンポーネント（再利用可能）。"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Generator

import duckdb
import streamlit as st
from openai import OpenAI

from kabusys.ai.backtest_summarizer import load_latest_summary
from kabusys.ai.param_extractor import extract_params
from kabusys.monitoring.components.param_review import render_param_review
from kabusys.monitoring.monitoring_db import MonitoringDB

_logger = logging.getLogger(__name__)
_MODEL = "gpt-4o"

_SYSTEM_PROMPT_TEMPLATE = """\
あなたは KabuSys の戦略チューニング・アシスタントです。
以下のバックテスト結果を踏まえ、購入ロジック（weights / threshold / sector パラメータ）および
リスク・フィルターロジック（stop_loss / trailing_stop / gap / holding_days / topix パラメータ）の
改善案を提案してください。回答は簡潔な日本語で行い、具体的な数値変更案を含めてください。

{context}

改善案がある場合は、回答末尾に必ず以下の形式で JSON ブロックを出力してください。
変更不要なパラメータは含めないでください。
weights は変更する重みキーのみ含めてください（例: {{"weights": {{"momentum": 0.45}}}}）。

```json
{{"threshold": 0.65, "trailing_stop_atr_mult": 2.5}}
```"""

_NO_DATA_CONTEXT = (
    "バックテスト結果がまだありません。一般的な戦略チューニングについて質問できます。"
)


def _stream_openai_response(
    client: OpenAI,
    messages: list[dict],
) -> Generator[str, None, None]:
    """OpenAI Chat Completions API をストリーミングで呼び出す。

    テスト時は
    unittest.mock.patch("kabusys.monitoring.components.ai_wizard._stream_openai_response")
    で差し替える。
    """
    stream = client.chat.completions.create(
        model=_MODEL,
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


def _load_prev_run_id(conn: duckdb.DuckDBPyConnection) -> str | None:
    """backtest_runs の最新 run_id を取得する。"""
    try:
        row = conn.execute(
            "SELECT run_id FROM backtest_runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return str(row[0]) if row else None
    except Exception:
        return None


def render(
    duckdb_conn: duckdb.DuckDBPyConnection,
    sqlite_conn: sqlite3.Connection,
    duckdb_path: Path,
    config_path: Path,
) -> None:
    """AI Co-Pilot チャット UI を Streamlit に描画する。

    Args:
        duckdb_conn:  DuckDB 接続（read_only=True 推奨）。backtest_runs を参照する。
        sqlite_conn:  SQLite 接続（monitoring.db）。ai_wizard_messages を読み書きする。
        duckdb_path:  subprocess に渡す DuckDB ファイルパス。
        config_path:  strategy_config.yaml の Path。config_manager に渡す。
    """
    if "wizard_session_id" not in st.session_state:
        st.session_state["wizard_session_id"] = str(uuid.uuid4())
    session_id: str = st.session_state["wizard_session_id"]

    db = MonitoringDB(sqlite_conn)

    api_key = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        st.error(
            "OPENAI_API_KEY が設定されていません。"
            "環境変数または st.secrets に設定してください。"
        )
        return

    if st.button("🗑 履歴クリア", key="wizard_clear"):
        db.clear_wizard_messages(session_id)
        st.session_state["wizard_session_id"] = str(uuid.uuid4())
        st.rerun()

    session_id = st.session_state["wizard_session_id"]

    prev_run_id = _load_prev_run_id(duckdb_conn)
    summary = load_latest_summary(duckdb_conn)
    context = summary if summary is not None else _NO_DATA_CONTEXT
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(context=context)

    history = db.load_wizard_messages(session_id)
    for msg in history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 保留中の提案または適用済み状態があれば param_review を常時表示
    if st.session_state.get("param_review_suggested") or st.session_state.get(
        "param_review_applied"
    ):
        render_param_review(
            suggested_params=st.session_state.get("param_review_suggested", {}),
            config_path=config_path,
            duckdb_path=duckdb_path,
            prev_run_id=prev_run_id,
        )

    user_input = st.chat_input("KabuSysの戦略について質問してください")
    if not user_input:
        return

    with st.chat_message("user"):
        st.write(user_input)
    db.save_wizard_message(session_id, "user", user_input)

    client = OpenAI(api_key=api_key)
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_input})

    try:
        with st.chat_message("assistant"):
            response_text = st.write_stream(_stream_openai_response(client, messages))
        if response_text:
            db.save_wizard_message(session_id, "assistant", str(response_text))
            suggested = extract_params(str(response_text))
            if suggested:
                st.session_state["param_review_suggested"] = suggested
                st.rerun()
    except Exception:
        _logger.exception(
            "OpenAI API 呼び出しに失敗しました (session_id=%s)", session_id
        )
        st.error(
            "OpenAI API の呼び出しに失敗しました。しばらく経ってから再度お試しください。"
        )
```

- [ ] **Step 3: 既存テストを新しいシグネチャに合わせて更新する**

`tests/test_ai_wizard.py` 内の全 `mod.render(wizard_duckdb, wizard_sqlite)` 呼び出しを以下のように置き換える（4 か所）:

```python
mod.render(
    wizard_duckdb,
    wizard_sqlite,
    duckdb_path=Path("data/kabusys.duckdb"),
    config_path=Path("config/strategy_config.yaml"),
)
```

また、ファイル先頭の import に `from pathlib import Path` を追加する。

さらに、`TestRenderWithApiKey::test_saves_user_and_assistant_to_sqlite` で `mock_st.write_stream.return_value` がプレーンテキスト（JSON ブロックなし）を返すため `extract_params` は None を返す。`st.rerun` が呼ばれないことを確認するアサーションを追加する:

```python
# レスポンスに JSON ブロックがないので rerun は呼ばれない
mock_st.rerun.assert_not_called()
```

- [ ] **Step 4: 新規テストケースを追加する**

`TestRenderWithApiKey` クラスの末尾に以下を追加する:

```python
    def test_suggested_params_stored_in_session_state(self, wizard_duckdb, wizard_sqlite):
        """AI 返答に JSON ブロックが含まれる場合、param_review_suggested が session_state に設定される。"""
        import kabusys.monitoring.components.ai_wizard as mod

        state: dict = {}
        mock_st = _make_st_mock(session_state=state)
        mock_st.chat_input.return_value = "ATRを改善してほしい"
        mock_st.write_stream.return_value = (
            "ATR乗数を2.5にすることを提案します。\n"
            "```json\n{\"trailing_stop_atr_mult\": 2.5}\n```"
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(mod, "st", mock_st):
                with patch(
                    "kabusys.monitoring.components.ai_wizard._stream_openai_response",
                    return_value=iter([]),
                ):
                    with patch("kabusys.monitoring.components.ai_wizard.OpenAI"):
                        with patch(
                            "kabusys.monitoring.components.ai_wizard.render_param_review"
                        ):
                            mod.render(
                                wizard_duckdb,
                                wizard_sqlite,
                                duckdb_path=Path("data/kabusys.duckdb"),
                                config_path=Path("config/strategy_config.yaml"),
                            )

        assert state.get("param_review_suggested") == {"trailing_stop_atr_mult": 2.5}
        mock_st.rerun.assert_called()

    def test_no_json_block_does_not_set_suggested(self, wizard_duckdb, wizard_sqlite):
        """AI 返答に JSON ブロックがない場合、param_review_suggested は設定されない。"""
        import kabusys.monitoring.components.ai_wizard as mod

        state: dict = {}
        mock_st = _make_st_mock(session_state=state)
        mock_st.chat_input.return_value = "現状維持でいいです"
        mock_st.write_stream.return_value = "現状のパラメータで問題ありません。"

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(mod, "st", mock_st):
                with patch(
                    "kabusys.monitoring.components.ai_wizard._stream_openai_response",
                    return_value=iter([]),
                ):
                    with patch("kabusys.monitoring.components.ai_wizard.OpenAI"):
                        mod.render(
                            wizard_duckdb,
                            wizard_sqlite,
                            duckdb_path=Path("data/kabusys.duckdb"),
                            config_path=Path("config/strategy_config.yaml"),
                        )

        assert "param_review_suggested" not in state
        mock_st.rerun.assert_not_called()
```

- [ ] **Step 5: 全テストがパスすることを確認する**

```bash
pytest tests/test_ai_wizard.py -v
```

Expected: 10 tests PASSED

- [ ] **Step 6: コミットする**

```bash
git add src/kabusys/monitoring/components/ai_wizard.py tests/test_ai_wizard.py
git commit -m "feat: ai_wizard — システムプロンプト更新・param_review 統合 (Issue #279)"
```

---

## Task 5: `10_Strategy_Lab.py` 更新 — `render_wizard()` 引数追加

**Files:**
- Modify: `src/kabusys/monitoring/pages/10_Strategy_Lab.py:79-85`

- [ ] **Step 1: `10_Strategy_Lab.py` の `render_wizard` 呼び出しを更新する**

`src/kabusys/monitoring/pages/10_Strategy_Lab.py` の `with tab_copilot:` ブロックを以下のように変更する:

変更前:
```python
    with tab_copilot:
        sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
        try:
            init_monitoring_db(sqlite_conn)
            render_wizard(conn, sqlite_conn)
        finally:
            sqlite_conn.close()
```

変更後:
```python
    with tab_copilot:
        sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
        try:
            init_monitoring_db(sqlite_conn)
            render_wizard(
                conn,
                sqlite_conn,
                duckdb_path=settings.duckdb_path,
                config_path=Path("config/strategy_config.yaml"),
            )
        finally:
            sqlite_conn.close()
```

また、ファイル先頭の import に `from pathlib import Path` を追加する（未追加の場合）。

- [ ] **Step 2: 全テストスイートがパスすることを確認する**

```bash
pytest tests/ -x -q
```

Expected: 全テスト PASSED（0 failures）

- [ ] **Step 3: コミットする**

```bash
git add src/kabusys/monitoring/pages/10_Strategy_Lab.py
git commit -m "feat: Strategy Lab — render_wizard に duckdb_path / config_path を追加 (Issue #279)"
```

---

## Task 6: ドキュメント更新

**Files:**
- Modify: `documents/08_Operations/TODO_AI_TuningWizard.md`
- Modify: `documents/08_Operations/Monitoring.md`

- [ ] **Step 1: `TODO_AI_TuningWizard.md` を更新する**

`documents/08_Operations/TODO_AI_TuningWizard.md` の Phase 4 セクションを以下のように更新する:

```markdown
## Phase 4: パラメータ自動反映・バックテスト再実行ループ（Issue #279, 2026-05-10）

**✅ 実装済み**

### 実装ファイル

| ファイル | 内容 |
|---|---|
| `src/kabusys/ai/param_extractor.py` | AI 返答から JSON ブロック抽出・ホワイトリスト検証 |
| `src/kabusys/ai/config_manager.py` | strategy_config.yaml バックアップ・適用・ロールバック |
| `src/kabusys/monitoring/components/param_review.py` | Streamlit: 確認→適用→subprocess→比較 |

### 変更ファイル

| ファイル | 内容 |
|---|---|
| `src/kabusys/monitoring/components/ai_wizard.py` | システムプロンプト更新（JSON ブロック出力指示追加）・`duckdb_path`/`config_path` 引数追加・param_review 統合 |
| `src/kabusys/monitoring/pages/10_Strategy_Lab.py` | `render_wizard()` に `duckdb_path`/`config_path` 追加 |
```

- [ ] **Step 2: `Monitoring.md` の Strategy Lab 行にパラメータ適用機能を追記する**

`documents/08_Operations/Monitoring.md` の Strategy Lab の表示内容欄を以下のように更新する:

```
市場レジーム・AI スコア・シグナル推移・🤖 AI Co-Pilot チャット（パラメータ提案・適用・バックテスト再実行・比較）
```

- [ ] **Step 3: コミットする**

```bash
git add documents/08_Operations/TODO_AI_TuningWizard.md documents/08_Operations/Monitoring.md
git commit -m "docs: AI Co-Pilot Phase 4 (Issue #279) 実装反映 — Monitoring.md / TODO 更新"
```
