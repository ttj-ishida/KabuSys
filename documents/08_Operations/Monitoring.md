
# Monitoring.md

## 1. 目的

本ドキュメントは、日本株自動売買システムの **監視（Monitoring）設計** を定義する。

自動売買システムでは、以下の理由から監視が極めて重要である。

- システム障害の早期検知
- 誤発注の防止
- API障害への迅速対応
- 戦略パフォーマンスの監視
- リスク状況のリアルタイム把握

監視システムは **本番運用の安全性を担保する最後の防御層**となる。

---

# 2. 監視対象

本システムでは以下のカテゴリを監視する。

| カテゴリ | 内容 |
|--------|------|
システム監視 | プロセス、CPU、メモリ |
データ監視 | データ更新状況 |
AI監視 | AIスコア生成 |
戦略監視 | シグナル生成 |
発注監視 | 注文状態 |
リスク監視 | ポジション、ドローダウン |

---

# 3. システム監視

監視対象

| 項目 | 内容 | 閾値 |
|----|----|----|
CPU使用率 | 高負荷検知 | > 90% |
メモリ使用量 | メモリリーク検知 | > 85% |
ディスク容量 | データ容量監視 | > 90% |
プロセス状態 | Execution プロセス生存確認 | PID ファイル方式 |

### プロセス生存確認（PID ファイル方式）

- `ExecutionEngine.run_session()` 起動時に `data/execution.pid` に PID を書き出す
- 正常終了時は `finally` ブロックで PID ファイルを削除
- `SystemMonitor.check_once()` が PID ファイルの存在とプロセス生存を確認

| 状態 | 判定 |
|---|---|
| PID ファイルなし | 未起動 or 正常終了（`process_ok=False`） |
| PID ファイルあり・プロセス生存 | 正常稼働（`process_ok=True`） |
| PID ファイルあり・プロセス死亡 | 異常終了 → stale PID 削除・アラート |

異常終了時のリカバリ: プロセスの自動再起動は行わない。`Reconciler` が次回起動時に状態復旧を担当。

---

# 4. データ監視

データ更新状況を監視する。

監視項目

| データ | 内容 | 判定方法 |
|------|------|------|
株価データ | 更新時刻 | `pipeline.get_last_price_date(duckdb_conn)` で最終更新日を取得、3日以上古い場合（または None）を異常とする。`SystemMonitor.check_once()` で実施。 |
ニュースデータ | 取得成功 | 将来フェーズで実装 |
特徴量 | 生成完了 | 将来フェーズで実装 |
AIスコア | 更新状況 | 将来フェーズで実装 |

異常例

- データ更新停止（株価データが 3 日以上未更新）
- ETL失敗
- データ欠損（`get_last_price_date()` が None を返す）

---

# 5. 戦略監視

戦略処理を監視する。

監視対象

| 項目 | 内容 |
|----|----|
シグナル生成 | 正常終了 |
銘柄数 | 異常値検知 |
スコア分布 | 偏り検知 |

例

```
シグナル数 = 0
```

異常検知

---

# 6. 発注監視

発注状態を監視する。

注文状態

```
Created
Sent
Accepted
PartialFill
Filled
Cancelled
Rejected
```

監視項目（`TradeMonitor.check_once()` で実施）

| 項目 | 内容 | 閾値 |
|----|----|---|
未約定注文 | 長時間滞留（Created/Sent/Accepted） | 30分以上経過で `STALE_ORDER` アラート |
注文失敗 | APIエラー | OrderRepository の state 参照 |
約定価格 | 発注価格との乖離 | ±20% 超で `PRICE_ANOMALY` アラート（成行注文は除外） |

---

# 7. リスク監視

ポートフォリオリスクを監視する。

監視項目（`RiskMonitor.check_once()` で実施）

| 指標 | 内容 | 閾値 |
|----|----|---|
ドローダウン | ポートフォリオ最高値からの下落率 | > 10% でアラート（monitoring のみ。5%/15% の執行制御は RiskManager が担当） |
保有銘柄数 | `positions` テーブルの `qty != 0` 行数 | > 10 でアラート |

