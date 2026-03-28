"""セクター集中制限・レジーム乗数。

PortfolioConstruction.md Section 8〜9 に基づく純粋関数。
DB 参照なし — メモリ内計算のみ。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def apply_sector_cap(
    candidates: list[dict],
    sector_map: dict[str, str],
    portfolio_value: float,
    current_positions: dict[str, int],
    price_map: dict[str, float],
    max_sector_pct: float = 0.30,
    sell_codes: set[str] | None = None,
) -> list[dict]:
    """同一セクターの既存保有比率が max_sector_pct を超える場合、そのセクターの新規候補を除外する。

    Args:
        candidates:        [{code, score, signal_rank}, ...]（重みなし）
        sector_map:        {code: sector}。コードが存在しないものは "unknown" 扱い。
        portfolio_value:   総資産（円）
        current_positions: 既存保有 {code: shares}
        price_map:         {code: price}。open・close どちらの価格マップも受け取れる。
        max_sector_pct:    1セクターの最大保有比率
        sell_codes:        当日売却予定のコード集合。エクスポージャー計算から除外する。

    Returns:
        セクター上限チェック後の candidates（同じ {code, score, signal_rank} 形式）。
        "unknown" セクターは max_sector_pct を適用しない（除外しない）。
    """
    if not candidates or portfolio_value <= 0:
        return candidates

    excluded = sell_codes or set()

    # 既存保有のセクター別時価を計算（当日売却予定銘柄を除外）
    sector_exposure: dict[str, float] = {}
    for code, shares in current_positions.items():
        if code in excluded:
            continue
        sector = sector_map.get(code, "unknown")
        if sector == "unknown":
            continue
        price = price_map.get(code, 0.0)
        # TODO: price が欠損（0.0）の場合、エクスポージャーが過少見積りされブロックが外れる。
        #       将来的には前日終値や取得原価などのフォールバック価格を使う拡張を検討。
        sector_exposure[sector] = sector_exposure.get(sector, 0.0) + shares * price

    # 超過セクターの集合を作成
    blocked_sectors: set[str] = set()
    for sector, exposure in sector_exposure.items():
        if exposure / portfolio_value >= max_sector_pct:
            blocked_sectors.add(sector)
            logger.debug(
                "apply_sector_cap: セクター '%s' が上限超過 (%.1f%% > %.1f%%)",
                sector, exposure / portfolio_value * 100, max_sector_pct * 100,
            )

    if not blocked_sectors:
        return candidates

    # 候補をフィルタ
    filtered = []
    for c in candidates:
        sector = sector_map.get(c["code"], "unknown")
        if sector == "unknown" or sector not in blocked_sectors:
            filtered.append(c)
        else:
            logger.debug(
                "apply_sector_cap: %s（%s）を除外（セクター上限）", c["code"], sector
            )

    return filtered


def calc_regime_multiplier(regime: str) -> float:
    """市場レジームに応じた投下資金乗数を返す。

    market_regime.regime_label は小文字で格納される（regime_detector.py 実装準拠）。
    "bull"    → 1.0（通常運用）
    "neutral" → 0.7（やや縮小）
    "bear"    → 0.3（大幅縮小）
    その他    → 1.0（未知レジームは Bull 相当でフォールバック）

    【重要】Bear レジームで BUY シグナルが生成されない理由:
    generate_signals() は regime が Bear の場合 BUY シグナルを一切生成しない
    (StrategyModel.md Section 5.1)。multiplier=0.3 は Neutral 等の中間局面向けの
    追加セーフガード。

    Args:
        regime: market_regime.regime_label の値（小文字）

    Returns:
        投下資金乗数（0.0〜1.0）
    """
    _MULTIPLIER_MAP: dict[str, float] = {
        "bull": 1.0,
        "neutral": 0.7,
        "bear": 0.3,
    }
    multiplier = _MULTIPLIER_MAP.get(regime)
    if multiplier is None:
        logger.warning(
            "calc_regime_multiplier: 未知のレジーム '%s'。1.0 でフォールバック。", regime
        )
        return 1.0
    return multiplier
