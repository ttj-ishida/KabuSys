"""
特徴量エンジニアリングモジュール

研究環境（research/）で計算した生ファクターを正規化・合成し、
戦略シグナル生成に用いる特徴量（feature）を作成して features テーブルへ保存する。

処理フロー:
  1. calc_momentum / calc_volatility / calc_value でファクター取得
  2. ユニバースフィルタ（株価・流動性）を適用
  3. 数値ファクターを Z スコア正規化し ±3 でクリップ
  4. features テーブルへ UPSERT（冪等）

設計方針:
  - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使用
  - 発注 API・execution 層への依存は持たない
"""

from __future__ import annotations

import logging
import math
from datetime import date
from typing import Any

import duckdb

from kabusys.data.stats import zscore_normalize
from kabusys.research.factor_research import (
    calc_momentum,
    calc_quality,
    calc_rsi,
    calc_topix_relative,
    calc_value,
    calc_volatility,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_MIN_PRICE: float = 300.0  # ユニバース最低株価（円）
_MIN_TURNOVER: float = 5e8  # ユニバース最低平均売買代金（円）
_ZSCORE_CLIP: float = 3.0  # Z スコアクリップ範囲

# Z スコア正規化対象カラム（per は逆数スコアに変換するため正規化しない）
_NORM_COLS: tuple[str, ...] = (
    "mom_1m",
    "mom_3m",
    "atr_pct",
    "volume_ratio",
    "ma200_dev",
    "topix_rel_20",
    "topix_rel_60",
    "op_margin",
    "rev_growth_yoy",
    "profit_growth_yoy",
)


# ---------------------------------------------------------------------------
# ユニバースフィルタ
# ---------------------------------------------------------------------------


def _apply_universe_filter(
    records: list[dict[str, Any]],
    price_map: dict[str, float],
) -> list[dict[str, Any]]:
    """株価・流動性フィルタを適用し、基準を満たす銘柄のみを返す。

    フィルタ条件 (StrategyModel.md Section 2.2 / UniverseDefinition.md Section 5):
      - 株価 >= _MIN_PRICE（300 円）
      - 20日平均売買代金 >= _MIN_TURNOVER（5 億円）
    """
    result = []
    for r in records:
        code = r["code"]
        close = price_map.get(code)
        avg_turnover = r.get("avg_turnover")
        if close is None or not math.isfinite(close) or close < _MIN_PRICE:
            continue
        if avg_turnover is None or not math.isfinite(avg_turnover) or avg_turnover < _MIN_TURNOVER:
            continue
        result.append(r)
    return result


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def build_features(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> int:
    """ファクターを計算・正規化し features テーブルへ書き込む。

    target_date 分をすべて削除してから挿入する日付単位の置換（冪等）。

    Args:
        conn:        DuckDB 接続。prices_daily / raw_financials テーブルを参照する。
        target_date: 計算基準日。

    Returns:
        upsert した銘柄数。
    """
    # 1. raw factors from research module
    mom_list = calc_momentum(conn, target_date)
    vol_list = calc_volatility(conn, target_date)
    val_list = calc_value(conn, target_date)
    topix_rel_list = calc_topix_relative(conn, target_date)
    quality_list = calc_quality(conn, target_date)
    rsi_list = calc_rsi(conn, target_date)

    mom_map: dict[str, dict] = {r["code"]: r for r in mom_list}
    vol_map: dict[str, dict] = {r["code"]: r for r in vol_list}
    val_map: dict[str, dict] = {r["code"]: r for r in val_list}
    topix_map: dict[str, dict] = {r["code"]: r for r in topix_rel_list}
    quality_map: dict[str, dict] = {r["code"]: r for r in quality_list}
    rsi_map: dict[str, dict] = {r["code"]: r for r in rsi_list}

    # 2. current close prices（ユニバースフィルタ用）
    # target_date 以前の最新価格を参照（休場日・当日欠損に対応）
    price_rows = conn.execute(
        """
        SELECT pd.code, CAST(pd.close AS DOUBLE)
        FROM prices_daily pd
        INNER JOIN (
            SELECT code, MAX(date) AS max_date
            FROM prices_daily
            WHERE date <= ?
            GROUP BY code
        ) m ON pd.code = m.code AND pd.date = m.max_date
        """,
        [target_date],
    ).fetchall()
    price_map: dict[str, float] = {code: close for code, close in price_rows}

    # 3. 全コードをマージしたレコードを構築
    all_codes = set(mom_map) | set(vol_map) | set(val_map)
    merged: list[dict[str, Any]] = []
    for code in sorted(all_codes):
        m = mom_map.get(code, {})
        v = vol_map.get(code, {})
        f = val_map.get(code, {})
        t = topix_map.get(code, {})
        q = quality_map.get(code, {})
        r = rsi_map.get(code, {})
        merged.append(
            {
                "code": code,
                "avg_turnover": v.get("avg_turnover"),  # フィルタ用（features には保存しない）
                "mom_1m": m.get("mom_1m"),
                "mom_3m": m.get("mom_3m"),
                "ma200_dev": m.get("ma200_dev"),
                "atr_pct": v.get("atr_pct"),
                "volume_ratio": v.get("volume_ratio"),
                "per": f.get("per"),
                "pbr": f.get("pbr"),
                "div_yield": f.get("div_yield"),
                "topix_rel_20": t.get("topix_rel_20"),
                "topix_rel_60": t.get("topix_rel_60"),
                "op_margin": q.get("op_margin"),
                "rev_growth_yoy": q.get("rev_growth_yoy"),
                "profit_growth_yoy": q.get("profit_growth_yoy"),
                "rsi_14": r.get("rsi_14"),
            }
        )

    # 4. ユニバースフィルタ
    filtered = _apply_universe_filter(merged, price_map)

    # 5. Z スコア正規化
    normalized = zscore_normalize(filtered, list(_NORM_COLS))

    # 6. Z スコアを ±3 でクリップ（外れ値の影響抑制）
    for r in normalized:
        for col in _NORM_COLS:
            v = r.get(col)
            if v is not None and math.isfinite(v):
                r[col] = max(-_ZSCORE_CLIP, min(_ZSCORE_CLIP, v))
            else:
                r[col] = None
        # quality_score: 正規化済み品質サブ指標の非 NULL 平均
        q_vals = [
            r.get("op_margin"),
            r.get("rev_growth_yoy"),
            r.get("profit_growth_yoy"),
        ]
        q_valid = [v for v in q_vals if v is not None and math.isfinite(v)]
        r["quality_score"] = sum(q_valid) / len(q_valid) if q_valid else None

    # 7. features テーブルへ日付単位の置換（トランザクション＋バルク挿入で原子性を保証）
    params = [
        (
            target_date,
            r["code"],
            r.get("mom_1m"),
            r.get("mom_3m"),
            r.get("atr_pct"),
            r.get("volume_ratio"),
            r.get("per"),
            r.get("pbr"),
            r.get("div_yield"),
            r.get("ma200_dev"),
            r.get("topix_rel_20"),
            r.get("topix_rel_60"),
            r.get("quality_score"),
            r.get("rsi_14"),
        )
        for r in normalized
    ]
    conn.execute("BEGIN")
    try:
        conn.execute("DELETE FROM features WHERE date = ?", [target_date])
        if params:
            conn.executemany(
                """
                INSERT INTO features
                    (date, code, momentum_20, momentum_60, volatility_20, volume_ratio,
                     per, pbr, div_yield, ma200_dev,
                     topix_rel_20, topix_rel_60, quality_score, rsi_14, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
                """,
                params,
            )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception as rb_exc:
            logger.warning("build_features: ROLLBACK failed: %s", rb_exc)
        raise

    count = len(normalized)
    logger.info("build_features: %d 銘柄 date=%s", count, target_date)
    return count


# ---------------------------------------------------------------------------
# TOPIX MA 事前計算
# ---------------------------------------------------------------------------


def ensure_topix_ma_columns(conn: duckdb.DuckDBPyConnection) -> None:
    """既存 DB に ma25/ma75/ma200 列がなければ追加する（冪等）。"""
    for col in ("ma25", "ma75", "ma200"):
        conn.execute(f"ALTER TABLE topix_daily ADD COLUMN IF NOT EXISTS {col} DOUBLE")


def update_topix_ma(conn: duckdb.DuckDBPyConnection, target_date: date) -> bool:
    """target_date の TOPIX MA25/MA75/MA200 を計算して topix_daily に保存する。

    データ不足の場合は対応 MA を NULL にして保存する。
    対象日付のレコードがない場合は False を返す。
    既存 DB に MA 列がなければ冪等に追加してから計算する。
    """
    ensure_topix_ma_columns(conn)

    row = conn.execute(
        """
        WITH topix_data AS (
            SELECT date, close,
                   CASE WHEN COUNT(*) OVER (ORDER BY date ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) >= 25
                        THEN AVG(close) OVER (ORDER BY date ROWS BETWEEN 24 PRECEDING AND CURRENT ROW)
                        ELSE NULL END AS ma25,
                   CASE WHEN COUNT(*) OVER (ORDER BY date ROWS BETWEEN 74 PRECEDING AND CURRENT ROW) >= 75
                        THEN AVG(close) OVER (ORDER BY date ROWS BETWEEN 74 PRECEDING AND CURRENT ROW)
                        ELSE NULL END AS ma75,
                   CASE WHEN COUNT(*) OVER (ORDER BY date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) >= 200
                        THEN AVG(close) OVER (ORDER BY date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW)
                        ELSE NULL END AS ma200
            FROM topix_daily
            WHERE date <= ?
        )
        SELECT ma25, ma75, ma200 FROM topix_data WHERE date = ?
        """,
        [target_date, target_date],
    ).fetchone()

    if row is None:
        return False

    conn.execute(
        "UPDATE topix_daily SET ma25 = ?, ma75 = ?, ma200 = ? WHERE date = ?",
        [row[0], row[1], row[2], target_date],
    )
    return True
