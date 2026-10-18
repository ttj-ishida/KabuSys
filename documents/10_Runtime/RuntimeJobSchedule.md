# Runtime Job Schedule

- 対象: KabuSys の日次ジョブ構成
- 前提: Single Windows Node / スケジューラーデーモン（Windows タスク `KabuSys_Scheduler`）
- 運用方式: 手動注文メイン（`.env` の `ENABLE_AUTO_EXECUTION=false`。自動執行は停止中）

---

## 1. 全体像

KabuSys は、夜間バッチで翌営業日のシグナルと注文候補を作り、夜 LINE と翌朝の手動注文レポートでユーザーに提示する構成です。発注はユーザーが証券画面で行い、約定を `manual_trades` に入力します。

kabuステーション API による自動執行（Execution / Monitoring）は停止中です。**自動売却の機能はありません**（`signal_queue` には BUY しか入らず、自動執行を再開しても自動で発注されるのは BUY だけ）。

### 1.1 スケジュール表（`scripts/run_scheduler.py` の定義）

excl = 実行前に Execution を停止し、DuckDB を排他利用するジョブ（`needs_exclusive_db=True`）。

| 時刻 | ジョブ | スクリプト | excl | 手動運用中 |
|---|---|---|---|---|
| 08:00 | `pre_market_report` | `run_pre_market_report.py` | - | 実行（自動執行の可否判定。手動運用中は `BLOCKED` でも問題なし） |
| 08:02 | `signal_queue_report` | `run_signal_queue_report.py`（前営業日の queue） | - | 実行 |
| 08:05 | `manual_order_report_morning` | `run_manual_order_report.py --phase morning`（LINE 通知あり） | - | 実行 |
| 08:30 | `execution_start` | `start_system.py --component execution --clear-stop-flag` | - | **無効** |
| 08:35 | `position_reconciliation_report` | `run_position_reconciliation_report.py`（kabu API 必須） | - | **無効** |
| 09:00 | `monitoring_start` | `start_system.py --component monitoring` | - | **無効** |
| 15:35 | `tdnet_collection`（`ENABLE_TDNET=true`） | `run_tdnet_collection.py` | YES | 実行 |
| 17:30 | `data_update` | `run_data_update.py` | YES | 実行 |
| 17:33 | `yahoonews_collection`（`ENABLE_YAHOONEWS=true`） | `run_yahoonews_collection.py` | YES | 実行 |
| 18:30 | `feature_gen` | `run_feature_gen.py` | YES | 実行 |
| 19:00 | `ai_analysis`（`ENABLE_AI_SENTIMENT=true`） | `run_ai_analysis.py` | YES | 実行（ただし現在スコアが出ていない：Issue #419） |
| 20:00 | `strategy_signal` | `run_strategy_signal.py [--date]` | YES | 実行（手動保有の SELL 候補を `manual_action_queue` に記録） |
| 21:00 | `portfolio_construction` | `run_portfolio_construction.py [--date]` | YES | 実行（夜 LINE：翌日 BUY/SELL、`[手動保有]`・`[買い増し]` 表示） |
| 21:10 | `manual_order_report_evening` | `run_manual_order_report.py --phase evening` | YES | 実行（LINE なし） |
| 21:15 | `night_batch_report` | `run_night_batch_report.py` | YES | 実行 |

人の作業（スケジュール外）:

```text
21:30  夜 LINE・night_batch_report の確認（手動）
08:05〜 朝のレポート確認・注文内容の決定（手動）
09:00  寄り付き → 証券画面で手動注文（手動）
約定後  manual_trades で約定入力（手動）
随時    売却候補への対応（手動）
```

- 非営業日（土日・祝日・年末年始）は全ジョブをスキップする
- `ENABLE_TDNET` / `ENABLE_YAHOONEWS` / `ENABLE_AI_SENTIMENT` が `true` でないジョブ、`ENABLE_AUTO_EXECUTION=false` のときの 08:30 / 08:35 / 09:00 は実行しない（`run_scheduler.py --list` で `skip` と表示される）
- EDINET 収集（`run_edinet_collection.py`）と開示分類（`run_disclosure_classification.py`）はスケジュールに含まれていない（必要なら手動実行）

