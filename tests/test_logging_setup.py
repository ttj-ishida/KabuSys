# tests/test_logging_setup.py
"""logging_setup モジュールのユニットテスト（Issue #55 / #308 / #309）"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from unittest.mock import patch

import pytest

from kabusys.utils.logging_setup import _TeeWriter, log_run_end, log_run_start, setup_logging


@pytest.fixture(autouse=True)
def reset_root_logger():
    """各テスト後にルートロガーのハンドラとレベルをリセットしてテスト間の独立性を保つ。"""
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    yield
    # capture_stdio テストが sys.stdout/stderr を置き換えた場合に復元する
    sys.stdout = orig_stdout
    sys.stderr = orig_stderr
    # ルートロガーをリセット
    root = logging.getLogger()
    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)
    root.setLevel(logging.WARNING)
    # stdio キャプチャ用ロガーをリセット
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if "kabusys.stdio" in name:
            lg = logging.getLogger(name)
            for h in list(lg.handlers):
                h.close()
                lg.removeHandler(h)


class TestSetupLogging:
    def test_creates_log_file(self, tmp_path):
        """setup_logging() でローテーションログファイルが作成される。"""
        setup_logging(app_name="test_app", log_dir=tmp_path)
        assert (tmp_path / "test_app.log").exists()

    def test_creates_run_log_file(self, tmp_path):
        """setup_logging() で実行単位ログファイル（YYYYMMDD_HHMMSS_PID サフィックス）が作成される。"""
        import os
        import re

        run_log = setup_logging(app_name="test_app", log_dir=tmp_path)
        assert run_log is not None
        assert run_log.exists()
        assert run_log.name.startswith("test_app_")
        assert run_log.suffix == ".log"
        assert re.search(r"_\d{8}_\d{6}_\d+\.log$", run_log.name), (
            "ファイル名に YYYYMMDD_HHMMSS_PID が含まれること"
        )
        assert str(os.getpid()) in run_log.name

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
        """StreamHandler と TimedRotatingFileHandler (Safe 実装) と FileHandler の3つが追加される。"""
        from kabusys.utils.logging_setup import _WindowsSafeRotatingFileHandler

        setup_logging(app_name="test", log_dir=tmp_path)
        root = logging.getLogger()
        assert any(type(h) is logging.StreamHandler for h in root.handlers)
        assert any(isinstance(h, _WindowsSafeRotatingFileHandler) for h in root.handlers)
        assert any(type(h) is logging.FileHandler for h in root.handlers)

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
        """_WindowsSafeRotatingFileHandler 作成失敗時も StreamHandler + 実行単位 FileHandler で継続する。"""
        with patch(
            "kabusys.utils.logging_setup._WindowsSafeRotatingFileHandler",
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

    def test_log_run_end_accepts_naive_datetime(self, caplog):
        """log_run_end() に naive datetime を渡しても TypeError にならない。"""
        started = datetime.now()  # naive (tzinfo=None)
        with caplog.at_level(logging.INFO, logger=self._LOGGER):
            log_run_end("my_job", status="success", started_at=started)
        assert any("duration=" in r.message for r in caplog.records)


class TestTeeWriter:
    """_TeeWriter の単体テスト（Issue #309）"""

    def test_write_forwards_to_orig_stream(self):
        """write() はオリジナルストリームへ書き込む。"""
        calls = []

        class FakeStream:
            encoding = "utf-8"

            def write(self, msg):
                calls.append(msg)
                return len(msg)

            def flush(self):
                pass

        logged = []
        tee = _TeeWriter(FakeStream(), logged.append)
        tee.write("hello\n")
        assert "hello\n" in calls

    def test_write_calls_logger_fn_on_newline(self):
        """改行区切りで logger_fn が呼ばれる。"""
        logged = []
        orig = type(
            "S", (), {"write": lambda s, m: len(m), "flush": lambda s: None, "encoding": "utf-8"}
        )()
        tee = _TeeWriter(orig, logged.append)
        tee.write("line1\nline2\n")
        assert "line1" in logged
        assert "line2" in logged

    def test_write_buffers_partial_lines(self):
        """改行なしの書き込みはバッファリングされ logger_fn を呼ばない。"""
        logged = []
        orig = type(
            "S", (), {"write": lambda s, m: len(m), "flush": lambda s: None, "encoding": "utf-8"}
        )()
        tee = _TeeWriter(orig, logged.append)
        tee.write("partial")
        assert logged == []

    def test_flush_drains_buffer(self):
        """flush() がバッファ内の残行を logger_fn に流す。"""
        logged = []
        orig = type(
            "S", (), {"write": lambda s, m: len(m), "flush": lambda s: None, "encoding": "utf-8"}
        )()
        tee = _TeeWriter(orig, logged.append)
        tee.write("partial")
        tee.flush()
        assert "partial" in logged

    def test_write_skips_empty_lines(self):
        """空行（改行のみ）では logger_fn を呼ばない。"""
        logged = []
        orig = type(
            "S", (), {"write": lambda s, m: len(m), "flush": lambda s: None, "encoding": "utf-8"}
        )()
        tee = _TeeWriter(orig, logged.append)
        tee.write("\n")
        assert logged == []

    def test_encoding_attribute(self):
        """encoding 属性がオリジナルストリームの値を返す。"""
        orig = type(
            "S", (), {"encoding": "utf-16", "write": lambda s, m: len(m), "flush": lambda s: None}
        )()
        tee = _TeeWriter(orig, lambda x: None)
        assert tee.encoding == "utf-16"

    def test_cr_treated_as_line_delimiter(self):
        """`\\r` だけの行区切りでも logger_fn が呼ばれる（プログレスバー対応）。"""
        logged = []
        orig = type(
            "S", (), {"write": lambda s, m: len(m), "flush": lambda s: None, "encoding": "utf-8"}
        )()
        tee = _TeeWriter(orig, logged.append)
        tee.write("step1\rstep2\r")
        assert "step1" in logged
        assert "step2" in logged

    def test_reentrancy_guard_prevents_recursion(self):
        """logger_fn 内から再び write() を呼んでも再帰ループしない。"""
        orig = type(
            "S", (), {"write": lambda s, m: len(m), "flush": lambda s: None, "encoding": "utf-8"}
        )()
        call_count = []

        def recursive_logger(msg):
            call_count.append(msg)
            # logger_fn 内から tee.write を呼ぶ（FileHandler 障害時の handleError 相当）
            tee.write("inner\n")

        tee = _TeeWriter(orig, recursive_logger)
        tee.write("outer\n")
        # recursive_logger は1回だけ呼ばれ、内部の tee.write は再入防止でスキップされる
        assert len(call_count) == 1
        assert call_count[0] == "outer"


