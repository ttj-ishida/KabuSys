# src/kabusys/utils/logging_setup.py
"""logging_setup.py — ログ設定ユーティリティ。

StreamHandler（コンソール stdout）、TimedRotatingFileHandler（日次ローテーション）、
FileHandler（実行単位のログファイル）をルートロガーに設定する。
全起動スクリプトから呼び出して統一的なログ管理を実現する。

使い方:
    from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

    setup_logging(app_name="execution")

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
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_LOG_LEVEL = "INFO"
_BACKUP_COUNT = 30  # 日次ローテーション・30日分保持

logger = logging.getLogger(__name__)


def setup_logging(
    app_name: str = "kabusys",
    log_dir: Path | None = None,
    level: str | int | None = None,
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
        app_name: ログファイル名のプレフィックス（例: ``"execution"`` → ``logs/execution.log``）。
        log_dir:  ログファイルの保存ディレクトリ。None の場合は上記解決順を使用。
        level:    ログレベル文字列（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）または
                  整数値（例: ``logging.DEBUG``）。None の場合は上記解決順を使用。

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
            file_handler = TimedRotatingFileHandler(
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

    return run_log_file


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
