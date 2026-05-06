# D. 本番運用

- 対象: `live` 環境で KabuSys を運用する担当者
- 前提: Paper Trading で一通り確認済み

---

## D-1. 本番切替前チェック

- `.env` の `KABUSYS_ENV=live`
- `python -m kabusys.validate_config`
- kabuステーション API 接続確認
- `config/risk_config.yaml` の再確認
- Task Scheduler の `KabuSys_*` が `Ready`

---

## D-2. 1日の流れ

```text
08:00  Pre-Market
08:30  Execution 起動
09:00  Monitoring 起動
09:00-15:00  ザラ場監視
15:00  Market Close
15:30-21:00  夜間バッチ
21:30  Night Batch 状態確認
```

---

## D-3. 朝の確認（08:00）

主要コマンド:

```cmd
python -m kabusys.run_pre_market_report --save
python -m kabusys.run_signal_queue_report
python -m kabusys.run_position_reconciliation_report
```

判定:

- `READY`
- `READY_WITH_WARNINGS`
- `BLOCKED`

`BLOCKED` の場合は Execution を開始しない。

出力先:

- `artifacts/pre_market/{date}/report.md`

---

## D-4. Execution 起動（08:30）

```cmd
python scripts\start_system.py --dry-run
python scripts\start_system.py --component execution
```

補足:

- `python -m kabusys.run_execution` 実行時に Execution Startup Summary が自動保存される
- 保存先: `artifacts/execution_startup/{date}/report.md`

`orders_no_status > 0` は執行継続不可の扱いにする。

---

## D-5. ザラ場監視（09:00-15:00）

見るもの:

- 注文エラー
- API エラー
- ドローダウン
- Kill Switch
- ポジション差分

CLI:

```cmd
python -m kabusys.run_intraday_monitor --watch
```

Streamlit:

```cmd
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

使うページ:

- `Home`
- `WebManual`
- `Signal Queue`
- `Performance`
- `Strategy Lab`

---

## D-6. 引け後の確認（15:00）

```cmd
python -m kabusys.run_market_close_report --save
python -m kabusys.run_performance_report --type daily --save
```

判定:

- `OK`: 夜間バッチへ進む
- `BLOCKED`: warning 解消まで進まない

出力先:

- `artifacts/market_close/{date}/report.md`
- `artifacts/performance/live/daily/{date}/report.md`

---

## D-7. 夜間バッチの確認（21:30）

```powershell
Get-ScheduledTask -TaskName "KabuSys_*" | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, LastTaskResult
```

```cmd
python -m kabusys.run_signal_queue_report
```

確認項目:

- 必須ジョブ成功
- `signals` 生成済み
- 翌営業日の `signal_queue` 作成済み
- warning の有無

判定の考え方:

- `READY`: 必須ジョブ成功かつ翌営業日の `signal_queue` が作成済み
- `READY_WITH_WARNINGS`: warning はあるが翌営業日の準備は完了
- `BLOCKED`: 必須ジョブ失敗または翌営業日の発注準備が未完了

補足:

- 判定ロジック自体は `src/kabusys/operations/night_batch_report.py` に実装済み
- 現行ツリーでは独立 CLI よりも Task Scheduler と queue 確認が導線

---

## D-8. 成績レポート

```cmd
python -m kabusys.run_performance_report --type daily --save
python -m kabusys.run_performance_report --type weekly --save
python -m kabusys.run_performance_report --type monthly --save
```

保存先:

- `artifacts/performance/live/daily/...`
- `artifacts/performance/live/weekly/...`
- `artifacts/performance/live/monthly/...`

---

## D-9. 異常時

停止:

```cmd
python scripts\stop_system.py
```

再開前:

```cmd
python scripts\start_system.py --dry-run
```

詳細は [E_FailureRecovery.md](./E_FailureRecovery.md) を参照。

---

## 関連

- [A_OperationsCycle.md](./A_OperationsCycle.md)
- [C_PaperTrading.md](./C_PaperTrading.md)
- [E_FailureRecovery.md](./E_FailureRecovery.md)
- [documents/08_Operations/TradingRunbook.md](../08_Operations/TradingRunbook.md)
