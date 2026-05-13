"""銘柄選定・配分重み計算。

PortfolioConstruction.md Section 5〜7 に基づく純粋関数群。
DB 参照なし — メモリ内計算のみ。
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PORTFOLIO_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "strategy_config.yaml"
_DEFAULT_MAX_POSITIONS = 10


def load_portfolio_config() -> dict:
    """config/strategy_config.yaml の portfolio セクションから設定を読み込む。

    ファイル不在・読み込み失敗・不正値はデフォルト値にフォールバック。
    """
    import yaml

    result: dict = {"max_positions": _DEFAULT_MAX_POSITIONS}
    if not _PORTFOLIO_CONFIG_PATH.exists():
        logger.warning(
            "strategy_config.yaml が見つからないため、max_positions はデフォルト %d を使用します",
            _DEFAULT_MAX_POSITIONS,
        )
        return result
    try:
        with open(_PORTFOLIO_CONFIG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        logger.warning(
            "strategy_config.yaml の読み込みに失敗したため、max_positions はデフォルト %d を使用します",
            _DEFAULT_MAX_POSITIONS,
            exc_info=True,
        )
        return result
    if not isinstance(data, dict):
        return result
    p = data.get("portfolio")
    if not isinstance(p, dict):
        return result
    v = p.get("max_positions")
    if v is None:
        return result
    if (
        isinstance(v, bool)
        or not isinstance(v, (int, float))
        or (isinstance(v, float) and not v.is_integer())
        or int(v) < 1
    ):
        logger.warning(
            "portfolio.max_positions=%r は無効な値のため、デフォルト %d を使用します",
            v,
            _DEFAULT_MAX_POSITIONS,
        )
        return result
    result["max_positions"] = int(v)
    return result


def select_candidates(
    buy_signals: list[dict],
    max_positions: int = 10,
) -> list[dict]:
    """BUY シグナルをスコア降順に並べ、上位 max_positions 件を返す。

    Args:
        buy_signals: [{"code": str, "signal_rank": int, "score": float}, ...]
        max_positions: 最大保有銘柄数（PortfolioConstruction.md 推奨: 5〜15）

    Returns:
        スコア降順の候補リスト（重みなし）。
    """
    if not buy_signals:
        return []
    # score 降順、同点時は signal_rank 昇順（小さい方が優先）でタイブレーク
    sorted_signals = sorted(
        buy_signals,
        key=lambda s: (-s.get("score", 0.0), s.get("signal_rank", 0)),
    )
    return sorted_signals[:max_positions]


def calc_equal_weights(candidates: list[dict]) -> dict[str, float]:
    """等金額配分の重みを返す。

    Args:
        candidates: [{code, score, signal_rank}, ...]

    Returns:
        {code: weight}。candidates が空なら {}。各重みは 1/N。
    """
    if not candidates:
        return {}
    n = len(candidates)
    return {c["code"]: 1.0 / n for c in candidates}


def calc_score_weights(candidates: list[dict]) -> dict[str, float]:
    """スコア加重配分の重みを返す。

    weight_i = score_i / sum(scores)。
    全銘柄のスコアが 0.0 の場合は等金額配分にフォールバックし WARNING を出す。

    Args:
        candidates: [{code, score, signal_rank}, ...]

    Returns:
        {code: weight}。candidates が空なら {}。
    """
    if not candidates:
        return {}

    total = sum(c.get("score", 0.0) for c in candidates)
    if total <= 0.0:
        logger.warning("calc_score_weights: 全銘柄のスコアが 0.0。等金額配分にフォールバック。")
        return calc_equal_weights(candidates)

    return {c["code"]: c.get("score", 0.0) / total for c in candidates}
