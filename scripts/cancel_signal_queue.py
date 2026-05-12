# scripts/cancel_signal_queue.py
"""signal_queue の pending シグナルを status='cancelled' に変更するヘルパー。

使い方:
    python scripts/cancel_signal_queue.py --date 2026-05-12
    python scripts/cancel_signal_queue.py --date 2026-05-12 --code 7203
    python scripts/cancel_signal_queue.py --all

用途:
    誤ったシグナルが signal_queue に入った場合に手動でキャンセルする。
    pending のみ対象（processing / filled は変更しない）。
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _fetch_targets(
    conn: duckdb.DuckDBPyConnection,
    target_date: date | None,
    code: str | None,
) -> list[dict]:
    """status='pending' の対象レコードを返す。"""
    conditions = ["status = 'pending'"]
    params: list = []
    if target_date is not None:
        conditions.append("date = ?")
        params.append(str(target_date))
    if code is not None:
        conditions.append("code = ?")
        params.append(code)
    where = " AND ".join(conditions)
    rows = conn.execute(
        f"""
        SELECT signal_id, code, date, status, side, size
        FROM signal_queue
        WHERE {where}
        ORDER BY date, code, signal_id
        """,
        params,
    ).fetchall()
    cols = ["signal_id", "code", "date", "status", "side", "size"]
    return [dict(zip(cols, row)) for row in rows]


def _print_records(records: list[dict]) -> None:
    print(f"\n{'SIGNAL_ID':>36}  {'CODE':>6}  {'DATE':>12}  {'SIDE':>6}  {'SIZE':>8}")
    print("-" * 80)
    for r in records:
        print(
            f"{str(r['signal_id']):>36}  {r['code']:>6}  {str(r['date']):>12}  "
            f"{str(r.get('side', '')):>6}  {r.get('size', ''):>8}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="signal_queue の pending シグナルを status='cancelled' に変更する"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--date",
        help="対象日付（YYYY-MM-DD 形式）。この日付の pending を全キャンセル",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="pending の全件をキャンセル（日付を問わない）",
    )
    parser.add_argument(
        "--code",
        default=None,
        help="銘柄コードで絞り込む（--date と組み合わせて使用）",
    )
    args = parser.parse_args()

    if args.all and args.code:
        parser.error("--all と --code は同時に指定できません")

    target_date: date | None = None
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            logger.error("--date の形式が不正です（YYYY-MM-DD）: %s", args.date)
            sys.exit(1)

    settings = Settings()
    if not settings.duckdb_path.exists():
        logger.error("DuckDB ファイルが見つかりません: %s", settings.duckdb_path)
        sys.exit(1)

    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        targets = _fetch_targets(conn, target_date, args.code)

        if not targets:
            logger.info("キャンセル対象の pending シグナルが見つかりませんでした。")
            sys.exit(0)

        print(f"以下の {len(targets)} 件を status='cancelled' に変更します:")
        _print_records(targets)

        answer = input("続行しますか？ [y/N]: ").strip().lower()
        if answer != "y":
            logger.info("ユーザーによりキャンセルされました。")
            sys.exit(0)

        signal_ids = [r["signal_id"] for r in targets]
        placeholders = ", ".join(["?"] * len(signal_ids))
        updated_rows = conn.execute(
            f"UPDATE signal_queue SET status = 'cancelled'"
            f" WHERE signal_id IN ({placeholders})"
            f" AND status = 'pending'"
            f" RETURNING signal_id",
            signal_ids,
        ).fetchall()
        updated = len(updated_rows)
        if updated != len(signal_ids):
            logger.warning(
                "%d 件を選択しましたが実際の更新は %d 件でした。"
                "並行処理で status が変更済みの行があります。",
                len(signal_ids),
                updated,
            )
        logger.info(
            "signal_queue を更新しました（%d 件を status='cancelled' に変更）。",
            updated,
        )

    except Exception:
        logger.exception("signal_queue の更新に失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
