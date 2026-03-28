# src/kabusys/execution/risk_manager.py
"""RiskManager — 3段階リスクガード。

Gate 1: check_signal()    — 余力・重複・ポジション上限（発注前）
Gate 2: check_execution() — レート制限・サーキットブレーカー（API 送信前）
Gate 3: check_metrics()   — ドローダウン監視（約定後）
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from kabusys.execution.broker_api import BrokerAPIProtocol
from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    max_position_pct: float = 0.10        # 1銘柄最大投資比率
    max_utilization: float = 0.80         # 全ポジション投下上限（キャッシュ最低20%）
    rate_limit_per_sec: int = 5           # API レート制限（毎秒5回）
    circuit_breaker_errors: int = 10      # ウィンドウ内エラー上限
    circuit_breaker_window_sec: int = 60  # エラーカウントウィンドウ（秒）
    max_drawdown: float = 0.15            # キルスイッチ発動ドローダウン閾値
    initial_portfolio_value: float = 0.0  # セッション開始時の資産評価額


@dataclass
class RiskResult:
    passed: bool
    reason: str = ""


class RiskManager:
    def __init__(
        self,
        broker: BrokerAPIProtocol,
        repo: OrderRepository,
        config: RiskConfig,
    ) -> None:
        self._broker = broker
        self._repo = repo
        self._config = config

        # Gate 2: トークンバケツ
        self._tokens: float = float(config.rate_limit_per_sec)
        self._last_refill: float = time.monotonic()

        # Gate 2: サーキットブレーカー
        self._cb_state: str = "CLOSED"  # "CLOSED" | "OPEN" | "HALF_OPEN"
        self._cb_error_times: list[float] = []
        self._cb_open_at: float = 0.0

    # ------------------------------------------------------------------
    # Gate 1: シグナルレベル（発注前）
    # ------------------------------------------------------------------

    def check_signal(
        self,
        signal_id: str,
        code: str,
        order_value: float,
    ) -> RiskResult:
        """余力・重複・ポジション上限を検査する。"""
        # 1. 余力チェック
        cash = self._broker.get_available_cash()
        if cash < order_value:
            return RiskResult(False, f"余力不足: 余力={cash:.0f}円, 発注額={order_value:.0f}円")

        # 2. 重複チェック（active 注文が存在するか）
        existing = self._repo.get_by_signal(signal_id)
        _TERMINAL = {OrderState.Closed, OrderState.Cancelled, OrderState.Rejected}
        active = [r for r in existing if r.state not in _TERMINAL]
        if active:
            return RiskResult(False, f"重複注文: signal_id={signal_id} の active 注文が存在します")

        # 3. ポジション上限チェック
        positions = self._broker.get_positions()
        total_market_value = sum(
            p.qty * p.current_price
            for p in positions
            if p.current_price is not None
        )
        # 同銘柄の現在評価額
        same_code_value = sum(
            p.qty * p.current_price
            for p in positions
            if p.code == code and p.current_price is not None
        )
        # 総資産 = キャッシュ + ポジション時価評価額（current_price が None のものは avg_price でフォールバック）
        total_fallback = sum(
            p.qty * (p.current_price if p.current_price is not None else p.avg_price)
            for p in positions
        )
        total_assets = cash + total_fallback

        # 3a. 1銘柄上限
        if total_assets > 0:
            new_position_value = same_code_value + order_value
            if new_position_value / total_assets > self._config.max_position_pct:
                return RiskResult(
                    False,
                    f"ポジション上限超過: 銘柄={code}, "
                    f"新規評価額={new_position_value:.0f}円 / 総資産={total_assets:.0f}円 "
                    f"> {self._config.max_position_pct:.0%}",
                )

        # 3b. 全体上限
        # NOTE: 分母はセッション開始時固定値を優先する。
        # live total_assets を分母にすると含み益が増えた場合に上限が緩むため、
        # 保守的な設計として initial_portfolio_value を基準にする。
        utilization_base = (
            self._config.initial_portfolio_value
            if self._config.initial_portfolio_value > 0
            else total_assets
        )
        if utilization_base > 0:
            new_total_market = total_market_value + order_value
            if new_total_market / utilization_base > self._config.max_utilization:
                return RiskResult(
                    False,
                    f"全体上限超過: 全ポジション評価額+発注額={new_total_market:.0f}円 / 総資産={utilization_base:.0f}円 "
                    f"> {self._config.max_utilization:.0%}",
                )

        return RiskResult(True)
