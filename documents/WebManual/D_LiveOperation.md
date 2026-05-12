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
17:30-21:15  夜間バッチ（21:15 にレポート自動生成）
21:30  Night Batch 状態確認（オペレーター）
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

**Core 標準導線 — 使うページ:**

- `Home`（Kill Switch・プロセス状態・ドローダウン・エラーイベント）
- `Pre-Market`（READY/BLOCKED 判定・データ鮮度確認）
- `Execution Startup`（起動直後のリコンシリエーション差分）
- `Intraday Monitor`（ザラ場監視・自動更新・Kill Switch 状態）
- `Signal Queue`（発注キュー・シグナル）
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
