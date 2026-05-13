# D. 本番運用

- 対象: `live` 環境で KabuSys を運用する担当者
- 前提: Paper Trading で一通り確認済み

---

## D-1. 本番切替前チェック

- `.env` の `KABUSYS_ENV=live`
- `python -m kabusys.validate_config`
- kabuステーション API 接続確認
- `config/risk_config.yaml` の再確認
- Task Scheduler の Core ジョブ（`KabuSys_DataUpdate` / `KabuSys_FeatureGen` など）が `Ready`
- Addon を有効にしている場合は、対応する Addon ジョブも登録・`Ready` であること
  - `ENABLE_YAHOONEWS=true` → `KabuSys_YahooNewsCollection`
  - `ENABLE_AI_SENTIMENT=true` → `KabuSys_AiAnalysis`
  - `ENABLE_TDNET=true` → `KabuSys_TdnetCollection`
  - `.env` の Addon フラグを変更した後は `powershell -File scripts\setup_task_scheduler.ps1` を再実行すること

---

## D-2. 1日の流れ

```text
08:00  pre_market_report（自動）
08:02  signal_queue_report（自動）
08:05  position_reconciliation_report（自動）
08:30  Execution 起動（自動）
09:00  Monitoring 起動（自動）
09:00-15:00  ザラ場監視
15:00  Market Close
17:30-21:15  夜間バッチ（21:15 にレポート自動生成）
21:30  Night Batch 状態確認（オペレーター）
```

---

## D-3. 朝の確認（08:00〜08:05）

3 本のレポートが Task Scheduler により自動実行されます。

| 時刻 | ジョブ | 出力先 |
|------|--------|--------|
| 08:00 | `KabuSys_PreMarketReport` | `artifacts/pre_market/{date}/report.md` |
| 08:02 | `KabuSys_SignalQueueReport` | `artifacts/signal_queue/{date}/report.md` |
| 08:05 | `KabuSys_PositionReconciliationReport` | `artifacts/position_reconciliation/{date}/report.json` |

LINE 通知が有効な場合、各レポート完了後に結果が自動送信されます。

判定:

- `READY`: 執行開始可
- `READY_WITH_WARNINGS`: 警告確認の上で開始判断
- `BLOCKED`: Execution を開始しない

`BLOCKED` の場合は原因を解消してから Execution を起動してください。

手動で再実行したい場合（再確認・デバッグ時）:

```cmd
python scripts/run_pre_market_report.py
python scripts/run_signal_queue_report.py
python scripts/run_position_reconciliation_report.py
```

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
python -m streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

> ⚠️ Streamlit はターミナルを占有します。レポートスクリプトなどを別途実行する場合は、**新しいターミナルウィンドウ**を開いて `.venv\Scripts\Activate.ps1` を有効化してから実行してください。

**Core 標準導線 — 使うページ:**

- `Home`（Kill Switch・プロセス状態・ドローダウン・エラーイベント）
- `Pre-Market`（READY/BLOCKED 判定・データ鮮度確認）
- `Execution Startup`（起動直後のリコンシリエーション差分）
- `Intraday Monitor`（ザラ場監視・自動更新・Kill Switch 状態）
- `Signal Queue`（発注キュー・シグナル）— **参照専用**。キャンセル・削除は画面上の CLI コマンドをターミナルで実行する
- `Performance`（エクイティカーブ・ポジション・取引履歴・Paper Verification）
- `Failure Recovery`（障害イベント集約・復旧ガイド）
- `WebManual`

**Addon 導線 — 追加ページ:**（未設定でも Core は動作します）

- `Strategy Lab`（市場レジーム・AI スコア・🤖 AI Co-Pilot チャット — AI Addon 有効時に意味をもつ）

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

**pending が残っている場合:**

```cmd
python scripts\cancel_signal_queue.py --date <日付>
```

**cancelled レコードの定期掃除（任意）:**

```cmd
python scripts\cancel_signal_queue.py --delete-cancelled
```

---

## D-7. 夜間バッチの確認（21:30）

21:15 に `KabuSys_NightBatchReport` が自動実行し、レポートを生成する。手動確認・再生成:

```cmd
python scripts/run_night_batch_report.py
```

Task Scheduler 結果確認:

```powershell
Get-ScheduledTask -TaskName "KabuSys_*" | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, LastTaskResult
```

Task Scheduler の保守（登録・削除）:

```powershell
# 登録（Core 常時 / Addon は .env フラグ依存）
powershell -File scripts\setup_task_scheduler.ps1

# KabuSys_* タスクをすべて削除
powershell -File scripts\remove_task_scheduler.ps1
```

確認項目:

- 必須ジョブ成功
- `signals` 生成済み
- 翌営業日の `signal_queue` 作成済み
- warnings の有無

判定:

- `READY`: 全必須ジョブ成功かつ `signal_queue` 作成済み → 翌日執行可
- `READY_WITH_WARNINGS`: warning はあるが翌営業日の準備は完了 → 内容確認の上で判断
- `BLOCKED`: 以下のいずれかに該当 → 自動執行を開始しない
  - 必須ジョブが失敗 / 欠落
  - `signal_queue == 0`
  - `prices_daily == 0`（価格データ未取得）
  - `features == 0`（特徴量未生成）

出力先:

- `artifacts/night_batch/{date}/summary.json`
- `artifacts/night_batch/{date}/report.md`
- `artifacts/night_batch/{date}/warnings.json`
- `artifacts/job_runs/{date}/{job_name}.json`（各ジョブの実行結果）

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
