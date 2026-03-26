"""銘柄選定・配分重み計算。

PortfolioConstruction.md Section 5〜7 に基づく純粋関数群。
DB 参照なし — メモリ内計算のみ。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


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
        logger.warning(
            "calc_score_weights: 全銘柄のスコアが 0.0。等金額配分にフォールバック。"
        )
        return calc_equal_weights(candidates)

    return {c["code"]: c.get("score", 0.0) / total for c in candidates}