> **スケジュール設計の根拠**: J-Quants の日足株価データ（`daily_quotes`）は東証引け（15:30）直後ではなく 16:30〜17:00 頃に公開される。15:30 に data_update を実行すると当日データを取得できず feature_gen が 0 件になる。17:30 に遅延することでデータ確実取得後に実行できる。

### 1.2 日付の決まり

- 夜間バッチ（D 日夜）は `signals` と `signal_queue` に `date = D` で書く
- 翌朝のレポート・執行は「前営業日（`prev_trading_day`）」の分を読む
- 夜間バッチが失敗した場合、翌朝に `--date <前営業日>` を付けて `strategy_signal` と `portfolio_construction` を再実行できる（`documents/08_Operations/FailureRecovery.md`）。特徴量は `build_features(conn, date)` で日付指定して再生成する

---

## 2. Night Batch

### 2.0 tdnet_collection（15:35、`ENABLE_TDNET=true`）/ yahoonews_collection（17:33、`ENABLE_YAHOONEWS=true`）

- TDnet 適時開示一覧を `raw_disclosures` に保存
- Yahoo News RSS を `raw_news` に保存（AI 分析の入力）

### 2.1 data_update（17:30）

役割:

- J-Quants 日次データ取得（取引カレンダー・株価・財務・配当・TOPIX・決算カレンダー）
- 品質チェック
- 市場 breadth 計算
- DuckDB 更新

主なテーブル:

- `market_calendar`
- `prices_daily`
- `fundamentals`
- `topix_daily`（Issue #257: `run_topix_etl()` が Step 5 として追加）
- `market_breadth`

> ニュース原文（`raw_news`）は data_update ではなく 17:33 の `yahoonews_collection` が保存する。

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

> ⚠️ **Issue #419:** 現在スコアが出ていない（ニューススコア 0 件・regime 常に neutral）。ジョブ自体は `success` で終わる。

### 2.4 strategy_signal（20:00）

役割:

- BUY / SELL シグナル生成
- Bear regime / breadth_stop / 決算回避反映
- `min_holding_days` / `time_exit` / `trailing_stop` を考慮
- `MANUAL_TRADING_ENABLED=true` のとき、手動保有にも同じ SELL ルール（損切り・トレーリングストップ・保有期限・スコア低下・決算回避）を適用し、売却候補を `manual_action_queue` に記録する

主なテーブル:

- `signals`
- `manual_action_queue`

### 2.5 portfolio_construction（21:00）

役割:

- ポジションサイズ計算
- 翌営業日の BUY 候補生成（手動保有中の銘柄は不足分だけを「買い増し」）
- 夜 LINE（翌日 BUY / SELL、`[手動保有]`・`[買い増し]` 表示）

主なテーブル:

- `signal_queue`（`date` = 当日＝夜間バッチ日。翌営業日のレポート・執行で読まれる。**BUY のみ**。運用ジョブで `signal_queue` に INSERT するのはこのスクリプトだけ）

補足（Issue #413）:

- 起動直後に、Execution Engine が SQLite の `signal_queue_status` に記録した処理状態
  （`processing` / `filled` / `cancelled` / `failed`）を DuckDB の `signal_queue.status` と
  `processed_at` に同期する。`pending` の行には触れない。同期に失敗しても警告ログのみで続行する。

### 2.6 manual_order_report evening（21:10）

役割:

