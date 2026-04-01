"""monitoring_engine.py — 各 Monitor を束ねてポーリングする。"""
from __future__ import annotations

import logging
import time

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
    ) -> None:
        self._monitors = [system_monitor, trade_monitor, risk_monitor]
        self._interval_sec = interval_sec

    def run_once(self) -> None:
        """テスト用: 各 Monitor を1回だけ呼び出す。"""
        for monitor in self._monitors:
            try:
                monitor.check_once()
            except Exception:
                logger.exception("Monitor %s failed", type(monitor).__name__)

    def run(self) -> None:
        """本番用: KeyboardInterrupt まで interval_sec 間隔でポーリング。"""
        logger.info("MonitoringEngine starting (interval=%ds)", self._interval_sec)
        while True:
            try:
                self.run_once()
                time.sleep(self._interval_sec)
            except KeyboardInterrupt:
                logger.info("MonitoringEngine stopped")
                break
            except Exception:
                logger.exception("MonitoringEngine run loop error — continuing")
