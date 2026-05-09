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


class TestComparisonDisplay:
    def test_comparison_rendered_when_new_run_id_set(self, config_file, tmp_path):
        import kabusys.monitoring.components.param_review as mod

        state: dict = {
            "param_review_applied": True,
            "param_review_backup_path": str(tmp_path / "backup.yaml"),
            "param_review_prev_run_id": "prev-001",
            "param_review_new_run_id": "new-001",
        }
        mock_st = _make_st_mock(session_state=state)
        mock_st.date_input.side_effect = [
            __import__("datetime").date(2023, 1, 1),
            __import__("datetime").date(2024, 12, 31),
        ]
        def columns_side_effect(n):
            return [MagicMock() for _ in range(n)]

        mock_st.columns.side_effect = columns_side_effect
        mock_st.button.return_value = False

        prev_metrics = {
            "cagr": 0.123, "sharpe": 1.23, "max_drawdown": -0.185,
            "win_rate": 0.55, "total_trades": 100.0,
        }
        new_metrics = {
            "cagr": 0.141, "sharpe": 1.41, "max_drawdown": -0.162,
            "win_rate": 0.58, "total_trades": 105.0,
        }

        def load_metrics_side_effect(duckdb_path, run_id):
            if run_id == "prev-001":
                return prev_metrics
            if run_id == "new-001":
                return new_metrics
            return None

        with patch.object(mod, "st", mock_st):
            with patch(
                "kabusys.monitoring.components.param_review._load_default_dates",
                return_value=("2023-01-01", "2024-12-31"),
            ):
                with patch(
                    "kabusys.monitoring.components.param_review._load_run_metrics",
                    side_effect=load_metrics_side_effect,
                ):
                    mod.render_param_review(
                        suggested_params={},
                        config_path=config_file,
                        duckdb_path=tmp_path / "test.duckdb",
                        prev_run_id=None,
                    )

        mock_st.subheader.assert_called()
        subheader_calls = [str(c) for c in mock_st.subheader.call_args_list]
        assert any("比較" in c for c in subheader_calls)
