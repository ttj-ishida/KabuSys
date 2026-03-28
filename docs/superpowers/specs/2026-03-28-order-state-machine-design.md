# Order State Machine 設計仕様

- Issue: #29
- 版数: v1.1
- 作成日: 2026-03-28

---

## 1. 目的

`signal_queue` から取り出した売買シグナルを kabu station REST API 経由で発注し、注文の状態を `OrderCreated → Closed` まで一貫して管理する。

- UUID による冪等キー（`client_order_id`）で二重発注を防止する
- SQLite に状態を永続化し、クラッシュ復旧時に `OrderSent` 状態の注文を検出できるようにする
- Reconciliation（Issue #32）と Execution Engine（Issue #30）が依存する基盤レイヤーを提供する

### DB 役割分担

| DB | テーブル | 用途 |
|----|---------|------|
| SQLite（`data/kabusys.sqlite`） | `orders` | **状態管理**：リアルタイムの現在状態管理・低レイテンシな読み書き |
| DuckDB（`audit.py`）            | `order_requests` / `executions` | **監査ログ**：追記専用・変更不可の証跡記録 |

SQLite の `orders` が「現在どの状態か」を保持し、DuckDB の `order_requests` が「何が起きたか」の証跡を保持する。両者は並行して更新される（DuckDB 更新は Execution Engine の責務：Issue #30）。

---

## 2. スコープ