**注意:** Phase 7 の RiskMonitor は観測・アラートのみ行う。RiskManagement.md の 5%（ポジション半減）・15%（全決済）トリガーは `ExecutionEngine` / `RiskManager` の執行パスで実施される。

---

# 8. AI監視

AIモデルの状態を監視する。

監視対象

| 項目 | 内容 |
|----|----|
ニュース解析数 | 異常検知 |
AIスコア分布 | 偏り検知 |
推論時間 | 遅延検知 |

異常例

- AI停止
- 全銘柄同一スコア

---

# 9. アラート設計

異常検知時は通知を行う。

通知方法

| 方法 | 内容 |
|----|----|
LINE通知 | 推奨（`LINE_NOTIFY_ENABLED=true` かつ認証情報設定時のみ有効） |
ログ | 必須（常に有効） |

### LINE 通知アーキテクチャ（Null Object パターン）

LINE 通知は `src/kabusys/operations/notifier.py` の `build_notifier(settings)` で構築する。
Core コードは返り値の型を意識せず `.send(message)` を呼ぶだけでよい。

| 条件 | 返り値 | `send()` の動作 |
|---|---|---|
| `LINE_NOTIFY_ENABLED=false`（デフォルト） | `NullNotifier` | 何もせず `False` を返す（例外なし） |
| `LINE_NOTIFY_ENABLED=true` かつ認証情報欠落 | `NullNotifier`（フォールバック） | 同上 |
| `LINE_NOTIFY_ENABLED=true` かつ認証情報あり | `LineNotifier` | LINE Messaging API にプッシュ送信 |

**設計原則**: LINE API が障害中・未設定の場合でも Core の発注・監視ループが停止しない。

---

# 10. ダッシュボード

監視ダッシュボードを用意する。

**Phase 1 実装（Issue #231 / Issue #260）:** Streamlit マルチページ構成（10ページ）

| ページ | ファイル | 表示内容 |
|---|---|---|
| Home | `streamlit_dashboard.py` | Kill Switch / Execution / Monitoring 状態、ドローダウン、エラーログ |
| Initial Setup | `pages/2_Initial_Setup.py` | 環境変数・設定・DB・Task Scheduler の初期セットアップ確認 |
| Pre-Market | `pages/3_Pre_Market.py` | 朝の READY/BLOCKED 判定・データ鮮度・停止フラグ確認 |
| Execution Startup | `pages/4_Execution_Startup.py` | 起動直後のリコンシリエーション差分・ポジション整合確認 |
| Intraday Monitor | `pages/5_Intraday_Monitor.py` | ザラ場監視（自動更新）・Kill Switch 状態・注文エラー・ドローダウン |
| Signal Queue | `pages/6_Signal_Queue.py` | 発注キュー・ポートフォリオ目標・シグナル（直近7日） |
| Performance | `pages/7_Performance.py` | エクイティカーブ・ポジション・取引履歴・Paper Verification |
| Failure Recovery | `pages/8_Failure_Recovery.py` | 障害イベント集約・復旧ガイド |
| WebManual | `pages/9_WebManual.py` | 運用マニュアル閲覧ビュー |
| Strategy Lab | `pages/10_Strategy_Lab.py` | 市場レジーム・AI スコア・シグナル推移 |

推奨

```
Phase 1: Streamlit
Phase 2: Grafana
```

---

# 11. ログ管理

各プロセス・スクリプトは `kabusys.utils.logging_setup.setup_logging` で統一されたロギングを設定する。

**出力先:**
- stdout（コンソール）: Task Scheduler 等でリダイレクト可能
- ファイル: `logs/<app_name>.log`（日次ローテーション・30日保持）

**フォーマット:** `%(asctime)s %(levelname)-8s %(name)s: %(message)s`

> `asctime` は `datefmt="%Y-%m-%dT%H:%M:%S"` によりローカル時刻の ISO8601 形式（タイムゾーンなし）で出力される。例: `2026-04-18T09:00:00`

