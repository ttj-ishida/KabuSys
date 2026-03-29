# Reconciliation（自動復旧）設計仕様

> **For agentic workers:** このドキュメントは Issue #32「自動復旧・リコンシリエーション実装」の設計仕様です。
> 実装前に必ず本ドキュメントを参照してください。

---

## 1. 目的

システム再起動・クラッシュ後に、ローカルDBの注文状態とブローカーの実際の状態を自動的に突合・同期し、安全に発注処理を再開する。

対象 Issue: #32「【Phase 6】自動復旧・リコンシリエーション実装 [CRITICAL]」

---

## 2. 前提・既存インフラ

以下は Phase 6（PR #132）で実装済みであり、本実装でそのまま利用する。

| メソッド | 場所 | 役割 |
|---------|------|------|
| `OrderRepository.list_uncertain()` | `order_repository.py` | `state=OrderSent` のレコードを返す |
| `OrderManager.sync_order(client_order_id)` | `order_manager.py` | broker API で照会して DB 状態を更新 |
| `BrokerAPIProtocol.get_positions()` | `broker_api.py` | ブローカーの現在保有ポジションを返す |

---

## 3. アーキテクチャ

`Reconciler` を独立クラスとして新設し、`ExecutionEngine` に注入する。

```
ExecutionEngine
└── reconciler: Reconciler   ← 新規注入（Optional）
      ├── broker: BrokerAPIProtocol
      ├── repo: OrderRepository
      └── order_manager: OrderManager
```

`ExecutionEngine.run_session()` の先頭（`signal_send_start` 待機より前）で `reconciler.run()` を呼ぶ。

---

## 4. 新規ファイル

### `src/kabusys/execution/reconciler.py`

#### データ型

```python
@dataclass
class PositionDiscrepancy:
    code: str
    broker_qty: int   # ブローカー側の保有数量
    local_qty: int    # ローカルDB推定値（注文履歴から集計）
    diff: int         # broker_qty - local_qty

@dataclass
class ReconcileResult:
    orders_synced: int                          # 状態が変化した OrderSent 件数
    orders_no_status: int                       # broker が None / broker_order_id 未設定
    position_discrepancies: list[PositionDiscrepancy]
```

#### `Reconciler` クラス

```python
class Reconciler:
    def __init__(
        self,
        broker: BrokerAPIProtocol,
        repo: OrderRepository,
        order_manager: OrderManager,
    ) -> None: ...

    def run(self) -> ReconcileResult:
        """Step 1: OrderSent 照合 → Step 2: ポジション差分照合"""
```

---

## 5. 処理フロー

### Step 1 — OrderSent 照合

```
list_uncertain() → [OrderSent レコード一覧]
  ※ list_uncertain が Exception を raise した場合:
    → logger.error してスキップ（run_session は停止しない）
    → ReconcileResult(0, 0, []) を返す

  for each record:
    if broker_order_id is None:
      → orders_no_status++   ← broker_order_id 未設定は照合不能
      → logger.warning（手動確認推奨）
      → スキップ
    else:
      try:
        before_state = record.state
        updated = sync_order(client_order_id)   ← 戻り値を直接使用（再DB読みは不要）
        if before_state != updated.state:
          orders_synced++
      except BrokerAPIError:
        → logger.error してスキップ（他の注文は続行）

  ※ sync_order 内部で broker.get_order_status() が None を返した場合:
    → sync_order は状態を変更せず元の record を返す
    → orders_no_status++ / logger.warning（broker 側に注文なし、手動確認推奨）
```

`orders_no_status` は以下の2ケースを合算する：
- `broker_order_id is None`（クラッシュで永続化前にプロセス停止）
- `get_order_status()` が `None` を返す（broker 側に注文レコードなし）

### Step 2 — ポジション差分照合

```
try:
  broker_positions = broker.get_positions()
  # → list[Position]。Position.qty は常に非負（保有数量）
  # → dict[str, int] に変換: {p.code: p.qty for p in broker_positions}
except BrokerAPIError:
  → logger.warning してステップ全体をスキップ
  → position_discrepancies = []

ローカル推定ポジション（code ごとにネット集計）:
  対象状態: Filled / PartialFill / Closed
    ※ Closed は決済済み（売り約定）だが、発注履歴から ポジションを正確に把握するために含める
  buy:  record.filled_qty を加算
  sell: record.filled_qty を減算
  ※ filled_qty は OrderRecord.filled_qty: int = 0 (NOT NULL)。None になることはない。

差分照合:
  union(broker_codes, local_codes) を走査
  diff = broker_qty - local_qty
  diff != 0 → PositionDiscrepancy に追加 + logger.warning
```

