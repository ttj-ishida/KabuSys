# scripts/reset_signals.py
"""signal_queue テーブルをクリアするメンテナンススクリプト。

未処理のシグナルをすべて削除する。
使い方: python scripts/reset_signals.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        cursor = conn.execute("DELETE FROM signal_queue")
        n = cursor.rowcount
        logger.info("signal_queue をクリアしました（%d 件削除）", n)
    except Exception:
        logger.exception("signal_queue のクリアに失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