- 手動注文メイン運用（#412）向けに、ユーザーが証券画面で注文するための BUY / SELL 候補を出力する
- DuckDB は読み取り専用。発注・kabu API 呼び出しはしない
- BUY: `signal_queue`（pending）に銘柄名・推奨株数・参考価格・想定金額・スコア/順位・保有株数・買い増し表記を付与
- SELL: `signals`（sell）に `manual_action_queue` の株数・理由・`[手動保有]` を付与。自動分は `positions` の最新株数
- 総資産・利用可能現金（`MANUAL_TRADING_ENABLED=true` 時）・1 銘柄上限（総資産の 10%）・想定投下額・利用率
  - 総資産（手動運用時）= 元手（`MANUAL_TRADING_INITIAL_CASH`）− 手動の買付額（手数料込み）+ 売却額（手数料差引）+ 保有時価
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

### 2.7 night_batch_report（21:15）

役割:

- `artifacts/job_runs/{date}/` から各ジョブの `JobRunResult` を読み込む
- DuckDB から当日の更新件数・翌営業日シグナル情報を集計
- READY / READY_WITH_WARNINGS / BLOCKED を判定してレポートを生成

主なアーティファクト:

- `artifacts/job_runs/{date}/{job_name}.json`（各ジョブの実行結果）
- `artifacts/reports/{date}/summary.json`
- `artifacts/reports/{date}/report.md`
- `artifacts/reports/{date}/warnings.json`

> 保存先は `scripts/run_night_batch_report.py` の既定値 `artifacts/reports/`（`--output-dir` で変更可）。`save_report()` 単体の既定値は `artifacts/night_batch/` だが、スクリプト経由では使われない。

関連モジュール:

- `src/kabusys/operations/night_batch_report.py`
- `src/kabusys/operations/job_run_recorder.py`

---

## 3. Night Batch 状態確認（21:15 以降）

21:15 に `night_batch_report` が自動実行し、CLI サマリーと `artifacts/reports/{date}/` を生成する。

手動実行（再生成・デバッグ時）:

```cmd
python scripts/run_night_batch_report.py
python scripts/run_night_batch_report.py --date 2026-05-07
```

スケジューラー側の結果確認（失敗したジョブは `REQUIRES ATTENTION: ジョブ失敗` と出る）:

```powershell
Select-String -Path logs\scheduler.log -Pattern "REQUIRES ATTENTION|ジョブ完了" | Select-Object -Last 20
```

判定:

- `READY`: 全必須ジョブ成功かつ翌営業日の `signal_queue` が作成済み。手動注文候補として確認可能
- `READY_WITH_WARNINGS`: warning はあるが翌営業日の準備は完了
- `BLOCKED`: 以下のいずれかに該当する場合

必須ジョブ: `data_update_job` / `feature_generation_job` / `ai_analysis_job` / `strategy_signal_job` / `portfolio_construction_job`

| 条件 | 判定 |
|------|------|
| 必須ジョブが欠落 / `failed` / `skipped` | BLOCKED |
| `signal_queue == 0` | BLOCKED |
| `prices_daily == 0` | BLOCKED |
| `features == 0` | BLOCKED |
| `signals == 0` | READY_WITH_WARNINGS |
| その他の warning | READY_WITH_WARNINGS |

> `prices_daily == 0` および `features == 0` は、価格データ・特徴量なしではシグナル生成が不可能なため BLOCKED とする。`signals == 0` は Bear レジームなど戦略上ありうる正常系のため READY_WITH_WARNINGS に留める（Issue #288）。

> 手動運用では、必須ジョブがすべて `success` で BUY が 0 件なだけ（例: `breadth_stop`）の `BLOCKED`（`signal_queue == 0`）は正常。ジョブ失敗の場合のみ復旧する。

---

## 4. Pre-Market（08:00〜08:05）

3 本のレポートがスケジューラーデーモンにより自動実行される。手動注文メイン運用では、証券口座との自動リコンシリエーション（08:35）は実行しない。

