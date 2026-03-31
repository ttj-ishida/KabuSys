"""trade_monitor.py — 注文滞留・約定異常価格を監視する。"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository
from kabusys.monitoring.monitoring_db import MonitoringDB


@dataclass
class TradeCheckResult:
    logged_at: str
    stale_orders: list[str] = field(default_factory=list)
    anomaly_fills: list[str] = field(default_factory=list)


class TradeMonitor:
    def __init__(
        self,
        monitoring_conn: sqlite3.Connection,
        order_repo: OrderRepository,
        stale_minutes: int = 30,
        price_anomaly_pct: float = 0.20,
    ) -> None:
        self._db = MonitoringDB(monitoring_conn)
        self._repo = order_repo
        self._stale_minutes = stale_minutes
        self._price_anomaly_pct = price_anomaly_pct

    def check_once(self, now: datetime | None = None) -> TradeCheckResult:
        now = now or datetime.now(timezone.utc)
        stale_orders: list[str] = []
        anomaly_fills: list[str] = []

        for order in self._repo.list_active():
            created = order.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            # 注文滞留チェック
            age = now - created
            if age >= timedelta(minutes=self._stale_minutes):
                stale_orders.append(order.client_order_id)
                self._db.log_risk_event(
                    event_type="STALE_ORDER",
                    metric_name="order_age_minutes",
                    metric_value=age.total_seconds() / 60,
                    threshold=float(self._stale_minutes),
                    detail=order.client_order_id,
                )

            # 約定異常価格チェック（成行は除外）
            if (
                order.state in (OrderState.PartialFill, OrderState.Filled)
                and order.price != 0.0
                and order.avg_fill_price is not None
            ):
                deviation = abs(order.avg_fill_price - order.price) / order.price
                if deviation > self._price_anomaly_pct:
                    anomaly_fills.append(order.client_order_id)
                    self._db.log_risk_event(
                        event_type="PRICE_ANOMALY",
                        metric_name="fill_price_deviation",
                        metric_value=deviation,
                        threshold=self._price_anomaly_pct,
                        detail=order.client_order_id,
                    )

        return TradeCheckResult(
            logged_at=now.isoformat(),
            stale_orders=stale_orders,
            anomaly_fills=anomaly_fills,
        )
