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
import sqlite3
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

import duckdb
import tomllib

if TYPE_CHECKING:
    from kabusys.backtest.engine import BacktestScope

from kabusys.core.interfaces import RegimeProvider, build_regime_provider
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
_MIN_HOLDING_DAYS: int = 5  # BUY 後この営業日数を経過するまで非ストップロス SELL を抑制
_MAX_HOLDING_DAYS: int = 60  # この営業日数を超えた保有は time_exit SELL を発動（最大保有期間）
_TRAILING_STOP_ATR_MULT: float = 2.0  # peak_close から ATR × N 下落で trailing_stop SELL を発動
_REENTRY_COOLDOWN_DAYS: int = 5  # SELL 後この営業日数を経過するまで同一銘柄の BUY を禁止

_TOPIX_SIZE_MULTIPLIER_WEAK_BEAR: float = 0.5  # MA25 < MA75（弱いベア）の size_multiplier
_TOPIX_SIZE_MULTIPLIER_STRONG_BEAR: float = 0.0  # MA75 < MA200（強いベア）の size_multiplier

_RSI_OVERBOUGHT_THRESHOLD: float = 65.0  # RSI(14) > この値の銘柄は BUY 抑制（過熱判定）

# features テーブルから SELECT する列（2箇所で共用）
_FEATURES_SELECT_COLS: tuple[str, ...] = (
    "code",
    "momentum_20",
    "momentum_60",
    "volatility_20",
    "volume_ratio",
    "per",
    "pbr",
    "div_yield",
    "ma200_dev",
    "ma75_dev",
    "ma25_dev",
    "rsi_14",
)


# ---------------------------------------------------------------------------
# 設定ファイル読み込み
# ---------------------------------------------------------------------------

_STRATEGY_CONFIG_DEFAULTS: dict = {
    "weights": {k: v for k, v in _DEFAULT_WEIGHTS.items()},
    "threshold": _DEFAULT_THRESHOLD,
    "stop_loss_rate": _STOP_LOSS_RATE,
    "gap_up_threshold": _GAP_UP_THRESHOLD,
    "gap_down_threshold": _GAP_DOWN_THRESHOLD,
    "min_holding_days": _MIN_HOLDING_DAYS,
    "max_holding_days": _MAX_HOLDING_DAYS,
    "trailing_stop_atr_mult": _TRAILING_STOP_ATR_MULT,
    "reentry_cooldown_days": _REENTRY_COOLDOWN_DAYS,
    "sector_boost": _SECTOR_BOOST,
    "sector_quartile": _SECTOR_QUARTILE,
    "topix_size_multiplier_weak_bear": _TOPIX_SIZE_MULTIPLIER_WEAK_BEAR,
    "topix_size_multiplier_strong_bear": _TOPIX_SIZE_MULTIPLIER_STRONG_BEAR,
    "rsi_overbought_threshold": _RSI_OVERBOUGHT_THRESHOLD,
}

_STRATEGY_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "strategy_config.yaml"

_strategy_config_cache: dict | None = None
_strategy_config_mtime: float = -1.0


