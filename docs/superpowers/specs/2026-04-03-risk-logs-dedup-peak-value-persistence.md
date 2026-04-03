# risk_logs デデュープ + peak_value DB永続化 設計仕様

**Issues:** #141 (risk_logs 連投防止) / #142 (RiskMonitor peak_value 永続化)
**対象フェーズ:** Phase 8
**作成日:** 2026-04-03

---

## 背景・問題

### Issue #141: risk_logs 連投防止

`TradeMonitor` と `RiskMonitor` は異常条件が継続している間、`MonitoringEngine` のポーリング間隔（デフォルト 60 秒）ごとに同じイベントを `risk_logs` に記録し続ける。

- `risk_logs` テーブルが急激に肥大化する
- Streamlit ダッシュボードの「Recent Risk Events」が同一イベントで埋まり、新規異常が埋もれる

### Issue #142: RiskMonitor peak_value 永続化

`RiskMonitor._peak_value` はインスタンスメモリのみで管理される。`MonitoringEngine` が再起動（クラッシュ・OS 再起動等）すると `_peak_value` がリセットされ、再起動直後は `portfolio_value` を新しいピーク値として初期化するためドローダウンが過小評価される。

---

## スコープ

変更対象ファイル:

| ファイル | 変更種別 |
|---|---|
| `src/kabusys/monitoring/monitoring_db.py` | 変更（dedup + peak_value カラム追加） |
| `src/kabusys/monitoring/risk_monitor.py` | 変更（DB から peak_value 読み込み・書き込み） |
| `src/kabusys/monitoring/trade_monitor.py` | 変更（log_risk_event に dedup_minutes 追加） |
| `tests/test_monitoring_engine.py` | 変更（新規テスト追加） |

---

## 設計

### 1. MonitoringDB: `log_risk_event()` デデュープ

`dedup_minutes: int | None = None` 引数を追加する。`dedup_minutes` が指定された場合、INSERT 前に以下のクエリで直近同一イベントを確認し、N 分以内に記録済みなら INSERT をスキップして `False` を返す。

**デデュープキー:** `(event_type, detail)` ペア
- `detail` は `NULL` 許容のため、`detail IS NULL` と等値比較を使い分ける
- `DRAWDOWN_ALERT` / `POSITION_LIMIT` は `detail=None` → `event_type` 単位でデデュープ
- `STALE_ORDER` / `PRICE_ANOMALY` は `detail=client_order_id` → 注文単位でデデュープ

```python
def log_risk_event(
    self,
    event_type: str,
    metric_name: str,
    metric_value: float,
    threshold: float,
    detail: str | None = None,
    logged_at: datetime | None = None,
    dedup_minutes: int | None = None,  # 追加
) -> bool:  # True=記録, False=スキップ
```

デデュープ SQL（`dedup_minutes` が指定されている場合のみ実行）:

```sql
SELECT MAX(logged_at) FROM risk_logs
WHERE event_type = ?
  AND (
        (detail IS NULL AND ? IS NULL)
        OR detail = ?
      )
```

最新 `logged_at` が `now - dedup_minutes` より新しければスキップ。

戻り値: `True`（INSERT 実行）/ `False`（スキップ）

### 2. MonitoringDB: `dashboard` テーブルへの `peak_value` カラム追加

#### 2.1 スキーマ変更

```sql
CREATE TABLE IF NOT EXISTS dashboard (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    updated_at       TEXT    NOT NULL,
    portfolio_value  REAL    NOT NULL,
    cash             REAL    NOT NULL,
    drawdown_pct     REAL    NOT NULL,
    open_order_count INTEGER NOT NULL,
    position_count   INTEGER NOT NULL,
    peak_value       REAL                -- 追加（NULL 許容: 永続化前の旧レコードに対応）
);
```

#### 2.2 マイグレーション

`init_monitoring_db()` で既存テーブルへのカラム追加を冪等に実行する:

```python
try:
    conn.execute("ALTER TABLE dashboard ADD COLUMN peak_value REAL")
    conn.commit()
except sqlite3.OperationalError:
    pass  # カラムが既存の場合は無視
```

