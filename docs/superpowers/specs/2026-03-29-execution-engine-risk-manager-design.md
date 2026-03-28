# Execution Engine + Risk Manager 設計仕様

- Issue: #30 Execution Engine メインループ、#31 リスク管理3段階ガード
- 日付: 2026-03-29
- フェーズ: Phase 6

---

## 1. 目的

`signal_generator.py` が夜間バッチで生成した DuckDB `signals` テーブルを、翌営業日の寄付き前後に発注に変換する Execution Engine と、発注前後に3段階のリスク検査を行う Risk Manager を実装する。

既存の `OrderManager` / `OrderRepository` / `KabuStationClient` を活用し、**クラッシュ安全性・二重発注防止・暴走防止**を担保する。

### 起動時リコンシリエーションについて

`OrderSent` 状態のレコードが残る起動時の自動復旧は **Issue #32（リコンシリエーション）** が担う。本スペックのスコープ外。

---

## 2. モジュール構成

```
src/kabusys/execution/
├── broker_api.py        ✅ 既存（BrokerAPIProtocol, データモデル）
├── kabu_client.py       ✅ 既存（REST） ← WebSocket 受信メソッド追加
├── mock_client.py       ✅ 既存
├── order_record.py      ✅ 既存（OrderState 8状態）
├── order_repository.py  ✅ 既存（SQLite 永続化）
├── order_manager.py     ✅ 既存
├── risk_manager.py      🆕 #31 — 3段階リスクガード
└── execution_engine.py  🆕 #30 — メインループ + WebSocket スレッド管理
```

> **注**: 既存ファイルは `origin/main` の `src/kabusys/execution/` 配下に実装済み。ローカルブランチとの乖離に注意。

### DB の役割分担

| DB | 用途 |
|----|------|
| **DuckDB** | `signals` テーブル（夜間バッチ生成・読み取り専用） |
| **SQLite** | `orders` テーブル（`OrderRepository` 管理・読み書き） |

### "active 注文" の定義

`order_repository.py` の `_TERMINAL_STATES = {Closed, Cancelled, Rejected}` に含まれない状態が active。`list_active()` はこれを返す。`kill_switch()` および Gate 1 重複チェックはこれを使う。

### 責務分担

| クラス | 責務 |
|-------|------|
| `RiskManager` | 発注前後の3段階リスク検査のみ。Gate 1/3 はステートレス、Gate 2 はサーキットブレーカー状態を保持 |
| `ExecutionEngine` | オーケストレーション。「いつ・何を・どの順で呼ぶか」を管理。DB・API は注入されたオブジェクトに委譲 |

---

## 3. signal_id 採番と冪等性

```python
signal_id = f"{date.isoformat()}_{code}_{side}"
# 例: "2026-03-29_1234_buy"
```

`OrderManager.create_order()` の `DuplicateOrderError` による冪等性をそのまま活用し、再起動時の二重発注を防ぐ。これが CLAUDE.md アーキテクチャ制約 #3「冪等な発注キュー」の実現手段である。`signals` テーブル自体が Pull 型の Signal Queue として機能する。

---

## 4. RiskManager 設計（#31）

### 4.1 設定データクラス

```python
@dataclass
class RiskConfig:
    max_position_pct: float = 0.10        # 1銘柄最大投資比率（RiskManagement.md Section 4.2）
    max_utilization: float = 0.80         # 全ポジション投下上限（キャッシュ最低20%に相当）
    rate_limit_per_sec: int = 5           # API レート制限（毎秒5回）
    circuit_breaker_errors: int = 10      # ウィンドウ内エラー上限
    circuit_breaker_window_sec: int = 60  # エラーカウントウィンドウ（秒）
    max_drawdown: float = 0.15            # キルスイッチ発動ドローダウン閾値（Phase 6 MVP）
    initial_portfolio_value: float = 0.0  # セッション開始時の資産評価額


@dataclass
class RiskResult:
    passed: bool
    reason: str = ""  # 不合格理由（ログ・Monitoring 用）
```

