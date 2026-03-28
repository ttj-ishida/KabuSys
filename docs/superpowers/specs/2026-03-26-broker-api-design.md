# Broker API Client 設計仕様

- 対象 Issue: #28 【Phase 6】kabuステーションAPIクライアント実装
- 作成日: 2026-03-26
- ステータス: 承認済み

---

## 1. 概要

kabuステーション® REST API への接続を抽象化するクライアント層を実装する。
`Protocol` ベースのインターフェースにより、実API実装（`KabuStationClient`）と
モック実装（`MockBrokerClient`）を差し替え可能にする。

**責務の境界（重要）:**
- `broker_api.py` / `kabu_client.py` / `mock_client.py` は **DB に一切触れない**。
- `signal_queue` ステータス管理・`orders` テーブルへの書き込みは Execution Engine（Issue #30）の責務。
- このモジュールは「kabu station API を呼ぶ」ことだけに集中する。

現時点ではモック実装を先行して開発し、kabuステーション環境が整い次第
実装を差し替える方針（Mock-first development）。

---

## 2. ファイル構成

```
src/kabusys/execution/
├── __init__.py         （既存・空）
├── broker_api.py       ← Protocol定義 + データモデル + ファクトリ
├── kabu_client.py      ← KabuStationClient（実API実装）
└── mock_client.py      ← MockBrokerClient（テスト・開発用）

tests/
└── test_broker_api.py  ← MockBrokerClient を使ったテスト
```

---

## 3. データモデル（`broker_api.py`）

```python
@dataclass
class OrderRequest:
    code: str               # 銘柄コード（例: "1234"）
    exchange: int = 1       # 市場コード（1=東証[デフォルト], 3=名証 ...）
    side: str = "buy"       # "buy" | "sell"
    qty: int = 0            # 発注株数（単元株単位）
                            # ※ schema.py の orders.size / signal_queue.size と同義。
                            #   呼び出し側が signal_queue.size → OrderRequest.qty にマップする責務を持つ。
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
```

**設計判断:**
- `OrderRequest.qty` は API パラメータとして自然な名称。`orders.size` / `signal_queue.size` との橋渡しは Execution Engine が担う。
- `price` は `float` で管理。既存の `position_sizing.py` / `simulator.py` と一貫した方針。`DECIMAL(18,4)` との変換（丸め誤差対策）は DB 書き込み時に呼び出し側が `round(price, 4)` で行う。
- `WalletInfo` は現物余力のみ。信用・先物は将来対応（YAGNI）。

---

## 4. Protocol インターフェース（`broker_api.py`）

```python
class BrokerAPIProtocol(Protocol):
    """kabu station API クライアントの共通インターフェース。

    get_token は内部実装（KabuStationClient では _get_token として隠蔽）。
    呼び出し元はトークン管理を意識しない設計。
    """

    def send_order(self, order: OrderRequest) -> OrderResponse:
        """発注する。成功時は order_id を含む OrderResponse を返す。
        証券会社に拒否された場合は OrderRejectedError を raise。
        """
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
```

**`get_token` を Protocol に含めない理由:**
トークン取得は `KabuStationClient` の内部実装（`_get_token`）として隠蔽する。
`MockBrokerClient` にトークン概念は不要であり、呼び出し元にも露出しない。

### 例外クラス

```python
class BrokerAPIError(Exception):
    """API呼び出し失敗の基底例外。"""
    def __init__(self, message: str, status_code: int | None = None): ...

class OrderRejectedError(BrokerAPIError):
    """発注が証券会社に拒否された（余力不足・規制等）。
    KabuStationClient: kabu station が拒否レスポンスを返した場合に raise。
    MockBrokerClient: fill_mode="reject" の場合に raise。
    """

class RateLimitError(BrokerAPIError):
    """APIレート制限（429）に達した。"""
```

### ファクトリ関数

```python
def create_broker_api(mock: bool = False, **kwargs) -> BrokerAPIProtocol:
    """環境に応じたクライアントを返す。
    mock=True → MockBrokerClient
    mock=False → KabuStationClient(**kwargs)
    """
```

---

## 5. KabuStationClient（`kabu_client.py`）

### 接続先

| 環境 | Base URL |
|------|----------|
| 本番 | `http://localhost:18080/kabusapi` |
| 検証 | `http://localhost:18081/kabusapi` |

kabuステーション® アプリが localhost で動作している前提。

### コンストラクタ

```python
class KabuStationClient:
    def __init__(
        self,
        api_password: str,
        base_url: str = "http://localhost:18080/kabusapi",
        timeout: float = 10.0,
    ) -> None:
```

### トークン管理（内部）

- `_token: str | None = None` として保持
- `_get_token(self) -> str`: 初回 API 呼び出し時に `POST /token` で自動取得（遅延初期化）
- `401 Unauthorized` 受信時に1回だけ `_get_token` を再実行してリトライ
- kabuステーション再起動時（早朝強制ログアウト等）に自然に再取得される

