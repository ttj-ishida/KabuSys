# Paper Trading 検証テスト 設計仕様書

**Issue:** #44 【Phase 8】Paper Trading検証テスト  
**Date:** 2026-04-11  
**Status:** Approved

---

## 概要

Phase 8 Paper Trading の動作を検証するため、以下2つのコンポーネントを実装する。

1. **pytest 統合テストスイート** (`tests/integration/test_paper_trading.py`)  
   MockBrokerClient + ExecutionEngine を組み合わせ、4指標を自動検証する。CI で繰り返し実行可能。

2. **検証レポートスクリプト** (`src/kabusys/tools/paper_verification_report.py`)  
   実稼働後の `paper_trading.db` を集計し、ゴーライブ判断に必要な指標をコンソールへ出力する。

---

## スキーマ変更

### `trade_logs` テーブルへの `latency_ms` カラム追加

`send_order()` のブローカーAPI応答時間を記録するため、カラムを追加する。

マイグレーションは既存の `peak_value` マイグレーションと同じ `PRAGMA table_info()` パターンで実装し、コードベースの一貫性を保つ。

```python
# init_monitoring_db() 内に追加（既存の peak_value マイグレーションの直後）
existing_trade_cols = {row[1] for row in conn.execute("PRAGMA table_info(trade_logs)")}
if "latency_ms" not in existing_trade_cols:
    conn.execute("ALTER TABLE trade_logs ADD COLUMN latency_ms REAL")
    conn.commit()
```

### `log_trade_event()` シグネチャ変更

既存の `log_trade_event()` に `latency_ms` オプション引数を末尾に追加する。  
`logged_at` の型は既存のまま `datetime | None` を保持する。

```python
def log_trade_event(
    self,
    event_type: str,
    client_order_id: str,
    code: str,
    side: str,
    qty: int,
    price: float,
    filled_qty: int = 0,
    state: str = "",
    logged_at: datetime | None = None,
    latency_ms: float | None = None,  # 追加（末尾オプション）
) -> None: ...
```

INSERT 文も `latency_ms` カラムを追加する（`VALUES` のプレースホルダーを1つ増やす）。

---

## レイテンシ計測（`execution_engine.py`）

`ExecutionEngine.__init__` に `monitoring_db: MonitoringDB | None = None` をオプション引数として追加する。  
既存の呼び出し元への変更は不要（`None` のときはレイテンシ記録をスキップ）。

`_process_signals()` 内の `send_order()` 呼び出し前後で `time.perf_counter()` を使用する。  
`OrderSentPendingError` の場合もブローカーはリクエストを受理しているため、**レイテンシを記録する**。

```python
t0 = time.perf_counter()
try:
    self._order_manager.send_order(record.client_order_id)
    latency_ms = (time.perf_counter() - t0) * 1000
    self._risk_manager.record_api_success()
    if self._monitoring_db is not None:
        self._monitoring_db.log_trade_event(
            "Sent", record.client_order_id, record.code, record.side,
            record.qty, record.price, record.filled_qty,
            record.state.value, latency_ms=latency_ms,
        )
except OrderSentPendingError:
    latency_ms = (time.perf_counter() - t0) * 1000
    self._risk_manager.record_api_success()
    if self._monitoring_db is not None:
        self._monitoring_db.log_trade_event(
            "Sent", record.client_order_id, record.code, record.side,
            record.qty, record.price, record.filled_qty,
            record.state.value, latency_ms=latency_ms,
        )
except Exception as exc:
    self._risk_manager.record_api_error()
    logger.error("発注失敗: signal_id=%s: %s", signal_id, exc)
```

---

## pytest 統合テストスイート

**ファイル:** `tests/integration/test_paper_trading.py`

SQLite in-memory DB + MockBrokerClient を使用し、外部依存なしで実行する。  
合計 **11 テスト**。

### TestSystemStability（システム安定性）

| テスト | 内容 |
|---|---|
| `test_multiple_polling_cycles_no_crash` | `_process_signals()` を 3 回呼び出し、例外なく完走することを確認 |
| `test_trade_logs_written_per_cycle` | 各サイクル後に `trade_logs` テーブルへの書き込みを確認（ExecutionEngine が OrderManager 経由で "Created" イベントを記録するため） |

### TestOrderSuccessRate（注文成功率）

| テスト | 内容 |
|---|---|
| `test_instant_mode_100pct_fill` | `PAPER_FILL_MODE=instant` → 全注文が `OrderState.Filled`（`.value = "filled"`）になることを確認 |
| `test_reject_mode_0pct_fill` | `PAPER_FILL_MODE=reject` → 全注文が `OrderState.Rejected`（`.value = "rejected"`）になることを確認 |
| `test_partial_mode_partial_fill` | `PAPER_FILL_MODE=partial` → 注文の `filled_qty` が `qty // 2` になることを確認 |
| `test_never_mode_order_stays_pending` | `PAPER_FILL_MODE=never` → 注文が `OrderState.OrderSent`（`.value = "sent"`）のまま残ることを確認 |