> **Phase 6 スコープ外（将来対応）:**
> - `RiskManagement.md` の段階的ドローダウン対応（5% → ポジション縮小、10% → 新規停止、15% → 全決済）は Phase 7 Monitoring と合わせて実装予定
> - 最大保有銘柄数（10銘柄）・セクター集中度（30%）チェックは Portfolio Construction 層（Phase 5）が担う想定

### 4.2 Gate 1: シグナルレベル（発注前）

```python
def check_signal(
    self,
    signal_id: str,
    code: str,
    order_value: float,  # 発注金額 = 株価 × 発注株数（ExecutionEngine が portfolio_targets から算出）
) -> RiskResult:
```

検査内容：
1. **余力チェック**: `broker.get_available_cash() >= order_value`
2. **重複チェック**: `repo.get_by_signal(signal_id)` に active 注文が存在しないか
3. **ポジション上限**: `broker.get_positions()` で同銘柄の評価額 + order_value が総資産の `max_position_pct` 以内か、かつ全ポジションが `max_utilization` 以内か

### 4.3 Gate 2: エグゼキューションレベル（API 送信前）

```python
def check_execution(self) -> RiskResult:
```

検査内容：
1. **レート制限**: トークンバケツ方式（`rate_limit_per_sec` 回/秒）。制限超過時は `passed=False`（呼び出し元がスリープして再試行）
2. **サーキットブレーカー**: 直近 `circuit_breaker_window_sec` 秒以内に `circuit_breaker_errors` 件のエラーが蓄積された場合に `OPEN` 状態へ遷移し発注停止

> **サーキットブレーカーのカウント方式**: 「ウィンドウ内の累積エラー件数」。成功が記録されると `record_api_success()` でカウンタがリセットされる（「連続エラー」ではない）。

**サーキットブレーカー状態遷移：**
```
CLOSED（正常）
  → [window内にN件エラー蓄積] → OPEN（発注停止）
  → [window秒経過] → HALF_OPEN（1件試行許可）
  → [成功 → record_api_success()] → CLOSED
  → [失敗 → record_api_error()] → OPEN
```

補助メソッド：
- `record_api_error()` — エラー記録（send_order 失敗時に呼ぶ）
- `record_api_success()` — 成功記録（HALF_OPEN → CLOSED 遷移用）

### 4.4 Gate 3: メトリクスレベル（約定後監視）

```python
def check_metrics(self, current_portfolio_value: float) -> RiskResult:
```

検査内容：
- ドローダウン = `(initial_portfolio_value - current_portfolio_value) / initial_portfolio_value`
- `> max_drawdown` (デフォルト 15%) でキルスイッチ発動フラグを返す

`current_portfolio_value` の計算は呼び出し元（ExecutionEngine）が以下で算出して渡す：
```python
positions = broker.get_positions()
market_value = sum(p.qty * p.current_price for p in positions if p.current_price is not None)
current_portfolio_value = broker.get_available_cash() + market_value
```

`Position.current_price` は下記 Section 10 で追加するフィールド。

> **Gate 3 の呼び出しタイミング**: シグナル送信ループ内ではなく、WebSocket push 受信後（約定が確定した後）にのみ呼ぶ。発注直後はまだ約定していないため意味がない。

---

## 5. ExecutionEngine 設計（#30）

### 5.1 設定データクラス

```python
@dataclass
class EngineConfig:
    target_date: date
    signal_send_start: time = time(8, 50)  # 発注開始時刻
    signal_send_end: time = time(9, 10)    # 発注締切時刻
    market_close: time = time(15, 30)      # セッション終了時刻
```

### 5.2 コンストラクタ

```python
class ExecutionEngine:
    def __init__(
        self,
        broker: BrokerAPIProtocol,
        repo: OrderRepository,
        risk_manager: RiskManager,
        duckdb_conn: duckdb.DuckDBPyConnection,
        config: EngineConfig,
    ) -> None:
```

すべての依存を外部注入。`ExecutionEngine` 自身は DB / API に直接触れない。

### 5.3 メインループ

```python
def run_session(self) -> None:
```

