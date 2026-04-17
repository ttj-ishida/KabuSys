"""monitoring_engine.py — 各 Monitor を束ねてポーリングする。"""

from __future__ import annotations

import logging
import time

from kabusys.monitoring.alert_manager import AlertManager
from kabusys.monitoring.kill_switch import KillSwitch
from kabusys.monitoring.risk_monitor import RiskMonitor
from kabusys.monitoring.system_monitor import SystemMonitor
from kabusys.monitoring.trade_monitor import TradeMonitor

logger = logging.getLogger(__name__)


class MonitoringEngine:
    def __init__(
        self,
        system_monitor: SystemMonitor,
        trade_monitor: TradeMonitor,
        risk_monitor: RiskMonitor,
        interval_sec: int = 60,
        kill_switch: KillSwitch | None = None,
        alert_manager: AlertManager | None = None,
    ) -> None:
        self._system_monitor = system_monitor
        self._trade_monitor = trade_monitor
        self._risk_monitor = risk_monitor
        self._interval_sec = interval_sec
        self._kill_switch = kill_switch
        self._alert_manager = alert_manager

    def run_once(self) -> None:
        """テスト用: 各 Monitor を1回だけ呼び出す。"""
        sys_result = None
        try:
            sys_result = self._system_monitor.check_once()
        except Exception:
            logger.exception("SystemMonitor failed")

        trade_result = None
        try:
            trade_result = self._trade_monitor.check_once()
        except Exception:
            logger.exception("TradeMonitor failed")

        risk_result = None
        try:
            risk_result = self._risk_monitor.check_once()
        except Exception:
            logger.exception("RiskMonitor failed")

        # Kill Switch 評価（全 result が揃っている場合のみ）
        if self._kill_switch and sys_result and trade_result and risk_result:
            reason = self._kill_switch.evaluate(sys_result, trade_result, risk_result)
            if reason and self._alert_manager:
                self._alert_manager.notify(
                    f"Kill Switch 発動: {reason}", "CRITICAL", category="KILL_SWITCH"
                )

        # 個別アラート（各 result が None でない場合のみ参照）
        if self._alert_manager:
            if sys_result and not sys_result.process_ok:
                self._alert_manager.notify(
                    "Execution プロセス停止を検出", "CRITICAL", category="PROCESS"
                )
            if trade_result and trade_result.stale_orders:
                self._alert_manager.notify(
                    f"滞留注文 {len(trade_result.stale_orders)} 件",
                    "WARNING",
                    category="STALE_ORDER",
                )
            if trade_result and trade_result.anomaly_fills:
                self._alert_manager.notify(
                    f"約定異常価格 {len(trade_result.anomaly_fills)} 件",
                    "WARNING",
                    category="PRICE_ANOMALY",
                )
            if risk_result and risk_result.drawdown_alert:
                self._alert_manager.notify(
                    f"DD {risk_result.drawdown_pct * 100:.1f}% 超過",
                    "CRITICAL",
                    category="DRAWDOWN",
                )
            if risk_result and risk_result.position_limit_alert:
                self._alert_manager.notify(
                    f"ポジション上限超過: {risk_result.position_count} 銘柄",
                    "WARNING",
                    category="POSITION_LIMIT",
                )
            if sys_result and not sys_result.data_freshness_ok:
                self._alert_manager.notify(
                    "株価データ鮮度異常", "WARNING", category="DATA_FRESHNESS"
                )

    def run(self) -> None:
        """本番用: KeyboardInterrupt まで interval_sec 間隔でポーリング。"""
        logger.info("MonitoringEngine starting (interval=%ds)", self._interval_sec)
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                logger.info("MonitoringEngine stopped")
                break
            except Exception:
                logger.exception("MonitoringEngine run loop error — continuing")
            try:
                time.sleep(self._interval_sec)
            except KeyboardInterrupt:
                logger.info("MonitoringEngine stopped")
                break