#### 2.3 `upsert_dashboard()` 更新

```python
def upsert_dashboard(
    self,
    portfolio_value: float,
    cash: float,
    drawdown_pct: float,
    open_order_count: int,
    position_count: int,
    peak_value: float | None = None,   # 追加
) -> None:
```

`peak_value=None` の場合は既存値を上書きしない（`COALESCE` で保護）:

```sql
INSERT OR REPLACE INTO dashboard
    (id, updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)
VALUES
    (1, ?, ?, ?, ?, ?, ?, COALESCE(?, (SELECT peak_value FROM dashboard WHERE id=1)))
```

#### 2.4 `get_dashboard()` 更新

戻り値の dict に `peak_value: float | None` を追加する。

### 3. RiskMonitor: peak_value の DB 読み書き

#### 3.1 起動時の読み込み

`check_once()` で `_peak_value is None` の場合、DB から値を復元する:

```python
if self._peak_value is None:
    dashboard = self._db.get_dashboard()
    if dashboard and dashboard.get("peak_value") is not None:
        self._peak_value = dashboard["peak_value"]
    elif dashboard:
        self._peak_value = dashboard["portfolio_value"]
```

#### 3.2 更新時の永続化

`_peak_value` が更新された場合（初期化時・新高値更新時）に `upsert_dashboard()` で DB へ書き込む:

```python
if self._peak_value is None or portfolio_value > self._peak_value:
    self._peak_value = portfolio_value
    self._db.upsert_dashboard(..., peak_value=self._peak_value)
```

### 4. TradeMonitor / RiskMonitor: dedup_minutes の適用

`log_risk_event()` 呼び出しにデフォルト 30 分のデデュープを追加:

| Monitor | event_type | dedup_minutes |
|---|---|---|
| TradeMonitor | `STALE_ORDER` | 30 |
| TradeMonitor | `PRICE_ANOMALY` | 30 |
| RiskMonitor | `DRAWDOWN_ALERT` | 30 |
| RiskMonitor | `POSITION_LIMIT` | 30 |

---

## エラーハンドリング

- `dedup_minutes` 指定時の SELECT が例外を投げた場合: INSERT を実行して記録する（フェイルオープン）
- `ALTER TABLE` が失敗した場合（カラム既存以外の理由）: 例外を上位に伝播させる

---

## テスト

### Issue #141 テスト

| テスト名 | 検証内容 |
|---|---|
| `test_log_risk_event_dedup_skips_within_window` | 同一 (event_type, detail) を 30 分以内に再呼び出し → スキップ（DB に 1 件のみ） |
| `test_log_risk_event_dedup_records_after_window` | 30 分超過後は記録される |
| `test_log_risk_event_no_dedup_when_none` | `dedup_minutes=None`（デフォルト）では毎回記録 |
| `test_log_risk_event_dedup_different_detail` | `detail` が異なれば別イベントとして記録 |
| `test_risk_monitor_dedup_suppresses_repeated_alert` | `RiskMonitor.check_once()` を連続呼び出しすると risk_log は 1 件のみ |
| `test_trade_monitor_dedup_suppresses_stale_order` | 同一注文の STALE_ORDER は 30 分以内は 1 件のみ |

### Issue #142 テスト

| テスト名 | 検証内容 |
|---|---|
| `test_peak_value_persisted_on_new_high` | 新高値更新時に dashboard.peak_value が更新される |
| `test_peak_value_restored_on_restart` | `RiskMonitor` を再生成後も peak_value が DB から復元される |
| `test_drawdown_correct_after_restart` | 再起動後もドローダウン計算が正確 |
| `test_migration_adds_peak_value_column` | 既存 DB（peak_value カラムなし）に `init_monitoring_db()` を実行してもエラーなし |

---

## 非スコープ

- `last_risk_events` テーブルの新設（シンプルな dedup で十分）
- Streamlit ダッシュボードの表示変更（現状のままで機能する）
- dedup 時間の設定ファイル化（30 分固定で十分）