| 時刻 | ジョブ | スクリプト | 出力先 |
|------|----------|------------|--------|
| 08:00 | `pre_market_report` | `scripts/run_pre_market_report.py` | `artifacts/pre_market/{date}/report.md` |
| 08:02 | `signal_queue_report` | `scripts/run_signal_queue_report.py`（既定で前営業日＝当日執行分の queue を読む。`--date` 指定可） | `artifacts/signal_queue/{date}/report.md`（`{date}` は queue の日付） |
| 08:05 | `manual_order_report_morning` | `scripts/run_manual_order_report.py --phase morning` | `artifacts/manual_orders/{date}/morning.md`（と `.json`） |

判定（pre_market_report）:

- `READY`
- `READY_WITH_WARNINGS`（データ鮮度が古い）
- `BLOCKED`（前営業日の `signal_queue` に pending がない / 停止フラグあり / スケジューラー未稼働）

確認対象（pre_market_report）:

- stop flag
- スケジューラー稼働（`KabuSys_Scheduler` が Running、または個別タスク `KabuSys_ExecutionStart` が Ready）
- Signal Queue（前営業日の pending 件数）
- データ鮮度

> pre_market_report は自動執行を開始してよいかの判定。手動運用中は BUY 候補 0 件の日などに `BLOCKED` になるが、問題ない（手動注文の判断には manual_order_report を使う）。

確認対象（manual_order_report morning）:

- 休場日（`is_trading_day` が false。カレンダーがなければ土日判定）なら警告し、BUY を全件見送り
- 前営業日のシグナル（`signal_date` が前営業日より古い場合は警告し、BUY を全件見送り）
- データ鮮度（`check_data_freshness`）
- stop flag（`data/stop_requested.flag`。ありなら BUY を全件見送り）
- DD 停止（監視 SQLite `dashboard.dd_stop_blocked_since`。ありなら BUY を全件見送り、読めなければ「不明」で警告のみ）
- 停止条件は BUY が 0 件でも警告としてステータス・LINE に出る
- `--date` で過去日を指定した場合も、停止フラグ・DD 停止・資金は実行時点の状態（過去日である旨を警告）
- 出力は「今日注文すべき候補（BUY・SELL）」と「見送り候補（理由付き）」に分かれる。SELL は常に表示
- ステータス: `OK` / `警告あり` / `BUY 見送り`（BUY 全件見送りの理由があれば `BUY 見送り`、警告があれば `警告あり`）
- LINE「【KabuSys 手動注文 当日朝】」: ステータス、BUY 上位 10 件、SELL 一覧、警告。送信失敗は無視

> ⚠️ **既知の誤警告（Issue #421）:** シグナル 0 件の正常な日（例: breadth_stop で BUY 全件停止）でも「シグナルが古い」と出て `BUY 見送り` になる。夜間バッチの成否は `logs/scheduler.log` と night_batch_report で確認する。

手動再実行（デバッグ時）:

```cmd
python scripts/run_pre_market_report.py
python scripts/run_signal_queue_report.py
python scripts/run_manual_order_report.py --phase morning
python scripts/run_manual_order_report.py --phase evening --date 2026-10-13
```

---

## 5. Manual Order / 自動執行（停止中）

### 5.1 手動注文の確認（08:05〜寄り付き）

手動注文メイン運用では、Execution は起動しない。

確認するもの（`artifacts/manual_orders/{date}/morning.md` / 朝 LINE）:

- ステータス（`OK` / `警告あり` / `BUY 見送り`）
- BUY 候補（株数・参考価格・想定金額・スコア・上限・下限・新規／買い増し）
- SELL 候補（売却候補）
- 見送り候補と理由
- 見送りルール: 寄り付きが前日終値比 +5% 超 / −3% 以下なら見送り（寄り前の気配は取得しないため、寄り付き価格と上限・下限を見比べる）

### 5.2 手動注文と約定入力（寄り付き〜）

ユーザーが証券会社の画面で注文する。約定後は `manual_trades` に入力する（運用フォルダで実行。コードは 5 桁）。

