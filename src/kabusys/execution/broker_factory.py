# src/kabusys/execution/broker_factory.py
"""broker_factory.py — 設定に応じたブローカークライアントを生成するファクトリ。"""
from __future__ import annotations

from kabusys.execution.broker_api import BrokerAPIProtocol, create_broker_api
from kabusys.config import Settings


class BrokerClientFactory:
    """設定に応じてブローカークライアントを生成するファクトリ。

    既存の create_broker_api() をラップし、Settings からパラメータを解決する。
    ExecutionEngine は BrokerAPIProtocol を受け取るだけでよく、
    環境判定ロジックをこのクラスに集約する。
    """

    @staticmethod
    def create(settings: Settings) -> BrokerAPIProtocol:
        """設定に応じたブローカークライアントを返す。

        - is_paper or is_dev → MockBrokerClient(fill_mode=settings.paper_fill_mode)
        - is_live            → NotImplementedError（将来実装）
        ※ それ以外の環境は Settings.env プロパティが ValueError を raise するため到達不可。
        """
        if settings.is_paper or settings.is_dev:
            return create_broker_api(mock=True, fill_mode=settings.paper_fill_mode)
        raise NotImplementedError(
            "Live broker client (KabuStationClient) は未実装です。"
            "KABUSYS_ENV=paper_trading または development を使用してください。"
        )
