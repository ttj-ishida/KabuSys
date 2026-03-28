# Execution System (執行系・状態監視・復旧原則)

- 対象: kabuステーションAPIを通じた発注およびリスク管理層
- 版数: v1.1

---

## 1. 目的

算出した「シグナル」を、三菱UFJ eスマート証券の `kabuステーション API` を用いて、実際の証券市場へ確実に送り届ける（執行する）層である。

ここでは、「利益を狙うこと」以上に「**システムを壊さないこと・想定外の損失や無限発注ループを防ぐこと**」が最優先される。通信エラーやシステムクラッシュに耐えうるフェイルセーフな設計を定義する。

---

## 2. 状態遷移と発注管理 (Order State Machine)

注文の二重発注を防ぐため、発注1件ごとに独自の発注ID（`client_order_id`）に一意のUUIDを採番し、冪等性（Idempotency）を完全に担保する。
注文は以下のステートマシンに従って厳密に状態遷移（State）を管理し、DBに永続化される。

```text
    [0. Signal] (シグナル生成)
         ↓
    [1. OrderCreated] (内部発注キュー生成)
         ↓ (API送信)
    [2. OrderSent] (証券会社へ送信済・応答待ち)
         ↓ (API受付・Order ID受領)
    [3. OrderAccepted] (証券会社受付済・市場待機)
         ↓ (PUSH約定通知)
  ┌──────┴──────┐
  ↓             ↓
[4. PartialFill][4. Filled] (完全約定)
 (一部約定)      ↓ (ポジション確定)
  ↓           [5. Closed] (取引完了)
  └─────────────┘
  
※ 例外ルート
[X. Cancelled] (取消済)
[Y. Rejected] (エラー・証券会社拒否/リスク統制拒否)
```

**※ 状態の不確実性（State Uncertainty）への対応**
`OrderSent` の状態でネットワークが切断されたりプロセスが落ちた場合、注文が通っているかいないか「不明」となる。この場合、再起動時は直ちに「注文照会API」を叩き、正しいステータスへ同期（Reconciliation）させる。

実装上の安全保証: `send_order` は **SQLite に `OrderSent` を保存してから** broker API を呼び出す。クラッシュ時でも SQLite に `OrderSent` レコードが残るため、再起動時に検出できる（Section 4 参照）。

---

## 3. リスク管理層 (Risk Manager) による 3段階ガード

Strategy層が生成したシグナルは、実行層（Execution）へ渡る直前および直後に「3段階のガード」を通過しなければならない。

### 第1関門: シグナルレベル・ガード（発注前検証）
- **余力チェック**: 現在の口座買付余力を超過していないか。
- **重複チェック**: すでに同一銘柄の注文が `OrderAccepted` `OrderSent` 状態で存在しないか（二重発注防止）。
- **ポジション上限**: すでに最大保有株数、または総資産に対する最大投資比率（10%等）に達していないか。

### 第2関門: エグゼキューションレベル・ガード（API送信前制限）
- **APIレート制限**: kabuステーションの「発注系API: 毎秒5回以内」等の制約を厳守するため、トークンバケツやスロットリングキューを挟む。
- **暴走防止（サーキットブレーカー）**: 短期間（例: 1分間）に指定回数（例: 10回）連続でエラーが返却された場合、APIキーの失効や取引所側の障害とみなし、システム全体の発注機能を停止させる。

### 第3関門: メトリクスレベル・ガード（発注後監視）
- ポートフォリオ全体の評価損益（Drawdown）を監視し、想定最大損失（MaxDD等）を超えた場合はすべての未約定注文をキャンセルさせ、保有ポジションを成行で安全にクローズする**キルスイッチ（Kill Switch）**を発動させる。

---

## 4. プロセス再起動と自動復旧 (Recovery)

サーバーの再起動、Windows Updateによる強制リブート、クラッシュに対し、システムは安全に自己復旧（Self-Healing）しなければならない。

1. **起動時検知**: `OrderRepository.list_uncertain()` を呼び、SQLite の `orders` テーブルから `state = "sent"` のレコードを抽出する。
2. **リコンシリエーション (突合)**: 各レコードに対して `OrderManager.sync_order()` を呼び、kabuステーション「注文照会API」（`GET /orders`）で実際の状態を照合する。broker が `"open"` を返せば `OrderAccepted`、`"filled"` なら `Filled`、`"cancelled"` なら `Cancelled` に遷移して SQLite を更新する。broker が `None`（注文が見つからない）を返した場合は状態を変えず、ログに記録して手動確認待ちとする。
3. **残高照合**: `GET /positions` で実際の口座ポジションを確認し、ローカルの想定ポジションとの差分をログに記録する。
4. **再開**: 正しい状態に同期した後、`signal_queue` の `pending` キューの消化を再開する。

> **実装**: Reconciliation ロジックは Issue #32 で実装する。`OrderRepository.list_uncertain()` と `OrderManager.sync_order()` のインターフェースは Issue #29 で提供済み。

---

## 5. Broker API クライアント実装方針 (Issue #28)

kabuステーション REST API へのアクセスは `src/kabusys/execution/` 配下に分離し、
`Protocol` ベースのインターフェースにより実装とモックを差し替え可能にする。

