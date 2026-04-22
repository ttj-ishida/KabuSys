"""
シグナル生成モジュール

features テーブルの正規化済みファクターと ai_scores を統合し、
各銘柄の最終スコア（final_score）を計算して売買シグナルを生成する。

シグナル生成フロー:
  1. features テーブルから正規化済みファクターを読み込む
  2. ai_scores テーブルから AI スコア・レジームスコアを読み込む
  3. Bear レジームフィルタの判定（Bear 相場では BUY シグナルを生成しない）
  3b. breadth_stop フィルタの判定（25日MA上銘柄比率 35%未満は全銘柄 BUY 停止）
  3c. セクター相対強弱の算出（Bear / breadth_stop 時はスキップ）
  4. 各銘柄のコンポーネントスコアを計算し final_score を算出（上位セクター銘柄は +0.03 ブースト）
  5. スコア降順ソート
  6. BUY シグナル生成（ギャップフィルタ・下位セクター銘柄の抑制を含む）
  7. 保有ポジションのエグジット条件を判定し SELL シグナルを生成
  8. signals テーブルへ書き込む（冪等）

設計方針:
  - StrategyModel.md Section 4〜5 の仕様に従う
  - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使用
  - 発注 API・execution 層への直接依存は持たない
"""

from __future__ import annotations

import logging
import math
from datetime import date
from typing import Any

import duckdb

from kabusys.data.calendar_management import get_trading_days, next_trading_day

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数（StrategyModel.md Section 4〜6）
# ---------------------------------------------------------------------------

# Section 4.1: 統合計算式の重み
_DEFAULT_WEIGHTS: dict[str, float] = {
    "momentum": 0.40,
    "value": 0.20,
    "volatility": 0.15,
    "liquidity": 0.15,
    "news": 0.10,
}

_DEFAULT_THRESHOLD: float = 0.60  # BUY シグナル閾値
_STOP_LOSS_RATE: float = -0.08  # ストップロス閾値（Section 5.2）
_GAP_UP_THRESHOLD: float = 0.05  # gap_ratio > 0.05 → BUY 抑制（超過のみ）
_GAP_DOWN_THRESHOLD: float = -0.03  # gap_ratio <= -0.03 → BUY 抑制（境界値含む）
# 二進浮動小数点の丸め誤差を吸収するための微小量。
# 上側 (gap-up): gap > _GAP_UP_THRESHOLD + ε
#   → 境界ちょうど（+5.0%）や誤差で僅かに下回る値を「許可」。
#     例: 1050/1000 - 1 = 0.050000000000000044 (IEEE754) が誤って抑制されるのを防ぐ。
# 下側 (gap-down): gap <= _GAP_DOWN_THRESHOLD + ε
#   → 境界ちょうど（-3.0%）を「抑制」し、誤差で僅かに上振れた値も安全側で抑制。
#     例: 970/1000 - 1 = -0.030000000000000044 が誤って許可されるのを防ぐ。
_GAP_THRESHOLD_EPSILON: float = 1e-9
_SECTOR_BOOST: float = 0.03  # 上位 _SECTOR_QUARTILE セクター銘柄への final_score 加算量
_SECTOR_QUARTILE: float = 0.25  # 上位・下位の区切り割合（各 ceil(N×0.25) セクター）
_MIN_HOLDING_DAYS: int = 5   # BUY 後この営業日数を経過するまで非ストップロス SELL を抑制
_REENTRY_COOLDOWN_DAYS: int = 5  # SELL 後この営業日数を経過するまで同一銘柄の BUY を禁止


# ---------------------------------------------------------------------------
# スコア計算ユーティリティ
# ---------------------------------------------------------------------------


def _sigmoid(z: float | None) -> float | None:
    """Z スコア（±3 にクリップ済み）を [0, 1] に変換する。"""
    if z is None or not math.isfinite(z):
        return None
    try:
        return 1.0 / (1.0 + math.exp(-z))
    except OverflowError:
        return 0.0 if z < 0 else 1.0