**保存対象:**
- システムログ（`logs/execution.log`, `logs/monitoring.log`）
- ETLログ（`logs/data_update.log`, `logs/feature_gen.log`）
- AIログ（`logs/ai_analysis.log`）
- 発注ログ（`logs/strategy_signal.log`, `logs/portfolio_construction.log`）
- エラーログ（各ファイル内に ERROR / CRITICAL レベルで記録）

**保存期間:** 30日（`TimedRotatingFileHandler` による自動ローテーション）

**ログレベル設定:** 環境変数 `LOG_LEVEL`（デフォルト: `INFO`）  
**ログディレクトリ設定:** 環境変数 `LOG_DIR`（Task Scheduler 起動時は絶対パスを推奨）

---

# 12. 障害対応フロー

障害時対応

```
異常検知
↓
アラート
↓
原因特定
↓
復旧
```

重大障害時

```
キルスイッチ
```

---

# 13. 監視ツール

## Phase 1 (初期推奨: 軽量・単一ノード構成)

Windows 1台での稼働を前提とし、オーバーヘッドの少ない構成とする。

| 種類 | ツール / 技術 | 用途・保存先 |
|----|----|----|
| データベース | SQLite | `monitoring.db` (テーブル: `system_status`, `trade_logs`, `positions`, `risk_logs`, `dashboard`) |
| ダッシュボード | Streamlit | 10ページ構成（Home / Initial Setup / Pre-Market / Execution Startup / Intraday Monitor / Signal Queue / Performance / Failure Recovery / WebManual / Strategy Lab）|
| アラート | LINE | LINE Messaging API 経由での異常通知 |

### SQLite テーブル設計（Phase 7 実装）

`src/kabusys/monitoring/monitoring_db.py` に `init_monitoring_db(conn)` + `MonitoringDB(conn)` として実装する。
接続管理は呼び出し側（監視エンジン等）が担当し、`MonitoringDB` は `conn` を受け取るのみ。

| テーブル | 書き込み方式 | 用途 |
|---|---|---|
| `system_status` | 追記（60秒ポーリング） | CPU/メモリ/ディスク/プロセス状態 |
| `trade_logs` | 追記（イベント駆動） | 発注・約定・キャンセル等のイベント履歴 |
| `positions` | upsert（code をキー） | 保有ポジション最新状態 |
| `risk_logs` | 追記（イベント駆動） | DD超過・ポジション上限等のリスクイベント |
| `dashboard` | 1行 upsert（id=1固定） | Streamlit向け最新集計値 |

`MonitoringDB` API:

```python
MonitoringDB(conn)
  .log_system_status(cpu_percent, memory_percent, disk_percent, process_ok, recorded_at=None)
  .log_trade_event(event_type, client_order_id, code, side, qty, price, filled_qty=0, state="", logged_at=None, latency_ms=None)
  .upsert_position(code, qty, avg_price, current_price=None, updated_at=None)
  .delete_position(code)
  .log_risk_event(event_type, metric_name, metric_value, threshold, detail=None, logged_at=None)
  .upsert_dashboard(portfolio_value, cash, drawdown_pct, open_order_count, position_count, updated_at=None)
  .get_dashboard() -> dict | None
```

### SystemMonitor API（Phase 7 実装、Issue #37）

`src/kabusys/monitoring/system_monitor.py` に実装。`psutil` でシステムメトリクスを取得し、`MonitoringDB` に記録する。呼び出し元がポーリング間隔を管理する（内部ループなし）。

```python
SystemMonitor(conn, duckdb_conn, pid_file=Path("data/execution.pid"))
  .check_once(today=None) -> SystemCheckResult
```

`SystemCheckResult` フィールド:

