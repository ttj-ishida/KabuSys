# D. 本番運用 — WebManual

- **対象**: KabuSys を日々運用する担当者
- **現在の運用方式**: **手動注文メイン**。前日夜・当日朝に候補を確認し、証券会社の画面から人が発注する
- **自動執行**: 停止中（`.env` の `ENABLE_AUTO_EXECUTION=false`）。再開する場合は [D-10. 自動執行を再開する場合](#d-10-自動執行を再開する場合) を参照

> ⚠️ **自動売却の機能はありません。** SELL は `signals` テーブル・LINE・売却候補（`manual_action_queue`）に出るだけです。`signal_queue` には BUY しか入らないため、自動執行を再開した場合でも自動で発注されるのは BUY だけです。監視・Kill Switch は未約定注文の取消のみで、保有の売却はしません。売却は常に人が証券画面で行います。

---

## D-1. 運用前チェック（手動運用）

- 運用フォルダ `C:\Projects\KabuSys` で作業する（開発フォルダとは別。DB・ログ・artifacts・`.env` は運用フォルダ側にある）
- `python -m kabusys.validate_config` がエラーなく完了する
- `.env` の手動運用関連の値を確認する

| キー | 値（現在の運用） | 意味 |
|---|---|---|
| `MANUAL_TRADING_ENABLED` | `true` | 手動保有を SELL 判定・BUY 株数計算・資金計算に含める |
| `MANUAL_TRADING_INITIAL_CASH` | `1000000` | 手動運用の元手（円） |
| `ENABLE_AUTO_EXECUTION` | `false` | 08:30 / 08:35 / 09:00 の自動執行系ジョブを実行しない |
| `LINE_NOTIFY_ENABLED` | `true` | 夜 LINE・朝 LINE を送る |
| `KABUSYS_ENV` | `paper_trading` | 現在の設定値（手動運用では発注しないため変更していない） |

- スケジューラー `KabuSys_Scheduler` が実行中であること

```powershell
Get-ScheduledTask -TaskName "KabuSys_Scheduler" | Get-ScheduledTaskInfo
python scripts\run_scheduler.py --list
```

- 手動注文メイン運用では、kabuステーションの起動は不要
- `config/risk_config.yaml` のドローダウン上限・ポジション上限を確認

---

## D-2. 1日の流れ（手動運用）

| 時刻 | 処理 | 実行方式 | スクリプト / コマンド |
|------|------|----------|-----------------------|
| 15:35 | TDnet 適時開示収集（`ENABLE_TDNET=true`） | 自動 | `scripts/run_tdnet_collection.py` |
| 17:30 | 市場データ更新 | 自動 | `scripts/run_data_update.py` |
| 17:33 | Yahoo News 収集（`ENABLE_YAHOONEWS=true`） | 自動 | `scripts/run_yahoonews_collection.py` |
| 18:30 | 特徴量計算 | 自動 | `scripts/run_feature_gen.py` |
| 19:00 | AI 分析（`ENABLE_AI_SENTIMENT=true`。現在スコアが出ていない：Issue #419） | 自動 | `scripts/run_ai_analysis.py` |
| 20:00 | 売買シグナル生成（手動保有の売却候補も記録） | 自動 | `scripts/run_strategy_signal.py` |
| 21:00 | ポートフォリオ構築・**夜 LINE** | 自動 | `scripts/run_portfolio_construction.py` |
| 21:10 | 手動注文候補レポート（夜） | 自動 | `scripts/run_manual_order_report.py --phase evening` |
| 21:15 | 夜間バッチ結果レポート | 自動 | `scripts/run_night_batch_report.py` |
| 21:30 頃 | 夜 LINE・夜間バッチ結果の確認 | **手動** | LINE / `artifacts/reports/{date}/report.md` |
| 08:00 | Pre-Market レポート（自動執行の可否判定） | 自動 | `scripts/run_pre_market_report.py` |
| 08:02 | Signal Queue レポート | 自動 | `scripts/run_signal_queue_report.py` |
| 08:05 | 手動注文候補レポート（朝）・**朝 LINE** | 自動 | `scripts/run_manual_order_report.py --phase morning` |
| 08:05〜寄り付き | 朝のレポート確認・手動発注 | **手動** | 証券会社画面 |
| 約定後 | 約定の入力 | **手動** | `python -m kabusys.manual_trades` / Streamlit Manual Trades |
| 随時 | 売却候補への対応 | **手動** | 証券会社画面 / Streamlit Manual Trades |

非営業日（土日・祝日・年末年始）はすべての自動ジョブがスキップされます。

---

## D-3. 夜の確認（21:00〜21:30）

- **夜 LINE（21:00）**: 翌営業日の BUY / SELL。手動保有の銘柄は `[手動保有]`、保有中の銘柄の BUY は不足分だけ `[買い増し]`
- **夜のレポート（21:10）**: `artifacts/manual_orders/{date}/evening.md`（LINE なし）
- **夜間バッチ結果（21:15）**: `artifacts/reports/{date}/report.md` / `summary.json` / `warnings.json`

**Night Batch レポートの判定:**

| 判定 | 意味 | 手動運用での対応 |
|------|------|------|
| `READY` | 全必須ジョブ成功・`signal_queue` 作成済み | 翌朝のレポートどおりに進める |
| `READY_WITH_WARNINGS` | 警告あり・翌日準備は完了 | 内容確認の上で判断 |
| `BLOCKED` | 必須ジョブ失敗 / `signal_queue == 0` / 価格・特徴量未生成 | ジョブ失敗なら復旧する。ジョブがすべて成功していて BUY が 0 件なだけなら正常 |

手動で再生成する場合:

```powershell
python scripts/run_night_batch_report.py
```

ジョブの成否はスケジューラーのログでも確認できます（失敗は `REQUIRES ATTENTION: ジョブ失敗`）。

```powershell
Select-String -Path logs\scheduler.log -Pattern "REQUIRES ATTENTION|ジョブ完了" | Select-Object -Last 20
```

---

## D-4. 朝の確認と手動注文（08:05〜寄り付き）

08:05 に朝のレポート `artifacts/manual_orders/{date}/morning.md` が作られ、LINE「【KabuSys 手動注文 当日朝】」が届きます。

**ステータス:**

| ステータス | 意味 | 対応 |
|------|------|------|
| `OK` | 警告なし | BUY 表・SELL 表を見て注文を検討 |
| `警告あり` | 警告あり | 警告を確認してから判断 |
| `BUY 見送り` | 停止フラグ・DD 停止・休場日・シグナルが古い | BUY は全件見送り候補へ。SELL は常に表示されるので対応する |

> **既知の誤警告（Issue #421）:** シグナル 0 件の正常な日でも「シグナルが古い」と出ます。夜間バッチの成否は `logs\scheduler.log` と night_batch_report で確認してください。

**BUY 表:** コード・銘柄名・株数・参考価格（前日終値）・想定金額・スコア・「この価格以下なら買付可（上限）」・「この価格以上なら買付可（下限）」・備考（新規／買い増し）。

**見送りルール:** 寄り付きが前日終値比 +5% 超 / −3% 以下なら見送り。寄り前の気配は取得しないため、寄り付き価格と上限・下限を見比べます（下限以上・上限以下なら買付可）。

> 08:00 の Pre-Market レポートは**自動執行を開始してよいか**の判定です。手動運用中は `BLOCKED` でも問題ありません（BUY 候補 0 件の日などに `BLOCKED` になる）。

手動で再実行したい場合:

```powershell
python scripts/run_manual_order_report.py --phase morning
python scripts/run_pre_market_report.py
python scripts/run_signal_queue_report.py
```

詳細な読み方は [A_OperationsCycle.md](./A_OperationsCycle.md) の「3.2 朝（08:05〜）: 朝のレポートを読む」を参照してください。

---

## D-5. 約定の入力

約定したら、運用フォルダで約定を KabuSys に登録します。銘柄コードは 5 桁（例: `72030`）です。

| 項目 | 内容 |
|------|------|
| `--date` | 約定日 |
| `--code` | 銘柄コード（5 桁） |
| `--side` | `buy` / `sell` |
| `--qty` | 約定数量 |
| `--price` | 約定単価 |
| `--fees` | 手数料・諸経費（既定 0） |
| `--source-signal-id` | 対応する Signal Queue ID（分かる場合・任意） |
| `--note` | メモ（任意） |

確認だけ行う場合（`--apply` なしでは保存しない）:

```powershell
.venv\Scripts\python.exe -m kabusys.manual_trades add --date 2026-10-15 --code 44770 --side buy --qty 100 --price 387 --fees 0
```

DB に保存する場合:

```powershell
.venv\Scripts\python.exe -m kabusys.manual_trades add --date 2026-10-15 --code 44770 --side buy --qty 100 --price 387 --fees 0 --apply
```

対話式で入力する場合:

```powershell
.venv\Scripts\python.exe -m kabusys.manual_trades wizard
```

確認・保有・削除:

```powershell
.venv\Scripts\python.exe -m kabusys.manual_trades list --date 2026-10-15
.venv\Scripts\python.exe -m kabusys.manual_trades positions --date 2026-10-15
.venv\Scripts\python.exe -m kabusys.manual_trades delete <trade_id>
```

- 同日・同銘柄・同売買の 2 件目以降は ID に `_2`、`_3`… が付く
- 全く同じ内容を 2 回入れると重複エラー（意図的なら `--allow-duplicate`）
- 保有を超える売却はエラー（記録開始前から持っていた株などは `--allow-oversell`）
- `--force` は非推奨（`--allow-duplicate` と同じ。上書きはしない）
- 夜間バッチ中（17:30〜21:20 頃）は DuckDB が排他利用されるため、入力は避ける

Streamlit では **Manual Trades** ページ（入力／手動ポジション／売却候補／履歴）で入力・確認できます。

---

## D-6. 売却候補への対応

手動保有にも自動売買と同じ SELL ルール（損切り・トレーリングストップ・保有期限・スコア低下・決算回避）が適用され、20:00 の `strategy_signal` で売却候補として記録されます。

1. 証券画面で売却する
2. 約定を `--side sell` で入力する
3. Streamlit **Manual Trades > 売却候補** で「対応済み」にする（売らない場合は「見送り」）

---

## D-7. Streamlit ダッシュボード

```powershell
python -m streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

> ⚠️ Streamlit はターミナルを占有します。他のスクリプトを実行する場合は新しいターミナルを開いて `.venv\Scripts\Activate.ps1` を有効化してください。

**手動運用で使うページ:**

| ページ | 確認内容 |
|--------|---------|
| `Manual Trades` | 約定入力・手動ポジション（評価日の終値で評価）・売却候補・履歴 |
| `Signal Queue` | 翌営業日の BUY 候補・シグナル（**参照専用**） |
| `Process Monitor` | 夜間バッチの実行状況 |
| `Strategy Lab` | 市場レジーム・シグナル推移 |

---

## D-8. 成績レポート（手動）

```powershell
python -m kabusys.run_performance_report --type daily --save
python -m kabusys.run_performance_report --type weekly --save
python -m kabusys.run_performance_report --type monthly --save
```

**保存先:**
- `artifacts/performance/{env}/daily/...`
- `artifacts/performance/{env}/weekly/...`
- `artifacts/performance/{env}/monthly/...`

> 手動保有の損益は Streamlit **Manual Trades > 手動ポジション** と `manual_trades positions` で確認します。

---

## D-9. 異常時

1. `logs\scheduler.log` で失敗したジョブを特定する
2. `logs\<job_name>.log` でエラー内容を確認する
3. 原因を解消して再実行する。翌朝に復旧する場合は `--date <前営業日>` を付ける

```powershell
python scripts\run_strategy_signal.py --date 2026-10-16
python scripts\run_portfolio_construction.py --date 2026-10-16
python scripts\run_manual_order_report.py --phase morning
```

スケジューラーが止まっている場合:

```powershell
Start-ScheduledTask -TaskName "KabuSys_Scheduler"
```

詳細は [E_FailureRecovery.md](./E_FailureRecovery.md) を参照。

---

## D-10. 自動執行を再開する場合

**現在は停止中です。** 以下は再開・検証する場合の手順です。

### D-10-1. 再開前チェック

- `.env` を `ENABLE_AUTO_EXECUTION=true` にする（デーモンが次の起動時または日付変更時に再読込する。すぐ反映するには `KabuSys_Scheduler` を再起動する）
- 本番では `.env` の `KABUSYS_ENV=live` を確認し、`python -m kabusys.validate_config` がエラーなく完了すること
- kabuステーション（本番ポート 18080）が起動・ログイン済みで API 接続できること
- `config/risk_config.yaml` のドローダウン上限・ポジション上限を確認
- 前夜の `signal_queue`（pending の BUY）が翌朝の発注対象になることを理解しておく。不要なら `scripts\cancel_signal_queue.py` でキャンセルする

> 自動執行でも自動で発注されるのは **BUY だけ** です。SELL は引き続き人が証券画面で発注します。

### D-10-2. 再開後に追加で動くジョブ

| 時刻 | ジョブ | スクリプト / コマンド |
|------|------|-----------------------|
| 08:30 | `execution_start` | `scripts/start_system.py --component execution --clear-stop-flag` |
| 08:35 | `position_reconciliation_report`（kabu API 必須） | `scripts/run_position_reconciliation_report.py` |
| 09:00 | `monitoring_start` | `scripts/start_system.py --component monitoring` |

- 執行は前営業日の `signal_queue`（BUY のみ）を 08:50〜09:10 に発注する
- ステータスは SQLite の `signal_queue_status` に記録し、夜の `portfolio_construction` の冒頭で DuckDB に同期する
- 業務キー `{signal_date}_{code}_{side}` による二重発注防止がある

**Pre-Market レポートの判定（自動執行時）:**

| 判定 | 意味 | 対応 |
|------|------|------|
| `READY` | 執行開始可 | そのまま執行 |
| `READY_WITH_WARNINGS` | 警告あり（データ鮮度など） | 内容を確認し、必要なら停止 |
| `BLOCKED` | pending 0 件 / 停止フラグ / スケジューラー未稼働 | 原因を解消するまで執行しない |

### D-10-3. Execution の手動起動・確認

```powershell
# ドライラン（発注しない起動確認）
python scripts\start_system.py --dry-run

# 本起動
python scripts\start_system.py --component execution
```

起動時に Execution Startup Summary が自動保存されます（`artifacts/execution_startup/{date}/report.md`）。

> `orders_no_status > 0` は執行継続不可の扱いにする。

### D-10-4. ザラ場監視（09:00〜15:00）

```powershell
python -m kabusys.run_intraday_monitor --watch
```

| ページ | 確認内容 |
|--------|---------|
| `Home` | Kill Switch 状態・プロセス状態・ドローダウン・エラーイベント |
| `Pre-Market` | READY/BLOCKED 判定・データ鮮度 |
| `Execution Startup` | 起動直後のリコンシリエーション差分 |
| `Intraday Monitor` | ザラ場監視・Kill Switch 状態（自動更新） |
| `Signal Queue` | 発注キュー・シグナル（**参照専用**。操作は CLI で） |
| `Performance` | エクイティカーブ・ポジション・取引履歴 |
| `Failure Recovery` | 障害イベント集約・復旧ガイド |

### D-10-5. 引け後の確認（15:00 手動）

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

### D-10-6. 停止

```powershell
python scripts\stop_system.py
```

再開前の確認:

```powershell
python scripts\start_system.py --dry-run
```

Paper での E2E 検証は [C_PaperTrading.md](./C_PaperTrading.md) と `documents/08_Operations/W1_08_PaperTradingValidationRunbook.md` を参照してください。

---

## D-11. スケジューラーについて（参考）

運用はスケジューラーデーモン方式（Windows タスク `KabuSys_Scheduler`、ログオン時に `scripts\run_scheduler.py` を常駐起動）です。登録は `powershell -File scripts\setup_scheduler_daemon.ps1` で行います。

個別タスク方式（`scripts\setup_task_scheduler.ps1` で `KabuSys_DataUpdate` などを個別登録）は従来方式で、現在は使っていません。個別タスク方式は `ENABLE_AUTO_EXECUTION` を参照しないため、手動運用中に使うと 08:30 の Execution 起動なども登録されます。

> EDINET 法定開示収集（`run_edinet_collection.py`）と開示分類（`run_disclosure_classification.py`）は、どちらの方式でもスケジュール登録されていません。必要な場合は手動で実行します。

---

## 関連ドキュメント

- [A_OperationsCycle.md](./A_OperationsCycle.md) — 日次運用サイクルの概要
- [C_ManualOrderOperation.md](./C_ManualOrderOperation.md) — 手動注文メイン運用の詳細
- [C_PaperTrading.md](./C_PaperTrading.md) — ペーパートレード手順
- [E_FailureRecovery.md](./E_FailureRecovery.md) — 障害復旧手順
- `documents/08_Operations/TradingRunbook.md` — 詳細な運用手順書