実行フロー：
```
1. WebSocket スレッド起動（kabu push 受信）
2. config.signal_send_start まで待機
3. シグナル処理ループ（signal_send_start ～ signal_send_end）:
   a. DuckDB の portfolio_targets から today の発注計画（code, qty, price）を取得
   b. DuckDB の signals から today のシグナルを取得し portfolio_targets と突合
   c. for each signal:
        signal_id = f"{date}_{code}_{side}"
        order_value = price × qty  （portfolio_targets の値を使用）
        [Gate 1] risk_manager.check_signal(signal_id, code, order_value)
                   → NG: skip & log
        [Gate 2] risk_manager.check_execution()
                   → rate limit: sleep 0.2秒して再試行
                   → circuit breaker OPEN: halt（kill_switch 判断は運用者に委ねる）
        OrderManager.create_order(signal_id, OrderRequest(code, side, qty, order_type, price))
        OrderManager.send_order(client_order_id)
        risk_manager.record_api_success() / record_api_error()（結果に応じて）
4. signal_send_end ～ market_close:
   WebSocket push を drain するループ:
     payload = _push_queue.get(timeout=1.0)
     OrderManager.sync_order(client_order_id)
     portfolio_value = broker.get_available_cash() + sum(p.market_value for p in broker.get_positions())
     [Gate 3] risk_manager.check_metrics(portfolio_value)
                → NG: kill_switch() 発動
5. market_close: _stop_event.set()、WebSocket スレッド停止、セッション終了
```

### 5.4 order_value の算出元

`signals` テーブルはシグナルのみ（code, side, score, signal_rank）を持つ。発注株数・価格は Phase 5 Portfolio Construction が生成した DuckDB の **`portfolio_targets`** テーブルから取得する：

```sql
SELECT pt.code, pt.target_size, pt.entry_price
FROM signals s
JOIN portfolio_targets pt ON s.date = pt.date AND s.code = pt.code
WHERE s.date = ? AND s.side = 'buy'
```

- `order_value = entry_price × target_size`
- `qty = target_size`（単元株に切り捨て済みの値）

### 5.5 WebSocket スレッド

```python
def _websocket_worker(self) -> None:
```

- WebSocket URL は `KabuStationClient.base_url` を `ws://` に変換して末尾に `/websocket` を付加
- `_stop_event`（`threading.Event`）が set されるまでループ
- 受信した push payload を `_push_queue`（`queue.Queue`）に投入
- メインループが `_push_queue` を drain して `OrderManager.sync_order()` を呼ぶ

**スレッド間通信：**
```
WebSocket thread ──[queue.Queue]──→ Main thread
                                     ↓
                                sync_order()     → SQLite UPDATE
                                check_metrics()  → ドローダウン監視（Gate 3）
```

`kabu_client.py` に `stream_push(on_message: Callable, stop_event: threading.Event)` メソッドを追加してWebSocket受信を抽象化する。

### 5.6 kill_switch()

```python
def kill_switch(self) -> None:
```

1. `_stop_event.set()` — 全ループ停止
2. `repo.list_active()` — active 注文を全件取得
3. 各注文に対して `order_manager.cancel_order(client_order_id)` を呼ぶ
   - `OrderManager.cancel_order()` は broker API 呼び出し + SQLite の状態を `Cancelled` に遷移する一気通貫処理
   - `InvalidStateTransitionError`（Filled 等の terminal 状態）と `RuntimeError` は無視してスキップ

> **注**: `broker.cancel_order(broker_order_id)` を直接呼ばないこと。SQLite の状態が更新されないため、再起動後も active 注文として残り二重発注や重複チェック誤検知の原因となる。

---

## 6. データフロー