def _load_strategy_config() -> dict:
    """config/strategy_config.yaml から戦略パラメータを読み込む。

    ファイルが存在しない・読み込み失敗の場合はデフォルト値にフォールバック。
    各キーは個別に検証し、不正値のみデフォルトで補完する。
    mtime ベースのキャッシュにより、同一ファイルの繰り返し読み込みを回避する。

    Returns:
        {
            "weights": dict[str, float],
            "threshold": float,
            "stop_loss_rate": float,
            "gap_up_threshold": float,
            "gap_down_threshold": float,
            "min_holding_days": int,
            "max_holding_days": int,
            "trailing_stop_atr_mult": float,
            "reentry_cooldown_days": int,
            "sector_boost": float,
            "sector_quartile": float,
            "topix_size_multiplier_weak_bear": float,
            "topix_size_multiplier_strong_bear": float,
            "rsi_overbought_threshold": float,
        }
    """
    global _strategy_config_cache, _strategy_config_mtime
    import yaml  # PyYAML（既存の依存パッケージ）

    def _defaults() -> dict:
        d = dict(_STRATEGY_CONFIG_DEFAULTS)
        d["weights"] = dict(_STRATEGY_CONFIG_DEFAULTS["weights"])
        return d

    if not _STRATEGY_CONFIG_PATH.exists():
        logger.debug(
            "strategy_config.yaml が見つかりません。デフォルトを使用します: %s",
            _STRATEGY_CONFIG_PATH,
        )
        return _defaults()

    try:
        current_mtime = _STRATEGY_CONFIG_PATH.stat().st_mtime
    except OSError as exc:
        logger.warning("strategy_config.yaml の stat() に失敗: %s (デフォルトを使用)", exc)
        return _defaults()

    if _strategy_config_cache is not None and current_mtime == _strategy_config_mtime:
        cached = _strategy_config_cache
        out = dict(cached)
        out["weights"] = dict(cached["weights"])
        return out

    try:
        with open(_STRATEGY_CONFIG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        logger.warning("strategy_config.yaml 読み込み失敗: %s (デフォルトを使用)", exc)
        return _defaults()

    if not isinstance(data, dict):
        logger.warning(
            "strategy_config.yaml のトップレベルが dict ではありません。デフォルトを使用します"
        )
        return _defaults()

    result = _defaults()
    s = data.get("strategy")
    if not isinstance(s, dict):
        _strategy_config_cache = result
        _strategy_config_mtime = current_mtime
        out = dict(result)
        out["weights"] = dict(result["weights"])
        return out

    # weights — 既知キーのみ受け付け、負値は無視、合計 0 以下ならデフォルト
    raw_w = s.get("weights")
    if isinstance(raw_w, dict):
        merged: dict[str, float] = {}
        for key in result["weights"]:
            v = raw_w.get(key)
            if (
                v is not None
                and isinstance(v, (int, float))
                and not isinstance(v, bool)
                and math.isfinite(float(v))
                and float(v) >= 0
            ):
                merged[key] = float(v)
            else:
                merged[key] = result["weights"][key]
        if sum(merged.values()) > 0:
            result["weights"] = merged
        else:
            logger.warning(
                "strategy_config.yaml: strategy.weights の合計が 0 以下。デフォルトを使用"
            )

    # float スカラーパラメータ
    for key in (
        "threshold",
        "stop_loss_rate",
        "gap_up_threshold",
        "gap_down_threshold",
        "trailing_stop_atr_mult",
    ):
        v = s.get(key)
        if (
            v is not None
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(float(v))
        ):
            result[key] = float(v)

    # int スカラーパラメータ（0 以上）
    for key in ("min_holding_days", "max_holding_days", "reentry_cooldown_days"):
        v = s.get(key)
        if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool):
            iv = int(v)
            if iv >= 0:
                result[key] = iv

    # sector セクション
    sec = data.get("sector")
    if isinstance(sec, dict):
        v = sec.get("boost")
        if (
            v is not None
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(float(v))
            and float(v) >= 0
        ):
            result["sector_boost"] = float(v)

        v = sec.get("quartile")
        if (
            v is not None
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(float(v))
            and 0.0 < float(v) < 1.0
        ):
            result["sector_quartile"] = float(v)

    # regime セクション
    reg = data.get("regime")
    if isinstance(reg, dict):
        v = reg.get("topix_size_multiplier_weak_bear")
        if (
            v is not None
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(float(v))
            and 0.0 <= float(v) <= 1.0
        ):
            result["topix_size_multiplier_weak_bear"] = float(v)

        v = reg.get("topix_size_multiplier_strong_bear")
        if (
            v is not None
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(float(v))
            and 0.0 <= float(v) <= 1.0
        ):
            result["topix_size_multiplier_strong_bear"] = float(v)

    # rsi_overbought_threshold: strategy セクション配下（50 < x <= 100）
    v = s.get("rsi_overbought_threshold") if isinstance(s, dict) else None
    if (
        v is not None
        and isinstance(v, (int, float))
        and not isinstance(v, bool)
        and math.isfinite(float(v))
        and 50.0 < float(v) <= 100.0
    ):
        result["rsi_overbought_threshold"] = float(v)

    _strategy_config_cache = result
    _strategy_config_mtime = current_mtime
    out = dict(result)
    out["weights"] = dict(result["weights"])
    return out


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


_VALUE_CONFIG_DEFAULTS: dict = {
    "weights": {"per": 0.50, "pbr": 0.30, "div_yield": 0.20},
    "normalization": {"per_mid": 20.0, "pbr_mid": 1.5, "div_yield_max": 3.0},
}

_value_config_cache: dict | None = None
_value_config_cache_mtimes: tuple[float, float] = (-1.0, -1.0)


def _load_value_config() -> dict:
    """strategy_config.yaml の value_score セクションからバリュースコア設定を読み込む。

    value_score セクションが存在しない場合は strategy.toml にフォールバック（後方互換）。
    ファイルが存在しない・読み込み失敗・不正値の場合はデフォルト値にフォールバック。
    yaml/toml の mtime ベースキャッシュにより繰り返し I/O を回避する。
    """
    global _value_config_cache, _value_config_cache_mtimes
    import yaml  # PyYAML

    def _defaults() -> dict:
        return {
            "weights": dict(_VALUE_CONFIG_DEFAULTS["weights"]),
            "normalization": dict(_VALUE_CONFIG_DEFAULTS["normalization"]),
        }

    def _current_mtimes() -> tuple[float, float]:
        toml_path = _STRATEGY_CONFIG_PATH.parent / "strategy.toml"
        y = t = -1.0
        try:
            if _STRATEGY_CONFIG_PATH.exists():
                y = _STRATEGY_CONFIG_PATH.stat().st_mtime
        except OSError:
            pass
        try:
            if toml_path.exists():
                t = toml_path.stat().st_mtime
        except OSError:
            pass
        return (y, t)

    mtimes = _current_mtimes()
    if _value_config_cache is not None and mtimes == _value_config_cache_mtimes:
        c = _value_config_cache
        return {
            "weights": dict(c["weights"]),
            "normalization": dict(c["normalization"]),
        }

    def _cache_and_return(result: dict) -> dict:
        global _value_config_cache, _value_config_cache_mtimes
        _value_config_cache = result
        _value_config_cache_mtimes = mtimes
        return {
            "weights": dict(result["weights"]),
            "normalization": dict(result["normalization"]),
        }

    # 1. strategy_config.yaml の value_score セクションを試みる
    if _STRATEGY_CONFIG_PATH.exists():
        try:
            with open(_STRATEGY_CONFIG_PATH, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict) and isinstance(data.get("value_score"), dict):
                raw = data["value_score"]
                w = {**_VALUE_CONFIG_DEFAULTS["weights"], **(raw.get("weights") or {})}
                n = {
                    **_VALUE_CONFIG_DEFAULTS["normalization"],
                    **(raw.get("normalization") or {}),
                }
                if any(v < 0 for v in w.values()) or sum(w.values()) <= 0:
                    logger.warning(
                        "strategy_config.yaml: value_score.weights が不正。デフォルトを使用"
                    )
                    return _cache_and_return(_defaults())
                if any(n.get(k, 0) <= 0 for k in ("per_mid", "pbr_mid", "div_yield_max")):
                    logger.warning(
                        "strategy_config.yaml: value_score.normalization に 0 以下の値。デフォルトを使用"
                    )
                    return _cache_and_return(_defaults())
                return _cache_and_return({"weights": dict(w), "normalization": dict(n)})
        except Exception as exc:
            logger.warning("strategy_config.yaml (value_score) 読み込み失敗: %s", exc)

    # 2. 後方互換: strategy.toml フォールバック
    toml_path = _STRATEGY_CONFIG_PATH.parent / "strategy.toml"
    raw_toml: dict = {}
    if toml_path.exists():
        try:
            with open(toml_path, "rb") as f:
                raw_toml = tomllib.load(f).get("value_score", {})
        except Exception as exc:
            logger.warning("strategy.toml 読み込み失敗: %s (デフォルトを使用)", exc)

    w = {**_VALUE_CONFIG_DEFAULTS["weights"], **(raw_toml.get("weights") or {})}
    n = {
        **_VALUE_CONFIG_DEFAULTS["normalization"],
        **(raw_toml.get("normalization") or {}),
    }

    if any(v < 0 for v in w.values()) or sum(w.values()) <= 0:
        logger.warning("value_score.weights が不正（負値または合計<=0）。デフォルトを使用")
        return _cache_and_return(_defaults())
    if any(n.get(k, 0) <= 0 for k in ("per_mid", "pbr_mid", "div_yield_max")):
        logger.warning("value_score.normalization に 0 以下の値。デフォルトを使用")
        return _cache_and_return(_defaults())

    return _cache_and_return({"weights": dict(w), "normalization": dict(n)})


