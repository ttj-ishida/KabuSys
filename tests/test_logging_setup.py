# tests/test_logging_setup.py
"""logging_setup モジュールのユニットテスト（Issue #55 / #308）"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from unittest.mock import patch

import pytest

from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging


@pytest.fixture(autouse=True)
def reset_root_logger():
    """各テスト後にルートロガーのハンドラとレベルをリセットしてテスト間の独立性を保つ。"""
    yield
    root = logging.getLogger()
    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)
    root.setLevel(logging.WARNING)


class TestSetupLogging:
    def test_creates_log_file(self, tmp_path):
        """setup_logging() でローテーションログファイルが作成される。"""
        setup_logging(app_name="test_app", log_dir=tmp_path)
        assert (tmp_path / "test_app.log").exists()

    def test_creates_run_log_file(self, tmp_path):
        """setup_logging() で実行単位ログファイル（YYYYMMDD_HHMMSS サフィックス）が作成される。"""
        run_log = setup_logging(app_name="test_app", log_dir=tmp_path)
        assert run_log is not None
        assert run_log.exists()
        assert run_log.name.startswith("test_app_")
        assert run_log.suffix == ".log"

    def test_returns_run_log_path(self, tmp_path):
        """setup_logging() は実行単位ログファイルのパスを返す。"""
        run_log = setup_logging(app_name="myapp", log_dir=tmp_path)
        assert run_log is not None
        assert run_log.parent == tmp_path
        assert run_log.name.startswith("myapp_")

    def test_returns_none_when_dir_fails(self, tmp_path):
        """ディレクトリ作成失敗時は None を返す。"""
        with patch.object(
            type(tmp_path), "mkdir", side_effect=PermissionError("permission denied")
        ):
            run_log = setup_logging(app_name="test", log_dir=tmp_path)
        assert run_log is None

    def test_creates_log_dir_if_missing(self, tmp_path):
        """存在しないディレクトリは自動作成される。"""
        log_dir = tmp_path / "subdir" / "logs"
        setup_logging(app_name="test", log_dir=log_dir)
        assert log_dir.exists()
        assert (log_dir / "test.log").exists()

    def test_stream_and_file_handlers_added(self, tmp_path):
        """StreamHandler と TimedRotatingFileHandler と FileHandler の3つが追加される。"""
        setup_logging(app_name="test", log_dir=tmp_path)
        root = logging.getLogger()
        handler_types = {type(h) for h in root.handlers}
        assert logging.StreamHandler in handler_types
        assert TimedRotatingFileHandler in handler_types
        assert logging.FileHandler in handler_types

    def test_stream_handler_uses_stdout(self, tmp_path):
        """StreamHandler が sys.stdout を使用する。"""
        setup_logging(app_name="test", log_dir=tmp_path)
        root = logging.getLogger()
        stream_handlers = [h for h in root.handlers if type(h) is logging.StreamHandler]
        assert len(stream_handlers) == 1
        assert stream_handlers[0].stream is sys.stdout

    def test_handler_count_is_three(self, tmp_path):
        """ハンドラ数がちょうど3（stream + rotating + run file）。"""
        setup_logging(app_name="test", log_dir=tmp_path)
        assert len(logging.getLogger().handlers) == 3

    def test_no_duplicate_handlers_on_second_call(self, tmp_path):
        """2回呼んでもハンドラが重複しない（3個のまま）。"""
        setup_logging(app_name="test", log_dir=tmp_path)
        setup_logging(app_name="test", log_dir=tmp_path)
        assert len(logging.getLogger().handlers) == 3

    def test_log_level_from_argument(self, tmp_path):
        """引数 level が反映される。"""
        setup_logging(app_name="test", log_dir=tmp_path, level="DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_log_level_as_int(self, tmp_path):
        """引数 level に int（例: logging.DEBUG）を渡しても正しく設定される。"""
        setup_logging(app_name="test", log_dir=tmp_path, level=logging.DEBUG)
        assert logging.getLogger().level == logging.DEBUG

    def test_log_level_from_env(self, tmp_path, monkeypatch):
        """環境変数 LOG_LEVEL が反映される。"""
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        setup_logging(app_name="test", log_dir=tmp_path)
        assert logging.getLogger().level == logging.WARNING

    def test_arg_level_takes_precedence_over_env(self, tmp_path, monkeypatch):
        """引数 level が環境変数より優先される。"""
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        setup_logging(app_name="test", log_dir=tmp_path, level="ERROR")
        assert logging.getLogger().level == logging.ERROR

    def test_default_level_is_info(self, tmp_path, monkeypatch):
        """LOG_LEVEL 未設定時のデフォルトは INFO。"""
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        setup_logging(app_name="test", log_dir=tmp_path)
        assert logging.getLogger().level == logging.INFO

    def test_log_dir_from_env(self, tmp_path, monkeypatch):
        """環境変数 LOG_DIR が反映される。"""
        monkeypatch.setenv("LOG_DIR", str(tmp_path))
        setup_logging(app_name="env_test")
        assert (tmp_path / "env_test.log").exists()

    def test_file_handler_rotation_config(self, tmp_path):
        """TimedRotatingFileHandler が midnight/30日保持で設定される。"""
        setup_logging(app_name="test", log_dir=tmp_path)
        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, TimedRotatingFileHandler)]
        assert len(file_handlers) == 1
        fh = file_handlers[0]
        assert fh.when == "MIDNIGHT"
        assert fh.backupCount == 30

    def test_invalid_log_level_falls_back_to_info(self, tmp_path, monkeypatch):
        """無効なログレベルは INFO にフォールバックされる。"""
        monkeypatch.setenv("LOG_LEVEL", "INVALID_LEVEL")
        setup_logging(app_name="test", log_dir=tmp_path)
        assert logging.getLogger().level == logging.INFO

    def test_app_name_used_as_filename(self, tmp_path):
        """app_name がファイル名 "<app_name>.log" に使われる。"""
        setup_logging(app_name="my_service", log_dir=tmp_path)
        assert (tmp_path / "my_service.log").exists()
        assert not (tmp_path / "kabusys.log").exists()

    def test_rotating_handler_failure_still_creates_run_log(self, tmp_path):
        """TimedRotatingFileHandler 作成失敗時も StreamHandler + 実行単位 FileHandler で継続する。"""
        with patch(
            "kabusys.utils.logging_setup.TimedRotatingFileHandler",
            side_effect=OSError("permission denied"),
        ):
            run_log = setup_logging(app_name="test", log_dir=tmp_path)
        root = logging.getLogger()
        # stream + run file handler
        assert len(root.handlers) == 2
        assert any(type(h) is logging.StreamHandler for h in root.handlers)
        assert run_log is not None

    def test_mkdir_failure_falls_back_to_stream_only(self, tmp_path):
        """ログディレクトリ作成失敗時も StreamHandler のみで継続する。"""
        with patch.object(
            type(tmp_path), "mkdir", side_effect=PermissionError("permission denied")
        ):
            setup_logging(app_name="test", log_dir=tmp_path)
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert type(root.handlers[0]) is logging.StreamHandler

    def test_existing_handlers_closed_before_setup(self, tmp_path):
        """2回目の呼び出しで既存ハンドラが close される（ spy で検証）。"""
        setup_logging(app_name="test", log_dir=tmp_path)
        root = logging.getLogger()
        first_handlers = list(root.handlers)

        closed = []

        # 既存ハンドラの close をラップして呼び出しを追跡する
        for h in first_handlers:
            original = h.close

            def make_spy(orig, handler):
                def spy():
                    closed.append(handler)
                    orig()

                return spy

            h.close = make_spy(original, h)

        setup_logging(app_name="test", log_dir=tmp_path)

        assert len(closed) == len(first_handlers)


class TestLogRunBoundaries:
    # setup_logging を呼ばない: caplog は root logger のハンドラを使うが、
    # setup_logging が既存ハンドラを全削除するため caplog のハンドラが消えてしまう。
    # caplog.at_level(..., logger=LOGGER_NAME) でそのロガーのキャプチャレベルだけ設定する。

    _LOGGER = "kabusys.utils.logging_setup"

    def test_log_run_start_emits_start_marker(self, caplog):
        """log_run_start() が START マーカーをログに出力する。"""
        with caplog.at_level(logging.INFO, logger=self._LOGGER):
            log_run_start("my_job")
        assert any("my_job START" in r.message for r in caplog.records)

    def test_log_run_start_includes_pid(self, caplog):
        """log_run_start() のメッセージに PID が含まれる。"""
        import os

        with caplog.at_level(logging.INFO, logger=self._LOGGER):
            log_run_start("my_job")
        combined = " ".join(r.message for r in caplog.records)
        assert str(os.getpid()) in combined

    def test_log_run_end_emits_end_marker(self, caplog):
        """log_run_end() が END マーカーをログに出力する。"""
        started = datetime.now(timezone.utc)
        with caplog.at_level(logging.INFO, logger=self._LOGGER):
            log_run_end("my_job", status="success", started_at=started)
        assert any("my_job END" in r.message for r in caplog.records)

    def test_log_run_end_includes_status(self, caplog):
        """log_run_end() のメッセージにステータスが含まれる。"""
        started = datetime.now(timezone.utc)
        with caplog.at_level(logging.INFO, logger=self._LOGGER):
            log_run_end("my_job", status="failed", started_at=started)
        assert any("status=failed" in r.message for r in caplog.records)

    def test_log_run_end_includes_duration(self, caplog):
        """log_run_end() のメッセージに duration が含まれる。"""
        started = datetime.now(timezone.utc)
        with caplog.at_level(logging.INFO, logger=self._LOGGER):
            log_run_end("my_job", status="success", started_at=started)
        assert any("duration=" in r.message for r in caplog.records)
