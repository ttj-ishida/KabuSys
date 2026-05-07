# Runtime Job Schedule

- 対象: KabuSys の日次ジョブ構成
- 前提: Single Windows Node / Windows Task Scheduler

---

## 1. 全体像

KabuSys は、夜間バッチで翌営業日のシグナルと発注キューを作り、翌朝に Execution / Monitoring を起動してザラ場を監視する構成です。

```text
15:30  data_update
16:00  feature_gen
18:00  ai_analysis
20:00  strategy_signal
21:00  portfolio_construction
21:15  night_batch_report（自動生成）
21:30  night batch status confirmation（オペレーター確認）
08:00  pre_market_report
08:30  execution start
09:00  monitoring start
15:00  market_close_report
```

---

## 2. Night Batch

### 2.1 data_update（15:30）

役割:

- J-Quants 日次データ取得
- ニュース原文保存
- DuckDB 更新

主なテーブル:

- `prices_daily`
- `fundamentals`
- `raw_news`
- `topix_daily`（Issue #257: `run_topix_etl()` が Step 5 として追加）

### 2.2 feature_gen（16:00）

役割:

- モメンタム
- ボラティリティ
- 流動性
- TOPIX 相対強度（`topix_rel_20` / `topix_rel_60`）（Issue #257）
- 財務品質スコア（`quality_score`）（Issue #257）
- その他特徴量

主なテーブル:

- `features`

### 2.3 ai_analysis（18:00）

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
- `BLOCKED`: 必須ジョブ失敗または `signal_queue` が空

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

登録スクリプト:

- `scripts/setup_task_scheduler.ps1`

標準ジョブ:

| 時刻 | タスク名 | スクリプト |
|---|---|---|
| 15:30 | `KabuSys_DataUpdate` | `scripts\run_data_update.py` |
| 16:00 | `KabuSys_FeatureGen` | `scripts\run_feature_gen.py` |
| 18:00 | `KabuSys_AiAnalysis` | `scripts\run_ai_analysis.py` |
| 20:00 | `KabuSys_StrategySignal` | `scripts\run_strategy_signal.py` |
| 21:00 | `KabuSys_PortfolioConstruction` | `scripts\run_portfolio_construction.py` |
| 21:15 | `KabuSys_NightBatchReport` | `scripts\run_night_batch_report.py` |
| 08:30 | `KabuSys_ExecutionStart` | `scripts\start_system.py --component execution` |
| 09:00 | `KabuSys_MonitoringStart` | `scripts\start_system.py --component monitoring` |

---

## 8. 補足

- `market_breadth` は data update / breadth 計算で日次更新される
- バックテストでは `prices_daily` から再計算して `breadth_stop` を評価する
- Streamlit ダッシュボードから `WebManual` を参照できる

---

## 9. 参考

- `documents/08_Operations/TradingRunbook.md`
- `documents/WebManual/A_OperationsCycle.md`
- `documents/10_Runtime/TODO_OperationsInterfaces.md`
