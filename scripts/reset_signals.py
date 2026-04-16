# scripts/reset_signals.py
"""signal_queue テーブルをクリアするメンテナンススクリプト。

未処理のシグナルをすべて削除する。
使い方: python scripts/reset_signals.py --force

安全ガード:
  - --force フラグが必須（誤実行防止）
  - 取引時間中（前場 09:00-11:30 / 後場 12:30-15:00 JST）は実行を拒否
  - 未処理注文（status='sent'）が存在する場合は確認プロンプトを表示
  - 削除前に DuckDB をバックアップ
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sqlite3
import sys
from datetime import datetime, time, timezone, timedelta
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

_JST = timezone(timedelta(hours=9))
_TRADING_PERIODS: list[tuple[time, time]] = [
    (time(9, 0), time(11, 30)),   # 前場
    (time(12, 30), time(15, 0)),  # 後場
]


def _is_trading_hours(now: datetime | None = None) -> bool:
    """現在時刻が TSE 取引時間内かどうかを返す。"""
    if now is None:
        now = datetime.now(_JST)
    t = now.time()
    return any(start <= t < end for start, end in _TRADING_PERIODS)


def _count_open_orders(sqlite_path: Path) -> int:
    """monitoring.db の orders テーブルで status='sent' の件数を返す。"""
    if not sqlite_path.exists():
        return 0
    try:
        conn = sqlite3.connect(str(sqlite_path))
        try:
            cur = conn.execute("SELECT COUNT(*) FROM orders WHERE status='sent'")
            return int(cur.fetchone()[0])
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("orders テーブルの確認に失敗しました: %s", e)
        return 0


def _backup_duckdb(duckdb_path: Path) -> Path:
    """DuckDB ファイルを同ディレクトリにタイムスタンプ付きでコピーする。"""
    ts = datetime.now(_JST).strftime("%Y%m%d_%H%M%S")
    backup_dir = duckdb_path.parent / "backup"
    backup_dir.mkdir(exist_ok=True)
    dest = backup_dir / f"{duckdb_path.stem}_{ts}.duckdb"
    shutil.copy2(str(duckdb_path), str(dest))
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="signal_queue テーブルをクリアする（--force 必須）"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="実際に削除を実行する（安全ガード解除）",
    )
    args = parser.parse_args()

    if not args.force:
        logger.error(
            "このスクリプトは --force を指定した場合のみ実行できます。"
            " signal_queue の全件削除は取り消せません。"
        )
        sys.exit(1)

    # 取引時間中チェック
    if _is_trading_hours():
        logger.error(
            "取引時間中（前場 09:00-11:30 / 後場 12:30-15:00 JST）は実行できません。"
            " 市場クローズ後に実行してください。"
        )
        sys.exit(1)

    settings = Settings()

    # 未処理注文チェック
    open_orders = _count_open_orders(settings.sqlite_path)
    if open_orders > 0:
        print(
            f"警告: status='sent' の未処理注文が {open_orders} 件あります。"
            " signal_queue をクリアしても注文は取り消されません。"
        )
        answer = input("続行しますか？ [y/N]: ").strip().lower()
        if answer != "y":
            logger.info("ユーザーによりキャンセルされました。")
            sys.exit(0)

    # バックアップ
    if settings.duckdb_path.exists():
        backup_path = _backup_duckdb(settings.duckdb_path)
        logger.info("バックアップを作成しました: %s", backup_path)
    else:
        logger.warning("DuckDB ファイルが見つかりません: %s", settings.duckdb_path)

    # signal_queue 削除
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
