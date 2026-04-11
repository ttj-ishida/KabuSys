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

```sql
ALTER TABLE trade_logs ADD COLUMN latency_ms REAL;
```

`init_monitoring_db()` に `ALTER TABLE` を冪等実行するマイグレーション処理を追加し、既存DBへの後方互換を保証する（カラム既存の場合は `OperationalError` を捕捉してスキップ）。

### `log_trade()` シグネチャ変更

```python
def log_trade(
    self,
    event_type: str,
    order: OrderRecord,
    latency_ms: float | None = None,
) -> None: ...
```

`latency_ms` はオプション（デフォルト `None`）とし、既存呼び出し元への影響を最小化する。

---

## レイテンシ計測（`execution_engine.py`）

`send_order()` 呼び出しの前後で `time.perf_counter()` を使用し、ミリ秒換算して `MonitoringDB.log_trade()` へ渡す。

```python
t0 = time.perf_counter()
result = broker.send_order(order)
latency_ms = (time.perf_counter() - t0) * 1000
monitoring_db.log_trade(event_type="Sent", order=order, latency_ms=latency_ms)
```

---

## pytest 統合テストスイート

**ファイル:** `tests/integration/test_paper_trading.py`

SQLite in-memory DB + MockBrokerClient を使用し、外部依存なしで実行する。

### TestSystemStability（システム安定性）

| テスト | 内容 |
|---|---|
| `test_multiple_polling_cycles_no_crash` | ExecutionEngine を 3 サイクル分ループさせ、例外なく完走することを確認 |
| `test_monitoring_db_written` | 各サイクル後に `system_status` テーブルへの書き込みを確認 |

### TestOrderSuccessRate（注文成功率）

| テスト | 内容 |
|---|---|
| `test_instant_mode_100pct_fill` | `PAPER_FILL_MODE=instant` → 全注文が Filled になることを確認 |
| `test_reject_mode_0pct_fill` | `PAPER_FILL_MODE=reject` → 全注文が Rejected になることを確認 |
| `test_partial_mode_partial_fill` | `PAPER_FILL_MODE=partial` → 注文が qty/2 で部分成立することを確認 |

### TestSignalAccuracy（シグナル精度）

| テスト | 内容 |
|---|---|
| `test_buy_signal_creates_buy_order` | BUY シグナルが BUY 注文に変換されることを確認 |
| `test_sell_signal_creates_sell_order` | SELL シグナルが SELL 注文に変換されることを確認 |
| `test_risk_rejection_blocks_order` | リスク上限超過シグナルが発注されないことを確認 |

### TestApiLatency（API レイテンシ）

| テスト | 内容 |
|---|---|
| `test_send_order_latency_recorded` | `send_order()` 後に `trade_logs.latency_ms` が記録されることを確認 |
| `test_send_order_latency_under_threshold` | MockBrokerClient の `send_order()` 応答が 500ms 以内であることを確認 |
| `test_get_board_latency_under_threshold` | `get_board()` 応答が 1000ms 以内であることを確認 |

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
  シグナル発生数:   52
  注文変換数:       48
  変換率:           92.3%  (リスク却下: 4件)

[APIレイテンシ]
  平均レイテンシ:    12.3 ms
  最大レイテンシ:    87.1 ms
  P95レイテンシ:     45.2 ms

判定: PASS (全指標が基準値を満たしています)
========================================
```

### 合格基準

| 指標 | 基準値 |
|---|---|
| 稼働率 | ≥ 99% |
| 注文成功率 | ≥ 90% |
| シグナル変換率 | ≥ 80% |
| P95 レイテンシ | ≤ 200 ms |

### データソース

| 指標 | テーブル | 計算方法 |
|---|---|---|
| 稼働率 | `system_status` | `(エラーなし行数 / 総行数) × 100` |
| 注文成功率 | `trade_logs` | `Filled 件数 / 総注文件数 × 100` |
| シグナル変換率 | `trade_logs` | `Created 件数 / (Created + RiskRejected 件数) × 100` |
| レイテンシ | `trade_logs.latency_ms` | `AVG / MAX / PERCENTILE(95)` |

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
| `src/kabusys/monitoring/monitoring_db.py` | 変更 | `trade_logs` スキーマ + migration + `log_trade()` シグネチャ |
| `src/kabusys/execution/execution_engine.py` | 変更 | `send_order()` 前後でレイテンシ計測 |
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
- `paper_verification_report.py` のロジック自体はユニットテスト対象外（手動レビュー前提）
- 既存テストへの破壊的変更は最小化（`latency_ms` はオプション引数）