def _compute_value_score(feat: dict[str, Any], config: dict) -> float | None:
    """バリュースコア（PER・PBR・配当利回りの加重平均）。

    各指標を 0〜1 に正規化し、config["weights"] で加重平均する。
    欠損指標は除外して残りの有効指標で重み正規化する（全欠損時は None）。
    重みと正規化基準値は config/strategy.toml で管理する。
    """
    w = config["weights"]
    n = config["normalization"]
    scores: dict[str, float] = {}

    per = feat.get("per")
    if per is not None and per > 0 and math.isfinite(per):
        scores["per"] = 1.0 / (1.0 + per / n["per_mid"])

    pbr = feat.get("pbr")
    if pbr is not None and pbr > 0 and math.isfinite(pbr):
        scores["pbr"] = 1.0 / (1.0 + pbr / n["pbr_mid"])

    dy = feat.get("div_yield")
    if dy is not None and dy > 0 and math.isfinite(dy):
        scores["div_yield"] = min(dy / n["div_yield_max"], 1.0)

    if not scores:
        return None
    total_w = sum(w[k] for k in scores)
    if total_w <= 0:
        return None
    return sum(w[k] * v for k, v in scores.items()) / total_w


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


def _get_topix_size_multiplier(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    size_multiplier_weak_bear: float = _TOPIX_SIZE_MULTIPLIER_WEAK_BEAR,
    size_multiplier_strong_bear: float = _TOPIX_SIZE_MULTIPLIER_STRONG_BEAR,
) -> float:
    """TOPIX の MA クロス状態に基づく size_multiplier を返す。

    topix_daily に事前計算済みの ma25/ma75/ma200 を参照する。
    強いベア判定（MA75 < MA200）が弱いベア（MA25 < MA75）に常に優先する。
    - MA75 < MA200（強いベア）: size_multiplier_strong_bear を返す（デフォルト 0.0）
    - MA25 < MA75（弱いベア）: size_multiplier_weak_bear を返す（デフォルト 0.5）
    - それ以外（強気）: 1.0 を返す
    - MA が NULL（データ不足）またはレコードなし: 安全側フォールバックとして 1.0 を返す

    Args:
        conn:                       DuckDB 接続。topix_daily テーブルを参照する。
        target_date:                基準日（この日以前の最新 TOPIX を使用）。
        size_multiplier_weak_bear:  弱いベア時の size_multiplier（MA25 < MA75）。
        size_multiplier_strong_bear: 強いベア時の size_multiplier（MA75 < MA200）。

    Returns:
        size_multiplier（設定値に依存。デフォルトは strong_bear=0.0 / weak_bear=0.5 / bull=1.0）。
    """
    try:
        row = conn.execute(
            """
            SELECT ma25, ma75, ma200
            FROM topix_daily
            WHERE date = (SELECT MAX(date) FROM topix_daily WHERE date <= ?)
            """,
            [target_date],
        ).fetchone()
    except Exception:
        logger.debug(
            "_get_topix_size_multiplier: topix_daily テーブルが存在しないため 1.0 を返す date=%s",
            target_date,
        )
        return 1.0

    if row is None or row[0] is None or row[1] is None or row[2] is None:
        return 1.0

    ma25, ma75, ma200 = float(row[0]), float(row[1]), float(row[2])
    if ma75 < ma200:
        return size_multiplier_strong_bear
    if ma25 < ma75:
        return size_multiplier_weak_bear
    return 1.0


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
    sector_quartile: float = _SECTOR_QUARTILE,
) -> tuple[frozenset[str], frozenset[str], dict[str, str]]:
    """セクター20営業日リターンを算出し、上位・下位セクターと銘柄→セクターマップを返す。

    stocks テーブルの全銘柄 × prices_daily で等加重セクターリターンを計算し、
    上位 sector_quartile / 下位 sector_quartile のセクターを分類する。

    データ欠損・セクター未登録銘柄は安全側（BUY 許可・スコアブーストなし）に倒す。

    Returns:
        (top_sectors, bottom_sectors, sector_map)
        - top_sectors:    上位 sector_quartile セクター名の frozenset
        - bottom_sectors: 下位 sector_quartile セクター名の frozenset
        - sector_map:     {code: sector}（NULL/空文字のセクターは除外）

    Note: 有効セクターが1つの場合は top と bottom が同一になるためフィルタ無効。
    """
    # sector_map を取得（NULL / 空白のみは除外）
    sector_rows = conn.execute("SELECT code, NULLIF(TRIM(sector), '') FROM stocks").fetchall()
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
    top_n = max(1, math.ceil(n * sector_quartile))
    bottom_n = max(1, math.ceil(n * sector_quartile))

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
# ATR / ピーク価格ヘルパー（トレーリングストップ用）
# ---------------------------------------------------------------------------


