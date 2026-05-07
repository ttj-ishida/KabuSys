# Trading Runbook

- 対象: KabuSys の日次運用
- 前提: Single Windows Node / kabuステーション API / J-Quants

---

## 1. 日次タイムライン

```text
07:50  PC / kabuステーション起動確認
08:00  Pre-Market Checklist
08:30  Execution 起動
09:00  Monitoring 起動・前場監視
11:30  昼休み確認
12:30  後場監視
15:00  Market Close 確認
15:30  data_update
16:00  feature_gen
18:00  ai_analysis
20:00  strategy_signal
21:00  portfolio_construction
21:15  night_batch_report（自動生成）
21:30  Night Batch 確認（オペレーター）
```

---

## 2. Pre-Market（08:00）

確認項目:

- Windows PC が正常
- kabuステーションが起動済み
- API 接続が正常
- `data/stop_requested.flag` が存在しない
- `signal_queue` の `pending` が残っている
- Task Scheduler の `KabuSys_*` が `Ready`
- DB と口座のポジション差分が許容範囲

主要コマンド:

```cmd
python -m kabusys.run_pre_market_report --save
python -m kabusys.run_signal_queue_report
python -m kabusys.run_position_reconciliation_report
```

判定:

- `READY`: 執行開始可
- `READY_WITH_WARNINGS`: 警告確認の上で開始判断
- `BLOCKED`: 自動執行を開始しない

出力先:

- `artifacts/pre_market/{date}/report.md`

---

## 3. Execution 起動（08:30）

```cmd
python scripts\start_system.py --dry-run
python scripts\start_system.py --component execution
```

起動直後の確認:

- `data/execution.pid` が生成されている
- `orders_no_status = 0`
- `position_discrepancies` が許容範囲

補足:

- `python -m kabusys.run_execution` 実行時に Execution Startup Summary が自動生成される
- 保存先: `artifacts/execution_startup/{date}/report.md`

---

## 4. ザラ場監視（09:00-15:00）

見るもの:

- `execution_service`
- `monitoring_service`
- 注文エラー
- API エラー
- ドローダウン
- Kill Switch
- ポジション差分

主要コマンド:

```cmd
python -m kabusys.run_intraday_monitor --watch
```

```powershell
Get-Content logs\execution.log -Tail 50
Select-String -Path logs\*.log -Pattern "ERROR|CRITICAL"
```

Streamlit を使う場合:

```cmd
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

利用ページ:

- `Home`（Kill Switch・プロセス状態・ドローダウン・エラーイベント）
- `Intraday Monitor`（ザラ場監視・自動更新・Kill Switch 状態）
- `Signal Queue`（発注キュー・ポートフォリオ目標・シグナル）
- `Performance`（エクイティカーブ・ポジション・取引履歴）
- `Failure Recovery`（障害イベント集約・復旧ガイド）
- `WebManual`

---

## 5. 障害時の基本対応

1. ログ確認
2. PID / stop flag / DB 状態確認
3. 必要なら Kill Switch
4. 再起動前に reconciliation

停止:

```cmd
python scripts\stop_system.py
```

再開前確認:

```cmd
python scripts\start_system.py --dry-run
```

---

## 6. Market Close（15:00）

確認項目:

- `signal_queue` に未処理 `pending` がない
- `positions` が更新済み
- `portfolio_performance` に当日分が記録済み

主要コマンド:

```cmd
python -m kabusys.run_market_close_report --save
python -m kabusys.run_performance_report --type daily --save
```

判定:

- `OK`: 夜間バッチへ進行可
- `BLOCKED`: warning 解消まで進めない

出力先:

- `artifacts/market_close/{date}/report.md`
- `artifacts/performance/live/daily/{date}/report.md`

---

## 7. 夜間バッチ（15:30-21:15）

ジョブ:

| 時刻 | スクリプト |
|---|---|
| 15:30 | `run_data_update.py` |
| 16:00 | `run_feature_gen.py` |
| 18:00 | `run_ai_analysis.py` |
| 20:00 | `run_strategy_signal.py` |
| 21:00 | `run_portfolio_construction.py` |
| 21:15 | `run_night_batch_report.py`（自動レポート生成） |

Task Scheduler 確認:

```powershell
Get-ScheduledTask -TaskName "KabuSys_*" | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, LastTaskResult
```

---

## 8. Night Batch 判定（21:30）

21:15 に `KabuSys_NightBatchReport` が自動実行し、レポートを生成する。

```cmd
python scripts/run_night_batch_report.py
```

出力先:

- `artifacts/night_batch/{date}/summary.json`
- `artifacts/night_batch/{date}/report.md`
- `artifacts/night_batch/{date}/warnings.json`

確認項目:

- 必須ジョブ成功（`data_update` / `feature_gen` / `ai_analysis` / `strategy_signal` / `portfolio_construction`）
- `signals` が生成されている
- 翌営業日の `signal_queue` が作られている
- warnings の有無

判定:

- `READY`: 全必須ジョブ成功かつ `signal_queue` 作成済み
- `READY_WITH_WARNINGS`: warning はあるが翌営業日の準備は完了
- `BLOCKED`: 必須ジョブ失敗または `signal_queue` が空

---

## 9. 成績レポート

```cmd
python -m kabusys.run_performance_report --type daily --save
python -m kabusys.run_performance_report --type weekly --save
python -m kabusys.run_performance_report --type monthly --save
```

Paper 環境:

```cmd
python -m kabusys.run_performance_report --type daily --env paper_trading
```

出力先:

- `artifacts/performance/{env}/{type}/{period}/report.md`

---

## 10. 参考

- `documents/08_Operations/FailureRecovery.md`
- `documents/08_Operations/Monitoring.md`
- `documents/10_Runtime/RuntimeJobSchedule.md`
- `documents/WebManual/D_LiveOperation.md`
