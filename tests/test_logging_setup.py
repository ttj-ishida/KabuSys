# tests/test_logging_setup.py
"""logging_setup モジュールのユニットテスト（Issue #55）"""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler

import pytest

from kabusys.utils.logging_setup import setup_logging


@pytest.fixture(autouse=True)
def reset_root_logger():
    """各テスト後にルートロガーのハンドラをリセットする。"""
    yield
    root = logging.getLogger()
    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)


class TestSetupLogging:
    def test_creates_log_file(self, tmp_path):
        """setup_logging() でログファイルが作成される。"""
        setup_logging(app_name="test_app", log_dir=tmp_path)
        assert (tmp_path / "test_app.log").exists()

    def test_creates_log_dir_if_missing(self, tmp_path):
        """存在しないディレクトリは自動作成される。"""
        log_dir = tmp_path / "subdir" / "logs"
        setup_logging(app_name="test", log_dir=log_dir)
        assert log_dir.exists()
        assert (log_dir / "test.log").exists()

    def test_stream_and_file_handlers_added(self, tmp_path):
        """StreamHandler と TimedRotatingFileHandler の2つが追加される。"""
        setup_logging(app_name="test", log_dir=tmp_path)
        root = logging.getLogger()
        handler_types = {type(h) for h in root.handlers}
        assert logging.StreamHandler in handler_types
        assert TimedRotatingFileHandler in handler_types

    def test_handler_count_is_two(self, tmp_path):
        """ハンドラ数がちょうど2（stream + file）。"""
        setup_logging(app_name="test", log_dir=tmp_path)
        assert len(logging.getLogger().handlers) == 2

    def test_no_duplicate_handlers_on_second_call(self, tmp_path):
        """2回呼んでもハンドラが重複しない。"""
        setup_logging(app_name="test", log_dir=tmp_path)
        setup_logging(app_name="test", log_dir=tmp_path)
        assert len(logging.getLogger().handlers) == 2

    def test_log_level_from_argument(self, tmp_path):
        """引数 level が反映される。"""
        setup_logging(app_name="test", log_dir=tmp_path, level="DEBUG")
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