def _avg_scores(values: list[float | None]) -> float | None:
    """有効な値の平均を返す。有効な値が 0 件の場合は None。"""
    valid = [v for v in values if v is not None and math.isfinite(v)]
    return sum(valid) / len(valid) if valid else None


def _compute_momentum_score(feat: dict[str, Any]) -> float | None:
    """モメンタムスコア（高いほど上昇トレンド）。"""
    return _avg_scores(
        [
            _sigmoid(feat.get("momentum_20")),
            _sigmoid(feat.get("momentum_60")),
            _sigmoid(feat.get("ma200_dev")),
        ]
    )


def _compute_value_score(feat: dict[str, Any]) -> float | None:
    """バリュースコア（PER が低いほど高スコア）。

    PER = 20 で 0.5、PER → 0 で 1.0、PER → ∞ で 0.0 に近似。
    """
    per = feat.get("per")
    if per is None or per <= 0 or not math.isfinite(per):
        return None
    return 1.0 / (1.0 + per / 20.0)


def _compute_volatility_score(feat: dict[str, Any]) -> float | None:
    """ボラティリティスコア（低ボラティリティ = 低リスク = 高スコア）。

    atr_pct の Z スコアを反転してシグモイド変換する。
    """
    z = feat.get("volatility_20")  # atr_pct の Z スコア
    if z is None or not math.isfinite(z):
        return None
    return _sigmoid(-z)


def _compute_liquidity_score(feat: dict[str, Any]) -> float | None:
    """流動性スコア（出来高比率が高いほど高スコア）。"""
    return _sigmoid(feat.get("volume_ratio"))