```cmd
.venv\Scripts\python.exe -m kabusys.manual_trades add --date 2026-10-15 --code 44770 --side buy --qty 100 --price 387 --fees 0 --apply
.venv\Scripts\python.exe -m kabusys.manual_trades wizard
.venv\Scripts\python.exe -m kabusys.manual_trades list --date 2026-10-15
.venv\Scripts\python.exe -m kabusys.manual_trades positions
```

`--apply` を付けないとプレビューのみ。売却候補に対応したら、Streamlit **Manual Trades > 売却候補** で「対応済み」（売らない場合は「見送り」）にする。

### 5.3 Execution Start（自動執行モード・現在停止中）

`ENABLE_AUTO_EXECUTION=true` のとき、08:30 にスケジューラーが実行する。手動で起動する場合:

```cmd
python scripts\start_system.py --component execution
```

補足:

- kabuステーションの起動・ログインが必要
- `python -m kabusys.run_execution` 実行時に Execution Startup Summary が自動保存される
- 保存先: `artifacts/execution_startup/{date}/report.md`
- 執行日（今日）の**前営業日**（`signal_date`）の `signal_queue` 行（BUY のみ）を読み、08:50〜09:10 に発注する。
  発注の業務キーは `{signal_date}_{code}_{side}`（二重発注防止）、`position_entries` の約定日は執行日
- Execution は DuckDB を **read_only** で開く（DuckDB には書かない。ダッシュボード等の読み取りと共存）
- 各 queue 行の処理状態は SQLite の `signal_queue_status` に記録し、夜間の
  portfolio_construction で DuckDB `signal_queue` に同期する。再起動時は `pending` 以外の行を再読込しない
- 08:35 `position_reconciliation_report`（kabu API 必須）も `ENABLE_AUTO_EXECUTION=true` のときだけ実行される

### 5.4 Monitoring Start（自動執行モード・現在停止中）

```cmd
python scripts\start_system.py --component monitoring
```

自動執行時に、注文・ポジション・リスク状態を監視する。Execution プロセスの死活を前提に CRITICAL 通知するため、自動執行停止中は起動しない。監視・Kill Switch は未約定注文の取消のみで、保有の売却はしない。

---

## 6. Market Close（15:00・自動執行時）

手動運用では必須ではない（手動保有の確認は Streamlit **Manual Trades** と `manual_trades positions` で行う）。

```cmd
python -m kabusys.run_market_close_report --save
python -m kabusys.run_performance_report --type daily --save
```

> ⚠️ `run_performance_report` は現在空のレポートを出して終了コード 1 を返す（`portfolio_performance` に書き込む処理がないため。`--env` の既定は `live`）。自動執行を再開しても、この状況は変わらない。

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

ジョブ自動実行の方式は **2 通り**ある。**運用では方式 A（スケジューラーデーモン）を使っている。**

### 方式 A: スケジューラーデーモン（運用で使用中）

単一の Python プロセス（`scripts/run_scheduler.py`）が常駐し、すべてのジョブを一元管理する方式。Windows タスク `KabuSys_Scheduler`（ログオン時トリガー）が運用フォルダ `C:\Projects\KabuSys` で起動する。

**特徴:**

- `run_execution` が DuckDB 接続（read_only）を保持したまま市場終了後も生存し続ける問題（夜間バッチの書き込みロック競合）を自動解消する。excl ジョブの実行前に execution を自動停止し、取引時間内（08:30〜15:35）に完了した場合のみ再起動する。
- `market_calendar` テーブルを参照して**土日・祝日・年末年始をスキップ**する（DB 未初期化時は土日フォールバック）。
- 起動時刻を過ぎたジョブは、起動直後に順次実行する（追いつき）。実行済みジョブは `data/scheduler_ran_today.json` に記録し、再起動しても当日分は重複実行しない。
- `.env` のフラグ（`ENABLE_AUTO_EXECUTION` / `ENABLE_TDNET` / `ENABLE_YAHOONEWS` / `ENABLE_AI_SENTIMENT` / `EXCLUSIVE_DB_STOP_WAIT_SEC`）は起動時と日付変更時に再読込する。
- Task Scheduler へは **「ログオン時に起動」の 1 エントリのみ**登録する。
- 現状、タスクの実行ファイルは `python`（グローバル `C:\Python313`）。`.venv` への切り替えを予定（管理者 PowerShell で `Set-ScheduledTask`）。

