"""株数決定・リスク制限・単元株丸め。

PortfolioConstruction.md Section 7、StrategyModel.md Section 6 に基づく純粋関数。
DB 参照なし — メモリ内計算のみ。
"""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


def calc_position_sizes(
    weights: dict[str, float],
    candidates: list[dict],
    portfolio_value: float,
    available_cash: float,
    current_positions: dict[str, int],
    open_prices: dict[str, float],
    allocation_method: str = "risk_based",
    risk_pct: float = 0.005,
    stop_loss_pct: float = 0.08,
    max_position_pct: float = 0.10,
    max_utilization: float = 0.70,
    lot_size: int = 100,
) -> dict[str, int]:
    """allocation_method に応じて各銘柄の発注株数を計算する。

    Args:
        weights:           {code: weight}（equal / score 方式で使用）
        candidates:        [{code, score, signal_rank}, ...]（risk_based 方式でも使用）
        portfolio_value:   総資産（円）
        available_cash:    レジーム乗数適用後の利用可能現金
        current_positions: 既存保有 {code: shares}
        open_prices:       {code: price}
        allocation_method: "equal" | "score" | "risk_based"
        risk_pct:          許容リスク率（risk_based 時）
        stop_loss_pct:     損切り率（risk_based 時）
        max_position_pct:  1銘柄上限（総資産比）
        max_utilization:   投下資金上限（総資産比）
        lot_size:          単元株数

    Returns:
        {code: shares_to_buy}（shares > 0 の銘柄のみ）
    """
    if not candidates:
        return {}

    def _max_per_stock(price: float) -> int:
        if price <= 0:
            return 0
        return math.floor(portfolio_value * max_position_pct / price)

    raw_shares: dict[str, int] = {}

    if allocation_method == "risk_based":
        for c in candidates:
            code = c["code"]
            price = open_prices.get(code)
            if price is None or price <= 0:
                logger.debug("calc_position_sizes: %s の価格が取得できません。スキップ。", code)
                continue

            base_shares = math.floor(
                portfolio_value * risk_pct / (price * stop_loss_pct)
            )
            target_shares = min(base_shares, _max_per_stock(price))
            target_shares = (target_shares // lot_size) * lot_size

            current = current_positions.get(code, 0)
            add_shares = max(0, target_shares - current)
            if add_shares > 0:
                raw_shares[code] = add_shares

    else:  # "equal" or "score"
        for c in candidates:
            code = c["code"]
            price = open_prices.get(code)
            if price is None or price <= 0:
                logger.debug("calc_position_sizes: %s の価格が取得できません。スキップ。", code)
                continue
            w = weights.get(code, 0.0)
            if w <= 0.0:
                continue

            alloc = portfolio_value * w * max_utilization
            base_shares = math.floor(alloc / price)
            target_shares = min(base_shares, _max_per_stock(price))
            target_shares = (target_shares // lot_size) * lot_size

            current = current_positions.get(code, 0)
            add_shares = max(0, target_shares - current)
            if add_shares > 0:
                raw_shares[code] = add_shares

    # aggregate cap: 全銘柄の投資合計が available_cash を超える場合にスケールダウン
    if raw_shares:
        total_cost = sum(
            raw_shares[code] * open_prices[code]
            for code in raw_shares
            if code in open_prices
        )
        if total_cost > available_cash and total_cost > 0:
            scale = available_cash / total_cost
            scaled: dict[str, int] = {}
            for code, shares in raw_shares.items():
                price = open_prices.get(code, 0)
                new_shares = math.floor(shares * scale)
                new_shares = (new_shares // lot_size) * lot_size
                if new_shares > 0:
                    scaled[code] = new_shares
            return scaled

    return raw_shares
