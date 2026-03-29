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
  for each record:
    if broker_order_id is None:
      → orders_no_status++
      → logger.warning（手動確認推奨）
      → スキップ
    else:
      try:
        before_state = record.state
        sync_order(client_order_id)
        after_state = repo.get(client_order_id).state
        if before_state != after_state:
          orders_synced++
      except BrokerAPIError:
        → logger.error してスキップ（他の注文は続行）
```

### Step 2 — ポジション差分照合

```
try:
  broker_positions = broker.get_positions()
except BrokerAPIError:
  → logger.warning してステップ全体をスキップ
  → position_discrepancies = []

ローカル推定ポジション:
  DB の Filled / PartialFill 注文を code ごとにネット集計
    buy:  filled_qty を加算（filled_qty が None なら qty を使用）
    sell: filled_qty を減算（filled_qty が None なら qty を使用）

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

| 障害 | 挙動 |
|------|------|
| `sync_order` が `BrokerAPIError` | そのレコードをスキップ、他の照合は続行 |
| `get_positions` が失敗 | ポジション照合ステップ全体をスキップ（`position_discrepancies=[]`） |
| `list_uncertain` が失敗 | `ReconcileResult(0, 0, [])` を返して続行（ログ記録） |
| いずれのエラーも | `run_session()` を停止させない |

---

## 8. テスト仕様（`tests/test_reconciler.py`）

| テストケース | 検証内容 |
|------------|---------|
| uncertain なし | `ReconcileResult(0, 0, [])` を返す |
| OrderSent + broker → `"open"` | `OrderAccepted` に遷移、`orders_synced=1` |
| OrderSent + broker → `"filled"` | `Filled` に遷移、`orders_synced=1` |
| OrderSent + broker_order_id なし | 状態変化なし、`orders_no_status=1` |
| broker が `None` を返す | 状態変化なし、`orders_no_status=1` |
| ポジション差分あり | `PositionDiscrepancy` リストに含まれ処理続行 |
| ポジション一致 | `position_discrepancies=[]` |
| `sync_order` が `BrokerAPIError` | スキップして他を処理、例外は伝播しない |
| `get_positions` が失敗 | `position_discrepancies=[]` で続行 |
| `ExecutionEngine.run_session` 統合 | `reconciler.run()` が signal_send_start 待機より先に呼ばれる |

---

## 9. ファイル変更サマリー

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `src/kabusys/execution/reconciler.py` | 新規作成 | `Reconciler` クラス、`ReconcileResult`、`PositionDiscrepancy` |
| `src/kabusys/execution/execution_engine.py` | 修正 | `__init__` に `reconciler` 追加、`run_session` の先頭で呼ぶ |
| `src/kabusys/execution/__init__.py` | 修正 | `Reconciler`、`ReconcileResult`、`PositionDiscrepancy` をエクスポート |
| `tests/test_reconciler.py` | 新規作成 | 上記テストケース |
