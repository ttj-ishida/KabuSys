"""kabu station API クライアント層 — データモデル・Protocol・例外・ファクトリ。

DB には一切触れない。API 呼び出しのみに専念する純粋なクライアント層。
signal_queue.size → OrderRequest.qty のマッピングは呼び出し元（Execution Engine）の責務。
"""
from __future__ import annotations

from dataclasses import dataclass


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
