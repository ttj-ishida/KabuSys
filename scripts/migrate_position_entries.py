# scripts/migrate_position_entries.py
"""DuckDB の position_entries テーブルを SQLite に移行するワンタイムスクリプト。

Issue #320 対応: position_entries を DuckDB から SQLite に移管した際、
既存の DuckDB データを SQLite へコピーするために使用する。

使い方:
    python scripts/migrate_position_entries.py [--dry-run]

オプション:
    --dry-run   実際の書き込みを行わず、移行件数のみ表示する。
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.execution.order_repository import init_position_entries_db


def migrate(dry_run: bool = False) -> None:
    settings = Settings()

    duckdb_conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    sqlite_path = settings.paper_sqlite_path if settings.is_paper else settings.sqlite_path
    sqlite_conn = sqlite3.connect(str(sqlite_path), timeout=30.0)

    try:
        # DuckDB に position_entries テーブルが存在するか確認
        tables = duckdb_conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name = 'position_entries'"
        ).fetchall()
        if not tables:
            print("DuckDB に position_entries テーブルが存在しません。移行不要です。")
            return

        rows = duckdb_conn.execute(
            "SELECT code, entry_date::TEXT, sell_date::TEXT FROM position_entries"
        ).fetchall()

        print(f"DuckDB から {len(rows)} 件を取得しました。")
        if dry_run:
            print("[dry-run] 書き込みをスキップします。")
            return

        init_position_entries_db(sqlite_conn)

        inserted = 0
        skipped = 0
        for code, entry_date, sell_date in rows:
            cur = sqlite_conn.execute(
                "INSERT OR IGNORE INTO position_entries (code, entry_date, sell_date)"
                " VALUES (?, ?, ?)",
                [code, entry_date, sell_date],
            )
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1

        sqlite_conn.commit()
        print(f"移行完了: 挿入 {inserted} 件 / スキップ（既存） {skipped} 件")

    finally:
        duckdb_conn.close()
        sqlite_conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="DuckDB position_entries → SQLite 移行")
    parser.add_argument("--dry-run", action="store_true", help="書き込みを行わずに件数のみ確認する")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