### リトライ戦略

| 状況 | 対応 |
|------|------|
| `429 Too Many Requests` | `RateLimitError` を raise（呼び出し側でウェイト） |
| `401 Unauthorized` | トークン再取得後1回リトライ |
| `5xx Server Error` | `BrokerAPIError` を raise |
| ネットワークタイムアウト | `BrokerAPIError` を raise |
| kabu station 発注拒否 | `OrderRejectedError` を raise |

### 使用エンドポイント

| メソッド | パス | 用途 |
|---------|------|------|
| POST | `/token` | トークン取得（内部のみ） |
| POST | `/sendorder` | 発注（現物株） |
| PUT | `/cancelorder` | 注文キャンセル |
| GET | `/orders` | 注文照会 |
| GET | `/positions` | 残高照会 |
| GET | `/wallet/cash` | 現物取引余力 |

### 発注パラメータ変換

kabu station API の固定パラメータ（現物株前提）:

```
side: "buy"  → Side: "2", CashMargin: 1（現物）
side: "sell" → Side: "1", CashMargin: 1（現物）
order_type: "market" → FrontOrderType: 10, Price: 0
order_type: "limit"  → FrontOrderType: 20, Price: <指値>
DelivType: 2（自動）, SecurityType: 1（株式）固定
```

### 依存ライブラリ

- `httpx`（同期HTTP。将来の async 対応を見越して requests ではなく httpx を選択）

---

## 6. MockBrokerClient（`mock_client.py`）

### コンストラクタ

```python
class MockBrokerClient:
    def __init__(
        self,
        fill_mode: str = "instant",   # "instant" | "partial" | "reject"
        available_cash: float = 10_000_000.0,
        initial_positions: list[Position] | None = None,
    ) -> None:
```

### fill_mode の挙動

| モード | 挙動 | 用途 |
|--------|------|------|
| `"instant"` | `send_order` 直後に全量約定。`_positions` と `_cash` を即時更新 | 通常テスト |
| `"partial"` | 発注数量の50%のみ約定、残りは `"open"` のまま | 部分約定テスト |
| `"reject"` | `send_order` 時に `OrderRejectedError` を raise（実APIと同じ動作） | エラーパステスト |

### 状態管理

```python
_orders: dict[str, OrderStatus]    # order_id → OrderStatus
_positions: dict[str, Position]    # code → Position
_cash: float
```

### エッジケース定義

| 操作 | 状態 | 挙動 |
|------|------|------|
| `cancel_order` | 存在しない order_id | `BrokerAPIError` |
| `cancel_order` | status = `"filled"` | `BrokerAPIError`（約定済みはキャンセル不可） |
| `cancel_order` | status = `"open"` / `"partial"` | status → `"cancelled"` に更新 |

### テスト補助メソッド

```python
def fill_order(self, order_id: str) -> None:
    """fill_mode="partial" 時に手動で全量約定させる。タイミング依存テストに使用。
    status を "filled" に更新し、残量（qty - filled_qty）分の _positions と _cash も追加更新する。
    """

def get_order_history(self) -> list[OrderStatus]:
    """送信された全注文の履歴を返す（アサーション用）。"""
```

---

## 7. テスト方針

実API・kabuステーションアプリ不要で全テストを実行できる。
`KabuStationClient` の結合テストは Paper Trading フェーズ（Issue #42）で実施。

### テストケース一覧（`tests/test_broker_api.py`）

```
# データモデル
test_order_request_defaults            # exchange=1, account_type=4 がデフォルト

# MockBrokerClient — ハッピーパス
test_mock_send_order_instant_fill      # 発注→即約定→positions更新・cash減少
test_mock_cancel_order_open            # open 注文のキャンセル
test_mock_get_order_status             # 存在する注文→OrderStatus返却
test_mock_get_order_status_not_found   # 存在しない注文→None
test_mock_get_positions                # 初期ポジション反映
test_mock_get_available_cash_decreases_after_buy

# MockBrokerClient — 部分約定
test_mock_fill_mode_partial            # filled_qty = qty // 2, status = "partial"
test_mock_fill_order_manual            # fill_order() で full filled に変化

# MockBrokerClient — 異常系
test_mock_fill_mode_reject             # OrderRejectedError が raise される
test_mock_cancel_unknown_order_raises  # 存在しない注文→BrokerAPIError
test_mock_cancel_filled_order_raises   # 約定済み注文→BrokerAPIError

# テスト補助メソッド
test_mock_get_order_history            # 全注文履歴が取得できる
```

---

## 8. 将来拡張（対象外）

- WebSocket（市場データ PUSH）は別モジュールで実装（Issue #30 の Execution Engine で扱う）
- 信用取引・先物・オプションの発注対応
- 銘柄登録（`PUT /register`）による板情報取得
- 非同期（`async/await`）対応（`httpx` を使っているため移行コスト低い）