**登録スクリプト:**

```powershell
powershell -File scripts\setup_scheduler_daemon.ps1
# .venv の python を使う場合
powershell -File scripts\setup_scheduler_daemon.ps1 -PythonPath C:\Projects\KabuSys\.venv\Scripts\python.exe
```

**動作確認コマンド:**

```powershell
# スケジュール一覧の表示（無効なジョブは enabled 列が skip）
python scripts\run_scheduler.py --list

# 1 回チェックして終了（テスト用）
# - 時刻を過ぎた未実行ジョブは実際に実行され、data/scheduler_ran_today.json に記録されるため、
#   その日はデーモンが同じジョブを再実行しない
# - デーモン稼働中は PID ロック（data/scheduler.pid）により起動せず終了する
python scripts\run_scheduler.py --once

# タスクの状態・手動起動
Get-ScheduledTask -TaskName "KabuSys_Scheduler" | Get-ScheduledTaskInfo
Start-ScheduledTask -TaskName "KabuSys_Scheduler"
```

**ログ・データファイル:**

| ファイル | 内容 |
|---|---|
| `logs/scheduler.log` | スケジューラー本体のログ（ジョブ失敗は `REQUIRES ATTENTION`） |
| `logs/<job_name>.log` | 各ジョブの stdout/stderr |
| `data/scheduler_ran_today.json` | 当日実行済みジョブ（重複防止・再起動耐性） |
| `data/scheduler.pid` | 多重起動防止用 PID ロック |

**`.env` 設定:**

| キー | デフォルト | 説明 |
|---|---|---|
| `ENABLE_AUTO_EXECUTION` | `true` | `false` で 08:30 `execution_start`・08:35 `position_reconciliation_report`・09:00 `monitoring_start` を実行しない（現在の運用値は `false`） |
| `EXCLUSIVE_DB_STOP_WAIT_SEC` | `20` | execution 停止後の追加待機上限（秒） |

---

### 方式 B: 個別タスク登録（従来方式・未使用）

従来の方式。個別ジョブを Task Scheduler に直接登録する。現在は使っていない。

> ⚠️ 個別タスク方式は `ENABLE_AUTO_EXECUTION` を参照しない。手動運用中に使うと 08:30 の Execution 起動・08:35 のリコンシリエーション・09:00 の Monitoring 起動も登録される。

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
| 08:30 | `KabuSys_ExecutionStart` | `scripts\start_system.py --component execution --clear-stop-flag` |
| 08:35 | `KabuSys_PositionReconciliationReport` | `scripts\run_position_reconciliation_report.py` |
| 09:00 | `KabuSys_MonitoringStart` | `scripts\start_system.py --component monitoring` |

**Addon ジョブ（`.env` フラグが `true` のときのみ登録）:**

| 時刻 | タスク名 | スクリプト | 条件 |
|---|---|---|---|
| 15:35 | `KabuSys_TdnetCollection` | `scripts\run_tdnet_collection.py` | `ENABLE_TDNET=true` |
| 17:33 | `KabuSys_YahooNewsCollection` | `scripts\run_yahoonews_collection.py` | `ENABLE_YAHOONEWS=true` |
| 19:00 | `KabuSys_AiAnalysis` | `scripts\run_ai_analysis.py` | `ENABLE_AI_SENTIMENT=true` |

---

## 8. 補足

- `market_breadth` は data_update（`calc_and_save_breadth`）で日次更新される
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
- `documents/08_Operations/FailureRecovery.md`
- `documents/WebManual/A_OperationsCycle.md`
- `documents/WebManual/C_ManualOrderOperation.md`