| フィールド | 型 | 内容 |
|---|---|---|
| `recorded_at` | str | ISO8601 UTC（例: `"2026-04-01T12:34:56.789012+00:00"`） |
| `cpu_percent` | float | CPU 使用率 |
| `memory_percent` | float | メモリ使用率 |
| `disk_percent` | float | ディスク使用率（`C:\` ドライブ） |
| `process_ok` | bool | Execution プロセス生存 |
| `data_freshness_ok` | bool | 株価データが 3 日以内に更新済み |
| `stale_pid_detected` | bool | 異常終了の PID ファイルを検出・削除した場合 True |

- `stale_pid_detected=True` の場合は `system_status` テーブルではなく `risk_logs` に `event_type="STALE_PID"` で記録する（`system_status` スキーマ変更なし）。
- データ鮮度チェックは `src.kabusys.data.pipeline.get_last_price_date(duckdb_conn)` を使用（`pipeline.py` モジュールレベル関数）。

---

### TradeMonitor API（Phase 7 実装、Issue #38）

`src/kabusys/monitoring/trade_monitor.py` に実装。`OrderRepository.list_active()` でアクティブ注文を取得し、滞留・異常価格を検出する。

```python
TradeMonitor(monitoring_conn, order_repo, stale_minutes=30, price_anomaly_pct=0.20)
  .check_once(now=None) -> TradeCheckResult
```

- `monitoring_conn`: monitoring.db の `sqlite3.Connection`（risk_logs 書き込み用）
- `order_repo`: `OrderRepository` インスタンス（orders.db、アクティブ注文読み取り用）

`TradeCheckResult` フィールド:

| フィールド | 型 | 内容 |
|---|---|---|
| `logged_at` | str | ISO8601 UTC |
| `stale_orders` | list[str] | 30分以上アクティブ状態の `client_order_id` リスト |
| `anomaly_fills` | list[str] | 約定価格が発注価格 ±20% 超の `client_order_id` リスト |

**ロジック:**
- **注文滞留検出:** `order_repo.list_active()` の `created_at` から `stale_minutes` 分以上経過している注文を `stale_orders` に追加。
- **約定異常価格検出:** `state == PartialFill or Filled` かつ `price != 0.0`（成行除外）の注文で `avg_fill_price` と `price` の乖離率が `price_anomaly_pct` 超の場合を `anomaly_fills` に追加。
- 異常検出時のみ `MonitoringDB.log_risk_event(event_type="STALE_ORDER" or "PRICE_ANOMALY")` で記録。

---

### RiskMonitor API（Phase 7 実装、Issue #38）

`src/kabusys/monitoring/risk_monitor.py` に実装。`dashboard` / `positions` テーブルを読み取り、ドローダウン・ポジション上限を監視する。

```python
RiskMonitor(conn, max_positions=10, dd_threshold=0.10)
  .check_once(now=None) -> RiskCheckResult
```

`RiskCheckResult` フィールド:

| フィールド | 型 | 内容 |
|---|---|---|
| `logged_at` | str | ISO8601 UTC |
| `drawdown_pct` | float | 現在のドローダウン率 |
| `drawdown_alert` | bool | `drawdown_pct > dd_threshold`（デフォルト 10%） |
| `position_count` | int | 保有銘柄数（`qty != 0` の行数） |
| `position_limit_alert` | bool | `position_count > max_positions`（デフォルト 10） |

**peak_value の管理（ハイウォーターマーク方式）:**
- 内部で `_peak_value: float` を保持。
- 初回 `check_once()` で `dashboard.portfolio_value` を初期値として設定。
- 以降は `portfolio_value > _peak_value` のときに更新。
- `dashboard` テーブルが空の場合は `drawdown_pct=0.0` / `drawdown_alert=False` として処理。

**Phase 7 の閾値スコープ:**
- Phase 7 では `dd_threshold=0.10`（10%）の 1 閾値のみを監視・アラート対象とする。
- RiskManagement.md の 5%（ポジション半減）・15%（全決済）は `ExecutionEngine`/`RiskManager` の執行パスで実施されており、`MonitoringEngine` は重複して執行制御を行わない。

---

### MonitoringEngine API（Phase 7 実装、Issue #38）

`src/kabusys/monitoring/monitoring_engine.py` に実装。各 Monitor を束ね、60秒間隔でポーリングする。

```python
MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60)
  .run_once() -> None   # テスト用：各 Monitor の check_once() を1回呼び出す
  .run() -> None        # 本番用：KeyboardInterrupt まで interval_sec 間隔でポーリング