def _is_bear_regime(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> bool:
    """market_regime テーブルの regime_label を参照し、Bear 相場か否かを判定する。

    データが存在しない場合は False（安全側：BUY を許可）を返す。
    """
    row = conn.execute(
        "SELECT regime_label FROM market_regime WHERE date = ?",
        [target_date],
    ).fetchone()
    if row is None:
        return False
    return row[0] == "bear"


def _is_breadth_stop(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> bool:
    """market_breadth.breadth_stop フラグを返す。

    breadth_stop=True の場合、25日MA上銘柄比率が 35% 未満であり新規 BUY を停止する。
    データが存在しない場合は False（安全側：BUY を許可）を返す。
    """
    row = conn.execute(
        "SELECT breadth_stop FROM market_breadth WHERE date = ?",
        [target_date],
    ).fetchone()
    if row is None:
        return False
    return bool(row[0])


def _fetch_gap_ratios(
    conn: duckdb.DuckDBPyConnection,
    codes: list[str],
    target_date: date,
) -> dict[str, float]:
    """target_date の open / 前日 close - 1.0 を銘柄ごとに返す。

    戻り値: {code: gap_ratio} — データ欠損銘柄はキーなし（BUY 許可・安全側）。
    前日は target_date より小さい最大日付を使用する。

    Note: DuckDB の list 型パラメータバインド（ANY(?)）はバージョン間で不安定なため
          IN (?, ?, ...) プレースホルダーを使用する（news_nlp.py と同方針）。
    """
    if not codes:
        return {}
    placeholders = ", ".join("?" * len(codes))
    rows = conn.execute(
        f"""
        SELECT t.code,
               CAST(t.open AS DOUBLE) / CAST(p.close AS DOUBLE) - 1.0
        FROM prices_daily t
        JOIN prices_daily p
          ON p.code = t.code
         AND p.date = (
             SELECT MAX(date) FROM prices_daily
             WHERE code = t.code AND date < ?
         )
        WHERE t.date = ?
          AND t.code IN ({placeholders})
          AND t.open IS NOT NULL
          AND CAST(t.open AS DOUBLE) > 0
          AND CAST(p.close AS DOUBLE) > 0
        """,
        [target_date, target_date, *codes],
    ).fetchall()
    return {code: ratio for code, ratio in rows}


def _calc_sector_strengths(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> tuple[frozenset[str], frozenset[str], dict[str, str]]:
    """セクター20営業日リターンを算出し、上位・下位セクターと銘柄→セクターマップを返す。

    stocks テーブルの全銘柄 × prices_daily で等加重セクターリターンを計算し、
    上位 _SECTOR_QUARTILE / 下位 _SECTOR_QUARTILE のセクターを分類する。

    データ欠損・セクター未登録銘柄は安全側（BUY 許可・スコアブーストなし）に倒す。

    Returns:
        (top_sectors, bottom_sectors, sector_map)
        - top_sectors:    上位 _SECTOR_QUARTILE セクター名の frozenset
        - bottom_sectors: 下位 _SECTOR_QUARTILE セクター名の frozenset
        - sector_map:     {code: sector}（NULL/空文字のセクターは除外）

    Note: 有効セクターが1つの場合は top と bottom が同一になるためフィルタ無効。
    """
    # sector_map を取得（NULL / 空白のみは除外）
    sector_rows = conn.execute(
        "SELECT code, NULLIF(TRIM(sector), '') FROM stocks"
    ).fetchall()
    sector_map: dict[str, str] = {code: sec for code, sec in sector_rows if sec}

    if not sector_map:
        return frozenset(), frozenset(), {}

    # セクター別20営業日等加重リターンを算出
    # biz_dates: prices_daily の distinct date を降順番号付け（rn=1=target_date, rn=21=20営業日前）
    rows = conn.execute(
        """
        WITH last_21 AS (
            SELECT DISTINCT date FROM prices_daily WHERE date <= ?
            ORDER BY date DESC LIMIT 21
        ),
        date_20d AS (
            SELECT MIN(date) AS date FROM last_21 HAVING COUNT(*) = 21
        )
        SELECT
            TRIM(s.sector) AS sector,
            AVG(CAST(cur.close AS DOUBLE) / CAST(prev.close AS DOUBLE) - 1.0) AS ret
        FROM stocks s
        JOIN prices_daily cur
          ON cur.code = s.code AND cur.date = ?
        JOIN prices_daily prev
          ON prev.code = s.code
         AND prev.date = (SELECT date FROM date_20d)
        WHERE NULLIF(TRIM(s.sector), '') IS NOT NULL
          AND CAST(cur.close AS DOUBLE) > 0
          AND CAST(prev.close AS DOUBLE) > 0
        GROUP BY TRIM(s.sector)
        ORDER BY ret DESC, sector ASC
        """,
        [target_date, target_date],
    ).fetchall()

    if not rows:
        return frozenset(), frozenset(), sector_map

    n = len(rows)
    top_n = max(1, math.ceil(n * _SECTOR_QUARTILE))
    bottom_n = max(1, math.ceil(n * _SECTOR_QUARTILE))

    top_sectors = frozenset(s for s, _ in rows[:top_n])
    bottom_sectors = frozenset(s for s, _ in rows[-bottom_n:])

    # オーバーラップ（n=1 など top と bottom が同一セクターを含む）→ 両方空
    if top_sectors & bottom_sectors:
        logger.debug(
            "_calc_sector_strengths: top/bottom オーバーラップ（セクター数=%d）"
            " — フィルタ無効 date=%s",
            n,
            target_date,
        )
        return frozenset(), frozenset(), sector_map

    logger.info(
        "_calc_sector_strengths: top=%d bottom=%d (total=%d) date=%s",
        len(top_sectors),
        len(bottom_sectors),
        n,
        target_date,
    )
    logger.debug(
        "_calc_sector_strengths: top_sectors=%s bottom_sectors=%s date=%s",
        sorted(top_sectors),
        sorted(bottom_sectors),
        target_date,
    )
    return top_sectors, bottom_sectors, sector_map


# ---------------------------------------------------------------------------
# 保有日数 / 再エントリー制限ヘルパー
# ---------------------------------------------------------------------------


def _held_days(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
) -> int | None:
    """position_entries から最新の未クローズ entry_date を取得し、
    entry_date 〜 target_date の営業日数を返す（entry_date 当日 = 0）。
    レコードなし → None（チェックスキップ・安全側）。
    """
    row = conn.execute(
        """
        SELECT entry_date FROM position_entries
        WHERE code = ? AND sell_date IS NULL
        ORDER BY entry_date DESC LIMIT 1
        """,
        [code],
    ).fetchone()
    if row is None:
        return None
    entry_date = row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0]))
    days = get_trading_days(conn, entry_date, target_date)
    return len(days) - 1  # 0 = entry 当日、5 = 5営業日後