```
【夜間バッチ済み】
DuckDB: signals(date, code, side, score, signal_rank)
DuckDB: portfolio_targets(date, code, target_size, entry_price, ...)
SQLite: orders（OrderRepository 管理）

【8:50 セッション開始】
ExecutionEngine.run_session()
  │
  ├─ DuckDB: signals JOIN portfolio_targets WHERE date=?
  │         → (code, side, qty, price) リスト
  │
  ├─ [Gate 1] RiskManager.check_signal(signal_id, code, order_value)
  │         → broker.get_available_cash()    REST
  │         → broker.get_positions()         REST
  │         → repo.get_by_signal(signal_id)  SQLite
  │
  ├─ [Gate 2] RiskManager.check_execution()
  │         → トークンバケツ / サーキットブレーカー（メモリ）
  │
  ├─ OrderManager.create_order()  → SQLite INSERT
  ├─ OrderManager.send_order()    → REST POST → SQLite UPDATE
  │
  └─ (Gate 3 は送信ループ内では呼ばない)

【約定 Push 受信（WebSocket スレッド → メインスレッド）】
kabu WebSocket push
  → _push_queue.put(payload)
  → Main: OrderManager.sync_order()            → SQLite UPDATE
  → Main: [Gate 3] RiskManager.check_metrics() → ドローダウン監視
           → NG: kill_switch()
```

---

## 7. kabu_client.py への追加

既存の `KabuStationClient` に以下を追加：

```python
def stream_push(
    self,
    on_message: Callable[[dict], None],
    stop_event: threading.Event,
) -> None:
    """WebSocket で kabu station の push 通知を受信するブロッキングメソッド。
    stop_event が set されるまでループする。スレッド内で呼び出すことを想定。

    WebSocket URL は self._base_url の http:// を ws:// に置換し /websocket を付加する。
    例: http://localhost:18080/kabusapi → ws://localhost:18080/kabusapi/websocket
    """
```

使用ライブラリ: `websocket-client`（依存に追加）

---

## 8. テスト方針

テストファイルは2つに分割：
- `tests/test_risk_manager.py` — RiskManager の単体テスト
- `tests/test_execution_engine.py` — ExecutionEngine の統合テスト（#34 も同ファイル）

| テスト対象 | ファイル | 手法 |
|-----------|---------|------|
| Gate 1: 余力不足 | test_risk_manager | `MockBrokerClient` で `get_available_cash()=0` |
| Gate 1: 重複チェック | test_risk_manager | インメモリ SQLite に active 注文を事前挿入 |
| Gate 1: ポジション上限 | test_risk_manager | `get_positions()` で上限超えポジションを返す |
| Gate 2: レート制限 | test_risk_manager | `check_execution()` を N+1 回呼んで拒否を確認 |
| Gate 2: CB CLOSED→OPEN | test_risk_manager | `record_api_error()` を N 回呼んで OPEN 遷移 |
| Gate 2: CB OPEN→HALF_OPEN→CLOSED | test_risk_manager | 時刻を注入して window 経過後の遷移を確認 |
| Gate 3: キルスイッチ | test_risk_manager | ドローダウン超過値を渡して `passed=False` |
| ExecutionEngine シグナル処理 | test_execution_engine | DuckDB インメモリ + MockBrokerClient + インメモリ SQLite |
| WebSocket push 処理 | test_execution_engine | `_push_queue` に直接投入して `sync_order()` 呼び出しを確認 |
| kill_switch | test_execution_engine | 全 active 注文が cancel されることを確認 |

---

## 10. broker_api.py への追加

既存の `Position` dataclass に `current_price` フィールドを追加：

```python
@dataclass
class Position:
    code: str
    qty: int
    avg_price: float
    current_price: float | None = None  # 現在値（時価評価額計算用）
```

- `kabu_client.py`: kabu API レスポンスの `CurrentPrice`（または `CurrentPriceTime` 付きフィールド）を `current_price` にマップする
- `mock_client.py`: `MockBrokerClient.get_positions()` で `current_price` を返すよう更新する

> `avg_price` は取得単価（コスト基準）であり、現在の市場価値ではない。ドローダウン計算に `avg_price` を使うと含み損が反映されないため、必ず `current_price` を使うこと。

---

## 9. 既存コードとの整合

- `BrokerAPIProtocol` の `get_available_cash() -> float`・`get_positions() -> list[Position]` は `broker_api.py` に定義済み
- `MockBrokerClient` は `fill_mode` パラメータ対応済み — テストでそのまま使用可能
- `OrderManager.create_order()` の `DuplicateOrderError` が冪等性を保証 — 追加ロジック不要
- `order_repository.py` の `_TERMINAL_STATES`・`list_active()` が "active 注文" の定義源