```

**ポーリング動作:**
- `run_once()` 内の例外はログに残し、次のポーリングサイクルを継続（システム全体の停止を防ぐ）。

---

### StreamlitDashboard（Phase 7 実装 Issue #35、Issue #231 で拡張）

Streamlit マルチページ構成で実装。ページファイルは `pages/` 配下に配置され、自動的にサイドバーへ表示される。データロードロジックは `dashboard_data.py` に集約し Streamlit 非依存・単体テスト可能な設計とする。

**起動方法:**

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

**ファイル構成:**

| ファイル | 役割 |
|---|---|
| `streamlit_dashboard.py` | Home ページ（エントリーポイント）。SQLite `monitoring.db` を読み取り |
| `dashboard_data.py` | 全ページ共通のデータロード関数群（Streamlit 非依存） |
| `operations_data.py` | 運用フローページ向けデータロード関数群（Streamlit 非依存） |
| `pages/2_Initial_Setup.py` | 環境変数・設定・DB・Task Scheduler 確認（4タブ） |
| `pages/3_Pre_Market.py` | 朝の READY/BLOCKED 判定・データ鮮度・停止フラグ確認 |
| `pages/4_Execution_Startup.py` | 起動直後のリコンシリエーション差分・ポジション整合確認 |
| `pages/5_Intraday_Monitor.py` | ザラ場監視（自動更新）・Kill Switch 状態・注文エラー・ドローダウン |
| `pages/6_Signal_Queue.py` | 発注キュー・ポートフォリオ目標・シグナル確認 |
| `pages/7_Performance.py` | エクイティカーブ・ポジション・取引履歴・Paper Verification |
| `pages/8_Failure_Recovery.py` | 障害イベント集約・復旧ガイド |
| `pages/9_WebManual.py` | 運用マニュアル閲覧ビュー |
| `pages/10_Strategy_Lab.py` | 市場レジーム・AI スコア・シグナル推移 |

**ページ別表示内容:**

| ページ | タブ / 表示 | 表示内容 | データソース |
|---|---|---|---|
| Home | Overview | Kill Switch / Execution / Monitoring 状態、portfolio_value / cash / drawdown_pct、エラーログ（直近） | SQLite `dashboard` / `risk_logs` |
| Home | Positions | 保有ポジション一覧 | SQLite `positions` |
| Home | Orders | trade_logs 最新20件 | SQLite `trade_logs` |
| Home | System | system_status 最新状態 | SQLite `system_status` |
| Initial Setup | 環境変数 | Settings から取得した主要環境変数一覧・検証結果 | `validate_config.run_checks()` |
| Initial Setup | 設定 | risk_config.yaml 等の設定値確認 | `validate_config.run_checks()` |
| Initial Setup | DB | monitoring.db / kabusys.duckdb / paper_trading.db 存在確認 | ファイルシステム |
| Initial Setup | Task Scheduler | KabuSys_* タスクの登録状態確認 | `schtasks` |
| Pre-Market | - | READY/BLOCKED 判定・データ鮮度・Signal Queue 件数・停止フラグ状態 | SQLite `monitoring.db` / `operations_data` |
| Execution Startup | - | 起動直後のリコンシリエーション差分（orders_no_status / position_discrepancies） | SQLite `monitoring.db` / `operations_data` |
| Intraday Monitor | - | Kill Switch 状態・Execution プロセス UP・注文エラー件数・ドローダウン（自動更新） | SQLite `monitoring.db` / `operations_data` |
| Signal Queue | 発注キュー | signal_queue 全件（status 別集計） | DuckDB `signal_queue` |
| Signal Queue | ポートフォリオ目標 | 最新日の target_weight / target_size | DuckDB `portfolio_targets` |
| Signal Queue | シグナル（直近7日） | signals テーブル | DuckDB `signals` |
| Performance | エクイティカーブ | equity / cash / drawdown / daily_return 推移 | DuckDB `portfolio_performance` |
| Performance | ポジション | 最新日の保有ポジション（position_size ≠ 0） | DuckDB `positions` |
| Performance | 取引履歴 | 直近50件の取引 | DuckDB `trades` |
| Performance | Paper Verification | 稼働率・注文成功率・送信率・P95 レイテンシ（ゴーライブ合格基準） | SQLite `paper_trading.db`（read-only） |
| Failure Recovery | - | 障害イベント種別ごとの件数集計（直近24時間）・直近イベント一覧（50件） | SQLite `risk_logs` / `operations_data` |
| WebManual | - | 運用マニュアル閲覧ビュー（documents/WebManual/ のマークダウン） | ファイルシステム |
| Strategy Lab | 市場レジーム | regime_score / regime_label 推移 | DuckDB `market_regime` |
| Strategy Lab | AI スコア | 最新日の ai_score ランキング | DuckDB `ai_scores` |
| Strategy Lab | シグナル推移 | 日別 buy/sell 件数集計 | DuckDB `signals` |

**データソース分離:**

- Home ページ: SQLite `monitoring.db`（read-only URI モード）
- Initial Setup / Pre-Market / Execution Startup / Intraday Monitor / Failure Recovery: SQLite `monitoring.db`（`operations_data.py` 経由）
- Performance > Paper Verification タブ: SQLite `paper_trading.db`（read-only URI モード）
- Signal Queue / Performance（Paper Verification 以外）/ Strategy Lab: DuckDB `kabusys.duckdb`（`read_only=True`）

**依存ライブラリ:** `psutil`（SystemMonitor）、`streamlit`（ダッシュボード UI）— `requirements.txt` に追加すること。

> **注:** `cpu_threshold_pct` / `memory_threshold_pct` / `disk_threshold_pct` は、現フェーズでは収集・記録のみを行い、`SystemMonitor` 内では使用しない。将来の LINE アラート実装（Issue #196）で閾値判定に利用する予定。

---

### Paper Trading 検証レポート（Phase 8 実装、Issue #44）

`src/kabusys/tools/paper_verification_report.py` に実装。実稼働後の `paper_trading.db` を集計し、ゴーライブ判断に必要な指標をコンソールへ出力する。

**起動方法:**

```bash
python -m kabusys.tools.paper_verification_report
# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```

