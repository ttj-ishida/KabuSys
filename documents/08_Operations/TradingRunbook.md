# Trading Runbook

- 対象: KabuSys の日次運用
- 前提: Single Windows Node / J-Quants / 運用フォルダ `C:\Projects\KabuSys`
- 現在の運用方式: **手動注文メイン**（KabuSys は候補を出すだけ。発注は証券画面で人が行う）
- 自動執行: **停止中**（`.env` の `ENABLE_AUTO_EXECUTION=false`）。手順は [10. 自動執行モード（現在停止中）](#10-自動執行モード現在停止中) に分けて残している

> コマンドはすべて運用フォルダ（`C:\Projects\KabuSys`）で実行する。仮想環境を有効化していない場合は `python` を `.venv\Scripts\python.exe` に読み替える。

---

## 1. 日次サイクルの全体像

手動注文メイン運用の 1 日は次の順で回る。

```text
D 日 夜   夜間バッチ（自動）→ 夜 LINE（翌営業日の BUY / SELL）→ 夜のレポート
D+1 朝    08:05 朝のレポート / 朝 LINE「【KabuSys 手動注文 当日朝】」
D+1 寄り  証券画面で手動注文（BUY は寄り付き価格と上限・下限を見比べる）
D+1 約定後 約定を KabuSys に入力（manual_trades CLI または Streamlit）
随時      売却候補への対応（証券画面で売却 → SELL を入力 → 「対応済み」にする）
```

**自動売却の機能はない。** SELL シグナルは `signals` テーブル・LINE・売却候補（`manual_action_queue`）に出るだけで、売るかどうか・いつ売るかは人が決めて証券画面で発注する。

---

## 2. 日次タイムライン

スケジューラーデーモン（Windows タスク `KabuSys_Scheduler`）が `scripts\run_scheduler.py` の定義どおりにジョブを実行する。非営業日（土日・祝日・年末年始）は全ジョブをスキップする。

| 時刻 | ジョブ / 作業 | 手動運用中 | 人がやること |
|---|---|---|---|
| 08:00 | `pre_market_report` | 実行 | なし（自動執行の可否判定。手動運用中は `BLOCKED` でも問題ない） |
| 08:02 | `signal_queue_report` | 実行 | なし（参考） |
| 08:05 | `manual_order_report_morning`（朝 LINE あり） | 実行 | **朝のレポートを確認し、注文内容を決める** |
| 08:30 | `execution_start` | **無効** | — |
| 08:35 | `position_reconciliation_report` | **無効** | — |
| 09:00 | `monitoring_start` | **無効** | — |
| 09:00〜 | 寄り付き | — | **証券画面で手動注文 → 約定を入力** |
| 15:35 | `tdnet_collection`（`ENABLE_TDNET=true`） | 実行 | なし |
| 17:30 | `data_update` | 実行 | なし |
| 17:33 | `yahoonews_collection`（`ENABLE_YAHOONEWS=true`） | 実行 | なし |
| 18:30 | `feature_gen` | 実行 | なし |
| 19:00 | `ai_analysis`（`ENABLE_AI_SENTIMENT=true`） | 実行（現在スコアが出ていない：Issue #419） | なし |
| 20:00 | `strategy_signal` | 実行 | なし（手動保有の SELL 候補を `manual_action_queue` に記録） |
| 21:00 | `portfolio_construction`（夜 LINE あり） | 実行 | **夜 LINE で翌営業日の BUY / SELL を確認** |
| 21:10 | `manual_order_report_evening` | 実行 | 必要なら夜のレポートを確認 |
| 21:15 | `night_batch_report` | 実行 | **夜間バッチの成否を確認** |

詳細は `documents/10_Runtime/RuntimeJobSchedule.md` を参照。

> 夜間バッチ（`tdnet_collection` 〜 `night_batch_report`）は DuckDB を排他利用する。17:30〜21:20 頃に約定入力や Streamlit からの書き込みを行うと、DB ロックで失敗することがある。約定入力はこの時間帯を避ける。

---

## 3. 夜（21:00〜21:30）: 翌営業日の候補確認

### 3.1 夜 LINE（21:00 portfolio_construction）

翌営業日の BUY / SELL 候補が LINE に届く。手動保有の銘柄には `[手動保有]`、手動保有中の銘柄が BUY 候補になった場合は不足分だけが `[買い増し]` として表示される。

### 3.2 夜のレポート（21:10 manual_order_report_evening）

- 出力: `artifacts/manual_orders/{日付}/evening.md`（と `evening.json`）
- LINE は送らない（夜 LINE に詳細が出るため）
- 内容は朝のレポートとほぼ同じ（BUY / SELL・資金・上限・見送りルール）。夜のうちに注文内容の当たりを付けておく

### 3.3 夜間バッチの成否（21:15 night_batch_report）

- 出力: `artifacts/reports/{日付}/report.md`（と `summary.json` / `warnings.json`）

> `scripts/run_night_batch_report.py` は既定で `artifacts/reports/` に保存する（モジュール単体の既定値 `artifacts/night_batch/` は使われない）。

確認するのは **「2. Job Status」の必須ジョブ（`data_update_job` / `feature_generation_job` / `ai_analysis_job` / `strategy_signal_job` / `portfolio_construction_job`）がすべて `success` か** どうか。

| 判定 | 意味 | 手動運用での扱い |
|---|---|---|
| `READY` | 全必須ジョブ成功・`signal_queue` 作成済み | 翌朝のレポートどおりに進める |
| `READY_WITH_WARNINGS` | 警告あり・翌営業日の準備は完了 | 警告内容を確認して進める |
| `BLOCKED` | 必須ジョブ失敗 / `signal_queue == 0` / 価格・特徴量が 0 件 | **ジョブ失敗なら復旧が必要**。ジョブがすべて成功していて BUY が 0 件（例: `breadth_stop` で BUY 全件停止）なだけなら正常 |

手動で再生成する場合:

```cmd
python scripts\run_night_batch_report.py
python scripts\run_night_batch_report.py --date 2026-10-16
```

スケジューラー側の成否は `logs\scheduler.log` で確認できる（失敗したジョブは `REQUIRES ATTENTION: ジョブ失敗` と出る）。各ジョブの出力は `logs\<job_name>.log`。

```powershell
Select-String -Path logs\scheduler.log -Pattern "REQUIRES ATTENTION|ジョブ完了" | Select-Object -Last 20
```

夜間バッチが失敗した場合の復旧は [5. 障害時の基本対応](#5-障害時の基本対応) と `documents/08_Operations/FailureRecovery.md` を参照。

---

## 4. 朝（08:05〜寄り付き）: 手動注文と約定入力

### 4.1 朝のレポートを確認する（08:05）

- 出力: `artifacts/manual_orders/{日付}/morning.md`（と `morning.json`）
- LINE:「【KabuSys 手動注文 当日朝】」（ステータス・BUY 上位 10 件・SELL 一覧・警告）

**ステータス:**

| ステータス | 意味 | 対応 |
|---|---|---|
| `OK` | 警告なし | BUY 表・SELL 表どおりに注文を検討する |
| `警告あり` | 警告がある（データ鮮度など） | 警告を読んでから判断する |
| `BUY 見送り` | 停止フラグ・DD 停止・休場日・シグナルが古い のいずれか | BUY は全件「見送り候補」に移る。**SELL は常に表示される**ので SELL だけ対応する |

> **既知の誤警告（Issue #421）:** シグナル 0 件の正常な日（例: `breadth_stop` で BUY 全件停止）でも「シグナルが古い」と出て `BUY 見送り` になる。夜間バッチの成否は `logs\scheduler.log` と night_batch_report（[3.3](#33-夜間バッチの成否2115-night_batch_report)）で確認する。

**BUY 表の列:** 順位・コード・銘柄名・株数・参考価格（前日終値）・想定金額・スコア・「この価格以下なら買付可（上限）」・「この価格以上なら買付可（下限）」・備考（新規／買い増し）。

**見送りルール:** 寄り付きが前日終値比 +5% 超、または −3% 以下なら見送る。寄り前の気配は取得しないため、ギャップ率は自動計算しない。**寄り付き価格が「下限」以上かつ「上限」以下なら買付可**、範囲外なら見送る。

資金欄（`MANUAL_TRADING_ENABLED=true` のとき）:

- 総資産 = 元手（`MANUAL_TRADING_INITIAL_CASH`）− 手動の買付額（手数料込み）+ 売却額（手数料差引）+ 保有時価
- 1 銘柄上限 = 総資産の 10%

手動で再生成する場合:

```cmd
python scripts\run_manual_order_report.py --phase morning
```

### 4.2 証券画面で手動注文する（寄り付き）

1. 朝のレポートの BUY 表から注文する銘柄・株数を決める
2. 寄り付き価格を見て、上限・下限の範囲外なら見送る
3. SELL 表（売却候補）にある銘柄は、売るかどうかを判断して売り注文を出す

### 4.3 約定を入力する

約定したら、運用フォルダで約定を KabuSys に入力する。銘柄コードは 5 桁（例: トヨタ = `72030`）。

```cmd
:: プレビューのみ（--apply なし。DB には保存しない）
.venv\Scripts\python.exe -m kabusys.manual_trades add --date 2026-10-15 --code 44770 --side buy --qty 100 --price 387 --fees 0

:: 保存する
.venv\Scripts\python.exe -m kabusys.manual_trades add --date 2026-10-15 --code 44770 --side buy --qty 100 --price 387 --fees 0 --apply

:: 対話式
.venv\Scripts\python.exe -m kabusys.manual_trades wizard
```

確認・修正:

```cmd
.venv\Scripts\python.exe -m kabusys.manual_trades list --date 2026-10-15
.venv\Scripts\python.exe -m kabusys.manual_trades positions
.venv\Scripts\python.exe -m kabusys.manual_trades delete <trade_id>
```

入力時の注意:

- 同日・同銘柄・同売買の 2 件目以降は ID に `_2`、`_3`… が付く（分割約定はそのまま複数件入力してよい）
- 全く同じ内容を 2 回入れると重複エラーになる。意図的なら `--allow-duplicate`
- 保有を超える売却はエラーになる。記録開始前から持っていた株などは `--allow-oversell`
- `--force` は非推奨（`--allow-duplicate` と同じ動作で、既存の約定を上書きはしない）

Streamlit の **Manual Trades** ページ（入力／手動ポジション／売却候補／履歴）からも入力できる。

### 4.4 売却候補に対応する

手動保有にも自動売買と同じ SELL ルール（損切り・トレーリングストップ・保有期限・スコア低下・決算回避）が適用され、毎晩 20:00 の `strategy_signal` で「売却候補」として `manual_action_queue` に記録される。

1. 証券画面で売却する
2. 約定を `--side sell` で入力する
3. Streamlit **Manual Trades > 売却候補** で、その候補を「対応済み」にする（売らないと決めた場合は「見送り」）

---

## 5. 障害時の基本対応

1. `logs\scheduler.log` で失敗したジョブを特定する
2. `logs\<job_name>.log`（または `logs\<app>_*.log`）でエラー内容を確認する
3. 原因を解消し、必要なジョブを手動で再実行する

```powershell
# 直近のエラー
Select-String -Path logs\*.log -Pattern "ERROR|CRITICAL" | Select-Object -Last 30

# 失敗したバッチの実行単位ログ（最新）
Get-ChildItem logs\data_update_*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content
```

**夜間バッチが失敗した場合（翌朝に復旧する）:** 夜間バッチは D 日夜に `signals` / `signal_queue` を `date = D` で書き、翌朝のレポートは前営業日の分を読む。日付が変わってから再実行する場合は、必ず `--date <前営業日>` を付ける。

```cmd
python scripts\run_strategy_signal.py --date 2026-10-16
python scripts\run_portfolio_construction.py --date 2026-10-16
python scripts\run_manual_order_report.py --phase morning
```

特徴量の再生成やその他の復旧手順は `documents/08_Operations/FailureRecovery.md` を参照。

**スケジューラーが動いていない場合:**

```powershell
Get-ScheduledTask -TaskName "KabuSys_Scheduler" | Get-ScheduledTaskInfo
Start-ScheduledTask -TaskName "KabuSys_Scheduler"
python scripts\run_scheduler.py --list
```

---

## 6. Streamlit ダッシュボード

```cmd
python -m streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

Home と 11 ページ（Initial Setup / Pre-Market / Execution Startup / Intraday Monitor / Signal Queue / Performance / Failure Recovery / WebManual / Strategy Lab / Process Monitor / Manual Trades）。手動運用で主に使うのは次のページ。

- `Manual Trades`（約定入力・手動ポジション（評価日の終値で評価）・売却候補・履歴）
- `Signal Queue`（翌営業日の候補・シグナル。参照専用）
- `Process Monitor`（夜間バッチの実行状況）
- `Strategy Lab`（市場レジーム・シグナル推移）

---

## 7. 成績レポート

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

> 手動運用の損益・保有は Streamlit **Manual Trades > 手動ポジション** と `manual_trades positions` で確認する。

---

## 8. 既知の問題（運用に影響するもの）

| Issue | 内容 | 運用上の扱い |
|---|---|---|
| #419 | AI 分析のスコアが出ていない（ニューススコア 0 件・レジーム常に neutral） | `ai_analysis` ジョブ自体は成功する。AI の影響がない状態で候補が出ていると理解する |
| #421 | シグナル 0 件の正常日に朝のレポートが「シグナルが古い」と誤警告する | 夜間バッチの成否は `logs\scheduler.log` と night_batch_report で確認する |
| #422 | `requirements.txt` / `constraints.txt` が Python 3.13 と非互換 | 運用 `.venv` は動作確認済みのバージョンを暫定的に入れている。`pip install -c constraints.txt -r requirements.txt` は失敗する |

---

## 9. 参考

- [W1_08 Paper Trading 4週間検証 Runbook](./W1_08_PaperTradingValidationRunbook.md)
- `documents/WebManual/C_ManualOrderOperation.md`（手動注文メイン運用の詳細）
- `documents/08_Operations/FailureRecovery.md`
- `documents/08_Operations/Monitoring.md`
- `documents/10_Runtime/RuntimeJobSchedule.md`
- `documents/WebManual/D_LiveOperation.md`

---

## 10. 自動執行モード（現在停止中）

この章は、kabuステーション API による自動執行を再開・検証する場合の手順。**現在は使っていない。**

### 10.1 再開のしかた

- `.env` を `ENABLE_AUTO_EXECUTION=true` にする（デーモンが次の起動時または日付変更時に再読込する。すぐ反映するには `KabuSys_Scheduler` を再起動する）
- kabuステーションの起動・ログインが必要
- 再開すると 08:30 `execution_start`、08:35 `position_reconciliation_report`、09:00 `monitoring_start` が実行される

> **自動執行でも、自動で発注されるのは BUY だけ。** `signal_queue` には BUY しか入らない（`scripts/run_portfolio_construction.py` のみが INSERT）。SELL は自動執行中も人が証券画面で発注する。監視・Kill Switch は未約定注文の取消のみで、保有の売却はしない。

> 執行は前営業日の `signal_queue`（pending の BUY）を読んで発注する。再開した朝は、前夜の queue がそのまま発注対象になる点に注意する。

### 10.2 Pre-Market（08:00〜08:35）

| 時刻 | ジョブ | 出力先 |
|------|--------|--------|
| 08:00 | `pre_market_report` | `artifacts/pre_market/{date}/report.md` |
| 08:02 | `signal_queue_report` | `artifacts/signal_queue/{date}/report.md`（`{date}` は queue の日付） |
| 08:35 | `position_reconciliation_report`（Execution 起動後・kabu API 必須） | `artifacts/position_reconciliation/{date}/report.json` |

確認項目:

- Windows PC が正常
- kabuステーションが起動済み・API 接続が正常
- `data/stop_requested.flag` が存在しない
- 前営業日の `signal_queue` に `pending` がある
- `KabuSys_Scheduler` が実行中
- DB と口座のポジション差分が許容範囲

判定（pre_market_report）:

- `READY`: 執行開始可
- `READY_WITH_WARNINGS`: 警告確認の上で開始判断（データ鮮度が古いなど）
- `BLOCKED`: 自動執行を開始しない（pending 0 件 / 停止フラグあり / スケジューラー未稼働）

手動再実行（再確認・デバッグ時）:

```cmd
python scripts\run_pre_market_report.py
python scripts\run_signal_queue_report.py
python scripts\run_position_reconciliation_report.py
```

**signal_queue に不要な pending がある場合:**

Streamlit の Signal Queue ページに表示される CLI コマンドをターミナルで実行する。

```cmd
:: 特定日付の pending をキャンセル
python scripts\cancel_signal_queue.py --date 2026-05-12

:: 銘柄コードで絞る場合
python scripts\cancel_signal_queue.py --date 2026-05-12 --code 7203

:: 全 pending をキャンセル（慎重に）
python scripts\cancel_signal_queue.py --all
```

### 10.3 Execution 起動（08:30）

スケジューラーが `start_system.py --component execution --clear-stop-flag` を実行する。手動で行う場合:

```cmd
python scripts\start_system.py --dry-run
python scripts\start_system.py --component execution
```

起動直後の確認:

- `data/execution.pid` が生成されている
- `orders_no_status = 0`（`> 0` は執行継続不可の扱い）
- `position_discrepancies` が許容範囲

補足:

- 前営業日の `signal_queue`（BUY のみ）を 08:50〜09:10 に発注する
- 各 queue 行の処理状態は SQLite の `signal_queue_status` に記録し、夜の `portfolio_construction` の冒頭で DuckDB に同期する
- 業務キー `{signal_date}_{code}_{side}` による二重発注防止がある
- `python -m kabusys.run_execution` 実行時に Execution Startup Summary が自動生成される（`artifacts/execution_startup/{date}/report.md`）

### 10.4 ザラ場監視（09:00-15:00）

見るもの:

- `execution_service` / `monitoring_service`
- 注文エラー・API エラー
- ドローダウン
- Kill Switch
- ポジション差分

主要コマンド:

```cmd
python -m kabusys.run_intraday_monitor --watch
```

```powershell
# 直近50行をリアルタイム表示（集約ファイル）
Get-Content logs\execution.log -Tail 50 -Wait

# 全ログからエラーを検索
Select-String -Path logs\*.log -Pattern "ERROR|CRITICAL"

# 今回の実行単位ログを特定して確認
Get-ChildItem logs\execution_*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

利用ページ（Streamlit）:

- `Home`（Kill Switch・プロセス状態・ドローダウン・エラーイベント）
- `Execution Startup`（起動直後のリコンシリエーション差分）
- `Intraday Monitor`（ザラ場監視・自動更新・Kill Switch 状態）
- `Signal Queue`（発注キュー・ポートフォリオ目標・シグナル）
- `Failure Recovery`（障害イベント集約・復旧ガイド）

### 10.5 自動執行中の障害対応

1. ログ確認
2. PID / stop flag / DB 状態確認
3. 必要なら Kill Switch（未約定注文の取消のみ。保有は売却しない）
4. 再起動前に reconciliation

停止:

```cmd
python scripts\stop_system.py
```

再開前確認:

```cmd
python scripts\start_system.py --dry-run
```

### 10.6 Market Close（15:00）

確認項目:

- `signal_queue` に未処理 `pending` がない（残っている場合は下記でキャンセル）
- `positions` が更新済み
- `portfolio_performance` に当日分が記録済み

```cmd
python -m kabusys.run_market_close_report --save
python -m kabusys.run_performance_report --type daily --save
```

当日 pending が残っている場合 / cancelled レコードの定期掃除:

```cmd
python scripts\cancel_signal_queue.py --date 2026-05-12
python scripts\cancel_signal_queue.py --delete-cancelled
```

判定:

- `OK`: 夜間バッチへ進行可
- `BLOCKED`: warning 解消まで進めない

出力先:

- `artifacts/market_close/{date}/report.md`
- `artifacts/performance/live/daily/{date}/report.md`

Paper の E2E 検証は `documents/WebManual/C_PaperTrading.md` と [W1_08 Paper Trading 4週間検証 Runbook](./W1_08_PaperTradingValidationRunbook.md) を参照。