### Step 3 — 結果返却と続行

```
ReconcileResult(orders_synced, orders_no_status, position_discrepancies) を返す
run_session() は結果を logger.info で出力し、処理続行
```

---

## 6. `ExecutionEngine` への統合

### `__init__` の変更

```python
def __init__(
    self,
    broker: BrokerAPIProtocol,
    repo: OrderRepository,
    risk_manager: RiskManager,
    order_manager: OrderManager,
    duckdb_conn: duckdb.DuckDBPyConnection,
    config: EngineConfig,
    reconciler: Reconciler | None = None,   # ← 追加（Optional）
) -> None:
    ...
    self._reconciler = reconciler
```

### `run_session()` の変更

```python
def run_session(self) -> None:
    logger.info("ExecutionEngine: セッション開始 target_date=%s", ...)

    # 起動時リコンシリエーション（reconciler が設定されている場合のみ）
    if self._reconciler is not None:
        result = self._reconciler.run()
        logger.info(
            "Reconciliation 完了: synced=%d, no_status=%d, position_discrepancies=%d",
            result.orders_synced,
            result.orders_no_status,
            len(result.position_discrepancies),
        )

    # WebSocket スレッド起動
    ws_thread = threading.Thread(...)
    ...
```

---

## 7. エラーハンドリング方針

| 障害 | 捕捉する例外型 | 挙動 |
|------|--------------|------|
| `sync_order` が失敗 | `BrokerAPIError` | そのレコードをスキップ、他の照合は続行 |
| `get_positions` が失敗 | `BrokerAPIError` | ポジション照合ステップ全体をスキップ（`position_discrepancies=[]`） |
| `list_uncertain` が失敗 | `Exception`（SQLite 接続断等） | `ReconcileResult(0, 0, [])` を返して続行。SQLite 障害は後続の発注でも顕在化するため、ここでの握りつぶしは許容範囲。`logger.error` で記録する。 |
| いずれのエラーも | — | `run_session()` を停止させない |

---

## 8. テスト仕様（`tests/test_reconciler.py`）

| テストケース | 検証内容 |
|------------|---------|
| uncertain なし | `ReconcileResult(0, 0, [])` を返す |
| OrderSent + broker → `"open"` | `OrderAccepted` に遷移、`orders_synced=1` |
| OrderSent + broker → `"filled"` | `Filled` に遷移、`orders_synced=1` |
| OrderSent + `broker_order_id=None` | 状態変化なし、`orders_no_status=1`（broker 呼び出しなし） |
| `broker_order_id` 設定済みだが `get_order_status()` が `None` を返す | 状態変化なし、`orders_no_status=1` |
| ポジション差分あり（broker 100株、local 80株） | `PositionDiscrepancy(code=..., broker_qty=100, local_qty=80, diff=20)` リストに含まれ処理続行 |
| ポジション一致 | `position_discrepancies=[]` |
| `sync_order` が `BrokerAPIError` | そのレコードをスキップ、他は処理継続、例外は伝播しない |
| `get_positions` が `BrokerAPIError` | `position_discrepancies=[]` で続行 |
| `list_uncertain` が `Exception` | `ReconcileResult(0, 0, [])` を返す、例外は伝播しない |
| `ExecutionEngine.run_session` 統合 | `reconciler.run()` が WebSocket スレッド起動・`signal_send_start` 待機より先に呼ばれる |

---

## 9. ファイル変更サマリー

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `src/kabusys/execution/reconciler.py` | 新規作成 | `Reconciler` クラス、`ReconcileResult`、`PositionDiscrepancy` |
| `src/kabusys/execution/execution_engine.py` | 修正 | `__init__` に `reconciler` 追加、`run_session` の先頭で呼ぶ |
| `src/kabusys/execution/__init__.py` | 修正 | 既存エクスポートに `Reconciler`、`ReconcileResult`、`PositionDiscrepancy` を追加 |
| `tests/test_reconciler.py` | 新規作成 | 上記テストケース |
