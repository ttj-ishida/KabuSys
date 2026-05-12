# Runtime Job Schedule

- 対象: KabuSys の日次ジョブ構成
- 前提: Single Windows Node / Windows Task Scheduler

---

## 1. 全体像

KabuSys は、夜間バッチで翌営業日のシグナルと発注キューを作り、翌朝に Execution / Monitoring を起動してザラ場を監視する構成です。

```text
17:30  data_update
17:33  yahoo_news_collection（News Addon — ENABLE_YAHOONEWS=true のみ）
18:30  feature_gen
19:00  ai_analysis（AI Addon — ENABLE_AI_SENTIMENT=true のみ）
20:00  strategy_signal
21:00  portfolio_construction
21:15  night_batch_report（自動生成）
21:30  night batch status confirmation（オペレーター確認）
08:00  pre_market_report
08:30  execution start
09:00  monitoring start
15:00  market_close_report
```

> **スケジュール設計の根拠**: J-Quants の日足株価データ（`daily_quotes`）は東証引け（15:30）直後ではなく 16:30〜17:00 頃に公開される。15:30 に data_update を実行すると当日データを取得できず feature_gen が 0 件になる。17:30 に遅延することでデータ確実取得後に実行できる。

---

## 2. Night Batch

### 2.1 data_update（17:30）

役割:

- J-Quants 日次データ取得
- ニュース原文保存
- DuckDB 更新

主なテーブル:

- `prices_daily`
- `fundamentals`
- `raw_news`
- `topix_daily`（Issue #257: `run_topix_etl()` が Step 5 として追加）

### 2.2 feature_gen（18:30）

役割:

- モメンタム
- ボラティリティ
- 流動性
- TOPIX 相対強度（`topix_rel_20` / `topix_rel_60`）（Issue #257）
- 財務品質スコア（`quality_score`）（Issue #257）
- その他特徴量

主なテーブル:

- `features`

### 2.3 ai_analysis（19:00）

役割:

- ニュース sentiment
- 市場 regime 判定

主なテーブル:

- `ai_scores`
- `market_regime`

### 2.4 strategy_signal（20:00）

役割:

- BUY / SELL シグナル生成
- Bear regime / breadth_stop / 決算回避反映
- `min_holding_days` / `time_exit` / `trailing_stop` を考慮

主なテーブル:

- `signals`

### 2.5 portfolio_construction（21:00）

役割:

- ポジションサイズ計算
- 翌営業日発注キュー生成

主なテーブル:

- `signal_queue`

### 2.6 night_batch_report（21:15）

役割:

- `artifacts/job_runs/{date}/` から各ジョブの `JobRunResult` を読み込む
- DuckDB から当日の更新件数・翌営業日シグナル情報を集計
- READY / READY_WITH_WARNINGS / BLOCKED を判定してレポートを生成

主なアーティファクト:

- `artifacts/job_runs/{date}/{job_name}.json`（各ジョブの実行結果）
- `artifacts/night_batch/{date}/summary.json`
- `artifacts/night_batch/{date}/report.md`
- `artifacts/night_batch/{date}/warnings.json`

関連モジュール:

- `src/kabusys/operations/night_batch_report.py`
- `src/kabusys/operations/job_run_recorder.py`

---

## 3. Night Batch 状態確認（21:15 以降）

21:15 に `KabuSys_NightBatchReport` が自動実行し、CLI サマリーと `artifacts/night_batch/{date}/` を生成する。

手動実行（再生成・デバッグ時）:

```cmd
python scripts/run_night_batch_report.py
python scripts/run_night_batch_report.py --date 2026-05-07
```

Task Scheduler 結果確認:

```powershell
Get-ScheduledTask -TaskName "KabuSys_*" | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, LastTaskResult
```

判定:

- `READY`: 全必須ジョブ成功かつ翌営業日の `signal_queue` が作成済み
- `READY_WITH_WARNINGS`: warning はあるが翌営業日の準備は完了
- `BLOCKED`: 以下のいずれかに該当する場合

| 条件 | 判定 |
|------|------|
| 必須ジョブが欠落 / `failed` / `skipped` | BLOCKED |
| `signal_queue == 0` | BLOCKED |
| `prices_daily == 0` | BLOCKED |
| `features == 0` | BLOCKED |
| `signals == 0` | READY_WITH_WARNINGS |
| その他の warning | READY_WITH_WARNINGS |

