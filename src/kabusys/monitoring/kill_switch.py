"""kill_switch.py — フラグファイル書き込みによる ExecutionEngine 停止シグナル。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from kabusys.monitoring.risk_monitor import RiskCheckResult
from kabusys.monitoring.system_monitor import SystemCheckResult
from kabusys.monitoring.trade_monitor import TradeCheckResult

logger = logging.getLogger(__name__)


class KillSwitch:
    """data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送る。

    flag_path は呼び出し元が Settings.kill_flag_path から渡す。
    """

    def __init__(self, flag_path: Path) -> None:
        self._flag_path = flag_path

    def evaluate(
        self,
        system: SystemCheckResult,
        trade: TradeCheckResult,
        risk: RiskCheckResult,
    ) -> str | None:
        """トリガー条件を評価する。

        該当すれば kill.flag を書き込み、理由文字列を返す。
        評価順序: drawdown_alert → position_limit_alert（テーブル上から順）。
        flag が既存の場合は再書き込みしない（冪等）。
        該当なしは None を返す。
        """
        reason: str | None = None

        if risk.drawdown_alert:
            reason = (
                f"DRAWDOWN_ALERT: DD {risk.drawdown_pct * 100:.1f}% exceeded threshold 10.0%"
                f" at {datetime.now(tz=timezone.utc).isoformat()}"
            )
        elif risk.position_limit_alert:
            reason = (
                f"POSITION_LIMIT_ALERT: {risk.position_count} positions exceeded limit"
                f" at {datetime.now(tz=timezone.utc).isoformat()}"
            )

        if reason:
            self._write_flag(reason)

        return reason

    def _write_flag(self, reason: str) -> None:
        """kill.flag を書き込む。既存の場合はスキップ（冪等）。"""
        if self._flag_path.exists():
            logger.debug("kill.flag already exists — skipping write")
            return
        self._flag_path.parent.mkdir(parents=True, exist_ok=True)
        self._flag_path.write_text(reason)
        logger.warning("kill.flag written: %s", reason)

    def is_flagged(self) -> bool:
        """kill.flag が存在するか確認する。"""
        return self._flag_path.exists()

    def clear(self) -> None:
        """kill.flag を削除する（ExecutionEngine 起動時のクリーンアップ用）。"""
        self._flag_path.unlink(missing_ok=True)
        logger.info("kill.flag cleared")
