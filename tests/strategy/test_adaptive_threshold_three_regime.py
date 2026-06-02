"""3 値レジーム適応閾値のテスト (Issue #376)"""
from __future__ import annotations

from datetime import date, timedelta

import duckdb

from kabusys.data.schema import init_schema
from kabusys.strategy.signal_generator import generate_signals


def _make_db(topix_close_series: list[float]) -> duckdb.DuckDBPyConnection:
    conn = init_schema(":memory:")

    base_date = date(2023, 6, 1)
    for i, close in enumerate(topix_close_series):
        d = base_date - timedelta(days=i)
        conn.execute(
            "INSERT INTO topix_daily (date, open, high, low, close) VALUES (?, ?, ?, ?, ?)",
            [d, close, close, close, close],
        )

    return conn


def _insert_feature(conn, target_date, code: str = "1234", momentum: float = 0.0) -> None:
    """features テーブルに挿入。momentum 値でスコアを制御する。

    スコア計算（デフォルト weights の場合）:
      s_mom = sigmoid(momentum) [momentum_20 / momentum_60 / ma200_dev すべて同値]
      s_val ≈ 0.46 (per=15, pbr=1.0, div_yield=0.02 固定)
      s_vol = sigmoid(0.1) ≈ 0.525
      s_liq = sigmoid(0.5) ≈ 0.622
      s_news = 0.5 (AI 無効)
      final = 0.40*s_mom + 0.20*s_val + 0.15*s_vol + 0.15*s_liq + 0.10*s_news
    """
    conn.execute(
        """
        INSERT INTO features
            (date, code, momentum_20, momentum_60, volatility_20, volume_ratio,
             per, pbr, div_yield, ma200_dev, ma75_dev, ma25_dev,
             rsi_14, topix_rel_20, quality_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [target_date, code,
         momentum, momentum,    # momentum_20, momentum_60
         -0.1,                  # volatility_20 (slight negative = low vol = good)
         0.5,                   # volume_ratio
         15.0, 1.0, 0.02,      # per, pbr, div_yield
         momentum,              # ma200_dev (same as momentum for simplicity)
         0.01, 0.01,           # ma75_dev, ma25_dev
         40.0,                  # rsi_14 (below overbought)
         0.05,                  # topix_rel_20
         0.5],                  # quality_score
    )
    conn.execute(
        "INSERT INTO stocks (code, sector) VALUES (?, 'T') ON CONFLICT DO NOTHING", [code]
    )


def _topix_series_with_vol(daily_move: float, n: int = 22) -> list[float]:
    """交互に上下する TOPIX 終値系列を生成する。

    実際の分散を持つ系列を生成するために、+/-daily_move を交互に適用する。
    annualized_vol ≈ daily_move * sqrt(2) * sqrt(252)

    参考:
      daily_move=0.005 → vol ≈ 0.08  (低ボラ、< 0.12)
      daily_move=0.011 → vol ≈ 0.18  (中ボラ、0.12-0.25)
      daily_move=0.016 → vol ≈ 0.26  (高ボラ、>= 0.25)
    """
    closes = [2000.0]
    sign = 1
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + sign * daily_move))
        sign *= -1
    closes.reverse()  # index 0 = 最新日（target_date）
    return closes


# --- スコアと momentum の対応 (実際の value_config: div_yield weight=0, ai_enabled=False) ---
# 実際の strategy_config.yaml が読み込まれるため、デフォルトの計算値とは異なる場合がある。
# 以下の値は実際の _compute_*_score 関数から逆算したもの。
# score ≈ 0.53 → momentum ≈ -0.086
# score ≈ 0.57 → momentum ≈  0.317
# score ≈ 0.60 → momentum ≈  0.636
# score ≈ 0.61 → momentum ≈  0.748
# score ≈ 0.63 → momentum ≈  0.988
_MOM_SCORE_053 = -0.0855  # final_score ≈ 0.530
_MOM_SCORE_057 = 0.3172   # final_score ≈ 0.570
_MOM_SCORE_060 = 0.6355   # final_score ≈ 0.600
_MOM_SCORE_061 = 0.7475   # final_score ≈ 0.610
_MOM_SCORE_063 = 0.9877   # final_score ≈ 0.630


def _buy_count(conn: duckdb.DuckDBPyConnection, target_date: date) -> int:
    """signals テーブルから BUY（side='buy'）シグナル数を返す。"""
    row = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE date = ? AND side = 'buy'",
        [target_date],
    ).fetchone()
    return int(row[0]) if row else 0


class TestThreeValueRegime:
    TARGET_DATE = date(2023, 6, 1)

    def test_low_vol_raises_threshold(self):
        """低ボラ（vol≈0.08 < 0.12）: 閾値が adaptive_threshold_hi（0.62）に引き上げられる。
        score ≈ 0.61 < 0.62 → BUY なし。
        """
        conn = _make_db(_topix_series_with_vol(0.005))  # vol ≈ 0.08
        _insert_feature(conn, self.TARGET_DATE, momentum=_MOM_SCORE_061)

        generate_signals(
            conn=conn,
            target_date=self.TARGET_DATE,
            threshold=0.58,
            adaptive_threshold_vol_regime=True,
            topix_vol_low_threshold=0.12,
            adaptive_threshold_hi=0.62,
            topix_vol_high_threshold=0.25,
            adaptive_threshold_lo=0.55,
        )
        assert _buy_count(conn, self.TARGET_DATE) == 0

    def test_low_vol_allows_buy_above_hi_threshold(self):
        """低ボラ（vol≈0.08 < 0.12）: score ≈ 0.63 >= 0.62 → BUY が発生する。"""
        conn = _make_db(_topix_series_with_vol(0.005))  # vol ≈ 0.08
        _insert_feature(conn, self.TARGET_DATE, momentum=_MOM_SCORE_063)

        generate_signals(
            conn=conn,
            target_date=self.TARGET_DATE,
            threshold=0.58,
            adaptive_threshold_vol_regime=True,
            topix_vol_low_threshold=0.12,
            adaptive_threshold_hi=0.62,
            topix_vol_high_threshold=0.25,
            adaptive_threshold_lo=0.55,
        )
        assert _buy_count(conn, self.TARGET_DATE) == 1

    def test_mid_vol_uses_base_threshold(self):
        """中ボラ（vol≈0.18: 0.12 <= vol < 0.25）: 閾値はベース（0.58）。score ≈ 0.60 → BUY。"""
        conn = _make_db(_topix_series_with_vol(0.011))  # vol ≈ 0.18
        _insert_feature(conn, self.TARGET_DATE, momentum=_MOM_SCORE_060)

        generate_signals(
            conn=conn,
            target_date=self.TARGET_DATE,
            threshold=0.58,
            adaptive_threshold_vol_regime=True,
            topix_vol_low_threshold=0.12,
            adaptive_threshold_hi=0.62,
            topix_vol_high_threshold=0.25,
            adaptive_threshold_lo=0.55,
        )
        assert _buy_count(conn, self.TARGET_DATE) == 1

    def test_high_vol_lowers_threshold(self):
        """高ボラ（vol≈0.26 >= 0.25）: 閾値が adaptive_threshold_lo（0.55）に引き下げられる。
        score ≈ 0.57（< 0.58 だが >= 0.55）→ BUY が発生する。
        """
        conn = _make_db(_topix_series_with_vol(0.016))  # vol ≈ 0.26
        _insert_feature(conn, self.TARGET_DATE, momentum=_MOM_SCORE_057)

        generate_signals(
            conn=conn,
            target_date=self.TARGET_DATE,
            threshold=0.58,
            adaptive_threshold_vol_regime=True,
            topix_vol_low_threshold=0.12,
            adaptive_threshold_hi=0.62,
            topix_vol_high_threshold=0.25,
            adaptive_threshold_lo=0.55,
        )
        assert _buy_count(conn, self.TARGET_DATE) == 1

    def test_high_vol_blocks_below_lo_threshold(self):
        """高ボラ（vol≈0.26 >= 0.25）: score ≈ 0.53 < 0.55 → BUY なし。"""
        conn = _make_db(_topix_series_with_vol(0.016))  # vol ≈ 0.26
        _insert_feature(conn, self.TARGET_DATE, momentum=_MOM_SCORE_053)

        generate_signals(
            conn=conn,
            target_date=self.TARGET_DATE,
            threshold=0.58,
            adaptive_threshold_vol_regime=True,
            topix_vol_low_threshold=0.12,
            adaptive_threshold_hi=0.62,
            topix_vol_high_threshold=0.25,
            adaptive_threshold_lo=0.55,
        )
        assert _buy_count(conn, self.TARGET_DATE) == 0

    def test_two_value_mode_backward_compat(self):
        """topix_vol_high_threshold=None のとき 2 値モード（後方互換）。
        高ボラ（vol≈0.31）でも高ボラ分岐は発動せず、閾値はベース（0.58）のまま。
        score ≈ 0.57 < 0.58 → BUY なし。
        """
        conn = _make_db(_topix_series_with_vol(0.019))  # vol ≈ 0.31
        _insert_feature(conn, self.TARGET_DATE, momentum=_MOM_SCORE_057)

        generate_signals(
            conn=conn,
            target_date=self.TARGET_DATE,
            threshold=0.58,
            adaptive_threshold_vol_regime=True,
            topix_vol_low_threshold=0.12,
            adaptive_threshold_hi=0.62,
            topix_vol_high_threshold=None,
            adaptive_threshold_lo=0.55,
        )
        assert _buy_count(conn, self.TARGET_DATE) == 0

    def test_boundary_at_low_threshold_is_mid(self):
        """vol == low_threshold（0.12）は MID 扱い（LOW は vol < low_threshold の厳密不等号）。
        d=0.0076 → vol≈0.124 ≥ 0.12 → MID。閾値はベース（0.58）のまま。
        score≈0.60 > 0.58 → BUY あり。LOW 扱いなら閾値=0.62 で 0.60 < 0.62 → BUY なし。
        """
        conn = _make_db(_topix_series_with_vol(0.0076))  # vol≈0.124 > low_threshold=0.12
        _insert_feature(conn, self.TARGET_DATE, momentum=_MOM_SCORE_060)

        generate_signals(
            conn=conn,
            target_date=self.TARGET_DATE,
            threshold=0.58,
            adaptive_threshold_vol_regime=True,
            topix_vol_low_threshold=0.12,
            adaptive_threshold_hi=0.62,
            topix_vol_high_threshold=0.25,
            adaptive_threshold_lo=0.55,
        )
        assert _buy_count(conn, self.TARGET_DATE) == 1, "MID: 閾値0.58, score≈0.60 → BUY"

    def test_boundary_at_high_threshold_is_high(self):
        """vol == high_threshold（0.25）は HIGH 扱い（HIGH は vol >= high_threshold の包含不等号）。
        d=0.0154 → vol≈0.251 ≥ 0.25 → HIGH。閾値が adaptive_threshold_lo（0.55）に引き下げ。
        score≈0.57 > 0.55 → BUY あり。MID 扱いなら閾値=0.58 で 0.57 < 0.58 → BUY なし。
        """
        conn = _make_db(_topix_series_with_vol(0.0154))  # vol≈0.251 ≥ high_threshold=0.25
        _insert_feature(conn, self.TARGET_DATE, momentum=_MOM_SCORE_057)

        generate_signals(
            conn=conn,
            target_date=self.TARGET_DATE,
            threshold=0.58,
            adaptive_threshold_vol_regime=True,
            topix_vol_low_threshold=0.12,
            adaptive_threshold_hi=0.62,
            topix_vol_high_threshold=0.25,
            adaptive_threshold_lo=0.55,
        )
        assert _buy_count(conn, self.TARGET_DATE) == 1, "HIGH: 閾値0.55, score≈0.57 → BUY"
