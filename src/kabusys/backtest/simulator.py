# src/kabusys/backtest/simulator.py
"""
PortfolioSimulator — 擬似約定とポートフォリオ状態管理。

BacktestFramework.md Section 4.3 のスリッページ・手数料モデルに従う。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class DailySnapshot:
    """日次ポートフォリオのスナップショット。"""

    date: date
    cash: float
    positions: dict[str, int]     # code → 株数
    portfolio_value: float        # cash + 時価評価額


@dataclass
class TradeRecord:
    """約定記録。"""

    date: date
    code: str
    side: str                     # "buy" | "sell"
    shares: int
    price: float                  # 約定価格（スリッページ適用後）
    commission: float
    realized_pnl: float | None    # SELL 時のみ。shares*(exit_price - avg_cost) - SELL手数料。BUY手数料は cash から別途控除済みのため含まない。


class PortfolioSimulator:
    """ポートフォリオシミュレータ。

    engine.py から呼び出される。DB 参照は持たない（純粋なメモリ内状態管理）。
    """

    def __init__(self, initial_cash: float) -> None:
        self.cash: float = initial_cash
        self.positions: dict[str, int] = {}          # code → 株数
        self.cost_basis: dict[str, float] = {}       # code → 平均取得単価
        self.history: list[DailySnapshot] = []
        self.trades: list[TradeRecord] = []

    def execute_orders(
        self,
        signals: list[dict],
        open_prices: dict[str, float],
        slippage_rate: float,
        commission_rate: float,
        trading_day: date | None = None,
    ) -> None:
        """シグナルリストを当日 open 価格で約定処理する。

        SELL を先に処理してから BUY を処理する（資金確保のため）。
        SELL は保有全量をクローズする（部分利確・部分損切り非対応）。

        Args:
            signals:       [{"code": str, "side": "buy"|"sell", "shares": int}]
                           sell の場合 shares キーは不要（保有全量をクローズ）。
            open_prices:   code → 当日始値 の辞書。
            slippage_rate: スリッページ率。BUY は +、SELL は -。
            commission_rate: 手数料率（約定金額 × commission_rate）。
            trading_day:   約定日（TradeRecord.date に使用）。None の場合は history[-1].date を使用。
        """
        # SELL を先に処理
        for sig in [s for s in signals if s["side"] == "sell"]:
            self._execute_sell(sig["code"], open_prices, slippage_rate, commission_rate, trading_day)
        # BUY を後に処理
        for sig in [s for s in signals if s["side"] == "buy"]:
            self._execute_buy(
                sig["code"],
                sig.get("shares", 0),
                open_prices,
                slippage_rate,
                commission_rate,
                trading_day,
            )

    def _execute_buy(
        self,
        code: str,
        shares: int,
        open_prices: dict[str, float],
        slippage_rate: float,
        commission_rate: float,
        trading_day: date | None = None,
    ) -> None:
        if shares <= 0:
            logger.debug("execute_orders: BUY %s shares=%d。スキップ。", code, shares)
            return

        open_price = open_prices.get(code)
        if open_price is None:
            logger.warning("execute_orders: BUY %s の始値が取得できません。スキップ。", code)
            return

        entry_price = open_price * (1.0 + slippage_rate)
        cost = shares * entry_price
        commission = cost * commission_rate
        total_cost = cost + commission

        if total_cost > self.cash:
            logger.debug("execute_orders: BUY %s 現金不足（必要: %.0f, 保有: %.0f）。スキップ。",
                         code, total_cost, self.cash)
            return

        self.cash -= total_cost

        # 平均取得単価の更新
        existing_shares = self.positions.get(code, 0)
        existing_cost = self.cost_basis.get(code, 0.0) * existing_shares
        new_total_shares = existing_shares + shares
        self.cost_basis[code] = (existing_cost + cost) / new_total_shares
        self.positions[code] = new_total_shares

        trade_date = trading_day if trading_day is not None else (
            self.history[-1].date if self.history else date(1970, 1, 1)
        )
        self.trades.append(TradeRecord(
            date=trade_date,
            code=code,
            side="buy",
            shares=shares,
            price=entry_price,
            commission=commission,
            realized_pnl=None,
        ))

    def _execute_sell(
        self,
        code: str,
        open_prices: dict[str, float],
        slippage_rate: float,
        commission_rate: float,
        trading_day: date | None = None,
    ) -> None:
        shares = self.positions.get(code, 0)
        if shares <= 0:
            logger.debug("execute_orders: SELL %s 保有なし。スキップ。", code)
            return

        open_price = open_prices.get(code)
        if open_price is None:
            logger.warning("execute_orders: SELL %s の始値が取得できません。スキップ。", code)
            return

        exit_price = open_price * (1.0 - slippage_rate)
        proceeds = shares * exit_price
        commission = proceeds * commission_rate
        net_proceeds = proceeds - commission

        avg_cost = self.cost_basis.get(code, 0.0)
        realized_pnl = shares * (exit_price - avg_cost) - commission

        self.cash += net_proceeds
        del self.positions[code]
        del self.cost_basis[code]

        trade_date = trading_day if trading_day is not None else (
            self.history[-1].date if self.history else date(1970, 1, 1)
        )
        self.trades.append(TradeRecord(
            date=trade_date,
            code=code,
            side="sell",
            shares=shares,
            price=exit_price,
            commission=commission,
            realized_pnl=realized_pnl,
        ))

    def mark_to_market(
        self,
        trading_day: date,
        close_prices: dict[str, float],
    ) -> None:
        """終値でポートフォリオを時価評価し、DailySnapshot を記録する。

        保有株に終値がない場合は 0 で評価し WARNING ログを出す。
        """
        stock_value = 0.0
        for code, shares in self.positions.items():
            price = close_prices.get(code)
            if price is None:
                logger.warning(
                    "mark_to_market: %s の終値が取得できません。0 で評価します。date=%s",
                    code, trading_day,
                )
                price = 0.0
            stock_value += shares * price

        portfolio_value = self.cash + stock_value
        self.history.append(DailySnapshot(
            date=trading_day,
            cash=self.cash,
            positions=dict(self.positions),
            portfolio_value=portfolio_value,
        ))
