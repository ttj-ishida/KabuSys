# D. 本番運用 — WebManual

- **対象**: `live` 環境で KabuSys を運用する担当者
- **前提**: Paper Trading で一通り確認済み

---

## D-1. 本番切替前チェック

- `.env` の `KABUSYS_ENV=live` を確認
- `python -m kabusys.validate_config` がエラーなく完了する
- kabuステーション（本番ポート 18080）が起動し API 接続できる
- `config/risk_config.yaml` のドローダウン上限・ポジション上限を確認
- Task Scheduler の Core ジョブ（`KabuSys_DataUpdate` / `KabuSys_FeatureGen` など）が `Ready` 状態
- Addon を有効にしている場合は対応ジョブも登録・`Ready` であること
  - `ENABLE_YAHOONEWS=true` → `KabuSys_YahooNewsCollection`
  - `ENABLE_AI_SENTIMENT=true` → `KabuSys_AiAnalysis`
  - `ENABLE_TDNET=true` → `KabuSys_TdnetCollection`
  - `.env` の Addon フラグを変更した後は `powershell -File scripts\setup_task_scheduler.ps1` を再実行すること

---

## D-2. 1日の流れ

| 時刻 | 処理 | 実行方式 | スクリプト / コマンド |
|------|------|----------|-----------------------|
| 17:30 | 市場データ更新 | 自動 | `scripts/run_data_update.py` |
| 18:30 | 特徴量計算 | 自動 | `scripts/run_feature_gen.py` |
| 20:00 | 売買シグナル生成 | 自動 | `scripts/run_strategy_signal.py` |
| 21:00 | ポートフォリオ構築 | 自動 | `scripts/run_portfolio_construction.py` |
| 21:15 | 夜間バッチ結果レポート | 自動 | `scripts/run_night_batch_report.py` |
| 21:30 頃 | 夜間バッチ結果の確認 | **手動** | Streamlit または `artifacts/night_batch/` |
| 08:00 | Pre-Market レポート | 自動 | `scripts/run_pre_market_report.py` |
| 08:02 | Signal Queue レポート | 自動 | `scripts/run_signal_queue_report.py` |
| 08:05 | Position Reconciliation レポート | 自動 | `scripts/run_position_reconciliation_report.py` |
| 08:30 | Execution Engine 起動 | 自動 | `scripts/start_system.py --component execution` |
| 09:00 | Monitoring 起動 | 自動 | `scripts/start_system.py --component monitoring` |
| 09:00〜15:00 | ザラ場監視 | **手動** | Streamlit ダッシュボード / CLI |
| 15:00 | 引け後確認・Market Close レポート | **手動** | `python -m kabusys.run_market_close_report --save` |

---

## D-3. 朝の確認（08:00〜08:05）

3 本のレポートが Task Scheduler により自動実行されます。

| 時刻 | ジョブ | 出力先 |
|------|--------|--------|
| 08:00 | `KabuSys_PreMarketReport` | `artifacts/pre_market/{date}/report.md` |
| 08:02 | `KabuSys_SignalQueueReport` | `artifacts/signal_queue/{date}/report.md` |
| 08:05 | `KabuSys_PositionReconciliationReport` | `artifacts/position_reconciliation/{date}/report.json` |

LINE 通知が有効な場合、各レポート完了後に結果が自動送信されます。

**Pre-Market レポートの判定:**

| 判定 | 意味 | 対応 |
|------|------|------|
| `READY` | 執行開始可 | そのまま 08:30 の自動起動を待つ |
| `READY_WITH_WARNINGS` | 警告あり | 内容を確認した上で判断 |
| `BLOCKED` | 執行不可 | 原因を解消してから Execution を手動起動 |

手動で再実行したい場合（再確認・デバッグ時）:

```powershell
python scripts/run_pre_market_report.py
python scripts/run_signal_queue_report.py
python scripts/run_position_reconciliation_report.py
```

---

## D-4. Execution 起動（08:30 自動）

Task Scheduler の `KabuSys_ExecutionStart`（08:30）が自動起動します。
手動で起動・確認したい場合:

```powershell
# ドライラン（発注しない起動確認）
python scripts\start_system.py --dry-run

# 本起動
python scripts\start_system.py --component execution
```

起動時に Execution Startup Summary が自動保存されます（`artifacts/execution_startup/{date}/report.md`）。

> `orders_no_status > 0` は執行継続不可の扱いにする。

---

## D-5. ザラ場監視（09:00〜15:00）

**Streamlit ダッシュボード:**

