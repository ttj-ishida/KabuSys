# TODO: 運用確認インターフェース整理メモ

- ステータス: 未着手
- 目的: `WebManual_OperationsCycle.md` に記載された「ユーザーが確認する必要があるシステムアウトプット」を抽出し、それをどのインターフェースで提供するか未検討の対象を整理する
- 対象: 実運用時の朝、起動時、ザラ場中、引け後、夜間バッチ後の確認導線

---

## 1. 背景

`WebManual_OperationsCycle.md` では、KabuSys は **自動執行 + 人間監督型** の運用モデルであると整理されている。

つまり、システムは分析・執行・監視の一次対応を行う一方で、ユーザーは以下を確認して最終判断を行う前提になっている。

- 朝の事前確認
- Execution 起動後の異常有無確認
- ザラ場中の異常監視
- 引け後の締め確認
- 夜間バッチ結果確認

しかし現状では、これらの確認に必要なシステムアウトプットが、**どのインターフェースで提供されるか** が統一的に設計されていない。

---

## 2. ユーザーが確認する必要があるシステムアウトプット

## 2.1 朝の事前確認で必要なもの

ユーザーは 08:00 頃に、運用開始可否を判断するために以下を確認する必要がある。

- 前日分データが正常に取り込まれていること
- 本日の `Signal Queue` に `pending` シグナルが存在すること
- DB 上のポジションと証券口座のポジションが一致していること
- `data/stop_requested.flag` が存在しないこと
- Task Scheduler の KabuSys タスクが `Ready` 状態であること

## 2.2 Execution 起動時に必要なもの

ユーザーは 08:30 の Execution 起動後に、以下を確認する必要がある。

- 起動ログに異常がないこと
- `orders_no_status` が出ていないこと
- `position_discrepancies` が出ていないこと
- リコンシリエーション結果に重大異常がないこと

## 2.3 ザラ場中に必要なもの

ユーザーはザラ場中に、以下を確認する必要がある。

- 注文エラーが多発していないこと
- API 接続断が起きていないこと
- ドローダウンが異常に拡大していないこと
- `execution.pid` と `monitoring.pid` が存在すること
- ログに `ERROR`, `CRITICAL`, `Kill Switch`, `position_discrepancies` が出ていないこと

## 2.4 引け後に必要なもの

ユーザーは市場終了後に、以下を確認する必要がある。

- `signal_queue` に `pending` が残っていないこと
- `positions` テーブルが更新されていること
- `portfolio_performance` に本日分が記録されていること

## 2.5 夜間バッチ後に必要なもの

ユーザーは 21:30 頃に、以下を確認する必要がある。

- 各ジョブが成功していること
- エラーログがないこと
- 明日の `Signal Queue` が作成されていること
- 翌営業日の自動執行を開始してよい状態か

この領域は、`TODO_NightBatchOperationsReport.md` と `MVP_NightBatchOperationsReportSpec.md` で一部整理済みである。

---

## 3. すでに一定の確認手段が想定されているもの

以下は、完全ではないが、確認手段の当たりが存在している。

- kabuステーション接続状態
  - kabuステーション画面
- 証券口座ポジション
  - kabuステーション画面
- Task Scheduler 状態
  - Windows Task Scheduler 画面
- 停止フラグ
  - ファイル存在確認
- PID ファイル
  - ファイル存在確認
- ログ
  - `logs/*.log`
- DB テーブル状態
  - DuckDB / SQLite 手動確認

ただし、これらは運用者が複数の場所を行き来して確認する前提であり、**統合された運用インターフェース** にはなっていない。

---

## 4. まだ未検討、または弱いインターフェース領域

以下が、特に未整理な対象である。

## 4.1 Pre-Market Report

