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
21:30  night batch status confirmation
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

### 2.2 feature_gen（16:00）

役割:

- モメンタム
- ボラティリティ
- 流動性
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

---

## 3. Night Batch 状態確認（21:30）

現行運用では、Task Scheduler の結果確認と `signal_queue` の確認を組み合わせて翌営業日の準備完了を判断する。

```powershell
Get-ScheduledTask -TaskName "KabuSys_*" | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, LastTaskResult
```

```cmd
python -m kabusys.run_signal_queue_report
```

判定の考え方:

- `READY`: 必須ジョブ成功かつ翌営業日の `signal_queue` が作成済み
- `READY_WITH_WARNINGS`: warning はあるが翌営業日の準備は完了
- `BLOCKED`: 必須ジョブ失敗または翌営業日の発注準備が未完了

補足:

- 判定ロジック自体は `src/kabusys/operations/night_batch_report.py` に実装済み
- 現行ツリーでは独立 CLI よりも Task Scheduler と queue 確認が導線

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

- `KabuSys_DataUpdate`
- `KabuSys_FeatureGen`
- `KabuSys_AiAnalysis`
- `KabuSys_StrategySignal`
- `KabuSys_PortfolioConstruction`
- `KabuSys_ExecutionStart`
- `KabuSys_MonitoringStart`

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