```powershell
python -m streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

> ⚠️ Streamlit はターミナルを占有します。他のスクリプトを実行する場合は新しいターミナルを開いて `.venv\Scripts\Activate.ps1` を有効化してください。

**CLI モニター（常時更新）:**

```powershell
python -m kabusys.run_intraday_monitor --watch
```

**確認すべきページ（Streamlit）:**

| ページ | 確認内容 |
|--------|---------|
| `Home` | Kill Switch 状態・プロセス状態・ドローダウン・エラーイベント |
| `Pre-Market` | READY/BLOCKED 判定・データ鮮度 |
| `Execution Startup` | 起動直後のリコンシリエーション差分 |
| `Intraday Monitor` | ザラ場監視・Kill Switch 状態（自動更新） |
| `Signal Queue` | 発注キュー・シグナル（**参照専用**。操作は CLI で） |
| `Performance` | エクイティカーブ・ポジション・取引履歴 |
| `Failure Recovery` | 障害イベント集約・復旧ガイド |

---

## D-6. 引け後の確認（15:00 手動）

```powershell
python -m kabusys.run_market_close_report --save
python -m kabusys.run_performance_report --type daily --save
```

| 判定 | 対応 |
|------|------|
| `OK` | 夜間バッチへ進む |
| `BLOCKED` | warning を解消するまで進まない |

**出力先:**
- `artifacts/market_close/{date}/report.md`
- `artifacts/performance/live/daily/{date}/report.md`

**未執行シグナルが残っている場合:**

```powershell
python scripts\cancel_signal_queue.py --date <日付>
```

**cancelled レコードの定期掃除（任意）:**

```powershell
python scripts\cancel_signal_queue.py --delete-cancelled
```

---

## D-7. 夜間バッチ（17:30〜21:15 自動）

以下のジョブが Task Scheduler により順番に自動実行されます。

| 時刻 | ジョブ名 | スクリプト |
|------|----------|-----------|
| 17:30 | `KabuSys_DataUpdate` | `scripts/run_data_update.py` |
| 18:30 | `KabuSys_FeatureGen` | `scripts/run_feature_gen.py` |
| 20:00 | `KabuSys_StrategySignal` | `scripts/run_strategy_signal.py` |
| 21:00 | `KabuSys_PortfolioConstruction` | `scripts/run_portfolio_construction.py` |
| 21:15 | `KabuSys_NightBatchReport` | `scripts/run_night_batch_report.py` |

**Addon ジョブ（`.env` フラグが `true` のときのみ実行）:**

| 時刻 | ジョブ名 | 条件 | スクリプト / コマンド |
|------|----------|------|----------------------|
| 15:35 | `KabuSys_TdnetCollection` | `ENABLE_TDNET=true` | `scripts/run_tdnet_collection.py` |
| 15:40 | `KabuSys_EdinetCollection` | `ENABLE_EDINET=true` | `scripts/run_edinet_collection.py` |
| 17:00 | `KabuSys_DisclosureClassification` | `ENABLE_TDNET=true` | `scripts/run_disclosure_classification.py` |
| 17:33 | `KabuSys_YahooNewsCollection` | `ENABLE_YAHOONEWS=true` | `scripts/run_yahoonews_collection.py` |
| 19:00 | `KabuSys_AiAnalysis` | `ENABLE_AI_SENTIMENT=true` | `scripts/run_ai_analysis.py` |

### 結果確認（21:30 頃 手動）

21:15 の `KabuSys_NightBatchReport` が完了後、結果を確認します。手動で再生成する場合:

```powershell
python scripts/run_night_batch_report.py
```

**Task Scheduler の実行結果一覧:**

```powershell
Get-ScheduledTask -TaskName "KabuSys_*" | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, LastTaskResult
```

**Night Batch レポートの判定:**

| 判定 | 意味 | 対応 |
|------|------|------|
| `READY` | 全必須ジョブ成功・`signal_queue` 作成済み | 翌日執行可 |
| `READY_WITH_WARNINGS` | 警告あり・翌日準備は完了 | 内容確認の上で判断 |
| `BLOCKED` | 必須ジョブ失敗 / `signal_queue == 0` / 価格・特徴量未生成 | 自動執行を開始しない |

**出力先:**
- `artifacts/night_batch/{date}/summary.json`
- `artifacts/night_batch/{date}/report.md`
- `artifacts/night_batch/{date}/warnings.json`
- `artifacts/job_runs/{date}/{job_name}.json`

**Task Scheduler の保守:**

```powershell
# 登録（Core 常時 / Addon は .env フラグ依存）
powershell -File scripts\setup_task_scheduler.ps1

# KabuSys_* タスクをすべて削除
powershell -File scripts\remove_task_scheduler.ps1
```

---

## D-8. 成績レポート（手動）

```powershell
python -m kabusys.run_performance_report --type daily --save
python -m kabusys.run_performance_report --type weekly --save
python -m kabusys.run_performance_report --type monthly --save
```

**保存先:**
- `artifacts/performance/live/daily/...`
- `artifacts/performance/live/weekly/...`
- `artifacts/performance/live/monthly/...`

---

## D-9. 異常時

**停止:**

```powershell
python scripts\stop_system.py
```

**再開前の確認:**

```powershell
python scripts\start_system.py --dry-run
```

詳細は [E_FailureRecovery.md](./E_FailureRecovery.md) を参照。

---

## 関連ドキュメント

- [A_OperationsCycle.md](./A_OperationsCycle.md) — 日次運用サイクルの概要
- [C_PaperTrading.md](./C_PaperTrading.md) — ペーパートレード手順
- [E_FailureRecovery.md](./E_FailureRecovery.md) — 障害復旧手順
- `documents/08_Operations/TradingRunbook.md` — 詳細な運用手順書
