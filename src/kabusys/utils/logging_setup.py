# src/kabusys/utils/logging_setup.py
"""logging_setup.py — ログ設定ユーティリティ。

StreamHandler（コンソール stdout）、TimedRotatingFileHandler（日次ローテーション）、
FileHandler（実行単位のログファイル）をルートロガーに設定する。
全起動スクリプトから呼び出して統一的なログ管理を実現する。

使い方:
    from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

    setup_logging(app_name="execution", capture_stdio=True)

    def main() -> None:
        started_at = datetime.now(timezone.utc)
        log_run_start("execution")
        ...
        log_run_end("execution", status="success", started_at=started_at)
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Callable

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_LOG_LEVEL = "INFO"
_BACKUP_COUNT = 30  # 日次ローテーション・30日分保持


class _WindowsSafeRotatingFileHandler(TimedRotatingFileHandler):
    """Windows で別プロセスがログファイルをロックしている場合のローテーション失敗を吸収する。

    TimedRotatingFileHandler.doRollover() は Windows で PermissionError (WinError 32) を
    送出することがある。これを握り潰して書き込みを継続し、ノイズログを防ぐ。
    """

    def doRollover(self) -> None:
        try:
            super().doRollover()
        except PermissionError as exc:
            import sys as _sys
            print(
                f"WARNING: ログローテーション失敗 (ファイルが別プロセスに使用中のためスキップ):"
                f" {self.baseFilename} — {exc}",
                file=_sys.__stderr__,
            )


logger = logging.getLogger(__name__)


_LINE_SEP_RE = __import__("re").compile(r"\r\n|\r|\n")


class _TeeWriter:
    """sys.stdout / sys.stderr をオリジナルストリームとロガーの両方に出力する tee ライター。

    write() で受け取ったメッセージを:
      1. オリジナルストリームへ書き込む（コンソール出力を維持）
      2. \\n / \\r\\n / \\r 区切りで logger_fn を呼び出してログファイルにも記録する
         （プログレスバー等の CR 更新もバッファに溜まらず都度ログ化される）

    部分行（区切り文字なしの断片）はバッファリングし flush() 時に書き出す。
    logger_fn 内でハンドラ障害が起きた場合の再帰ループは再入防止フラグで防ぐ。
    """

    def __init__(self, orig_stream: Any, logger_fn: Callable[[str], None]) -> None:
        self._orig = orig_stream
        self._logger_fn = logger_fn
        self._buf = ""
        self._local = threading.local()

    def _safe_log(self, msg: str) -> None:
        """再帰ループを防ぎつつ logger_fn を呼ぶ。

        FileHandler の emit 失敗 → handleError が sys.stderr に書く → _TeeWriter.write
        → stderr_logger.warning → 同じハンドラで再失敗、という無限再帰を防ぐ。
        """
        if getattr(self._local, "active", False):
            return
        self._local.active = True
        try:
            self._logger_fn(msg)
        finally:
            self._local.active = False

    def write(self, msg: str) -> int:
        try:
            n = self._orig.write(msg)
        except UnicodeEncodeError:
            enc = getattr(self._orig, "encoding", None) or "utf-8"
            safe = msg.encode(enc, errors="replace").decode(enc)
            n = self._orig.write(safe)
        self._buf += msg
        parts = _LINE_SEP_RE.split(self._buf)
        for line in parts[:-1]:
            if line.strip():
                self._safe_log(line)
        self._buf = parts[-1]
        return n if n is not None else len(msg)

    def writelines(self, lines: Any) -> None:
        for line in lines:
            self.write(line)

    def flush(self) -> None:
        buf, self._buf = self._buf, ""
        stripped = buf.rstrip("\r\n")
        if stripped.strip():
            self._safe_log(stripped)
        self._orig.flush()

    @property
    def encoding(self) -> str:
        return getattr(self._orig, "encoding", "utf-8")

    @property
    def errors(self) -> str:
        return getattr(self._orig, "errors", "replace")

    def isatty(self) -> bool:
        return bool(getattr(self._orig, "isatty", lambda: False)())

    def fileno(self) -> int:
        fn = getattr(self._orig, "fileno", None)
        if fn is None:
            raise OSError("fileno not supported")
        return fn()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._orig, name)


def setup_logging(
    app_name: str = "kabusys",
    log_dir: Path | None = None,
    level: str | int | None = None,
    capture_stdio: bool = False,
) -> Path | None:
    """ロギングを設定する。

    ルートロガーに以下の3ハンドラを設定する:
      - StreamHandler: コンソール（stdout）出力
      - TimedRotatingFileHandler: ``<log_dir>/<app_name>.log`` への日次ローテーション出力
      - FileHandler: ``<log_dir>/<app_name>_YYYYMMDD_HHMMSS.log`` への実行単位出力

    既にハンドラが設定されている場合は一度クリアしてから再設定する（二重設定防止）。

    ログレベルの解決順:
      1. 引数 ``level``
      2. 環境変数 ``LOG_LEVEL``
      3. デフォルト ``"INFO"``

    ログディレクトリの解決順:
      1. 引数 ``log_dir``
      2. 環境変数 ``LOG_DIR``
      3. デフォルト ``"logs/"``

    Args:
        app_name:      ログファイル名のプレフィックス（例: ``"execution"`` → ``logs/execution.log``）。
        log_dir:       ログファイルの保存ディレクトリ。None の場合は上記解決順を使用。
        level:         ログレベル文字列（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）または
                       整数値（例: ``logging.DEBUG``）。None の場合は上記解決順を使用。
        capture_stdio: True の場合、sys.stdout / sys.stderr を ``_TeeWriter`` で置き換え、
                       print() や C拡張ライブラリの出力も実行単位ログファイルに記録する。
                       コンソール出力は従来通り維持（tee 動作）。

    Returns:
        実行単位ログファイルのパス（``<app_name>_YYYYMMDD_HHMMSS.log``）。
        ファイルハンドラの作成に失敗した場合は None を返す。
    """
    # ログレベル解決（int / str の両形式を受け入れる）
    if isinstance(level, int):
        numeric_level = level
    else:
        resolved_level_str = (level or os.environ.get("LOG_LEVEL", _DEFAULT_LOG_LEVEL)).upper()
        numeric_level = getattr(logging, resolved_level_str, logging.INFO)

    # ログディレクトリ解決・作成
    # 作成失敗時は FileHandler をスキップして StreamHandler のみで継続する
    resolved_dir = log_dir or Path(os.environ.get("LOG_DIR", str(_DEFAULT_LOG_DIR)))
    _dir_ok = True
    try:
        resolved_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        _dir_ok = False
        # ルートロガー未設定のため print で警告を出す
        print(
            f"WARNING: ログディレクトリの作成に失敗しました。ファイル出力を無効化します: {e}",
            file=sys.stderr,
        )

    # ルートロガーにレベルを設定（既存ハンドラを flush/close してから削除）
    root = logging.getLogger()
    root.setLevel(numeric_level)
    for h in list(root.handlers):
        try:
            h.flush()
        except Exception:
            pass
        try:
            h.close()
        except Exception:
            pass
        root.removeHandler(h)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # StreamHandler（コンソール stdout 出力）
    # stderr ではなく stdout を使用: Task Scheduler/cron から起動する際に
    # stdout/stderr を一本化してリダイレクトするため
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(numeric_level)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    run_log_file: Path | None = None

    if _dir_ok:
        # TimedRotatingFileHandler（日次ローテーション・30日保持）
        # 全実行ログを集約したファイル。`tail -f` での監視に適する。
        log_file = resolved_dir / f"{app_name}.log"
        try:
            file_handler = _WindowsSafeRotatingFileHandler(
                log_file,
                when="midnight",
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except Exception as e:
            logger.warning(
                "ファイルハンドラの作成に失敗しました。コンソール出力のみ有効です: %s",
                e,
            )

        # FileHandler（実行単位ログファイル）
        # 実行ごとに独立したファイルを生成し、特定の実行ログを追跡しやすくする。
        # UTC + PID でファイル名を一意化し、同一秒の並行起動での衝突を防ぐ。
        run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_log_file = resolved_dir / f"{app_name}_{run_ts}_{os.getpid()}.log"
        try:
            run_file_handler = logging.FileHandler(run_log_file, encoding="utf-8")
            run_file_handler.setLevel(numeric_level)
            run_file_handler.setFormatter(formatter)
            root.addHandler(run_file_handler)
        except Exception as e:
            logger.warning(
                "実行単位ファイルハンドラの作成に失敗しました: %s",
                e,
            )
            run_log_file = None

    logger.debug(
        "ロギングを設定しました: level=%s, rotating=%s, run_log=%s",
        logging.getLevelName(numeric_level),
        resolved_dir / f"{app_name}.log" if _dir_ok else None,
        run_log_file,
    )

    if capture_stdio and run_log_file is not None:
        _install_stdio_tee(app_name, run_log_file, formatter)

    return run_log_file


def _install_stdio_tee(
    app_name: str,
    run_log_file: Path,
    formatter: logging.Formatter,
) -> None:
    """sys.stdout / sys.stderr を _TeeWriter に置き換えて run_log_file にも出力する。

    stdout / stderr それぞれに専用の FileHandler（append mode）を作成して
    ``kabusys.stdio.<app_name>.stdout`` / ``kabusys.stdio.<app_name>.stderr``
    ロガーに登録する。これらのロガーは propagate=False のため
    root ロガーの StreamHandler には流れず、コンソール二重出力が発生しない。

    既に _TeeWriter に置き換え済みの場合はスキップする（二重ネスト防止）。
    """
    stdout_logger = logging.getLogger(f"kabusys.stdio.{app_name}.stdout")
    stderr_logger = logging.getLogger(f"kabusys.stdio.{app_name}.stderr")

    for lg in (stdout_logger, stderr_logger):
        # DEBUG に固定して stdio ロガー自身はレベルフィルタをかけない。
        # NOTSET だと getEffectiveLevel() が親チェーンを辿り root の ERROR が適用されるため、
        # LOG_LEVEL=ERROR 設定時に print() 出力が消えてしまう。
        lg.setLevel(logging.DEBUG)
        lg.propagate = False
        for h in list(lg.handlers):
            h.close()
            lg.removeHandler(h)

    # 実行単位ログファイルへの専用 FileHandler（append）
    # root ロガーの run_file_handler とは別オブジェクトで同一ファイルに追記する
    try:
        fh_out = logging.FileHandler(run_log_file, mode="a", encoding="utf-8")
        fh_out.setLevel(logging.DEBUG)
        fh_out.setFormatter(formatter)
        stdout_logger.addHandler(fh_out)
    except Exception as e:
        logger.warning("stdout キャプチャ用ハンドラの作成に失敗しました: %s", e)
        return

    try:
        fh_err = logging.FileHandler(run_log_file, mode="a", encoding="utf-8")
        fh_err.setLevel(logging.DEBUG)
        fh_err.setFormatter(formatter)
        stderr_logger.addHandler(fh_err)
    except Exception as e:
        logger.warning("stderr キャプチャ用ハンドラの作成に失敗しました: %s", e)

    # sys.stdout / sys.stderr を使用（sys.__stdout__ ではなく）:
    # pytest capsys など他フレームワークのラッパーを保持するため
    if not isinstance(sys.stdout, _TeeWriter):
        sys.stdout = _TeeWriter(sys.stdout, stdout_logger.info)
    if not isinstance(sys.stderr, _TeeWriter):
        sys.stderr = _TeeWriter(sys.stderr, stderr_logger.warning)


def log_run_start(app_name: str) -> None:
    """実行開始マーカーをログに出力する。

    Args:
        app_name: スクリプト名（例: ``"data_update"``）。
    """
    logging.getLogger(__name__).info("===== %s START (PID=%d) =====", app_name, os.getpid())


def log_run_end(app_name: str, status: str, started_at: datetime) -> None:
    """実行終了マーカーをログに出力する。

    Args:
        app_name:   スクリプト名（例: ``"data_update"``）。
        status:     終了ステータス（``"success"`` / ``"warning"`` / ``"failed"``）。
        started_at: 実行開始時刻（``datetime.now(timezone.utc)``）。
    """
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    duration = (datetime.now(timezone.utc) - started_at).total_seconds()
    logging.getLogger(__name__).info(
        "===== %s END status=%s duration=%.1fs =====", app_name, status, duration
    )
