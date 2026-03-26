"""kabu station API クライアント層 — データモデル・Protocol・例外・ファクトリ。

DB には一切触れない。API 呼び出しのみに専念する純粋なクライアント層。
signal_queue.size → OrderRequest.qty のマッピングは呼び出し元（Execution Engine）の責務。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# データモデル
# ---------------------------------------------------------------------------

@dataclass
class OrderRequest:
    code: str               # 銘柄コード（例: "1234"）
    exchange: int = 1       # 市場コード（1=東証[デフォルト], 3=名証 ...）
    side: str = "buy"       # "buy" | "sell"
    qty: int = 0            # 発注株数（単元株単位）
    price: float = 0.0      # 指値価格（0.0 = 成行）
    order_type: str = "market"  # "market" | "limit"
    account_type: int = 4   # 口座種別（2=一般, 4=特定[デフォルト], 12=法人）


@dataclass
class OrderResponse:
    order_id: str           # kabu station が返す注文番号


@dataclass
class OrderStatus:
    order_id: str
    code: str
    side: str               # "buy" | "sell"
    qty: int                # 発注数量
    filled_qty: int         # 約定済数量
    status: str             # "open" | "partial" | "filled" | "cancelled" | "rejected"
    price: float | None     # 約定平均価格（未約定時は None）


@dataclass
class Position:
    code: str
    qty: int                # 保有株数
    avg_price: float        # 平均取得単価


@dataclass
class WalletInfo:
    available_cash: float   # 現物取引余力（円）


# ---------------------------------------------------------------------------
# 例外クラス
# ---------------------------------------------------------------------------

class BrokerAPIError(Exception):
    """API 呼び出し失敗の基底例外。"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OrderRejectedError(BrokerAPIError):
    """発注が証券会社に拒否された（余力不足・規制等）。"""


class RateLimitError(BrokerAPIError):
    """API レート制限（429）に達した。"""


# ---------------------------------------------------------------------------
# Protocol インターフェース
# ---------------------------------------------------------------------------

@runtime_checkable
class BrokerAPIProtocol(Protocol):
    """kabu station API クライアントの共通インターフェース。

    get_token は内部実装（KabuStationClient では _get_token として隠蔽）。
    呼び出し元はトークン管理を意識しない設計。
    """

    def send_order(self, order: OrderRequest) -> OrderResponse:
        """発注する。証券会社に拒否された場合は OrderRejectedError を raise。"""
        ...

    def cancel_order(self, order_id: str) -> None:
        """注文をキャンセルする。
        - 対象注文が存在しない → BrokerAPIError
        - 既に filled の注文 → BrokerAPIError（キャンセル不可）
        """
        ...

    def get_order_status(self, order_id: str) -> OrderStatus | None:
        """注文状態を照会する。対象注文が存在しない場合は None。"""
        ...

    def get_positions(self) -> list[Position]:
        """現在の保有ポジション一覧を返す。"""
        ...

    def get_available_cash(self) -> float:
        """現物取引余力（円）を返す。"""
        ...


# ---------------------------------------------------------------------------
# ファクトリ関数
# ---------------------------------------------------------------------------

def create_broker_api(mock: bool = False, **kwargs) -> BrokerAPIProtocol:
    """環境に応じたクライアントを返す。
    mock=True  → MockBrokerClient(**kwargs)  # fill_mode, available_cash 等を渡せる
    mock=False → KabuStationClient(**kwargs)  # api_password, base_url 等を渡せる
    """
    if mock:
        from kabusys.execution.mock_client import MockBrokerClient
        return MockBrokerClient(**kwargs)
    from kabusys.execution.kabu_client import KabuStationClient
    return KabuStationClient(**kwargs)
