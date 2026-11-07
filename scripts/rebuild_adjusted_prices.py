# scripts/rebuild_adjusted_prices.py
"""prices_daily を株式分割・併合で後方補正した値に作り直す（Issue #424）。

raw_prices.adj_factor（1 以外）を持つ銘柄について、raw_prices の全期間から prices_daily を
作り直す。何度実行しても同じ結果になる（冪等）。

DuckDB に書き込むため、スケジューラーと Execution を停止してから実行すること。

使い方:
    python scripts/rebuild_adjusted_prices.py [--codes 83880 485A0] [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
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
        "--dry-run", action="store_true", help="対象銘柄と件数を表示するだけで書き込まない"
    )
    return parser.parse_args(argv)


def run(conn: duckdb.DuckDBPyConnection, codes: list[str] | None, dry_run: bool) -> int:
    """作り直しを実行し、書き込んだ prices_daily の行数を返す（dry_run は 0）。"""
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
        n = run(conn, args.codes, args.dry_run)
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