class TestCaptureStdio:
    """capture_stdio=True の統合テスト（Issue #309）"""

    def test_stdout_replaced_with_tee_writer(self, tmp_path):
        """capture_stdio=True で sys.stdout が _TeeWriter に置き換えられる。"""
        setup_logging(app_name="test", log_dir=tmp_path, capture_stdio=True)
        assert isinstance(sys.stdout, _TeeWriter)

    def test_stderr_replaced_with_tee_writer(self, tmp_path):
        """capture_stdio=True で sys.stderr が _TeeWriter に置き換えられる。"""
        setup_logging(app_name="test", log_dir=tmp_path, capture_stdio=True)
        assert isinstance(sys.stderr, _TeeWriter)

    def test_stdout_unchanged_when_capture_false(self, tmp_path):
        """capture_stdio=False（デフォルト）では sys.stdout は変わらない。"""
        orig = sys.stdout
        setup_logging(app_name="test", log_dir=tmp_path)
        assert sys.stdout is orig

    def test_print_captured_to_run_log(self, tmp_path):
        """capture_stdio=True でのprint()出力が実行単位ログファイルに記録される。"""
        run_log = setup_logging(app_name="test", log_dir=tmp_path, capture_stdio=True)
        assert run_log is not None
        print("hello from print")
        sys.stdout.flush()
        content = run_log.read_text(encoding="utf-8")
        assert "hello from print" in content

    def test_stderr_captured_to_run_log(self, tmp_path):
        """capture_stdio=True での sys.stderr 出力が実行単位ログファイルに記録される。"""
        run_log = setup_logging(app_name="test", log_dir=tmp_path, capture_stdio=True)
        assert run_log is not None
        sys.stderr.write("err output\n")
        sys.stderr.flush()
        content = run_log.read_text(encoding="utf-8")
        assert "err output" in content

    def test_second_setup_call_no_nested_tee(self, tmp_path):
        """2回目の setup_logging でも TeeWriter の二重ネストにならない。"""
        setup_logging(app_name="test", log_dir=tmp_path, capture_stdio=True)
        setup_logging(app_name="test", log_dir=tmp_path, capture_stdio=True)
        assert not isinstance(sys.stdout._orig, _TeeWriter)  # type: ignore[union-attr]

    def test_capture_stdio_false_by_default(self, tmp_path):
        """capture_stdio 引数のデフォルトは False。"""
        orig = sys.stdout
        setup_logging(app_name="test", log_dir=tmp_path)
        assert sys.stdout is orig

    def test_high_log_level_still_captures_print(self, tmp_path):
        """LOG_LEVEL=ERROR 設定時も print() 出力は実行単位ログに記録される。"""
        run_log = setup_logging(
            app_name="test", log_dir=tmp_path, level="ERROR", capture_stdio=True
        )
        assert run_log is not None
        print("captured despite error level")
        sys.stdout.flush()
        content = run_log.read_text(encoding="utf-8")
        assert "captured despite error level" in content

    def test_flush_clears_whitespace_only_buffer(self):
        """flush() で空白のみのバッファを呼び出してもバッファがクリアされ logger_fn を呼ばない。"""
        logged = []
        orig = type(
            "S", (), {"write": lambda s, m: len(m), "flush": lambda s: None, "encoding": "utf-8"}
        )()
        tee = _TeeWriter(orig, logged.append)
        tee.write("   ")  # whitespace only, no newline
        tee.flush()
        assert logged == []
        # バッファがクリアされていること
        assert tee._buf == ""


