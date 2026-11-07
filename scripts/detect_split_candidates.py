# scripts/detect_split_candidates.py
"""adj_factor が欠けている期間から株式分割・併合の候補を一覧表示する（Issue #424）。

raw_prices の終値の前日比が約 1/2・1/3・1/4・1/5・1/10（分割）またはその逆数（併合）で、
その日の adj_factor が NULL の行を候補として表示する。**表示のみで DB には書き込まない**
（読み取り専用で接続する）。確定した分割は scripts/backfill_adj_factor.py で係数を補う。

使い方:
    python scripts/detect_split_candidates.py [--from 2026-06-01] [--to 2026-11-06]
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

RATIOS = (2, 3, 4, 5, 10)
DEFAULT_TOLERANCE = 0.1  # 比率からの相対誤差（±10%）
# 前日の終値を探すため、期間開始より前に遡る日数
_LOOKBACK_DAYS = 31


def _match(ratio: float, tolerance: float) -> str | None:
    for n in RATIOS:
        if abs(ratio * n - 1.0) <= tolerance:
            return f"1:{n} 分割"
        if abs(ratio / n - 1.0) <= tolerance:
            return f"{n}:1 併合"
    return None


def detect_split_candidates(
    conn: duckdb.DuckDBPyConnection,
    date_from: date,
    date_to: date,
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[dict[str, Any]]:
    """分割・併合の候補（code, date, prev_close, close, ratio, label）を返す。読み取りのみ。"""
    rows = conn.execute(
        """
        WITH s AS (
            SELECT code, date, CAST(close AS DOUBLE) AS close, adj_factor,
                   LAG(CAST(close AS DOUBLE)) OVER (PARTITION BY code ORDER BY date)
                       AS prev_close
            FROM raw_prices
            WHERE date >= ? AND date <= ? AND close IS NOT NULL AND close > 0
        )
        SELECT code, date, prev_close, close, close / prev_close AS ratio
        FROM s
        WHERE date >= ? AND adj_factor IS NULL AND prev_close IS NOT NULL
        ORDER BY code, date
        """,
        [date_from - timedelta(days=_LOOKBACK_DAYS), date_to, date_from],
    ).fetchall()
    found: list[dict[str, Any]] = []
    for code, d, prev_close, close, ratio in rows:
        label = _match(float(ratio), tolerance)
        if label is None:
            continue
        found.append(
            {
                "code": str(code),
                "date": d,
                "prev_close": float(prev_close),
                "close": float(close),
                "ratio": float(ratio),
                "label": label,
            }
        )
    return found


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="株式分割・併合の候補を表示します（表示のみ）。")
    parser.add_argument("--from", dest="date_from", type=_parse_date, default=date(2026, 6, 1))
    parser.add_argument("--to", dest="date_to", type=_parse_date, default=date.today())
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    args = parser.parse_args(argv)

    from kabusys.config import Settings

    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        found = detect_split_candidates(conn, args.date_from, args.date_to, args.tolerance)
    finally:
        conn.close()

    print(f"期間 {args.date_from} 〜 {args.date_to}: 候補 {len(found)} 件")
    for c in found:
        print(
            f"  {c['date']}  {c['code']:<6} {c['prev_close']:>10,.1f} → {c['close']:>10,.1f}"
            f"  (×{c['ratio']:.3f})  {c['label']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
