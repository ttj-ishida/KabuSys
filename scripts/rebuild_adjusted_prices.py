# scripts/rebuild_adjusted_prices.py
"""prices_daily を株式分割・併合で後方補正した値に作り直す（Issue #424）。

既定（移行用）: raw_prices の全日付・全銘柄を prices_daily に同期し直す（補正込み）。
ETL 停止などで一度も同期されていない raw の日付も埋まる。1 以外の adj_factor を持つ銘柄は
全期間を作り直す。
--factor-codes-only: 1 以外の adj_factor を持つ銘柄だけを作り直す（軽い）。
--codes: 指定銘柄だけを作り直す。
何度実行しても同じ結果になる（冪等）。

DuckDB に書き込むため、スケジューラーと Execution を停止してから実行すること。

使い方:
    python scripts/rebuild_adjusted_prices.py [--codes 83880 485A0 | --factor-codes-only]
                                              [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.data.pipeline import sync_raw_prices_to_prices_daily
from kabusys.data.price_adjustment import codes_with_factors, rebuild_adjusted_prices

logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="prices_daily を分割補正済みの値に作り直します。")
    parser.add_argument(
        "--codes",
        nargs="+",
        metavar="CODE",
        help="対象銘柄（省略時は 1 以外の adj_factor を持つ全銘柄）",
    )
    parser.add_argument(
        "--factor-codes-only",
        action="store_true",
        help="1 以外の adj_factor を持つ銘柄だけを作り直す（既定は全日付・全銘柄を同期し直す）",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="対象銘柄と件数を表示するだけで書き込まない"
    )
    return parser.parse_args(argv)


def run(
    conn: duckdb.DuckDBPyConnection,
    codes: list[str] | None,
    dry_run: bool,
    all_dates: bool = True,
) -> int:
    """作り直しを実行し、書き込んだ prices_daily の行数を返す（dry_run は 0）。

    codes が None かつ all_dates=True（既定）のときは、raw_prices の全日付・全銘柄を同期し直す。
    """
    if codes is None and all_dates:
        lo, hi = conn.execute("SELECT MIN(date), MAX(date) FROM raw_prices").fetchone()
        missing = conn.execute(
            "SELECT COUNT(*) FROM raw_prices r WHERE NOT EXISTS ("
            "SELECT 1 FROM prices_daily p WHERE p.date = r.date AND p.code = r.code)"
        ).fetchone()[0]
        logger.info(
            "全日付モード: raw_prices %s 〜 %s（prices_daily にない raw 行 %d 件）", lo, hi, missing
        )
        if dry_run or lo is None:
            if dry_run:
                logger.info("[dry-run] 書き込みは行いません。")
            return 0
        return sync_raw_prices_to_prices_daily(conn, lo, hi)
    targets = codes if codes is not None else codes_with_factors(conn)
    factor_rows = conn.execute(
        "SELECT COUNT(*) FROM raw_prices "
        "WHERE adj_factor IS NOT NULL AND adj_factor > 0 AND adj_factor <> 1"
    ).fetchone()[0]
    logger.info(
        "対象 %d 銘柄（1 以外の adj_factor の行は DB 全体で %d 件）", len(targets), factor_rows
    )
    if dry_run:
        preview = ", ".join(targets[:20]) + (" ..." if len(targets) > 20 else "")
        logger.info("[dry-run] 書き込みは行いません。対象: %s", preview or "(なし)")
        return 0
    return rebuild_adjusted_prices(conn, targets)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args(argv)
    from kabusys.config import Settings

    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path), read_only=args.dry_run)
    try:
        n = run(conn, args.codes, args.dry_run, all_dates=not args.factor_codes_only)
        if not args.dry_run:
            logger.info("prices_daily の作り直しが完了しました: %d 件", n)
        return 0
    except Exception:
        logger.exception("rebuild_adjusted_prices が失敗しました")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
