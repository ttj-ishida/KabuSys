# src/kabusys/execution/broker_factory.py
"""broker_factory.py — 設定に応じたブローカークライアントを生成するファクトリ。"""

from __future__ import annotations

from kabusys.execution.broker_api import BrokerAPIProtocol, Position, create_broker_api
from kabusys.config import Settings

_SANDBOX_BASE_URL = "http://localhost:18081/kabusapi"


class BrokerClientFactory:
    """設定に応じてブローカークライアントを生成するファクトリ。

    既存の create_broker_api() をラップし、Settings からパラメータを解決する。
    ExecutionEngine は BrokerAPIProtocol を受け取るだけでよく、
    環境判定ロジックをこのクラスに集約する。
    """

    @staticmethod
    def create(
        settings: Settings,
        available_cash: float | None = None,
        initial_positions: list[Position] | None = None,
    ) -> BrokerAPIProtocol:
        """設定に応じたブローカークライアントを返す。

        - is_paper かつ kabu_use_sandbox → KabuStationClient（検証 URL: port 18081）
        - is_paper または is_dev         → MockBrokerClient（available_cash / initial_positions を注入）
        - is_live                        → KabuStationClient（本番）
        - それ以外                       → ValueError（settings.env の評価で確定）
        """
        if settings.is_paper and settings.kabu_use_sandbox:
            password = settings.kabu_sandbox_api_password or settings.kabu_api_password
            return create_broker_api(
                mock=False,
                api_password=password,
                trade_password=settings.kabu_trade_password,
                base_url=_SANDBOX_BASE_URL,
            )
        if settings.is_paper or settings.is_dev:
            cash = (
                available_cash
                if available_cash is not None
                else settings.paper_trading_initial_cash
            )
            return create_broker_api(
                mock=True,
                fill_mode=settings.paper_fill_mode,
                available_cash=cash,
                initial_positions=initial_positions,
            )
        if settings.is_live:
            return create_broker_api(
                mock=False,
                api_password=settings.kabu_api_password,
                trade_password=settings.kabu_trade_password,
                base_url=settings.kabu_api_base_url,
            )
        env = settings.env  # 明示評価（未知の env ならここで ValueError）
        raise ValueError(f"未知の KABUSYS_ENV: {env!r}")
