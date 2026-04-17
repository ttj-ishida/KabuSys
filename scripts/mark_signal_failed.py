# scripts/mark_signal_failed.py
"""signal_queue の指定シグナルを status='failed' に手動更新するヘルパー。

使い方:
    python scripts/mark_signal_failed.py --code 7203
    python scripts/mark_signal_failed.py --code 7203 --date 2026-04-17

用途:
    注文エラー（order rejected）発生時に FailureRecovery.md §10.1 の手順として使用する。
    DuckDB CLI で直接 UPDATE するよりもヒューマンエラーリスクが低い。
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

_JST = timezone(timedelta(hours=9))


def _fetch_targets(conn: duckdb.DuckDBPyConnection, code: str, target_date: date) -> list[dict]:
    """status が 'pending' または 'processing' の対象レコードを返す。"""
    rows = conn.execute(
        """
        SELECT signal_id, code, date, status, side, size
        FROM signal_queue
        WHERE code = ?
          AND date = ?
          AND status IN ('pending', 'processing')
        ORDER BY signal_id
        """,
        [code, str(target_date)],
    ).fetchall()
    cols = ["signal_id", "code", "date", "status", "side", "size"]
    return [dict(zip(cols, row)) for row in rows]


def _print_records(records: list[dict]) -> None:
    print(f"\n{'SIGNAL_ID':>36}  {'CODE':>6}  {'DATE':>12}  {'STATUS':>12}  {'SIDE':>6}  {'SIZE':>8}")
    print("-" * 90)
    for r in records:
        print(f"{str(r['signal_id']):>36}  {r['code']:>6}  {str(r['date']):>12}  "
              f"{r['status']:>12}  {str(r.get('side','')[:6]):>6}  {r.get('size', ''):>8}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="signal_queue の指定シグナルを status='failed' に更新する"
    )
    parser.add_argument(
        "--code",
        required=True,
        help="銘柄コード（例: 7203）",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="対象日付（YYYY-MM-DD 形式。省略時は当日 JST）",
    )
    args = parser.parse_args()

    # 日付の解決
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            logger.error("--date の形式が不正です。YYYY-MM-DD 形式で指定してください: %s", args.date)
            sys.exit(1)
    else:
        target_date = datetime.now(_JST).date()

    settings = Settings()

    if not settings.duckdb_path.exists():
        logger.error("DuckDB ファイルが見つかりません: %s", settings.duckdb_path)
        sys.exit(1)

    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        targets = _fetch_targets(conn, args.code, target_date)

        if not targets:
            logger.error(
                "対象レコードが見つかりません（code=%s, date=%s, status=pending/processing）。",
                args.code, target_date,
            )
            sys.exit(1)

        print(f"以下の {len(targets)} 件を status='error' に更新します:")
        _print_records(targets)

        answer = input("続行しますか？ [y/N]: ").strip().lower()
        if answer != "y":
            logger.info("ユーザーによりキャンセルされました。")
            sys.exit(0)

        signal_ids = [r["signal_id"] for r in targets]
        placeholders = ", ".join(["?"] * len(signal_ids))
        # TOCTOU 対策: UPDATE 側にも status 条件を付け、
        # SELECT 後に別プロセスが status を変更済みの行は更新しない。
        # DuckDB の rowcount は信頼できないため RETURNING で実更新件数を確認する。
        updated_rows = conn.execute(
            f"UPDATE signal_queue SET status = 'error'"
            f" WHERE signal_id IN ({placeholders})"
            f" AND status IN ('pending', 'processing')"
            f" RETURNING signal_id",
            signal_ids,
        ).fetchall()
        updated = len(updated_rows)
        if updated != len(signal_ids):
            logger.warning(
                "%d 件を選択しましたが実際の更新は %d 件でした。"
                "並行処理で status が変更済みの行があります。",
                len(signal_ids), updated,
            )
        logger.info(
            "signal_queue を更新しました（%d 件を status='error' に変更）。",
            updated,
        )

    except Exception:
        logger.exception("signal_queue の更新に失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