> `prices_daily == 0` および `features == 0` は、価格データ・特徴量なしではシグナル生成が不可能なため BLOCKED とする。`signals == 0` は Bear レジームなど戦略上ありうる正常系のため READY_WITH_WARNINGS に留める（Issue #288）。

---

## 4. Pre-Market（08:00）

```cmd
python -m kabusys.run_pre_market_report --save
```

判定:

- `READY`
- `READY_WITH_WARNINGS`
- `BLOCKED`

確認対象:

- stop flag
- Task Scheduler readiness
- Signal Queue
- ポジション差分
- データ鮮度

出力先:

- `artifacts/pre_market/{date}/report.md`

---

## 5. Execution / Monitoring

### 5.1 Execution Start（08:30）

```cmd
python scripts\start_system.py --component execution
```

補足:

- `python -m kabusys.run_execution` 実行時に Execution Startup Summary が自動保存される
- 保存先: `artifacts/execution_startup/{date}/report.md`

### 5.2 Monitoring Start（09:00）

```cmd
python scripts\start_system.py --component monitoring
```

ザラ場では `execution_service` と `monitoring_service` が動作し、注文・ポジション・リスク状態を監視する。

---

## 6. Market Close（15:00）

```cmd
python -m kabusys.run_market_close_report --save
python -m kabusys.run_performance_report --type daily --save
```

判定:

- `OK`
- `BLOCKED`

出力先:

- `artifacts/market_close/{date}/report.md`
- `artifacts/performance/live/daily/{date}/report.md`

---

## 7. Task Scheduler

スクリプト:

- `scripts/setup_task_scheduler.ps1` — 登録（Core は常時、Addon は `.env` フラグが `true` のときのみ）
- `scripts/remove_task_scheduler.ps1` — `KabuSys_*` タスクを一括削除

**Core ジョブ（常時登録）:**

| 時刻 | タスク名 | スクリプト |
|---|---|---|
| 17:30 | `KabuSys_DataUpdate` | `scripts\run_data_update.py` |
| 18:30 | `KabuSys_FeatureGen` | `scripts\run_feature_gen.py` |
| 20:00 | `KabuSys_StrategySignal` | `scripts\run_strategy_signal.py` |
| 21:00 | `KabuSys_PortfolioConstruction` | `scripts\run_portfolio_construction.py` |
| 21:15 | `KabuSys_NightBatchReport` | `scripts\run_night_batch_report.py` |
| 08:30 | `KabuSys_ExecutionStart` | `scripts\start_system.py --component execution` |
| 09:00 | `KabuSys_MonitoringStart` | `scripts\start_system.py --component monitoring` |

**Addon ジョブ（`.env` フラグが `true` のときのみ登録）:**

| 時刻 | タスク名 | スクリプト | 条件 |
|---|---|---|---|
| 15:35 | `KabuSys_TdnetCollection` | `scripts\run_tdnet_collection.py` | `ENABLE_TDNET=true` |
| 17:33 | `KabuSys_YahooNewsCollection` | `scripts\run_yahoonews_collection.py` | `ENABLE_YAHOONEWS=true` |
| 19:00 | `KabuSys_AiAnalysis` | `scripts\run_ai_analysis.py` | `ENABLE_AI_SENTIMENT=true` |

---

## 8. 補足

- `market_breadth` は data update / breadth 計算で日次更新される
- バックテストでは `prices_daily` から再計算して `breadth_stop` を評価する
- Streamlit ダッシュボードから `WebManual` を参照できる
- 全 Core バッチスクリプト（`run_data_update`, `run_feature_gen`, `run_strategy_signal`, `run_portfolio_construction`, `run_night_batch_report`, `run_execution`）および Addon スクリプトは `process_registry` と統合されており、実行履歴を `monitoring.db` の `process_runs` テーブルに記録する（Issue #310）
- バッチジョブ実行状況は Streamlit `Process Monitor` ページまたは CLI で確認できる:

```bash
python -m kabusys.run_process_monitor           # 直近 24 時間
python -m kabusys.run_process_monitor --hours 48
```

---

## 9. 参考

- `documents/08_Operations/TradingRunbook.md`
- `documents/WebManual/A_OperationsCycle.md`
- `documents/10_Runtime/TODO_OperationsInterfaces.md`
