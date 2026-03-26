"""KabuStationClient — kabu station REST API 実装（将来対応）。"""
from __future__ import annotations


class KabuStationClient:
    """kabu station REST API クライアント。"""

    def __init__(
        self,
        api_password: str,
        base_url: str = "http://localhost:18080/kabusapi",
        timeout: float = 10.0,
    ) -> None:
        self._api_password = api_password
        self._base_url = base_url
        self._timeout = timeout
        self._token: str | None = None