def _atr_20d(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
) -> float | None:
    """直近 20 本の Average True Range（ATR）を返す。

    True Range = GREATEST(high − low, |high − prev_close|, |low − prev_close|)
    20 本未満のデータしかない場合は None を返す。
    """
    row = conn.execute(
        """
        WITH recent AS (
            SELECT date, high, low, close
            FROM prices_daily
            WHERE code = ? AND date <= ?
            ORDER BY date DESC
            LIMIT 21
        ),
        with_prev AS (
            SELECT
                date,
                high,
                low,
                LAG(close) OVER (ORDER BY date) AS prev_close
            FROM recent
        ),
        tr AS (
            SELECT GREATEST(
                high - low,
                ABS(high - prev_close),
                ABS(low  - prev_close)
            ) AS true_range
            FROM with_prev
            WHERE prev_close IS NOT NULL
        )
        SELECT AVG(true_range), COUNT(*) FROM tr
        """,
        [code, target_date],
    ).fetchone()
    if row is None or row[1] is None or int(row[1]) < 20:
        return None
    return float(row[0])


def _peak_close(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
    sqlite_conn: sqlite3.Connection | None = None,
) -> float | None:
    """すべてのオープンエントリーの最古のエントリー日以降 target_date までの最高 close を返す。

    オープンな position_entries が存在しない場合は None を返す。
    sqlite_conn が指定された場合は position_entries を SQLite から取得する（ライブ実行用）。
    sqlite_conn が None の場合は DuckDB conn から取得する（バックテスト互換）。
    """
    if sqlite_conn is not None:
        # SQLite から最古の未クローズ entry_date を取得
        row = sqlite_conn.execute(
            "SELECT MIN(entry_date) FROM position_entries WHERE code = ? AND sell_date IS NULL",
            [code],
        ).fetchone()
        if row is None or row[0] is None:
            return None
        first_entry_date = date.fromisoformat(str(row[0]))
        # DuckDB から当該期間の最高 close を取得
        price_row = conn.execute(
            "SELECT MAX(close) FROM prices_daily WHERE code = ? AND date >= ? AND date <= ?",
            [code, first_entry_date, target_date],
        ).fetchone()
        if price_row is None or price_row[0] is None:
            return None
        return float(price_row[0])
    else:
        row = conn.execute(
            """
            WITH first_entry AS (
                SELECT MIN(entry_date) AS entry_date
                FROM position_entries
                WHERE code = ?
                  AND sell_date IS NULL
            )
            SELECT MAX(pd.close)
            FROM first_entry fe
            JOIN prices_daily pd
              ON pd.date >= fe.entry_date
             AND pd.date <= ?
             AND pd.code = ?
            WHERE fe.entry_date IS NOT NULL
            """,
            [code, target_date, code],
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return float(row[0])


# ---------------------------------------------------------------------------
# 保有日数 / 再エントリー制限ヘルパー
# ---------------------------------------------------------------------------


def _held_days(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
    sqlite_conn: sqlite3.Connection | None = None,
) -> int | None:
    """position_entries から最新の未クローズ entry_date を取得し、
    entry_date 〜 target_date の営業日数を返す（entry_date 当日 = 0）。
    レコードなし → None（チェックスキップ・安全側）。
    sqlite_conn が指定された場合は SQLite から取得する（ライブ実行用）。
    """
    if sqlite_conn is not None:
        row = sqlite_conn.execute(
            "SELECT entry_date FROM position_entries WHERE code = ? AND sell_date IS NULL "
            "ORDER BY entry_date DESC LIMIT 1",
            [code],
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT entry_date FROM position_entries WHERE code = ? AND sell_date IS NULL "
            "ORDER BY entry_date DESC LIMIT 1",
            [code],
        ).fetchone()
    if row is None:
        return None
    entry_date = row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0]))
    if entry_date > target_date:
        return 0
    days = get_trading_days(conn, entry_date, target_date)
    return len(days) - 1  # 0 = entry 当日、5 = 5営業日後


