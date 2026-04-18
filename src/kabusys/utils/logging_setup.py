# src/kabusys/utils/logging_setup.py
"""logging_setup.py — ログ設定ユーティリティ。

StreamHandler（コンソール）と TimedRotatingFileHandler（日次ローテーション）を
ルートロガーに設定する。全起動スクリプトから呼び出して統一的なログ管理を実現する。

使い方:
    from kabusys.utils.logging_setup import setup_logging
    setup_logging(app_name="execution")
"""

from __future__ import annotations

import logging
import os
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
    level: str | None = None,
) -> None:
    """ロギングを設定する。

    ルートロガーに以下の2ハンドラを設定する:
      - StreamHandler: コンソール（stdout）出力
      - TimedRotatingFileHandler: ``<log_dir>/<app_name>.log`` への日次ローテーション出力

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
        level:    ログレベル文字列（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）。
                  None の場合は上記解決順を使用。
    """
    # ログレベル解決
    resolved_level_str = (
        level or os.environ.get("LOG_LEVEL", _DEFAULT_LOG_LEVEL)
    ).upper()
    numeric_level = getattr(logging, resolved_level_str, logging.INFO)

    # ログディレクトリ解決・作成
    resolved_dir = log_dir or Path(os.environ.get("LOG_DIR", str(_DEFAULT_LOG_DIR)))
    resolved_dir.mkdir(parents=True, exist_ok=True)

    # ルートロガーにレベルを設定（既存ハンドラをクリア）
    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # StreamHandler（コンソール出力）
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(numeric_level)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    # TimedRotatingFileHandler（日次ローテーション・30日保持）
    log_file = resolved_dir / f"{app_name}.log"
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    logger.debug(
        "ロギングを設定しました: level=%s, log_file=%s",
        resolved_level_str,
        log_file,
    )
