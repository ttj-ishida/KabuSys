# Runtime Job Schedule

- 対象: KabuSys の日次ジョブ構成
- 前提: Single Windows Node / Windows Task Scheduler

---

## 1. 全体像

KabuSys は、夜間バッチで翌営業日のシグナルと注文候補を作り、翌朝にユーザーが手動注文できるよう確認レポートを生成する構成です。

当面の本番運用では kabuステーション API による自動発注を主ルートにしない。Execution / Monitoring は Paper Trading や検証時のみ使用する。

```text
17:30  data_update
17:33  yahoo_news_collection（News Addon — ENABLE_YAHOONEWS=true のみ）
18:30  feature_gen
19:00  ai_analysis（AI Addon — ENABLE_AI_SENTIMENT=true のみ）
20:00  strategy_signal
21:00  portfolio_construction
21:10  manual_order_report --phase evening（自動・手動注文候補）
21:15  night_batch_report（自動生成）
21:30  night batch status confirmation（オペレーター確認）
08:00  pre_market_report（自動）
08:02  signal_queue_report（自動）
08:05  manual_order_report --phase morning（自動・LINE 通知）
08:05  manual order final check（手動）
08:30  broker web/order screen preparation（手動）
09:00  manual order entry（手動）
15:00  market_close_report（手動）
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
- 翌営業日手動注文候補生成

主なテーブル:

- `signal_queue`（`date` = 当日＝夜間バッチ日。翌営業日の執行で読まれる）

補足（Issue #413）:

- 起動直後に、Execution Engine が SQLite の `signal_queue_status` に記録した処理状態
  （`processing` / `filled` / `cancelled` / `failed`）を DuckDB の `signal_queue.status` と
  `processed_at` に同期する。`pending` の行には触れない。同期に失敗しても警告ログのみで続行する。

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

### 2.7 manual_order_report evening（21:10）

役割:

- 手動注文メイン運用（#412）向けに、ユーザーが証券画面で注文するための BUY / SELL 候補を出力する
- DuckDB は読み取り専用。発注・kabu API 呼び出しはしない
- BUY: `signal_queue`（pending）に銘柄名・推奨株数・参考価格・想定金額・スコア/順位・保有株数・買い増し表記を付与
- SELL: `signals`（sell）に `manual_action_queue` の株数・理由・`[手動保有]` を付与。自動分は `positions` の最新株数
- 総資産・利用可能現金（`MANUAL_TRADING_ENABLED=true` 時）・1 銘柄上限（総資産の 10%）・想定投下額・利用率
- ギャップ見送りルール（`strategy_config.yaml` の `gap_up_threshold` / `gap_down_threshold`）と、銘柄ごとの買付可能価格（「この価格以下なら買付可（上限）」=floor、「この価格以上なら買付可（下限）」=−3% 境界を超える最小の円）
- 保有株数は sizing と同じくシグナル日時点（手動分は `MANUAL_TRADING_ENABLED=true` のときのみ）。シグナル生成後に手動約定（約定日 > シグナル日、または登録時刻 > signal_queue.created_at）がある銘柄の BUY は「シグナル生成後に保有が変わりました。株数を再確認してください」として見送り
- 当日（report_date）のシグナルがない場合は BUY を全件見送り
- signals に BUY があるのに signal_queue に pending BUY がない場合は警告（portfolio_construction 失敗の可能性）
- LINE は送らない（portfolio_construction の夜 LINE に BUY/SELL 詳細が出るため）
- スケジューラでは `needs_exclusive_db=True`（execution 停止後に read-only で読む）

主なアーティファクト:

- `artifacts/manual_orders/{date}/evening.md`
- `artifacts/manual_orders/{date}/evening.json`

関連モジュール:

- `scripts/run_manual_order_report.py`
- `src/kabusys/operations/manual_order_report.py`（収集）
- `src/kabusys/operations/manual_order_report_format.py`（Markdown / JSON / CLI / LINE）

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

- `READY`: 全必須ジョブ成功かつ翌営業日の `signal_queue` が作成済み。手動注文候補として確認可能
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

## 4. Pre-Market（08:00〜08:05）

3 本のレポートが Task Scheduler により自動実行される。手動注文メイン運用では、証券口座との自動リコンシリエーションは必須にしない。

| 時刻 | タスク名 | スクリプト | 出力先 |
|------|----------|------------|--------|
| 08:00 | `KabuSys_PreMarketReport` | `scripts/run_pre_market_report.py` | `artifacts/pre_market/{date}/report.md` |
| 08:02 | `KabuSys_SignalQueueReport` | `scripts/run_signal_queue_report.py`（既定で前営業日＝当日執行分の queue を読む。`--date` 指定可） | `artifacts/signal_queue/{date}/report.md`（`{date}` は queue の日付） |
| 08:05 | `KabuSys_ManualOrderReportMorning` | `scripts/run_manual_order_report.py --phase morning` | `artifacts/manual_orders/{date}/morning.md` |
| 08:05 | 手動確認 | WebManual / Manual Order Report / Signal Queue Report | `artifacts/manual_orders/{date}/morning.md` |

判定（pre_market_report）:

- `READY`
- `READY_WITH_WARNINGS`
- `BLOCKED`

確認対象（pre_market_report）:

- stop flag
- Task Scheduler readiness
- Signal Queue
- データ鮮度

確認対象（manual_order_report morning）:

- 休場日（`is_trading_day` が false。カレンダーがなければ土日判定）なら警告し、BUY を全件見送り
- 前営業日のシグナル（`signal_date` が前営業日より古い場合は警告し、BUY を全件見送り）
- データ鮮度（`check_data_freshness`）
- stop flag（`data/stop_requested.flag`。ありなら BUY を全件見送り）
- DD 停止（監視 SQLite `dashboard.dd_stop_blocked_since`。ありなら BUY を全件見送り、読めなければ「不明」で警告のみ）
- 停止条件は BUY が 0 件でも警告としてステータス・LINE に出る
- `--date` で過去日を指定した場合も、停止フラグ・DD 停止・資金は実行時点の状態（過去日である旨を警告）
- 出力は「今日注文すべき候補（BUY・SELL）」と「見送り候補（理由付き）」に分かれる。SELL は常に表示
- LINE: ステータス（OK / 警告あり / BUY 見送り）、BUY 上位 10 件、SELL 一覧、警告。送信失敗は無視

手動再実行（デバッグ時）:

```cmd
python scripts/run_pre_market_report.py
python scripts/run_signal_queue_report.py
python scripts/run_manual_order_report.py --phase morning
python scripts/run_manual_order_report.py --phase evening --date 2026-10-13
```

---

## 5. Manual Order / Optional Execution

### 5.1 手動注文確認（08:30）

手動注文メイン運用では、Execution は起動しない。

確認するもの:

- `artifacts/signal_queue/{date}/report.md`
- BUY 候補
- SELL 候補
- 推奨数量
- 想定約定金額
- 見送り条件

### 5.2 手動注文（09:00）

ユーザーが証券会社の画面で注文する。

約定後は、約定日、銘柄コード、売買、数量、単価、メモを保存する。手動約定投入 CLI 実装後は `manual_trades` に取り込む。

### 5.3 Optional Execution Start（検証用）

```cmd
python scripts\start_system.py --component execution
```

補足:

- Paper Trading や自動発注検証時のみ使用する
- `python -m kabusys.run_execution` 実行時に Execution Startup Summary が自動保存される
- 保存先: `artifacts/execution_startup/{date}/report.md`
- 執行日（今日）の**前営業日**（`signal_date`）の `signal_queue` 行を読む（夜間バッチの行）。
  発注の業務キーは `{signal_date}_{code}_{side}`、`position_entries` の約定日は執行日
- Execution は DuckDB を **read_only** で開く（DuckDB には書かない。ダッシュボード等の読み取りと共存）
- 各 queue 行の処理状態は SQLite の `signal_queue_status` に記録し、夜間の
  portfolio_construction で DuckDB `signal_queue` に同期する。再起動時は `pending` 以外の行を再読込しない

### 5.4 Optional Monitoring Start（検証用）

```cmd
python scripts\start_system.py --component monitoring
```

Paper Trading や自動発注検証時に、注文・ポジション・リスク状態を監視する。

---

## 6. Market Close（15:00）

```cmd
python -m kabusys.run_market_close_report --save
python -m kabusys.run_performance_report --type daily --save
```

判定:

- `OK`
- `BLOCKED`

シグナル件数は当日執行分（前営業日の `signal_date`）で数える。pending は DuckDB
`signal_queue` の pending 行のうち、SQLite `signal_queue_status` で処理済み（pending 以外）と
記録されていない件数（Execution 未起動・未処理も pending として数える）。filled は
`signal_queue_status` の件数。SQLite は Execution と同じく paper_trading では `paper_trading.db` を読む。

出力先:

- `artifacts/market_close/{date}/report.md`
- `artifacts/performance/live/daily/{date}/report.md`

---

## 7. Task Scheduler / スケジューラーデーモン

ジョブ自動実行の方式は **2 通り**あります。運用環境に合わせて選択してください。

### 方式 A: スケジューラーデーモン（推奨）

単一の Python プロセス（`scripts/run_scheduler.py`）が常駐し、すべてのジョブを一元管理する方式です。

**メリット:**

- `run_execution` が DuckDB 接続（read_only）を保持したまま市場終了後も生存し続ける問題（夜間バッチの書き込みロック競合）を自動解消する。夜間バッチ実行前に execution を自動停止し、完了後に再起動する。
- `market_calendar` テーブルを参照して**土日・祝日・年末年始をスキップ**する（DB 未初期化時は土日フォールバック）。
- Task Scheduler へは **「ログオン時に起動」の 1 エントリのみ**登録する。

**登録スクリプト:**

```powershell
powershell -File scripts\setup_scheduler_daemon.ps1
```

**動作確認コマンド:**

```powershell
# スケジュール一覧の表示
python scripts\run_scheduler.py --list

