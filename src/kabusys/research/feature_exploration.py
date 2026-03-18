"""
特徴量探索モジュール

Research 環境において、ファクターと将来リターンの関係を統計的に分析する。

提供機能:
  - ファクター相関分析: ファクター値と翌日/翌週リターンの相関
  - IC（Information Coefficient）計算: ランク相関によるファクター有効性評価
  - 統計サマリー: 各ファクターの基本統計量

設計方針:
  - DuckDB 接続を受け取り、prices_daily テーブルのみを参照する
  - 本番口座・発注 API には一切アクセスしない
  - 外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装する
"""

from __future__ import annotations

import logging
import math
from datetime import date, timedelta
from typing import Any

import duckdb

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 将来リターン計算
# ---------------------------------------------------------------------------


def calc_forward_returns(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    horizons: list[int] | None = None,
) -> list[dict[str, Any]]:
    """各銘柄の将来リターンを計算する。

    target_date の終値から、各ホライズン（営業日数）後の終値までのリターンを計算する。
    ホライズン先のデータが存在しない場合は None を返す。

    Args:
        conn:        DuckDB 接続。prices_daily テーブルを参照する。
        target_date: 基準日。
        horizons:    計算するホライズン（営業日数）のリスト。
                     デフォルトは [1, 5, 21]（翌日・翌週・翌月）。

    Returns:
        [{"date": date, "code": str, "fwd_1d": float|None, "fwd_5d": ..., ...}, ...] のリスト。
    """
    if horizons is None:
        horizons = [1, 5, 21]
    if any(not isinstance(h, int) or h <= 0 or h > 252 for h in horizons):
        raise ValueError("horizons must be positive integers <= 252")

    # 全ホライズンをまとめて1クエリで取得
    lag_exprs = ", ".join(
        f"LEAD(close, {h}) OVER (PARTITION BY code ORDER BY date) AS fwd_close_{h}"
        for h in horizons
    )
    return_exprs = ", ".join(
        f"CASE WHEN close > 0 AND fwd_close_{h} IS NOT NULL "
        f"THEN (fwd_close_{h} - close) / close END AS fwd_{h}d"
        for h in horizons
    )
    col_names = [f"fwd_{h}d" for h in horizons]

    rows = conn.execute(
        f"""
        WITH leads AS (
            SELECT date, code, close, {lag_exprs}
            FROM prices_daily
        )
        SELECT date, code, {return_exprs}
        FROM leads
        WHERE date = ?
        ORDER BY code
        """,  # noqa: S608
        [target_date],
    ).fetchall()

    cols = ["date", "code"] + col_names
    result = [dict(zip(cols, r)) for r in rows]
    logger.info("calc_forward_returns: %d 銘柄 date=%s horizons=%s", len(result), target_date, horizons)
    return result


# ---------------------------------------------------------------------------
# IC（Information Coefficient）計算
# ---------------------------------------------------------------------------


def calc_ic(
    factor_records: list[dict[str, Any]],
    forward_records: list[dict[str, Any]],
    factor_col: str,
    return_col: str,
) -> float | None:
    """ランク相関 IC（Spearman の ρ）を計算する。

    factor_records と forward_records を code で結合し、
    factor_col と return_col のスピアマンランク相関を計算する。

    どちらかが None のレコードは除外する。
    有効レコードが 3 件未満の場合は None を返す。

    Args:
        factor_records:  ファクター計算結果のリスト（"code" キーを含む）。
        forward_records: 将来リターン計算結果のリスト（"code" キーを含む）。
        factor_col:      ファクターカラム名（例: "mom_1m"）。
        return_col:      将来リターンカラム名（例: "fwd_1d"）。

    Returns:
        スピアマン ρ（-1.0〜1.0）。計算不能な場合は None。
    """
    fwd_map = {r["code"]: r.get(return_col) for r in forward_records}

    pairs: list[tuple[float, float]] = []
    for r in factor_records:
        fval = r.get(factor_col)
        rval = fwd_map.get(r["code"])
        if fval is not None and rval is not None:
            pairs.append((float(fval), float(rval)))

    if len(pairs) < 3:
        return None

    n = len(pairs)
    factor_vals = [p[0] for p in pairs]
    return_vals = [p[1] for p in pairs]

    factor_ranks = _rank(factor_vals)
    return_ranks = _rank(return_vals)

    # スピアマンのρ = 1 - 6*Σd²/(n*(n²-1))
    d_sq_sum = sum((fr - rr) ** 2 for fr, rr in zip(factor_ranks, return_ranks))
    rho = 1.0 - 6.0 * d_sq_sum / (n * (n * n - 1))
    return rho


def _rank(values: list[float]) -> list[float]:
    """値のリストをランクに変換する（同順位は平均ランク）。"""
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        # 同値の範囲を探す
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # 1-indexed
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


# ---------------------------------------------------------------------------
# 統計サマリー
# ---------------------------------------------------------------------------


def factor_summary(
    records: list[dict[str, Any]],
    columns: list[str],
) -> dict[str, dict[str, float | int | None]]:
    """ファクター列の基本統計量を計算する。

    各カラムについて count/mean/std/min/max/median を計算する。
    None 値は除外する。

    Args:
        records: ファクター計算結果のリスト。
        columns: 統計対象のカラム名リスト。

    Returns:
        {カラム名: {"count": int, "mean": float, "std": float,
                    "min": float, "max": float, "median": float}} の辞書。
    """
    result: dict[str, dict[str, float | int | None]] = {}
    for col in columns:
        values = sorted(r[col] for r in records if r.get(col) is not None)
        n = len(values)
        if n == 0:
            result[col] = {"count": 0, "mean": None, "std": None,
                           "min": None, "max": None, "median": None}
            continue
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance)
        median = values[n // 2] if n % 2 == 1 else (values[n // 2 - 1] + values[n // 2]) / 2.0
        result[col] = {
            "count": n,
            "mean": mean,
            "std": std,
            "min": values[0],
            "max": values[-1],
            "median": median,
        }
    return result