class TestWindowsSafeRotatingFileHandler:
    def test_dorollover_permission_error_is_suppressed(self, tmp_path):
        """doRollover() が PermissionError を raise しても例外が外に漏れない。"""
        from unittest.mock import patch

        from kabusys.utils.logging_setup import _WindowsSafeRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_text("initial", encoding="utf-8")
        handler = _WindowsSafeRotatingFileHandler(str(log_file), when="midnight", backupCount=1)
        try:
            with patch.object(
                TimedRotatingFileHandler,
                "doRollover",
                side_effect=PermissionError("[WinError 32] ファイルが使用中"),
            ):
                handler.doRollover()  # 例外が漏れないこと
        finally:
            handler.close()

    def test_dorollover_success_still_works(self, tmp_path):
        """PermissionError がない場合は親クラスの doRollover が呼ばれる。"""
        from unittest.mock import patch

        from kabusys.utils.logging_setup import _WindowsSafeRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_text("initial", encoding="utf-8")
        handler = _WindowsSafeRotatingFileHandler(str(log_file), when="midnight", backupCount=1)
        try:
            called = []
            with patch.object(
                TimedRotatingFileHandler,
                "doRollover",
                side_effect=lambda *a, **kw: called.append(True),
            ):
                handler.doRollover()
            assert called == [True]
        finally:
            handler.close()

    def test_setup_logging_uses_safe_handler(self, tmp_path):
        """setup_logging() が _WindowsSafeRotatingFileHandler を使う。"""
        from kabusys.utils.logging_setup import _WindowsSafeRotatingFileHandler

        setup_logging(app_name="test_safe", log_dir=tmp_path)
        root = logging.getLogger()
        rotating_handlers = [
            h for h in root.handlers if isinstance(h, _WindowsSafeRotatingFileHandler)
        ]
        assert len(rotating_handlers) == 1