### TestSignalAccuracy（シグナル精度）

| テスト | 内容 |
|---|---|
| `test_buy_signal_creates_buy_order` | BUY シグナルが `side="buy"` の注文に変換されることを確認 |
| `test_sell_signal_creates_sell_order` | SELL シグナルが `side="sell"` の注文に変換されることを確認 |
| `test_risk_rejection_blocks_order` | リスク上限超過シグナルが発注されないことを確認（`OrderRepository.get_all()` で `OrderRecord` が作成されていないことを検証） |

### TestApiLatency（API レイテンシ）

| テスト | 内容 |
|---|---|
| `test_send_order_latency_recorded` | `monitoring_db` 付きで `send_order()` 後に `trade_logs.latency_ms` が `NOT NULL` で記録されることを確認 |
| `test_send_order_latency_under_threshold` | MockBrokerClient の `send_order()` 応答が 500ms 以内であることを `time.perf_counter()` で計測して確認 |

---

## 検証レポートスクリプト

**ファイル:** `src/kabusys/tools/paper_verification_report.py`

### 出力形式

```
========================================
 Paper Trading 検証レポート
 期間: YYYY-MM-DD ~ YYYY-MM-DD
========================================
[システム安定性]
  総ポーリング数:   240
  エラー発生数:     0
  稼働率:           100.0%

[注文成功率]
  総注文数:         48
  成立数(Filled):   46
  成功率:           95.8%

[シグナル精度]
  Created 注文数:   48
  Sent 注文数:      47
  送信率:           97.9%
  リスク却下数:     4 件  (risk_logs 参照)

[APIレイテンシ]
  平均レイテンシ:    12.3 ms
  最大レイテンシ:    87.1 ms
  P95レイテンシ:     45.2 ms  (Python側で statistics.quantiles() を使用)

判定: PASS (全指標が基準値を満たしています)
========================================
```

### 合格基準

| 指標 | 基準値 |
|---|---|
| 稼働率 | ≥ 99% |
| 注文成功率（Filled / Created） | ≥ 90% |
| 送信率（Sent / Created） | ≥ 95% |
| P95 レイテンシ | ≤ 200 ms |

### データソース

| 指標 | テーブル・条件 | 計算方法 |
|---|---|---|
| 稼働率 | `system_status` | `SUM(process_ok) / COUNT(*) × 100`（`process_ok` は 0 or 1 の INTEGER） |
| 注文成功率 | `trade_logs` | `COUNT(*) FILTER (WHERE event_type='Filled') / COUNT(*) FILTER (WHERE event_type='Created') × 100` |
| 送信率 | `trade_logs` | `COUNT(*) FILTER (WHERE event_type='Sent') / COUNT(*) FILTER (WHERE event_type='Created') × 100` |
| リスク却下数 | `risk_logs` | `COUNT(*)` （参考情報） |
| レイテンシ | `trade_logs WHERE latency_ms IS NOT NULL` | `AVG(latency_ms)` / `MAX(latency_ms)` / P95 は Python 側で `statistics.quantiles()` を使用 |

### 使用方法

```bash
python -m kabusys.tools.paper_verification_report
# または期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```

環境変数 `PAPER_TRADING_SQLITE_PATH` が未設定の場合は `data/paper_trading.db` をデフォルトとして使用する。

---

## 影響ファイル一覧

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/kabusys/monitoring/monitoring_db.py` | 変更 | `trade_logs` スキーマ migration (PRAGMA方式) + `log_trade_event()` に `latency_ms: float \| None = None` 追加 |
| `src/kabusys/execution/execution_engine.py` | 変更 | `__init__` に `monitoring_db: MonitoringDB \| None = None`、`send_order()` 前後でレイテンシ計測（`OrderSentPendingError` 分岐でも記録） |
| `src/kabusys/tools/__init__.py` | 新規 | パッケージマーカー |
| `src/kabusys/tools/paper_verification_report.py` | 新規 | 集計レポートスクリプト |
| `tests/integration/__init__.py` | 新規 | パッケージマーカー |
| `tests/integration/test_paper_trading.py` | 新規 | 統合テストスイート（11テスト） |
| `tests/test_monitoring_db.py` | 変更 | `latency_ms` を含むテスト更新 |
| `tests/test_execution_engine.py` | 変更 | latency 記録の検証テスト追加 |

---

## テスト戦略

- 統合テストは全て `pytest` で自動実行（CI 対応）
- `tests/integration/` は外部依存なし（SQLite in-memory + MockBrokerClient）
- `paper_verification_report.py` のロジック自体は手動レビュー前提（単体テスト対象外）
- 既存テストへの破壊的変更は最小化：
  - `latency_ms` はオプション引数（既存呼び出し元変更不要）
  - `monitoring_db` は `ExecutionEngine` へのオプション引数（既存テスト変更不要）