**本 Issue (#29) に含まれるもの**:
- `OrderRecord` dataclass と状態遷移ルール
- `OrderRepository`（SQLite 永続化）
- `OrderManager`（外向き API）
- 単体テスト

**本 Issue (#29) に含まれないもの**:
- リコンシリエーションの実装（`list_uncertain()` のインターフェースのみ提供し、実装は Issue #32）
- Execution Engine のメインループ（Issue #30）
- リスク管理3段階ガード（Issue #31）
- `signal_queue.status` の更新（Issue #30 の責務：Execution Engine が注文完了後に DuckDB の `signal_queue` を更新する）

---

## 3. ファイル構成

```
src/kabusys/execution/
├── broker_api.py        # 既存（BrokerAPIProtocol + データモデル）
├── kabu_client.py       # 既存
├── mock_client.py       # 既存
├── order_record.py      # 新規: OrderRecord dataclass + 状態遷移ルール（DB なし純粋ロジック）
├── order_repository.py  # 新規: SQLite 読み書き（永続化のみ）
├── order_manager.py     # 新規: 外向き API（order_record + order_repository を組み合わせ）
└── __init__.py          # 既存（新クラスを追記エクスポート）

data/
└── kabusys.sqlite       # 新規: Order State Machine 用 SQLite ファイル
```

**レイヤー間の依存方向**:

```
order_manager.py
   ├── order_record.py     (状態遷移ロジック)
   ├── order_repository.py (SQLite 永続化)
   └── broker_api.py       (OrderRequest / OrderResponse / OrderStatus 型)
```

`order_record.py` と `order_repository.py` は互いに依存しない。

---

## 4. データモデル

### 4.1 OrderState（enum）

```python
class OrderState(str, enum.Enum):
    OrderCreated  = "created"   # 内部キューに登録済み、まだ送信前
    OrderSent     = "sent"      # broker API に送信済み、応答待ち（クラッシュ時に不明状態になりうる）
    OrderAccepted = "accepted"  # 証券会社受付済み、市場待機中
    PartialFill   = "partial"   # 一部約定済み
    Filled        = "filled"    # 全量約定済み
    Closed        = "closed"    # ポジション確定済み（Filled 後処理完了）
    Cancelled     = "cancelled" # 取消済み
    Rejected      = "rejected"  # 証券会社拒否 or リスク統制拒否
```

### 4.2 許可される状態遷移

```
OrderCreated  → OrderSent, Rejected, Cancelled
OrderSent     → OrderAccepted, Rejected, Cancelled
OrderAccepted → PartialFill, Filled, Cancelled, Rejected
PartialFill   → Filled, Cancelled
Filled        → Closed
```

不正な遷移は `InvalidStateTransitionError` を raise する。

### 4.3 OrderRecord dataclass

```python
@dataclass
class OrderRecord:
    client_order_id: str          # UUID（冪等キー）
    signal_id: str                # signal_queue の signal_id
    code: str                     # 銘柄コード
    side: str                     # "buy" | "sell"
    qty: int                      # 発注数量
    order_type: str               # "market" | "limit"
    price: float                  # 指値価格（成行は 0.0）
    state: OrderState             # 現在の状態
    broker_order_id: str | None   # 証券会社から受領した注文ID
    filled_qty: int               # 約定済み数量
    avg_fill_price: float | None  # 約定平均価格
    created_at: datetime          # UTC
    updated_at: datetime          # UTC
    error_message: str | None     # エラー詳細（Rejected 時など）

    def transition_to(self, new_state: OrderState, **kwargs) -> None:
        """
        状態遷移を検証して self.state を更新する。
        不正な遷移は InvalidStateTransitionError を raise する。
        kwargs には broker_order_id / filled_qty / avg_fill_price / error_message を渡せる。
        updated_at は呼び出し時点の UTC に自動更新される。
        """
```

### 4.4 broker API の OrderStatus → OrderState マッピング

| `OrderStatus.status` | `OrderState` |
|----------------------|--------------|
| `"open"`             | `OrderAccepted` |
| `"partial"`          | `PartialFill` |
| `"filled"`           | `Filled` |
| `"cancelled"`        | `Cancelled` |
| `"rejected"`         | `Rejected` |

---

## 5. OrderRepository

### 5.1 SQLite テーブル `orders`

```sql
CREATE TABLE IF NOT EXISTS orders (
    client_order_id  TEXT     NOT NULL PRIMARY KEY,
    signal_id        TEXT     NOT NULL,
    code             TEXT     NOT NULL,
    side             TEXT     NOT NULL CHECK (side IN ('buy', 'sell')),
    qty              INTEGER  NOT NULL,
    order_type       TEXT     NOT NULL CHECK (order_type IN ('market', 'limit')),
    price            REAL     NOT NULL DEFAULT 0.0,
    state            TEXT     NOT NULL,
    broker_order_id  TEXT,
    filled_qty       INTEGER  NOT NULL DEFAULT 0,
    avg_fill_price   REAL,
    error_message    TEXT,
    created_at       TEXT     NOT NULL,
    updated_at       TEXT     NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_state    ON orders (state);
CREATE INDEX IF NOT EXISTS idx_orders_signal   ON orders (signal_id);
```

### 5.2 公開メソッド

```python
class OrderRepository:
    def __init__(self, conn: sqlite3.Connection) -> None: ...

    def save(self, record: OrderRecord) -> None
    # INSERT のみ（重複 client_order_id は sqlite3.IntegrityError）
    # 使用場面: OrderCreated レコードの初回挿入のみ
    # 状態変更後の永続化は必ず update() を使用すること

    def update(self, record: OrderRecord) -> None
    # UPDATE（存在しない場合は RuntimeError）

    def get(self, client_order_id: str) -> OrderRecord | None

    def get_by_signal(self, signal_id: str) -> list[OrderRecord]

    def list_active(self) -> list[OrderRecord]
    # state が Closed / Cancelled / Rejected 以外を返す

    def list_uncertain(self) -> list[OrderRecord]
    # state == OrderSent のみ返す（Reconciliation 用・Issue #32 の入口）
```

---

## 6. OrderManager

### 6.1 コンストラクタ

```python
class OrderManager:
    def __init__(
        self,
        broker: BrokerAPIProtocol,
        repo: OrderRepository,
    ) -> None: ...
```

### 6.2 公開メソッド

```python
def create_order(
    self,
    signal_id: str,
    request: OrderRequest,
) -> OrderRecord:
    """
    OrderCreated レコードを生成して DB に保存する。
    同一 signal_id の active 注文が存在する場合は DuplicateOrderError を raise。
    client_order_id には uuid4 を採番する。
    """

def send_order(self, client_order_id: str) -> OrderRecord:
    """
    以下の順序で処理する（クラッシュ安全性のため OrderSent の永続化を broker 呼び出しの前に行う）:

    1. OrderCreated → OrderSent に遷移して SQLite に保存（commit）
    2. broker API の send_order を呼び出す
    3. 成功: broker_order_id を受領 → OrderSent → OrderAccepted に遷移して SQLite を更新
    4. 失敗（OrderRejectedError）: OrderSent → Rejected に遷移して SQLite を更新

    kabu station は同期的に OrderId を返すため、正常時は常に OrderAccepted まで遷移する。
    ステップ1 と broker 呼び出しの間でクラッシュした場合、OrderSent レコードが残る。
    Reconciliation（Issue #32）が list_uncertain() でこのレコードを検出して状態を回復する。
    """

def sync_order(self, client_order_id: str) -> OrderRecord:
    """
    broker API の get_order_status を呼び、最新状態に同期する。
    broker が None を返した場合は状態を変更しない。
    OrderSent のまま不明な注文の Reconciliation 時にも使用する（Issue #32 の入口）。

    OrderSent に対して broker が "open" を返した場合は OrderAccepted に遷移する。
    """

def cancel_order(self, client_order_id: str) -> OrderRecord:
    """
    DB の現在状態を確認し、終端状態（Closed / Filled / Cancelled / Rejected）の場合は
    broker API を呼ばずに InvalidStateTransitionError を raise する。
    それ以外の場合は broker API の cancel_order を呼び、Cancelled に遷移する。
    broker API が失敗した場合は BrokerAPIError を re-raise する。
    """
```

### 6.3 例外クラス

```python
class DuplicateOrderError(Exception):
    """同一 signal_id の active 注文が既に存在する場合に raise される。"""

class InvalidStateTransitionError(Exception):
    """不正な状態遷移を試みた場合に raise される。"""
```

---

## 7. テスト設計

**テストファイル**: `tests/test_order_state_machine.py`

### Group 1 — OrderRecord の状態遷移（DB なし・Mock なし）

- 正常遷移: Created→Sent→Accepted→Filled→Closed
- 部分約定: Accepted→PartialFill→Filled→Closed
- キャンセル: Created→Cancelled, Accepted→Cancelled
- 拒否: Created→Rejected, Sent→Rejected
- 不正遷移: Filled→Sent は `InvalidStateTransitionError`
- 不正遷移: Closed→Accepted は `InvalidStateTransitionError`

### Group 2 — OrderRepository（インメモリ SQLite）

- `save` → `get` の往復でフィールドが一致する
- `save` を同一 `client_order_id` で2回呼ぶと `IntegrityError`
- `list_active` は Closed / Cancelled / Rejected を除外する
- `list_uncertain` は OrderSent のみ返す
- `update` で存在しない ID は RuntimeError

### Group 3 — OrderManager（MockBrokerClient + インメモリ SQLite）

**通常フロー**:
- `create_order` → `send_order` の正常フロー（OrderAccepted に遷移）
- 同一 `signal_id` で `create_order` を2回呼ぶと `DuplicateOrderError`
- `send_order` で broker が `OrderRejectedError` → Rejected に遷移

**クラッシュ復旧シナリオ**:
- `send_order` ステップ1（OrderSent 永続化）完了後、broker 呼び出し前に「クラッシュ」を模擬（broker は呼ばれなかったとする）→ `list_uncertain()` がそのレコードを返すこと
- `sync_order` を OrderSent のレコードに呼び出し、broker が `"open"` を返したら OrderAccepted に遷移すること

**sync / cancel**:
- `sync_order`: broker が `"filled"` を返したら Filled に遷移
- `sync_order`: broker が `None` を返したら状態変化なし
- `cancel_order`: OrderAccepted → Cancelled
- `cancel_order`: Filled の注文は `InvalidStateTransitionError`（broker を呼ばない）

インメモリ SQLite は `sqlite3.connect(":memory:")` で各テスト独立に生成する。

---

## 8. `__init__.py` 追記エクスポート

```python
from kabusys.execution.order_record import OrderRecord, OrderState
from kabusys.execution.order_repository import OrderRepository
from kabusys.execution.order_manager import OrderManager, DuplicateOrderError, InvalidStateTransitionError
```

---

## 9. 関連 Issue

| Issue | 内容 | 本 Issue との関係 |
|-------|------|-----------------|
| #28 | kabuステーション API クライアント | `BrokerAPIProtocol` を消費する（依存先）|
| #30 | Execution Engine メインループ | `OrderManager` を呼ぶ（依存元）・`signal_queue.status` 更新を担当 |
| #31 | リスク管理3段階ガード | `OrderRepository.list_active` を参照（依存元）|
| #32 | 自動復旧・リコンシリエーション | `list_uncertain` + `sync_order` を使用（依存元）|