環境変数 `PAPER_TRADING_SQLITE_PATH` が未設定の場合は `data/paper_trading.db` をデフォルトとして使用する。

**出力指標とゴーライブ合格基準:**

| 指標 | データソース | 合格基準 |
|---|---|---|
| 稼働率 | `system_status.process_ok`（SUM/COUNT） | ≥ 99% |
| 注文成功率（Filled/Created） | `trade_logs.event_type` | ≥ 90% |
| 送信率（Sent/Created） | `trade_logs.event_type` | ≥ 95% |
| P95 APIレイテンシ | `trade_logs.latency_ms`（Python側計算） | ≤ 200 ms |

**`latency_ms` カラム（Issue #44 追加）:**

`trade_logs` テーブルには `latency_ms REAL` カラムが追加されている（`init_monitoring_db()` による PRAGMA マイグレーションで既存 DB にも自動追加）。`ExecutionEngine` が `send_order()` 前後を `time.perf_counter()` で計測し、`MonitoringDB.log_trade_event()` の `latency_ms` 引数として記録する。

## Phase 2 (将来拡張)

システム規模拡大時や専用監視環境への切り出し時に移行可能。

| 種類 | ツール |
|----|----|
| ログ | Loki |
| ダッシュボード | Grafana |
| アラート | LINE |
| メトリクス | Prometheus |

---

# 14. 将来拡張

将来的には以下を検討する。

- 異常検知AI
- 自動復旧
- SLA監視
- パフォーマンス分析

---

# 15. まとめ

Monitoringシステムは以下を監視する。

```
System
Data
Strategy
Execution
Risk
AI
```

本監視設計により、自動売買システムを **安全かつ安定して運用できる環境** を構築する。