def _is_reentry_blocked(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
    cooldown_days: int = _REENTRY_COOLDOWN_DAYS,
    sqlite_conn: sqlite3.Connection | None = None,
) -> bool:
    """最新の sell_date から target_date までの営業日数が cooldown_days 未満なら True。
    sell_date が NULL またはレコードなしは False（制限なし）。
    sqlite_conn が指定された場合は SQLite から取得する（ライブ実行用）。
    """
    if sqlite_conn is not None:
        row = sqlite_conn.execute(
            "SELECT sell_date FROM position_entries WHERE code = ? AND sell_date IS NOT NULL "
            "ORDER BY sell_date DESC LIMIT 1",
            [code],
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT sell_date FROM position_entries WHERE code = ? AND sell_date IS NOT NULL "
            "ORDER BY sell_date DESC LIMIT 1",
            [code],
        ).fetchone()
    if row is None or row[0] is None:
        return False
    sell_date = row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0]))
    days = get_trading_days(conn, sell_date, target_date)
    return (len(days) - 1) < cooldown_days


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
    is_bear: bool = False,
    min_holding_days: int = _MIN_HOLDING_DAYS,
    max_holding_days: int = _MAX_HOLDING_DAYS,
    trailing_stop_atr: float = _TRAILING_STOP_ATR_MULT,
    stop_loss_rate: float = _STOP_LOSS_RATE,
    sqlite_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """保有ポジションに対してエグジット条件を判定し、SELL シグナルを返す。

    実装済みの条件と優先順序 (StrategyModel.md Section 5.2):
      1. ストップロス: 終値 / avg_price - 1 < -8%（最優先・min_holding_days バイパス）
      2. 決算回避 (earnings_avoidance): 翌営業日が決算発表日（min_holding_days バイパス）
      3. トレーリングストップ: close < peak_close - trailing_stop_atr x ATR_20d（含み益あり時・min_holding_days バイパス）
      4. 時間決済 (time_exit): 保有営業日数 >= max_holding_days（min_holding_days バイパス）
      5. 最低保有日数 (min_holding_days): 上記1-4 はバイパスされる
      6. スコア低下: final_score が threshold 未満

    Args:
        conn:                DuckDB 接続。
        target_date:         シグナル生成対象日。
        score_map:           {code: final_score} の辞書。
        threshold:           BUY/SELL 判定の閾値。
        is_bear:             True のとき最低保有日数チェックをスキップする（Bear レジーム例外）。
        min_holding_days:    SELL を抑制する最低保有営業日数（デフォルト: _MIN_HOLDING_DAYS）。
        max_holding_days:    この営業日数以上保有した銘柄に time_exit SELL を発動（デフォルト: _MAX_HOLDING_DAYS）。
                             ストップロス・決算回避より低優先。min_holding_days は無視して発火する。
        trailing_stop_atr:   ATR 乗数。peak_close − N×ATR を下回ったら trailing_stop SELL（含み益ありの場合のみ）。
        stop_loss_rate:      ストップロス閾値（デフォルト: _STOP_LOSS_RATE）。pnl_rate がこの値以下で SELL。

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
        if pnl_rate <= stop_loss_rate:
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

        # トレーリングストップ（含み益保護）: min_holding_days を無視して発火
        # peak_close > avg_price のとき（含み益あり）のみ適用
        peak = _peak_close(conn, code, target_date, sqlite_conn=sqlite_conn)
        if peak is not None and peak > avg_price:
            atr = _atr_20d(conn, code, target_date)
            if atr is not None and close < peak - trailing_stop_atr * atr:
                logger.debug(
                    "_generate_sell_signals: %s trailing_stop"
                    " close=%.2f peak=%.2f atr=%.2f mult=%.1f date=%s",
                    code,
                    close,
                    peak,
                    atr,
                    trailing_stop_atr,
                    target_date,
                )
                sell_signals.append(
                    {
                        "code": code,
                        "score": final_score,
                        "reason": "trailing_stop",
                    }
                )
                continue

        # 時間決済（最大保有期間超過）: min_holding_days を無視して発火
        held = _held_days(conn, code, target_date, sqlite_conn=sqlite_conn)
        if held is not None and held >= max_holding_days:
            logger.debug(
                "_generate_sell_signals: %s 保有 %d 営業日 >= max %d — time_exit date=%s",
                code,
                held,
                max_holding_days,
                target_date,
            )
            sell_signals.append(
                {
                    "code": code,
                    "score": final_score,
                    "reason": "time_exit",
                }
            )
            continue

        # 最低保有日数チェック（Bear レジーム時はスキップ）
        if is_bear:
            logger.debug(
                "_generate_sell_signals: Bear レジームのため最低保有日数チェックをスキップ: %s date=%s",
                code,
                target_date,
            )
        else:
            if held is not None and held < min_holding_days:
                logger.debug(
                    "_generate_sell_signals: %s 保有 %d 営業日（最低 %d 日）— SELL 抑制 date=%s",
                    code,
                    held,
                    min_holding_days,
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

    logger.debug("_generate_sell_signals: %d シグナル date=%s", len(sell_signals), target_date)
    return sell_signals


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def generate_signals(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    threshold: float | None = None,
    weights: dict[str, float] | None = None,
    event_dates: dict[date, str] | None = None,
    scope: BacktestScope | None = None,
    min_holding_days: int | None = None,
    max_holding_days: int | None = None,
    trailing_stop_atr: float | None = None,
    topix_size_multiplier_weak_bear: float | None = None,
    topix_size_multiplier_strong_bear: float | None = None,
    use_ma200_filter: bool = False,
    volume_breakout_threshold: float | None = None,
    *,
    use_stock_ma_cross_filter: bool = False,
    stock_ma_cross_weak_bear_multiplier: float = 0.5,
    regime_provider: RegimeProvider | None = None,
    sqlite_conn: sqlite3.Connection | None = None,
) -> int:
    """features テーブルを読み込み、売買シグナルを生成して signals テーブルへ書き込む。

    target_date 分をすべて削除してから挿入する日付単位の置換（冪等）。

    Args:
        conn:              DuckDB 接続。features / ai_scores / positions テーブルを参照する。
        target_date:       シグナル生成日。
        threshold:         BUY シグナル生成の final_score 閾値（None の場合は config から読み込む）。
        weights:           ファクター重みの辞書（None の場合は config から読み込む）。
        event_dates:       {event_date: event_name} の辞書。翌営業日がイベント日の場合、
                           BUY の size_multiplier を 0.5 に縮小する。省略時はイベントなし扱い。
        scope:             BacktestScope インスタンス。mode='manual_codes' かつ codes が指定されている場合、
                           features クエリを指定銘柄に絞る。省略時（None）は全銘柄が対象。
        min_holding_days:  SELL を抑制する最低保有営業日数（None の場合は config から読み込む）。
                           ストップロスと Bear レジーム時は保有日数に関わらず SELL が発生する。
        max_holding_days:  この営業日数以上保有した銘柄に time_exit SELL を発動（None の場合は config から読み込む）。
                           1 以上を指定すること。
        trailing_stop_atr: ATR 乗数。peak_close − N×ATR を下回ったら trailing_stop SELL。
                           正の値を指定すること（None の場合は config から読み込む）。
        topix_size_multiplier_weak_bear: MA25 < MA75（弱いベア）時の BUY size_multiplier（0 <= x <= 1）。
                           None の場合は strategy_config.yaml から読み込む。
        topix_size_multiplier_strong_bear: MA75 < MA200（強いベア）時の BUY size_multiplier（0 <= x <= 1）。
                           None の場合は strategy_config.yaml から読み込む。
        use_ma200_filter:  True のとき株価が 200 日移動平均線を下回る銘柄（ma200_dev < 0）
                           の BUY を抑制する。ma200_dev が None の場合は安全側で BUY 許可。
                           False（デフォルト）では無効。
        use_stock_ma_cross_filter: True のとき銘柄単位の MA クロスで BUY を段階制御する。
                           - ma75_dev < 0（株価が MA75 を下回る）→ BUY スキップ（強ベア）
                           - ma75_dev >= 0 かつ ma25_dev < 0 → size_multiplier を縮小（弱ベア）
                           ma75_dev / ma25_dev のどちらかが None の場合は安全側で BUY 許可。
                           False（デフォルト）では無効。
        stock_ma_cross_weak_bear_multiplier: 弱ベア時（ma75_dev >= 0 かつ ma25_dev < 0）の
                           size_multiplier 縮小率（0 < x <= 1）。デフォルト 0.5。
                           use_stock_ma_cross_filter=True のときのみ有効。
        volume_breakout_threshold: 指定した場合、volume_ratio（20日平均出来高比）が
                           この値を下回る銘柄の BUY を抑制する（例: 1.5 = 1.5倍未満を除外）。
                           volume_ratio が None の場合は安全側で BUY 許可。
                           None（デフォルト）で無効。
        regime_provider:   レジームラベルを返すプロバイダー。明示的に渡した場合は
                           ENABLE_AI_SENTIMENT の設定値より優先される。省略時は
                           ENABLE_AI_SENTIMENT フラグに基づいて自動生成する。

    Returns:
        signals テーブルへ書き込んだシグナル数（BUY + SELL の合計）。
    """
    _cfg = _load_strategy_config()
    if threshold is None:
        threshold = _cfg["threshold"]
    if weights is None:
        weights = _cfg["weights"]
    if min_holding_days is None:
        min_holding_days = _cfg["min_holding_days"]
    if max_holding_days is None:
        max_holding_days = _cfg["max_holding_days"]
    if trailing_stop_atr is None:
        trailing_stop_atr = _cfg["trailing_stop_atr_mult"]
    sector_boost = _cfg["sector_boost"]

    if min_holding_days < 0:
        raise ValueError(f"min_holding_days は 0 以上を指定してください: {min_holding_days}")
    if max_holding_days < 1:
        raise ValueError(f"max_holding_days は 1 以上を指定してください: {max_holding_days}")
    if max_holding_days <= min_holding_days:
        logger.warning(
            "max_holding_days (%d) が min_holding_days (%d) 以下です。"
            " time_exit が min_holding_days チェックより先に発火するため、"
            " min_holding_days は実質的に無効になります。",
            max_holding_days,
            min_holding_days,
        )
    if trailing_stop_atr <= 0:
        raise ValueError(f"trailing_stop_atr は正の値を指定してください: {trailing_stop_atr}")
    # weights を _DEFAULT_WEIGHTS でフォールバック補完し、合計が 1.0 でなければ再スケール
    # 未知キー・非数値・NaN/Inf・負値は無視して既知キー（_DEFAULT_WEIGHTS）のみを受け付ける
    allowed = set(_DEFAULT_WEIGHTS)
    user_w: dict[str, float] = {}
    for k, v in (weights or {}).items():
        if k not in allowed:
            continue
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0:
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

    _weak_bear: float = (
        topix_size_multiplier_weak_bear
        if topix_size_multiplier_weak_bear is not None
        else _cfg["topix_size_multiplier_weak_bear"]
    )
    _strong_bear: float = (
        topix_size_multiplier_strong_bear
        if topix_size_multiplier_strong_bear is not None
        else _cfg["topix_size_multiplier_strong_bear"]
    )
    if _strong_bear > _weak_bear:
        raise ValueError(
            f"topix_size_multiplier_strong_bear ({_strong_bear}) は"
            f" topix_size_multiplier_weak_bear ({_weak_bear}) 以下にしてください"
        )
    topix_multiplier = _get_topix_size_multiplier(
        conn,
        target_date,
        size_multiplier_weak_bear=_weak_bear,
        size_multiplier_strong_bear=_strong_bear,
    )
    size_multiplier = min(size_multiplier, topix_multiplier)

    # 1. features 読み込み（scope.mode="manual_codes" の場合は対象銘柄に限定）
    _scope_codes: frozenset[str] | None = None
    if scope is not None and scope.mode == "manual_codes":
        # codes が指定されている場合（空リストを含む）
        _scope_codes = frozenset(scope.codes) if scope.codes else frozenset()

    _select_cols = ", ".join(_FEATURES_SELECT_COLS)
    if _scope_codes is not None:
        if _scope_codes:
            # codes が空でない場合
            placeholders = ", ".join(["?" for _ in _scope_codes])
            feat_rows = conn.execute(
                f"SELECT {_select_cols} FROM features WHERE date = ? AND code IN ({placeholders})",
                [target_date, *_scope_codes],
            ).fetchall()
        else:
            # codes が空リストの場合 → 銘柄なし → 空結果
            feat_rows = []
    else:
        feat_rows = conn.execute(
            f"SELECT {_select_cols} FROM features WHERE date = ?",
            [target_date],
        ).fetchall()
    features = [dict(zip(_FEATURES_SELECT_COLS, r)) for r in feat_rows]

    if not features:
        logger.warning(
            "generate_signals: features が空 date=%s — BUY シグナルなし、SELL 判定のみ実施",
            target_date,
        )

    # 2. AI スコア読み込み（ENABLE_AI_SENTIMENT=false 時はスキップ）
    from kabusys.config import Settings

    ai_enabled = Settings().enable_ai_sentiment
    ai_map: dict[str, dict]
    if ai_enabled:
        ai_rows = conn.execute(
            "SELECT code, ai_score FROM ai_scores WHERE date = ?",
            [target_date],
        ).fetchall()
        ai_map = {code: {"ai_score": ai} for code, ai in ai_rows}
    else:
        ai_map = {}

    if regime_provider is None:
        regime_provider = build_regime_provider(conn, ai_enabled)

    # 3. Bear レジーム判定
    regime_is_bear = regime_provider.get_regime(target_date) == "bear"
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
            conn, target_date, sector_quartile=_cfg["sector_quartile"]
        )

    # 4. 各銘柄の final_score 計算（Section 4.1）
    # バリュースコア設定・AI フラグをループ外で1回だけ評価する
    value_config = _load_value_config()
    scored: list[dict[str, Any]] = []
    for feat in features:
        code = feat["code"]
        s_mom = _compute_momentum_score(feat)
        s_val = _compute_value_score(feat, value_config)
        s_vol = _compute_volatility_score(feat)
        s_liq = _compute_liquidity_score(feat)

        # AI ニューススコア（未登録の場合は中立 0.5 で補完）
        ai_raw = ai_map.get(code, {}).get("ai_score")
        s_news = _sigmoid(ai_raw) if ai_raw is not None else None
        if s_news is None and ai_enabled:
            logger.warning(
                "generate_signals: AI スコアが見つかりません。デフォルト値(0.5)でシグナルを生成します code=%s date=%s",
                code,
                feat.get("date", "unknown"),
            )

        # None のコンポーネントは中立値 0.5 で補完（欠損銘柄の不当な降格を防ぐ）
        final_score = (
            weights["momentum"] * (s_mom if s_mom is not None else 0.5)
            + weights["value"] * (s_val if s_val is not None else 0.5)
            + weights["volatility"] * (s_vol if s_vol is not None else 0.5)
            + weights["liquidity"] * (s_liq if s_liq is not None else 0.5)
            + weights["news"] * (s_news if s_news is not None else 0.5)
        )
        # セクター強弱スコア補正（上位セクターは +sector_boost）
        sector = sector_map.get(code, "")
        if sector and sector in top_sectors:
            old_score = final_score
            final_score += sector_boost
            logger.debug(
                "sector boost: %s sector=%s score %.4f→%.4f date=%s",
                code,
                sector,
                old_score,
                final_score,
                target_date,
            )
            boosted_count += 1
        scored.append(
            {
                "code": code,
                "score": final_score,
                "rsi_14": feat.get("rsi_14"),
                "ma200_dev": feat.get("ma200_dev"),
                "ma75_dev": feat.get("ma75_dev"),
                "ma25_dev": feat.get("ma25_dev"),
                "volume_ratio": feat.get("volume_ratio"),
            }
        )

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
    _gap_up = _cfg["gap_up_threshold"]
    _gap_down = _cfg["gap_down_threshold"]
    _rsi_threshold = _cfg["rsi_overbought_threshold"]
    buy_signals: list[dict] = []
    if not regime_is_bear and not breadth_stop:
        # 3c. ギャップ比率を一括取得（BUY 生成が必要な場合のみ実行）
        gap_ratios = _fetch_gap_ratios(
            conn, [r["code"] for r in scored if r["score"] >= threshold], target_date
        )
        gap_suppressed = 0
        rsi_suppressed = 0
        ma200_suppressed = 0
        stock_ma_cross_suppressed = 0
        stock_ma_cross_reduced = 0
        volume_suppressed = 0
        sector_suppressed = 0
        reentry_suppressed = 0
        earnings_suppressed = 0
        for rank, r in enumerate(scored, 1):
            if r["score"] < threshold:
                continue
            # RSI 過熱フィルタ（rsi_14 が None の場合は安全側で許可）
            rsi = r.get("rsi_14")
            if rsi is not None and rsi > _rsi_threshold:
                logger.debug(
                    "rsi filter: %s rsi=%.1f — BUY を抑制 date=%s",
                    r["code"],
                    rsi,
                    target_date,
                )
                rsi_suppressed += 1
                continue
            # 200MA バイナリフィルタ（use_ma200_filter=True のとき MA200 下の銘柄を抑制）
            if use_ma200_filter:
                ma200_dev_val = r.get("ma200_dev")
                if ma200_dev_val is not None and ma200_dev_val < 0:
                    logger.debug(
                        "ma200 filter: %s ma200_dev=%.4f — BUY を抑制 date=%s",
                        r["code"],
                        ma200_dev_val,
                        target_date,
                    )
                    ma200_suppressed += 1
                    continue
            # 銘柄単位 MA クロスフィルタ
            # - ma75_dev < 0（株価が MA75 を下回る）→ BUY スキップ（強ベア）
            # - ma75_dev >= 0 かつ ma25_dev < 0 → size_multiplier を縮小（弱ベア）
            # - どちらかが None（データ不足）→ 安全側で制御しない
            stock_ma_cross_size_multiplier: float | None = None
            if use_stock_ma_cross_filter:
                ma75_dev_val = r.get("ma75_dev")
                ma25_dev_val = r.get("ma25_dev")
                if ma75_dev_val is not None and ma75_dev_val < 0:
                    logger.debug(
                        "stock ma cross filter: %s ma75_dev=%.4f — BUY を抑制 date=%s",
                        r["code"],
                        ma75_dev_val,
                        target_date,
                    )
                    stock_ma_cross_suppressed += 1
                    continue
                if (
                    ma75_dev_val is not None
                    and ma75_dev_val >= 0
                    and ma25_dev_val is not None
                    and ma25_dev_val < 0
                ):
                    logger.debug(
                        "stock ma cross filter: %s ma25_dev=%.4f — size 縮小 date=%s",
                        r["code"],
                        ma25_dev_val,
                        target_date,
                    )
                    stock_ma_cross_size_multiplier = stock_ma_cross_weak_bear_multiplier
                    stock_ma_cross_reduced += 1
            # 出来高ブレイクアウトフィルタ（threshold 指定時に volume_ratio が閾値未満の銘柄を抑制）
            if volume_breakout_threshold is not None:
                volume_ratio_val = r.get("volume_ratio")
                if volume_ratio_val is not None and volume_ratio_val < volume_breakout_threshold:
                    logger.debug(
                        "volume breakout filter: %s volume_ratio=%.2f < threshold=%.2f — BUY を抑制 date=%s",
                        r["code"],
                        volume_ratio_val,
                        volume_breakout_threshold,
                        target_date,
                    )
                    volume_suppressed += 1
                    continue
            gap = gap_ratios.get(r["code"])
            if gap is not None and (
                gap > _gap_up + _GAP_THRESHOLD_EPSILON or gap <= _gap_down + _GAP_THRESHOLD_EPSILON
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
            if _is_reentry_blocked(
                conn,
                r["code"],
                target_date,
                cooldown_days=_cfg["reentry_cooldown_days"],
                sqlite_conn=sqlite_conn,
            ):
                logger.debug("reentry blocked: %s — date=%s", r["code"], target_date)
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
            per_signal_multiplier = size_multiplier
            if stock_ma_cross_size_multiplier is not None:
                per_signal_multiplier = min(per_signal_multiplier, stock_ma_cross_size_multiplier)
            buy_signals.append(
                {
                    "code": r["code"],
                    "score": r["score"],
                    "rank": rank,
                    "size_multiplier": per_signal_multiplier,
                }
            )
        if rsi_suppressed:
            logger.info(
                "generate_signals: rsi filter — %d 銘柄を RSI 過熱(%s超)で抑制 date=%s",
                rsi_suppressed,
                _rsi_threshold,
                target_date,
            )
        if ma200_suppressed:
            logger.info(
                "generate_signals: ma200 filter — %d 銘柄を MA200 下で抑制 date=%s",
                ma200_suppressed,
                target_date,
            )
        if stock_ma_cross_suppressed:
            logger.info(
                "generate_signals: stock ma cross filter — %d 銘柄を MA75 下で抑制 date=%s",
                stock_ma_cross_suppressed,
                target_date,
            )
        if stock_ma_cross_reduced:
            logger.info(
                "generate_signals: stock ma cross filter — %d 銘柄を MA25 下で size 縮小 date=%s",
                stock_ma_cross_reduced,
                target_date,
            )
        if volume_suppressed:
            logger.info(
                "generate_signals: volume breakout filter — %d 銘柄を出来高不足で抑制 date=%s",
                volume_suppressed,
                target_date,
            )
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
    sell_signals = _generate_sell_signals(
        conn,
        target_date,
        score_map,
        threshold,
        is_bear=regime_is_bear,
        min_holding_days=min_holding_days,
        max_holding_days=max_holding_days,
        trailing_stop_atr=trailing_stop_atr,
        stop_loss_rate=_cfg["stop_loss_rate"],
        sqlite_conn=sqlite_conn,
    )

    # SELL 対象銘柄は BUY から除外し、ランクを連番で再付与（SELL 優先ポリシー）
    sell_codes = {s["code"] for s in sell_signals}
    buy_signals = [b for b in buy_signals if b["code"] not in sell_codes]
    buy_signals.sort(key=lambda x: x["score"], reverse=True)
    for i, b in enumerate(buy_signals, 1):
        b["rank"] = i

    # 8. signals テーブルへ日付単位の置換（トランザクション＋バルク挿入で原子性を保証）
    buy_params = [
        (target_date, r["code"], r["score"], r["rank"], r.get("size_multiplier", size_multiplier))
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