**ステータス: 実装済み (Issue #200, PR #214)**

目的:

- 08:00 時点で「今日の運用を開始してよいか」を判断する

確認対象:

- 前日データ更新状態
- `Signal Queue` 準備完了
- ポジション整合性
- 停止フラグ
- Task Scheduler 状態

実装済み設計:

- インターフェース: CLI（stdout）＋ Markdown ＋ JSON（3 ファイル保存）
- ステータス判定: `READY / READY_WITH_WARNINGS / BLOCKED`
- BLOCKED 条件: `signal_queue_pending == 0` OR `stop_flag_exists` OR NOT `task_scheduler_ready`
- READY_WITH_WARNINGS 条件: NOT `data_freshness_ok`
- 保存先: `artifacts/pre_market/{date}/summary.json`, `report.md`, `warnings.json`
- エントリポイント: `run_pre_market_report.py`（`src/kabusys/operations/pre_market_report.py` + `pre_market_collector.py`）

## 4.2 Execution Startup Summary

**ステータス: 設計済み (Issue #201, 設計書: `docs/superpowers/specs/2026-04-27-execution-startup-summary-design.md`)**

目的:

- Execution 起動直後に、運転継続可否を判断する

確認対象:

- リコンシリエーション結果
- `orders_no_status`
- `position_discrepancies`
- 起動成功 / warning / failure

確定済み設計:

- 生成タイミング: `run_execution.py` が `reconciler.run()` 直後に自動生成（try/except で保護）
- インターフェース: CLI（stdout）＋ Markdown ＋ JSON（3 ファイル保存）
- ステータス判定: `READY / READY_WITH_WARNINGS / BLOCKED`
- BLOCKED 条件: `orders_no_status > 0`
- READY_WITH_WARNINGS 条件: `len(position_discrepancies) > 0`
- 保存先: `artifacts/execution_startup/{date}/summary.json`, `report.md`, `warnings.json`
- 新規モジュール: `src/kabusys/operations/execution_startup_report.py`（純粋関数）

## 4.3 Intraday Monitoring Interface

**ステータス: 設計済み (Issue #203, 設計書: `docs/superpowers/specs/2026-04-29-intraday-monitoring-interface-design.md`)**

目的:

- ザラ場中に異常を素早く検知し、ユーザーが対応判断できるようにする

確認対象:

- 注文エラー件数（直近1時間）
- API 接続状態（`system_status.process_ok` 最新値）
- 日次ドローダウン（`dashboard.drawdown_pct`）
- Kill Switch 状態（`data/kill.flag` 存在確認）
- `execution.pid` / `monitoring.pid` の稼働状態（psutil で生存確認）

設計決定:

- **CLI `--watch` モード** + **Streamlit ダッシュボード強化** の2インターフェースを実装する
- 共有データ層: `intraday_collector.py`（monitoring SQLite を read-only で参照）
- CLI ステータス判定: `OK` / `WARNING` / `CRITICAL`（3段階）
  - `CRITICAL`: Kill Switch 発動 OR `execution.pid` 停止
  - `WARNING`: drawdown ≤ -10% OR 注文エラー > 0 OR 滞留注文 > 0 OR `monitoring.pid` 停止
  - `OK`: それ以外
- Streamlit: 自動更新（30/60/120秒 選択）、Kill Switch を最上部に表示、drawdown 閾値超過で赤表示
- 終了コード: `0` = OK、`1` = WARNING または CRITICAL

コマンド:

```cmd
python -m kabusys.run_intraday_monitor
python -m kabusys.run_intraday_monitor --watch
python -m kabusys.run_intraday_monitor --watch --interval 60
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

新規モジュール:

- `src/kabusys/operations/intraday_collector.py`（monitoring DB クエリ）
- `src/kabusys/run_intraday_monitor.py`（CLI エントリーポイント）

強化モジュール:

- `src/kabusys/monitoring/streamlit_dashboard.py`（Kill Switch・PID・自動更新を追加）
- `src/kabusys/run_monitoring.py`（`data/monitoring.pid` 書き込みを追加）

## 4.4 Market Close Summary

**ステータス: 設計済み (Issue #205, 設計書: `docs/superpowers/specs/2026-04-29-market-close-summary-design.md`)**

目的:

- 引け後（15:30 頃）に「今日の運用が正常に締まったか」を確認し、夜間バッチへ進んでよいかを判断する

確認対象:

- `signal_queue` に当日 `pending` が残っていないこと
- `positions` テーブルに当日分が記録されていること
- `portfolio_performance` に当日分が記録されていること

設計決定:

- **独立した CLI コマンド** として実装する
- インターフェース: CLI（stdout）＋ Markdown ＋ JSON（3 ファイル保存）
- ステータス判定: `OK` / `BLOCKED`（2 段階）
- BLOCKED 条件（いずれかが真）:
  - `signal_queue` に当日 `pending` が残っている
  - `positions` に当日分が記録されていない
  - `portfolio_performance` に当日分が記録されていない
- サマリ情報（判定に影響しない表示情報）:
  - 当日 filled シグナル件数
  - 日次リターン（`portfolio_performance.daily_return`）
  - 当日損益額（equity 変動から近似）
  - 期末総資産
- 保存先: `artifacts/market_close/{date}/summary.json`, `report.md`, `warnings.json`
- 終了コード: `0` = OK、`1` = BLOCKED

コマンド:

```cmd
python -m kabusys.run_market_close_report
python -m kabusys.run_market_close_report --date 2026-04-28
python -m kabusys.run_market_close_report --save
python -m kabusys.run_market_close_report --json
```

新規モジュール:

- `src/kabusys/operations/market_close_collector.py`（DB クエリ）
- `src/kabusys/operations/market_close_report.py`（純粋関数）
- `src/kabusys/run_market_close_report.py`（CLI エントリーポイント）

## 4.5 Position Reconciliation View

**ステータス: 設計済み (Issue #204)**

目的:

- DB上のローカル推定ポジション（注文履歴から集計）と証券口座（kabuステーション）のポジションを突き合わせ、一致・不一致を銘柄単位で確認する

設計決定:

- **独立した CLIコマンド** として実装する（Execution Startup Summary には組み込まない）
  - 理由: 起動時レポートは既に差分警告を表示しており重複になるため
  - 任意のタイミング（朝の事前確認・ザラ場中・手動確認）で実行可能
- **全保有銘柄を表示**する（差分がある銘柄のみではなく broker / local の union を一覧表示）
- `--watch` オプションによる定期ポーリング（デフォルト10分間隔）をサポート

確認対象:

- 銘柄ごとの broker_qty / local_qty / diff / MATCH・MISMATCH 判定
- 全体ステータス: `CLEAN`（全銘柄一致）/ `DISCREPANCY`（1件以上差分あり）
- 差分銘柄の警告一覧

コマンド:

```cmd
python -m kabusys.run_position_reconciliation_report
python -m kabusys.run_position_reconciliation_report --watch --interval 300
python -m kabusys.run_position_reconciliation_report --save --json
```

出力先: `artifacts/position_reconciliation/{date}/summary.json|report.md|warnings.json`

詳細設計: `docs/superpowers/specs/2026-04-27-position-reconciliation-view-design.md`

## 4.6 Signal Queue Confirmation View

目的:

- 明日の発注予定内容をユーザーが理解できるようにする

確認対象:

- BUY 件数
- SELL 件数
- 対象銘柄数
- 銘柄一覧
- 発注予定数量

未検討点:

- 夜間バッチレポートに含めるか
- 専用確認画面にするか
- 詳細粒度をどこまで見せるか

---

## 5. 既に比較的整理が進んでいる領域

以下は、別 TODO / MVP / 実装済みで整理が進んでいる。

- Night Batch Operations Report
  - `TODO_NightBatchOperationsReport.md`
  - `MVP_NightBatchOperationsReportSpec.md`
  - 実装済み
- Pre-Market Report
  - `TODO_LivePerformanceReport.md` ※関連
  - 実装済み (Issue #200, PR #214)
- Execution Startup Summary
  - 設計済み (Issue #201)

このため、次に優先して検討すべきなのは、それ以外の時間帯の確認インターフェースである。

---

## 6. 未検討対象の優先順位

### 実装済み / 設計済み

- Pre-Market Report（実装済み: Issue #200, PR #214）
- Execution Startup Summary（設計済み: Issue #201）

### 優先度高

1. Signal Queue Confirmation View

### 優先度中（設計済み）

1. Position Reconciliation View（設計済み: Issue #204）

### 優先度中（設計済み）

1. Market Close Summary（設計済み: Issue #205）

### 優先度中（未着手）

1. Intraday Monitoring Interface

### 優先度低

1. 各確認結果のダッシュボード統合
2. 通知チャネルの統合設計
3. モバイル確認導線

---

## 7. まず決めるべきこと

### 優先度高

1. 各確認対象を CLI / Markdown / JSON / Dashboard / Slack のどれで出すか
2. 朝の運用開始判断を 1 つのレポートに集約するか
3. Execution 起動結果をログ以外で見せるか
4. `Signal Queue` をどの粒度でユーザーに見せるか

### 優先度中

1. ザラ場監視をログベースで行うか、画面ベースにするか
2. 引け後確認をレポート化するか
3. 差分確認を専用ビューにするか

---

## 8. 推奨する整理単位

今後は、以下の単位でインターフェース設計を分けて検討するのがよい。

| モジュール | ステータス |
|-----------|-----------|
| `NightBatchOperationsReport` | 実装済み |
| `PreMarketOperationsReport` | 実装済み (Issue #200, PR #214) |
| `ExecutionStartupSummary` | 実装済み (Issue #201, PR #215) |
| `SignalQueueConfirmationView` | 実装済み (Issue #202, PR #216) |
| `PositionReconciliationView` | 設計済み (Issue #204) |
| `IntradayMonitoringInterface` | 設計済み (Issue #203) |
| `MarketCloseSummary` | 実装済み (Issue #205, PR #218) |

---

## 9. 反映対象候補

### `documents/10_Runtime/WebManual_OperationsCycle.md`

- 現状は「何を確認するか」中心なので、将来的には「どの画面 / レポートで確認するか」へのリンクを追加する

### `documents/10_Runtime/RuntimeArchitecture.md`

- 運用確認インターフェースが追加される場合、どのプロセスがその出力を担当するかを整理する

### `documents/08_Operations/TradingRunbook.md`

- 各時間帯の確認手順に、対応する確認インターフェースを紐づける

---

## 10. 反映後の状態イメージ

設計反映後の到達イメージは以下。

- ユーザーが確認すべきシステムアウトプットが時間帯ごとに整理される
- 各確認対象に対して、どのインターフェースで提供するかが定義される
- ログ依存の運用から、構造化された確認導線へ移行できる
- 朝、起動直後、ザラ場中、引け後、夜間の各確認が標準化される