# 1 回チェックして終了（テスト用）
python scripts\run_scheduler.py --once
```

**ログ・データファイル:**

| ファイル | 内容 |
|---|---|
| `logs/scheduler.log` | スケジューラー本体のログ |
| `logs/<job_name>.log` | 各ジョブの stdout/stderr |
| `data/scheduler_ran_today.json` | 当日実行済みジョブ（重複防止・再起動耐性） |
| `data/scheduler.pid` | 多重起動防止用 PID ロック |

**`.env` 設定（任意）:**

| キー | デフォルト | 説明 |
|---|---|---|
| `EXCLUSIVE_DB_STOP_WAIT_SEC` | `20` | execution 停止後の追加待機上限（秒） |

---

### 方式 B: 個別タスク登録

従来の方式。個別ジョブを Task Scheduler に直接登録します。DB ロック問題が発生する環境では方式 A を推奨します。

**登録スクリプト:**

- `scripts/setup_task_scheduler.ps1` — 登録（Core は常時、Addon は `.env` フラグが `true` のときのみ）
- `scripts/remove_task_scheduler.ps1` — `KabuSys_*` タスクを一括削除

**Core ジョブ（常時登録）:**

| 時刻 | タスク名 | スクリプト |
|---|---|---|
| 17:30 | `KabuSys_DataUpdate` | `scripts\run_data_update.py` |
| 18:30 | `KabuSys_FeatureGen` | `scripts\run_feature_gen.py` |
| 20:00 | `KabuSys_StrategySignal` | `scripts\run_strategy_signal.py` |
| 21:00 | `KabuSys_PortfolioConstruction` | `scripts\run_portfolio_construction.py` |
| 21:10 | `KabuSys_ManualOrderReportEvening` | `scripts\run_manual_order_report.py --phase evening` |
| 21:15 | `KabuSys_NightBatchReport` | `scripts\run_night_batch_report.py` |
| 08:00 | `KabuSys_PreMarketReport` | `scripts\run_pre_market_report.py` |
| 08:02 | `KabuSys_SignalQueueReport` | `scripts\run_signal_queue_report.py` |
| 08:05 | `KabuSys_ManualOrderReportMorning` | `scripts\run_manual_order_report.py --phase morning` |
| 08:05 | `KabuSys_PositionReconciliationReport` | `scripts\run_position_reconciliation_report.py` |
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

## 自動執行の停止（手動注文メイン運用）

`.env` に `ENABLE_AUTO_EXECUTION=false` を設定すると、スケジューラーデーモンは 08:30 `execution_start` と 08:35 `position_reconciliation_report`（かぶステ API 必須）を実行しない。夜間バッチ・手動注文候補レポート・その他のレポートは従来どおり動く。未設定時は `true`（従来動作）。設定はデーモンの起動時と日付変更時に再読込される。
