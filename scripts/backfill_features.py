# scripts/backfill_features.py
"""バックテスト用特徴量バックフィル。

指定期間の全営業日分の特徴量を一括生成し features テーブルへ格納する。
バックテスト実行前の事前準備として使用する。

使い方:
    python scripts/backfill_features.py --start 2022-01-01 --end 2024-12-31
    python scripts/backfill_features.py --start 2022-01-01 --end 2024-12-31 --force
    python scripts/backfill_features.py --start 2022-01-01 --end 2024-12-31 --dry-run

ワークフロー:
    1. python -m kabusys.data.bootstrap          # 価格・財務データ取得
    2. python scripts/backfill_features.py       # 特徴量を期間一括生成（本スクリプト）
    3. python -m kabusys.backtest.run ...        # バックテスト実行
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
from kabusys.data.calendar_management import get_trading_days
from kabusys.strategy.feature_engineering import build_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# RSI(14) に必要なルックバック日数（カレンダー日）
# factor_research._RSI_SCAN_DAYS と同値: (14+1) * 3 = 45
_RSI_LOOKBACK_DAYS = 45


def _check_rsi_lookback(conn: duckdb.DuckDBPyConnection, start: date) -> None:
    """start 以前に RSI 計算に必要な価格データが存在するか確認し、不足時は警告を出す。

    RSI(14) は target_date から遡って最低 14 件の日次変化量が必要。
    prices_daily の最古日が start - _RSI_LOOKBACK_DAYS より新しい場合、
    開始直後の数営業日は rsi_14 = NULL となりバックテスト精度が下がる。
    """
    from datetime import timedelta

    required_from = start - timedelta(days=_RSI_LOOKBACK_DAYS)
    row = conn.execute(
        "SELECT MIN(date) FROM prices_daily WHERE date < ?", [start]
    ).fetchone()
    oldest = row[0] if row else None

    if oldest is None:
        logger.warning(
            "prices_daily に --start (%s) 以前のデータが存在しません。"
            "開始直後の約 14 営業日は rsi_14 = NULL になります。"
            "先に `python -m kabusys.data.bootstrap` で過去データを取得してください。",
            start,
        )
    elif oldest > required_from:
        logger.warning(
            "prices_daily の最古データ (%s) が RSI ルックバック要求日 (%s) より新しいです。"
            "--start 付近の最初の約 14 営業日は rsi_14 = NULL になる可能性があります。"
            "より古いデータを bootstrap で取得するか、--start を %s 以降に設定してください。",
            oldest,
            required_from,
            oldest + timedelta(days=_RSI_LOOKBACK_DAYS),
        )
    else:
        logger.debug("RSI ルックバック確認OK: 最古価格=%s, 要求=%s", oldest, required_from)


def _dates_with_features(conn: duckdb.DuckDBPyConnection, start: date, end: date) -> set[date]:
    rows = conn.execute(
        "SELECT DISTINCT date FROM features WHERE date >= ? AND date <= ?",
        [start, end],
    ).fetchall()
    return {r[0] for r in rows}


def _has_prices(conn: duckdb.DuckDBPyConnection, target_date: date) -> bool:
    count = conn.execute(
        "SELECT COUNT(*) FROM prices_daily WHERE date = ?", [target_date]
    ).fetchone()[0]
    return count > 0


def backfill(
    conn: duckdb.DuckDBPyConnection,
    start: date,
    end: date,
    force: bool = False,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """指定期間の特徴量を生成する。

    Returns:
        (processed, skipped, no_price_data) のタプル。
    """
    _check_rsi_lookback(conn, start)

    trading_days = get_trading_days(conn, start, end)
    if not trading_days:
        logger.warning("指定期間に営業日が見つかりません: %s ~ %s", start, end)
        return 0, 0, 0

    existing = _dates_with_features(conn, start, end) if not force else set()

    processed = skipped = no_price = 0

    for i, target_date in enumerate(trading_days, 1):
        prefix = f"[{i}/{len(trading_days)}] {target_date}"

        if target_date in existing:
            logger.info("%s — スキップ（既存データあり。上書きは --force を指定）", prefix)
            skipped += 1
            continue

        if not _has_prices(conn, target_date):
            logger.warning("%s — スキップ（prices_daily にデータなし）", prefix)
            no_price += 1
            continue

        if dry_run:
            logger.info("%s — [dry-run] 生成対象", prefix)
            processed += 1
            continue

        n = build_features(conn, target_date)
        logger.info("%s — 完了 (%d 銘柄)", prefix, n)
        processed += 1

    return processed, skipped, no_price


def main() -> None:
    parser = argparse.ArgumentParser(
        description="バックテスト用特徴量バックフィル",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--start", required=True, help="開始日 YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="終了日 YYYY-MM-DD")
    parser.add_argument("--db", default=None, help="DuckDB ファイルパス（省略時は設定ファイルのパス）")
    parser.add_argument(
        "--force",
        action="store_true",
        help="既存データを上書きする（省略時はスキップ）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="対象日付の一覧を表示するのみ（DB への書き込みなし）",
    )
    args = parser.parse_args()

    try:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    except ValueError as exc:
        logger.error("日付フォーマットが不正です: %s", exc)
        sys.exit(1)

    if start_date > end_date:
        logger.error("--start は --end より前の日付を指定してください")
        sys.exit(1)

    db_path = args.db or str(Settings().duckdb_path)

    if args.dry_run:
        logger.info("[dry-run] DB への書き込みは行いません")

    conn = duckdb.connect(db_path)
    try:
        processed, skipped, no_price = backfill(
            conn,
            start=start_date,
            end=end_date,
            force=args.force,
            dry_run=args.dry_run,
        )
    except Exception:
        logger.exception("backfill_features が失敗しました")
        sys.exit(1)
    finally:
        conn.close()

    label = "[dry-run] " if args.dry_run else ""
    logger.info(
        "%s完了 — 処理: %d 日 / スキップ: %d 日 / 価格データなし: %d 日",
        label,
        processed,
        skipped,
        no_price,
    )

    if no_price > 0:
        logger.warning(
            "価格データなしでスキップされた日があります。"
            "先に `python -m kabusys.data.bootstrap` を実行してください。"
        )


if __name__ == "__main__":
    main()
