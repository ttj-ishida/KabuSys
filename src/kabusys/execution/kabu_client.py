# src/kabusys/execution/kabu_client.py
"""KabuStationClient — kabu station REST API 実装。

httpx（同期）を使用。将来の async 対応は httpx.AsyncClient への切り替えで対応可能。
DB には一切触れない。トークン管理は内部で完結（_get_token として隠蔽）。
"""
from __future__ import annotations

import logging

import httpx

from kabusys.execution.broker_api import (
    BrokerAPIError,
    OrderRejectedError,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    Position,
    RateLimitError,
)

logger = logging.getLogger(__name__)

# kabu station 注文状態コード → 内部ステータス文字列
_KABU_STATUS_MAP: dict[int, str] = {
    1: "open",       # 待機
    2: "open",       # 処理中
    3: "open",       # 受付済
    4: "partial",    # 一部約定
    5: "filled",     # 全部約定
    6: "cancelled",  # 取消済
    7: "rejected",   # 失効
}


class KabuStationClient:
    """kabu station REST API クライアント。

    接続先:
        本番: http://localhost:18080/kabusapi
        検証: http://localhost:18081/kabusapi

    kabuステーション® アプリが PC 上で起動していることが前提。
    """

    def __init__(
        self,
        api_password: str,
        base_url: str = "http://localhost:18080/kabusapi",
        timeout: float = 10.0,
    ) -> None:
        self._api_password = api_password
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._token: str | None = None
        self._client = httpx.Client(timeout=timeout)

    def _get_token(self) -> str:
        """API トークンを取得する（遅延初期化・早朝失効時に自動再取得）。"""
        try:
            resp = self._client.post(
                f"{self._base_url}/token",
                json={"APIPassword": self._api_password},
            )
        except httpx.TimeoutException as exc:
            raise BrokerAPIError(f"トークン取得タイムアウト: {exc}") from exc
        except httpx.RequestError as exc:
            raise BrokerAPIError(f"トークン取得ネットワークエラー: {exc}") from exc
        if resp.status_code != 200:
            raise BrokerAPIError(
                f"トークン取得失敗: {resp.status_code}", status_code=resp.status_code
            )
        self._token = resp.json()["Token"]
        return self._token

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """認証付きリクエスト。401 時はトークン再取得して1回リトライ。"""
        if self._token is None:
            self._get_token()

        headers = {"X-API-KEY": self._token}
        try:
            resp = getattr(self._client, method)(
                f"{self._base_url}{path}",
                headers=headers,
                **kwargs,
            )
        except httpx.TimeoutException as exc:
            raise BrokerAPIError(f"タイムアウト: {exc}") from exc
        except httpx.RequestError as exc:
            raise BrokerAPIError(f"ネットワークエラー: {exc}") from exc

        if resp.status_code == 401:
            logger.info("401 Unauthorized — トークン再取得してリトライ")
            self._get_token()
            headers = {"X-API-KEY": self._token}
            try:
                resp = getattr(self._client, method)(
                    f"{self._base_url}{path}",
                    headers=headers,
                    **kwargs,
                )
            except httpx.TimeoutException as exc:
                raise BrokerAPIError(f"タイムアウト（リトライ）: {exc}") from exc
            except httpx.RequestError as exc:
                raise BrokerAPIError(f"ネットワークエラー（リトライ）: {exc}") from exc

        if resp.status_code == 429:
            raise RateLimitError("API レート制限超過", status_code=429)
        if resp.status_code >= 500:
            raise BrokerAPIError(
                f"サーバーエラー: {resp.status_code}", status_code=resp.status_code
            )

        return resp

    def send_order(self, order: OrderRequest) -> OrderResponse:
        """現物株を発注する。"""
        side_map = {"buy": "2", "sell": "1"}
        front_order_type = 10 if order.order_type == "market" else 20

        payload = {
            "Password": self._api_password,
            "Symbol": order.code,
            "Exchange": order.exchange,
            "SecurityType": 1,
            "Side": side_map[order.side],
            "CashMargin": 1,
            "DelivType": 2,
            "AccountType": order.account_type,
            "Qty": order.qty,
            "FrontOrderType": front_order_type,
            "Price": order.price,
        }

        resp = self._request("post", "/sendorder", json=payload)

        if resp.status_code != 200:
            raise OrderRejectedError(
                f"発注拒否: {resp.status_code} {resp.text}",
                status_code=resp.status_code,
            )

        data = resp.json()
        if data.get("Result") != 0:
            raise OrderRejectedError(f"発注拒否: {data}")

        return OrderResponse(order_id=str(data["OrderId"]))

    def cancel_order(self, order_id: str) -> None:
        """注文をキャンセルする。"""
        payload = {
            "OrderId": order_id,
            "Password": self._api_password,
        }
        resp = self._request("put", "/cancelorder", json=payload)
        if resp.status_code != 200:
            raise BrokerAPIError(
                f"キャンセル失敗: {resp.status_code}", status_code=resp.status_code
            )

    def get_order_status(self, order_id: str) -> OrderStatus | None:
        """注文状態を照会する。"""
        resp = self._request("get", f"/orders?id={order_id}")
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise BrokerAPIError(
                f"注文照会失敗: {resp.status_code}", status_code=resp.status_code
            )

        orders = resp.json()
        if not orders:
            return None

        # kabu station は list を返す。order_id で絞り込み
        for o in orders:
            if str(o.get("ID")) == str(order_id):
                return self._parse_order_status(o)
        return None

    def _parse_order_status(self, data: dict) -> OrderStatus:
        """kabu station の注文データを OrderStatus に変換する。"""
        raw_status = data.get("State", 0)
        status_str = _KABU_STATUS_MAP.get(raw_status, "open")

        filled_details = [d for d in data.get("Details", []) if d.get("Type") == 3]
        filled_qty = sum(int(d.get("Qty", 0)) for d in filled_details)
        avg_price: float | None = None
        if filled_qty > 0:
            weighted = sum(
                float(d.get("Price", 0)) * int(d.get("Qty", 0)) for d in filled_details
            )
            avg_price = weighted / filled_qty

        side_map = {"1": "sell", "2": "buy"}
        return OrderStatus(
            order_id=str(data.get("ID", "")),
            code=str(data.get("Symbol", "")),
            side=side_map.get(str(data.get("Side", "2")), "buy"),
            qty=int(data.get("OrderQty", 0)),
            filled_qty=filled_qty,
            status=status_str,
            price=avg_price,
        )

    def get_positions(self) -> list[Position]:
        """現在の保有ポジション一覧を返す。"""
        resp = self._request("get", "/positions")
        if resp.status_code != 200:
            raise BrokerAPIError(
                f"残高照会失敗: {resp.status_code}", status_code=resp.status_code
            )
        positions = []
        for p in resp.json() or []:
            positions.append(
                Position(
                    code=str(p.get("Symbol", "")),
                    qty=int(p.get("LeavesQty", 0)),
                    avg_price=float(p.get("Price", 0.0)),
                )
            )
        return positions

    def get_available_cash(self) -> float:
        """現物取引余力（円）を返す。"""
        resp = self._request("get", "/wallet/cash")
        if resp.status_code != 200:
            raise BrokerAPIError(
                f"余力照会失敗: {resp.status_code}", status_code=resp.status_code
            )
        return float(resp.json().get("StockAccountWallet", 0.0))

    def close(self) -> None:
        """HTTP クライアントを閉じる。"""
        self._client.close()

    def __enter__(self) -> KabuStationClient:
        return self

    def __exit__(self, *_) -> None:
        self.close()