### ファイル構成

```
src/kabusys/execution/
├── broker_api.py    ← BrokerAPIProtocol（Protocol）+ データモデル + ファクトリ関数
├── kabu_client.py   ← KabuStationClient（実API実装）
└── mock_client.py   ← MockBrokerClient（テスト・開発用）
```

### Protocol インターフェース（`BrokerAPIProtocol`）

```python
class BrokerAPIProtocol(Protocol):
    # get_token は KabuStationClient の内部実装（_get_token）として隠蔽。
    # 呼び出し元はトークン管理を意識しない設計。
    def send_order(self, order: OrderRequest) -> OrderResponse: ...
    def cancel_order(self, order_id: str) -> None: ...
    def get_order_status(self, order_id: str) -> OrderStatus | None: ...
    def get_positions(self) -> list[Position]: ...
    def get_available_cash(self) -> float: ...
```

broker API の `OrderStatus.status`（GET /orders レスポンス）から Order State Machine の状態への変換:

| `OrderStatus.status` | `OrderState`（内部状態） | 備考 |
|----------------------|------------------------|------|
| `"open"` | `OrderAccepted` | 受付済み・市場待機中 |
| `"partial"` | `PartialFill` | 一部約定済み |
| `"filled"` | `Filled` | 全量約定済み |
| `"cancelled"` | `Cancelled` | 取消済み |
| `"rejected"` | `Rejected` | 拒否済み |

> `OrderCreated` と `OrderSent` は内部状態のみ。broker API は受付前の状態を返さないため、これらへの逆マッピングは存在しない。

### 使用 REST エンドポイント

| メソッド | パス | 用途 |
|---------|------|------|
| POST | `/token` | APIトークン取得（早朝失効時に自動再取得） |
| POST | `/sendorder` | 現物株発注 |
| PUT | `/cancelorder` | 注文キャンセル |
| GET | `/orders` | 注文照会（Reconciliation でも使用） |
| GET | `/positions` | 残高照会（Reconciliation でも使用） |
| GET | `/wallet/cash` | 現物取引余力（第1関門チェック） |

**Base URL**: `http://localhost:18080/kabusapi`（本番）/ `http://localhost:18081/kabusapi`（検証）

### 差し替え方法

```python
# 開発・テスト時
api = create_broker_api(mock=True)

# 本番時
api = create_broker_api(mock=False, api_password="...", base_url="http://localhost:18080/kabusapi")
```

### 注意事項

- kabuステーション® アプリが PC 上で起動している前提（localhost 接続）
- 発注系 API はレート制限 5 req/sec（Section 3 第2関門で制御）
- WebSocket（市場データ PUSH）は Execution Engine（Issue #30）で別途扱う
- 詳細仕様: `docs/superpowers/specs/2026-03-26-broker-api-design.md`

---

## 6. Order State Machine 実装方針 (Issue #29)

### DB 役割分担

| DB | ファイル | テーブル | 用途 |
|----|---------|---------|------|
| SQLite | `data/kabusys.sqlite` | `orders` | **状態管理**: リアルタイムの現在状態・低レイテンシ読み書き |
| DuckDB | `audit.py` 管理 | `order_requests` / `executions` | **監査ログ**: 追記専用・変更不可の証跡記録 |

### ファイル構成

```
src/kabusys/execution/
├── broker_api.py        ← BrokerAPIProtocol + データモデル（Issue #28）
├── kabu_client.py       ← KabuStationClient（Issue #28）
├── mock_client.py       ← MockBrokerClient（Issue #28）
├── order_record.py      ← OrderRecord dataclass + 状態遷移ルール（DB なし純粋ロジック）
├── order_repository.py  ← SQLite 読み書き（永続化のみ）
└── order_manager.py     ← 外向き API（order_record + order_repository を組み合わせ）
```

### OrderState（enum 値）

| 値 | 意味 |
|----|------|
| `"created"` | 内部キューに登録済み、未送信 |
| `"sent"` | broker API に送信済み、応答待ち（クラッシュ時に不明状態になりうる） |
| `"accepted"` | 証券会社受付済み、市場待機中 |
| `"partial"` | 一部約定済み |
| `"filled"` | 全量約定済み |
| `"closed"` | ポジション確定済み（Filled 後処理完了） |
| `"cancelled"` | 取消済み |
| `"rejected"` | 証券会社拒否 or リスク統制拒否 |

### OrderManager の主要メソッド

| メソッド | 役割 |
|---------|------|
| `create_order(signal_id, request)` | `OrderCreated` レコードを生成・保存。同一 `signal_id` の active 注文があれば `DuplicateOrderError` |
| `send_order(client_order_id)` | **SQLite に `OrderSent` を保存してから** broker を呼ぶ（クラッシュ安全）。成功で `OrderAccepted` に遷移 |
| `sync_order(client_order_id)` | broker の `get_order_status` で最新状態に同期。Reconciliation の入口 |
| `cancel_order(client_order_id)` | 終端状態なら broker を呼ばず `InvalidStateTransitionError`。それ以外は broker に cancel を送信 |

### 詳細仕様

`docs/superpowers/specs/2026-03-28-order-state-machine-design.md`