def _is_reentry_blocked(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
) -> bool:
    """最新の sell_date から target_date までの営業日数が _REENTRY_COOLDOWN_DAYS 未満なら True。
    sell_date が NULL またはレコードなしは False（制限なし）。
    """
    row = conn.execute(
        """
        SELECT sell_date FROM position_entries
        WHERE code = ? AND sell_date IS NOT NULL
        ORDER BY sell_date DESC LIMIT 1
        """,
        [code],
    ).fetchone()
    if row is None or row[0] is None:
        return False
    sell_date = row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0]))
    days = get_trading_days(conn, sell_date, target_date)
    return (len(days) - 1) < _REENTRY_COOLDOWN_DAYS


def _has_upcoming_earnings(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
) -> bool:
    """翌営業日が earnings_calendar の announcement_date に登録されている銘柄なら True。"""
    next_day = next_trading_day(conn, target_date)
    row = conn.execute(
        "SELECT 1 FROM earnings_calendar WHERE code = ? AND announcement_date = ?",
        [code, next_day],
    ).fetchone()
    return row is not None


def _get_event_size_multiplier(
    event_dates: dict[date, str],
    target_date: date,
    conn: duckdb.DuckDBPyConnection,
) -> float:
    """翌営業日が event_dates に含まれる場合 0.5、それ以外は 1.0 を返す。"""
    if not event_dates:
        return 1.0
    next_day = next_trading_day(conn, target_date)
    return 0.5 if next_day in event_dates else 1.0


# ---------------------------------------------------------------------------
# 売りシグナル生成（エグジット判定）
# ---------------------------------------------------------------------------


