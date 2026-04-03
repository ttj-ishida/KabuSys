"""risk_monitor.py — ドローダウン・ポジション上限を監視する。"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from kabusys.monitoring.monitoring_db import MonitoringDB


@dataclass(frozen=True)
class RiskCheckResult:
    logged_at: str
    drawdown_pct: float
    drawdown_alert: bool
    position_count: int
    position_limit_alert: bool


class RiskMonitor:
    def __init__(
        self,
        conn: sqlite3.Connection,
        max_positions: int = 10,
        dd_threshold: float = 0.10,
    ) -> None:
        self._db = MonitoringDB(conn)
        self._conn = conn
        self._max_positions = max_positions
        self._dd_threshold = dd_threshold
        self._peak_value: float | None = None

    def check_once(self, now: datetime | None = None) -> RiskCheckResult:
        now = now or datetime.now(timezone.utc)
        logged_at = now.isoformat()

        dashboard = self._db.get_dashboard()
        if dashboard is None:
            return RiskCheckResult(
                logged_at=logged_at,
                drawdown_pct=0.0,
                drawdown_alert=False,
                position_count=0,
                position_limit_alert=False,
            )

        portfolio_value = dashboard["portfolio_value"]

        # 起動時: _peak_value が未設定なら DB から復元
        first_init = False
        if self._peak_value is None:
            if dashboard.get("peak_value") is not None:
                self._peak_value = dashboard["peak_value"]
            else:
                self._peak_value = portfolio_value
                first_init = True  # DB に peak_value がなかった → 書き込みが必要

        # ハイウォーターマーク更新（新高値なら DB に永続化）
        peak_updated = portfolio_value > self._peak_value
        if peak_updated:
            self._peak_value = portfolio_value

        drawdown_pct = (
            (self._peak_value - portfolio_value) / self._peak_value
            if self._peak_value > 0
            else 0.0
        )
        drawdown_alert = drawdown_pct > self._dd_threshold

        # ポジション数（qty != 0 のみ）
        row = self._conn.execute(
            "SELECT COUNT(*) FROM positions WHERE qty != 0"
        ).fetchone()
        position_count = row[0]
        position_limit_alert = position_count > self._max_positions

        # drawdown_pct / position_count を常に永続化。peak_value は更新時のみ書き込む
        self._db.upsert_dashboard(
            portfolio_value=portfolio_value,
            cash=dashboard["cash"],
            drawdown_pct=drawdown_pct,
            open_order_count=dashboard["open_order_count"],
            position_count=position_count,
            peak_value=self._peak_value if (peak_updated or first_init) else None,
        )

        if drawdown_alert:
            self._db.log_risk_event(
                event_type="DRAWDOWN_ALERT",
                metric_name="drawdown_pct",
                metric_value=drawdown_pct,
                threshold=self._dd_threshold,
                logged_at=now,
                dedup_minutes=30,
            )

        if position_limit_alert:
            self._db.log_risk_event(
                event_type="POSITION_LIMIT",
                metric_name="position_count",
                metric_value=float(position_count),
                threshold=float(self._max_positions),
                logged_at=now,
                dedup_minutes=30,
            )

        return RiskCheckResult(
            logged_at=logged_at,
            drawdown_pct=drawdown_pct,
            drawdown_alert=drawdown_alert,
            position_count=position_count,
            position_limit_alert=position_limit_alert,
        )
