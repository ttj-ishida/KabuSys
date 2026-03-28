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

_TERMINAL_STATES: frozenset[OrderState] = frozenset(
    {OrderState.Closed, OrderState.Cancelled, OrderState.Rejected}
)


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
        self._cb_open_observed: bool = False  # OPEN 状態を一度返したか

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
        active = [r for r in existing if r.state not in _TERMINAL_STATES]
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

    # ------------------------------------------------------------------
    # Gate 2: エグゼキューションレベル（API 送信前）
    # ------------------------------------------------------------------

    def check_execution(self) -> RiskResult:
        """レート制限・サーキットブレーカーを検査する。"""
        # サーキットブレーカー
        cb = self._check_circuit_breaker()
        if not cb.passed:
            return cb

        # レート制限（トークンバケツ）
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            float(self._config.rate_limit_per_sec),
            self._tokens + elapsed * self._config.rate_limit_per_sec,
        )
        self._last_refill = now

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return RiskResult(True)

        return RiskResult(False, f"レート制限: {self._config.rate_limit_per_sec}回/秒を超過")

    def record_api_error(self) -> None:
        """API エラーを記録する（send_order 失敗時に呼ぶ）。"""
        now = time.monotonic()
        window = self._config.circuit_breaker_window_sec
        if window > 0:
            self._cb_error_times = [t for t in self._cb_error_times if now - t < window]
        self._cb_error_times.append(now)

        if (
            self._cb_state == "CLOSED"
            and len(self._cb_error_times) >= self._config.circuit_breaker_errors
        ):
            self._cb_state = "OPEN"
            self._cb_open_at = now
            self._cb_open_observed = False
            logger.warning(
                "サーキットブレーカー OPEN: %d秒以内に%dエラー",
                window, len(self._cb_error_times),
            )

    def record_api_success(self) -> None:
        """API 成功を記録する（HALF_OPEN → CLOSED 遷移用）。"""
        self._cb_error_times.clear()
        if self._cb_state in ("HALF_OPEN", "OPEN"):
            self._cb_state = "CLOSED"
            logger.info("サーキットブレーカー CLOSED")

    def _check_circuit_breaker(self) -> RiskResult:
        now = time.monotonic()
        if self._cb_state == "CLOSED":
            return RiskResult(True)

        if self._cb_state == "OPEN":
            # OPEN 状態を少なくとも1回返してからウィンドウ経過を確認する。
            # これにより window_sec=0 でも最初の check で False を返し、
            # 次の check で HALF_OPEN に遷移できる。
            if self._cb_open_observed and now - self._cb_open_at >= self._config.circuit_breaker_window_sec:
                self._cb_state = "HALF_OPEN"
                logger.info("サーキットブレーカー HALF_OPEN")
                return RiskResult(True)  # 1件試行許可
            self._cb_open_observed = True
            return RiskResult(False, "サーキットブレーカー OPEN: 発注停止中")

        # HALF_OPEN: 1件だけ許可して OPEN に戻す（成功なら record_api_success() で CLOSED へ）
        self._cb_state = "OPEN"
        self._cb_open_at = now
        self._cb_open_observed = False
        logger.warning("サーキットブレーカー HALF_OPEN → OPEN: プローブ送信 (成功なら record_api_success() を呼ぶこと)")
        return RiskResult(True)

    # ------------------------------------------------------------------
    # Gate 3: メトリクスレベル（約定後監視）
    # ------------------------------------------------------------------

    def check_metrics(self, current_portfolio_value: float) -> RiskResult:
        """ドローダウンを検査する。initial_portfolio_value=0 の場合はスキップ。"""
        if self._config.initial_portfolio_value <= 0:
            return RiskResult(True)

        drawdown = (
            self._config.initial_portfolio_value - current_portfolio_value
        ) / self._config.initial_portfolio_value

        if drawdown > self._config.max_drawdown:
            return RiskResult(
                False,
                f"ドローダウン超過: {drawdown:.1%} > {self._config.max_drawdown:.1%} "
                f"(現在={current_portfolio_value:.0f}円, 開始={self._config.initial_portfolio_value:.0f}円)",
            )

        return RiskResult(True)