def _generate_sell_signals(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    score_map: dict[str, float],
    threshold: float,
) -> list[dict[str, Any]]:
    """保有ポジションに対してエグジット条件を判定し、SELL シグナルを返す。

    実装済みの条件 (StrategyModel.md Section 5.2):
      1. ストップロス: 終値 / avg_price - 1 < -8%
      2. スコア低下: final_score が threshold 未満

    未実装の条件（positions テーブルに peak_price / entry_date が必要）:
      - トレーリングストップ（直近最高値から -10%）
      - 時間決済（保有 60 営業日超過）

    Returns:
        [{"code": str, "score": float, "reason": str}, ...] のリスト。
    """
    pos_rows = conn.execute(
        """
        WITH latest_pos AS (
            SELECT p.*
            FROM positions p
            INNER JOIN (
                SELECT code, MAX(date) AS max_date
                FROM positions
                WHERE date <= ?
                GROUP BY code
            ) m ON p.code = m.code AND p.date = m.max_date
        ),
        latest_price AS (
            SELECT pd.code, CAST(pd.close AS DOUBLE) AS close
            FROM prices_daily pd
            INNER JOIN (
                SELECT code, MAX(date) AS max_date
                FROM prices_daily
                WHERE date <= ?
                GROUP BY code
            ) mp ON pd.code = mp.code AND pd.date = mp.max_date
        )
        SELECT p.code, CAST(p.avg_price AS DOUBLE), pr.close
        FROM latest_pos p
        LEFT JOIN latest_price pr ON pr.code = p.code
        WHERE p.position_size > 0
        """,
        [target_date, target_date],
    ).fetchall()

    sell_signals: list[dict[str, Any]] = []
    for code, avg_price, close in pos_rows:
        if avg_price is None or avg_price <= 0:
            continue

        # 価格が取得できない場合は SELL 判定全体をスキップ（価格欠損時の誤クローズ防止）
        if close is None:
            logger.warning(
                "_generate_sell_signals: %s の価格が取得できないため SELL 判定をスキップ date=%s",
                code,
                target_date,
            )
            continue

        # features に存在しない保有銘柄は final_score = 0.0 と見なす（threshold 未満 → SELL 対象）
        if code not in score_map:
            logger.warning(
                "_generate_sell_signals: %s は features に存在しません。score=0.0 として SELL 判定します date=%s",
                code,
                target_date,
            )
        final_score = score_map.get(code, 0.0)

        # 1. ストップロス（最優先・保有日数チェックをスキップ）
        pnl_rate = (close - avg_price) / avg_price
        if pnl_rate <= _STOP_LOSS_RATE:
            sell_signals.append(
                {
                    "code": code,
                    "score": final_score,
                    "reason": "stop_loss",
                }
            )
            continue

        # 決算回避 SELL（翌営業日が決算日 → 最低保有日数を問わず即 SELL）
        if _has_upcoming_earnings(conn, code, target_date):
            sell_signals.append(
                {
                    "code": code,
                    "score": final_score,
                    "reason": "earnings_avoidance",
                }
            )
            continue

        # 最低保有日数チェック（stop_loss 以外の SELL を抑制）
        held = _held_days(conn, code, target_date)
        if held is not None and held < _MIN_HOLDING_DAYS:
            logger.debug(
                "_generate_sell_signals: %s 保有 %d 営業日（最低 %d 日）— SELL 抑制 date=%s",
                code,
                held,
                _MIN_HOLDING_DAYS,
                target_date,
            )
            continue

        # 2. スコア低下
        if final_score < threshold:
            sell_signals.append(
                {
                    "code": code,
                    "score": final_score,
                    "reason": "score_drop",
                }
            )

    logger.debug(
        "_generate_sell_signals: %d シグナル date=%s", len(sell_signals), target_date
    )
    return sell_signals


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def generate_signals(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    threshold: float = _DEFAULT_THRESHOLD,
    weights: dict[str, float] | None = None,
    event_dates: dict[date, str] | None = None,  # ← 追加
) -> int:
    """features テーブルを読み込み、売買シグナルを生成して signals テーブルへ書き込む。

    target_date 分をすべて削除してから挿入する日付単位の置換（冪等）。

    Args:
        conn:        DuckDB 接続。features / ai_scores / positions テーブルを参照する。
        target_date: シグナル生成日。
        threshold:   BUY シグナル生成の final_score 閾値（デフォルト 0.60）。
        weights:     ファクター重みの辞書（デフォルトは StrategyModel.md Section 4.1 の値）。

    Returns:
        signals テーブルへ書き込んだシグナル数（BUY + SELL の合計）。
    """
    # weights を _DEFAULT_WEIGHTS でフォールバック補完し、合計が 1.0 でなければ再スケール
    # 未知キー・非数値・NaN/Inf・負値は無視して既知キー（_DEFAULT_WEIGHTS）のみを受け付ける
    allowed = set(_DEFAULT_WEIGHTS)
    user_w: dict[str, float] = {}
    for k, v in (weights or {}).items():
        if k not in allowed:
            continue
        if (
            not isinstance(v, (int, float))
            or isinstance(v, bool)
            or not math.isfinite(v)
            or v < 0
        ):
            logger.warning(
                "generate_signals: weights[%s]=%r は無効な値のためスキップします。",
                k,
                v,
            )
            continue
        user_w[k] = float(v)
    merged_weights = {**_DEFAULT_WEIGHTS, **user_w}
    total_w = sum(merged_weights.values())
    if total_w <= 0:
        logger.warning(
            "generate_signals: weights の合計が 0 以下です。_DEFAULT_WEIGHTS にフォールバックします。"
        )
        merged_weights = dict(_DEFAULT_WEIGHTS)
    elif not math.isclose(total_w, 1.0):
        merged_weights = {k: v / total_w for k, v in merged_weights.items()}
    weights = merged_weights

    event_dates = event_dates or {}
    size_multiplier = _get_event_size_multiplier(event_dates, target_date, conn)

    # 1. features 読み込み
    feat_rows = conn.execute(
        """
        SELECT code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev
        FROM features
        WHERE date = ?
        """,
        [target_date],
    ).fetchall()
    feat_cols = [
        "code",
        "momentum_20",
        "momentum_60",
        "volatility_20",
        "volume_ratio",
        "per",
        "ma200_dev",
    ]
    features = [dict(zip(feat_cols, r)) for r in feat_rows]

    if not features:
        logger.warning(
            "generate_signals: features が空 date=%s — BUY シグナルなし、SELL 判定のみ実施",
            target_date,
        )

    # 2. AI スコア読み込み（センチメントスコアのみ使用）
    ai_rows = conn.execute(
        "SELECT code, ai_score FROM ai_scores WHERE date = ?",
        [target_date],
    ).fetchall()
    ai_map: dict[str, dict] = {code: {"ai_score": ai} for code, ai in ai_rows}

    # 3. Bear レジーム判定（market_regime テーブルから取得）
    regime_is_bear = _is_bear_regime(conn, target_date)
    if regime_is_bear:
        logger.info(
            "generate_signals: Bear レジーム検知 — BUY シグナル抑制 date=%s",
            target_date,
        )

    # 3b. breadth_stop 判定（25日MA上銘柄比率 < 35% で BUY 全件停止）
    breadth_stop = _is_breadth_stop(conn, target_date)
    if breadth_stop:
        logger.warning(
            "generate_signals: breadth_stop=True — 25日MA上銘柄比率 < 35%% のため BUY を全件スキップ date=%s",
            target_date,
        )

    # 3c. セクター強弱分類（Bear レジーム / breadth_stop では BUY 不要なためスキップ）
    top_sectors: frozenset[str] = frozenset()
    bottom_sectors: frozenset[str] = frozenset()
    sector_map: dict[str, str] = {}
    boosted_count = 0
    if not regime_is_bear and not breadth_stop:
        top_sectors, bottom_sectors, sector_map = _calc_sector_strengths(
            conn, target_date
        )

    # 4. 各銘柄の final_score 計算（Section 4.1）
    scored: list[dict[str, Any]] = []
    for feat in features:
        code = feat["code"]
        s_mom = _compute_momentum_score(feat)
        s_val = _compute_value_score(feat)
        s_vol = _compute_volatility_score(feat)
        s_liq = _compute_liquidity_score(feat)

        # AI ニューススコア（未登録の場合は中立 0.5 で補完）
        ai_raw = ai_map.get(code, {}).get("ai_score")
        s_news = _sigmoid(ai_raw) if ai_raw is not None else None

        # None のコンポーネントは中立値 0.5 で補完（欠損銘柄の不当な降格を防ぐ）
        final_score = (
            weights["momentum"] * (s_mom if s_mom is not None else 0.5)
            + weights["value"] * (s_val if s_val is not None else 0.5)
            + weights["volatility"] * (s_vol if s_vol is not None else 0.5)
            + weights["liquidity"] * (s_liq if s_liq is not None else 0.5)
            + weights["news"] * (s_news if s_news is not None else 0.5)
        )
        # セクター強弱スコア補正（上位セクターは +_SECTOR_BOOST）
        sector = sector_map.get(code, "")
        if sector and sector in top_sectors:
            old_score = final_score
            final_score += _SECTOR_BOOST
            logger.debug(
                "sector boost: %s sector=%s score %.4f→%.4f date=%s",
                code,
                sector,
                old_score,
                final_score,
                target_date,
            )
            boosted_count += 1
        scored.append({"code": code, "score": final_score})

    if not regime_is_bear and not breadth_stop and boosted_count:
        logger.info(
            "generate_signals: sector boost — %d 銘柄をスコアブースト date=%s",
            boosted_count,
            target_date,
        )

    # 5. スコア降順でランク付け
    scored.sort(key=lambda r: r["score"], reverse=True)
    score_map: dict[str, float] = {r["code"]: r["score"] for r in scored}

    # 6. BUY シグナル生成（Bear レジームまたは breadth_stop では抑制）
    buy_signals: list[dict] = []
    if not regime_is_bear and not breadth_stop:
        # 3c. ギャップ比率を一括取得（BUY 生成が必要な場合のみ実行）
        gap_ratios = _fetch_gap_ratios(
            conn, [r["code"] for r in scored if r["score"] >= threshold], target_date
        )
        gap_suppressed = 0
        sector_suppressed = 0
        reentry_suppressed = 0
        earnings_suppressed = 0
        for rank, r in enumerate(scored, 1):
            if r["score"] < threshold:
                continue
            gap = gap_ratios.get(r["code"])
            if gap is not None and (
                gap > _GAP_UP_THRESHOLD + _GAP_THRESHOLD_EPSILON
                or gap <= _GAP_DOWN_THRESHOLD + _GAP_THRESHOLD_EPSILON
            ):
                logger.debug(
                    "gap filter: %s gap=%.2f%% — BUY を抑制 date=%s",
                    r["code"],
                    gap * 100,
                    target_date,
                )
                gap_suppressed += 1
                continue
            # セクター下位フィルタ
            sector = sector_map.get(r["code"], "")
            if sector and sector in bottom_sectors:
                logger.debug(
                    "sector filter: %s sector=%s — BUY を抑制 date=%s",
                    r["code"],
                    sector,
                    target_date,
                )
                sector_suppressed += 1
                continue
            # 再エントリー制限チェック
            if _is_reentry_blocked(conn, r["code"], target_date):
                logger.debug(
                    "reentry blocked: %s — date=%s", r["code"], target_date
                )
                reentry_suppressed += 1
                continue
            # 決算回避フィルタ（翌営業日が決算日の銘柄は BUY 抑制）
            if _has_upcoming_earnings(conn, r["code"], target_date):
                logger.debug(
                    "earnings filter: %s — 翌営業日決算のため BUY 抑制 date=%s",
                    r["code"],
                    target_date,
                )
                earnings_suppressed += 1
                continue
            buy_signals.append({"code": r["code"], "score": r["score"], "rank": rank})
        if gap_suppressed:
            logger.info(
                "generate_signals: gap filter — %d 銘柄を抑制 date=%s",
                gap_suppressed,
                target_date,
            )
        if sector_suppressed:
            logger.info(
                "generate_signals: sector filter — %d 銘柄を下位セクターで抑制 date=%s",
                sector_suppressed,
                target_date,
            )
        if reentry_suppressed:
            logger.info(
                "generate_signals: reentry block — %d 銘柄を再エントリー制限で抑制 date=%s",
                reentry_suppressed,
                target_date,
            )
        if earnings_suppressed:
            logger.info(
                "generate_signals: earnings filter — %d 銘柄を決算回避で抑制 date=%s",
                earnings_suppressed,
                target_date,
            )

    # 7. SELL シグナル生成（エグジット条件）
    sell_signals = _generate_sell_signals(conn, target_date, score_map, threshold)

    # SELL 対象銘柄は BUY から除外し、ランクを連番で再付与（SELL 優先ポリシー）
    sell_codes = {s["code"] for s in sell_signals}
    buy_signals = [b for b in buy_signals if b["code"] not in sell_codes]
    buy_signals.sort(key=lambda x: x["score"], reverse=True)
    for i, b in enumerate(buy_signals, 1):
        b["rank"] = i

    # 8. signals テーブルへ日付単位の置換（トランザクション＋バルク挿入で原子性を保証）
    buy_params = [
        (target_date, r["code"], r["score"], r["rank"], size_multiplier)
        for r in buy_signals
    ]
    sell_params = [(target_date, r["code"], r["score"]) for r in sell_signals]
    conn.execute("BEGIN")
    try:
        conn.execute("DELETE FROM signals WHERE date = ?", [target_date])
        if buy_params:
            conn.executemany(
                "INSERT INTO signals (date, code, side, score, signal_rank, size_multiplier) "
                "VALUES (?, ?, 'buy', ?, ?, ?)",
                buy_params,
            )
        if sell_params:
            conn.executemany(
                "INSERT INTO signals (date, code, side, score, signal_rank) VALUES (?, ?, 'sell', ?, NULL)",
                sell_params,
            )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception as rb_exc:
            logger.warning("generate_signals: ROLLBACK failed: %s", rb_exc)
        raise

    total = len(buy_signals) + len(sell_signals)
    logger.info(
        "generate_signals: BUY=%d SELL=%d total=%d date=%s",
        len(buy_signals),
        len(sell_signals),
        total,
        target_date,
    )
    return total
