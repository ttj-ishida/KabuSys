# E. 障害時の対応 — WebManual

- **対象**: KabuSys の運用中に異常が発生した際の対応手順
- **想定読者**: 運用者・管理者
- **目的**: 異常が起きたときに、原因を素早く特定し、安全に復旧できるようにする

> **基本方針: 迷ったら止める**
> 原因がわからない・確信が持てない場合は、まず `python scripts\stop_system.py` で安全停止してから調査してください。

---

## E-1. 障害の種類と優先度

| 種類 | 内容 | 優先度 | 対応セクション |
|---|---|---|---|
| PC停止・OS障害・強制再起動 | Windows 障害・電源断 | 🔴 最高 | [E-4. PC 再起動後の復旧](#e-4-pc-再起動後の復旧) |
| kabuステーション API 接続断 | API から応答なし | 🔴 最高 | [E-3. API 接続障害](#e-3-api-接続障害) |
| Kill Switch 発動 | ドローダウン超過・連続エラー | 🔴 最高 | [E-2. 緊急停止と復旧](#e-2-緊急停止kill-switchと復旧) |
| ポジション不整合 | DB と口座の保有株が一致しない | 🟡 高 | [E-5. ポジション不整合の復旧](#e-5-ポジション不整合の復旧) |
| Signal Queue 破損 | シグナルが正常に読めない | 🟡 高 | [E-6. Signal Queue の再生成](#e-6-signal-queue-の再生成) |
| 夜間バッチ失敗 | バッチが途中で止まった | 🟡 高 | [E-7. 夜間バッチ失敗時の手動再実行](#e-7-夜間バッチ失敗時の手動再実行) |
| Monitoring プロセス停止 | 監視が止まっているが発注は継続 | 🟢 中 | [E-8. その他の障害](#e-8-その他の障害) |
| ダッシュボード黄色警告 | バッチ・エンジン実行中に DB ロック | 🟢 低（正常動作） | [E-9. DB ロック中の警告表示について](#e-9-db-ロック中の警告表示について) |

---

## E-2. 緊急停止（Kill Switch）と復旧

### 自動で Kill Switch が発動する条件

以下の状態を Execution Engine が検知すると、**自動的に全発注を停止**します。

- 最大ドローダウン（`risk_config.yaml` の `max_drawdown`）を超過した
- API 接続断が続いてサーキットブレーカーが発動した
- 連続エラーが設定回数（`circuit_breaker_errors`）を超えた

ログに以下が出力されます：
```
CRITICAL Kill Switch 発動 — reason=...
```

### 手動で今すぐ停止したい場合

```cmd
python scripts\stop_system.py
```

これにより `data\stop_requested.flag` が作成され、Execution / Monitoring が安全に終了します（最大 10 秒）。

### Kill Switch 発動後の確認手順

```
1. kabuステーション の画面でポジション・未約定注文を直接確認する

2. ログで発動原因を確認する
   Select-String -Path logs\execution.log -Pattern "CRITICAL|Kill Switch"

3. --dry-run で DB 状態を確認する（発注なし）
   python scripts\start_system.py --dry-run

4. 原因が解消したら以下の手順で再起動する
```

### 復旧して再起動する手順

```cmd
:: 発注なしの状態確認（推奨）
python scripts\start_system.py --dry-run

:: 停止フラグを解除して再起動
python scripts\start_system.py --clear-stop-flag
```

> ⚠️ **当日中の再開は慎重に。** 原因が解消されていない場合、同じ状況が繰り返されます。翌日以降に再開することを推奨します。

| DD の状態 | 対応 |
|---|---|
| `max_drawdown` 以内に回復している | 再開可能 |
| `max_drawdown` を超えたまま | 翌日以降まで待機 |
| 原因が特定・解消済み | 再開可能 |
| 原因が不明 | 再開しない（調査優先） |

---

## E-3. API 接続障害

### 症状

- kabuステーション から応答なし
- ログに `ConnectionError` / `TimeoutError` / `CIRCUIT_BREAKER_OPEN` が出力されている

### 対応手順

```
1. kabuステーション の画面を確認する
   → ログイン状態・接続状態のアイコンが緑色か確認

2. kabuステーション を再起動する
   → タスクバーのアイコンから「終了」→ 再起動

3. API の自動再接続を待つ（数分）
   → ExecutionEngine は自動でリトライする

4. それでも接続できない場合
   → python scripts\stop_system.py でシステムを停止する
   → auカブコム証券の公式サイト・SNSで障害情報を確認する

5. 接続が回復したら
   → python scripts\start_system.py --clear-stop-flag で再起動
```

---

## E-4. PC 再起動後の復旧

### 症状

Windows の自動更新・電源障害・OS クラッシュなどで PC が予期せず再起動された。

### 復旧手順

```
1. PC 起動後、kabuステーション を起動してログインする

2. 停止フラグを確認する
   → data\stop_requested.flag が存在する場合は削除する
   （または start_system.py 起動時に --clear-stop-flag を指定すると自動削除される）

3. Execution を起動する（リコンシリエーション自動実行）
   python scripts\start_system.py --component execution

   ※ 起動時に以下が自動実行される（冪等）：
   - 状態不明（status='sent'）の注文をブローカー API と突合
   - 約定済み → status='filled' に更新
   - キャンセル済み → status='cancelled' に更新
   - ポジション差分をログに記録

4. リコンシリエーション結果をログで確認する
   → orders_no_status > 0 または position_discrepancies > 0 が出た場合は
     [E-5. ポジション不整合の復旧](#e-5-ポジション不整合の復旧) を参照

5. Monitoring を起動する
   python scripts\start_system.py --component monitoring
```

> ⚠️ **市場時間中（前場 09:00〜11:30 / 後場 12:30〜15:00）の再起動は特に注意。**
> Signal Queue に `pending` シグナルが残っている場合、起動後に即時発注が開始されます。
> 発注させたくない場合は先に Signal Queue を確認し、必要なら [E-6. Signal Queue の再生成](#e-6-signal-queue-の再生成) でリセットしてください。

---

## E-5. ポジション不整合の復旧

### 症状

- ログに `position_discrepancies > 0` が出力されている
- DB の `positions` テーブルと kabuステーション の口座ポジションが一致しない

### 差分の種類（DiscrepancyKind）

差分ログには `kind` フィールドが含まれる。対応方針はそれぞれ異なる。

| kind | 意味 | 対応 |
|------|------|------|
| `CLOSED_STATE_CONSTRAINT` | `Filled→Closed` 遷移未実装による既知差分（`broker_qty==0, local_qty>0`） | 対応不要。正常運用中に発生する既知の状態 |
| `AMOUNT_MISMATCH` | 数量が一致しない（真の異常の可能性） | 下記対応手順に従い調査・修正する |

`CLOSED_STATE_CONSTRAINT` のみの場合はポジション修正不要。`AMOUNT_MISMATCH` が含まれる場合のみ以下の対応手順を実施する。

### 対応手順

```
1. Execution を停止する
   python scripts\stop_system.py

2. kabuステーション の画面で実際のポジションを確認する
   → 銘柄・数量・平均取得単価を記録する

3. DB の positions テーブルを確認する
   duckdb data\kabusys.duckdb "SELECT * FROM positions ORDER BY code"

4. 差分の原因を特定する
   ├─ 約定処理の漏れ → orders テーブル（SQLite）を確認
   └─ 手動取引による差分 → 手動で DB を修正

5. DB を修正する前にバックアップを取る
   copy data\kabusys.duckdb data\backup\kabusys_YYYYMMDD.duckdb

6. positions テーブルを修正する（DuckDB CLI または Python）

7. ポートフォリオ目標を再計算する
   python scripts\run_portfolio_construction.py

8. Execution を再起動する
   python scripts\start_system.py --component execution

9. リコンシリエーション結果を確認する
   → ログの position_discrepancies = 0 になっていること
```

---

## E-6. Signal Queue の再生成

### 症状

- `signal_queue` の読み込みエラーが発生している
- `pending` シグナルの件数が異常に多い・少ない

### 対応手順

**軽症（特定日・銘柄の pending が誤っているだけ）:**

```
1. 対象を絞ってキャンセルする（Execution が停止していること）
   python scripts\cancel_signal_queue.py --date 2026-05-12
   python scripts\cancel_signal_queue.py --date 2026-05-12 --code 7203

2. 夜間バッチを手動で再実行する（必要な場合のみ）
   python scripts\run_strategy_signal.py
   python scripts\run_portfolio_construction.py

3. シグナルが生成されたことを確認する
   python -m kabusys.run_signal_queue_report
```

**重症（全件リセットが必要な場合）:**

```
1. Execution を停止する（起動中の場合）
   python scripts\stop_system.py

2. Signal Queue をリセットする（取引時間外に実施すること）
   python scripts\reset_signals.py
   ※ signal_queue テーブルが全削除される（取り消し不可）

3. 夜間バッチを手動で再実行する（順番通りに）
   python scripts\run_strategy_signal.py
   python scripts\run_portfolio_construction.py

4. シグナルが生成されたことを確認する
   python -m kabusys.run_signal_queue_report
   → pending が存在すれば OK

5. Execution を再起動する
   python scripts\start_system.py --component execution
```

**cancelled レコードが大量に蓄積している場合（定期掃除）:**

```
python scripts\cancel_signal_queue.py --delete-cancelled
```

> Streamlit の Signal Queue ページはこれらの CLI コマンドを動的に表示する（参照専用）。

---

## E-7. 夜間バッチ失敗時の手動再実行

### 症状

- Task Scheduler の `LastTaskResult` が `0` 以外になっている
- 翌朝の Signal Queue に `pending` シグナルがない

### Task Scheduler の実行結果確認

```powershell
Get-ScheduledTask -TaskName "KabuSys_*" | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, LastTaskResult
```

### 失敗したジョブのログを確認する

各バッチスクリプトは起動ごとに `logs/<app_name>_YYYYMMDD_HHMMSS_<PID>.log` を生成します。  
Task Scheduler で失敗した実行は、最新の実行単位ログファイルで原因を確認できます。

```powershell
# 失敗したジョブの実行単位ログを特定する（例: data_update）
Get-ChildItem logs\data_update_*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content

# 全集約ログから ERROR / CRITICAL を横断検索する
Select-String -Path logs\*.log -Pattern "ERROR|CRITICAL"
```

### 手動再実行（依存関係の順番どおりに実行）

```cmd
python scripts\run_data_update.py
python scripts\run_feature_gen.py
python scripts\run_ai_analysis.py
python scripts\run_strategy_signal.py
python scripts\run_portfolio_construction.py
```

> AI 分析（`run_ai_analysis.py`）は `ENABLE_AI_SENTIMENT=false` の場合は省略可能です。

---

## E-8. その他の障害

### 注文エラー（`rejected` 注文）が多発する場合

```cmd
:: 対象銘柄のシグナルを手動で失敗扱いに更新する
python scripts\mark_signal_failed.py --code 7203

:: 日付を指定する場合
python scripts\mark_signal_failed.py --code 7203 --date 2026-05-05
```

### Monitoring プロセスが停止している場合

```cmd
python scripts\start_system.py --component monitoring
```

> Monitoring は発注に関与しないため、停止中も Execution は継続動作します。

### 特徴量データが壊れている場合

```cmd
python scripts\rebuild_features.py
```
`prices_daily` を元に特徴量を全再計算します。

---

## E-9. DB ロック中の警告表示について

### 症状

Signal Queue・Performance・Strategy Lab ページに以下の黄色の警告が表示される。

> ⚙️ バッチまたは執行エンジンが DB を使用中のため、データを一時的に表示できません。しばらく待ってから 🔄 Refresh してください。

### 原因と対応

**これは障害ではありません。** ExecutionEngine（08:30〜15:00）または夜間バッチ（17:30〜21:15）が DuckDB を read-write で開いている間、ダッシュボードが一時的に接続できない状態です。

| タイミング | 対応 |
|---|---|
| バッチ・エンジン実行中 | 終了まで待ってから **🔄 Refresh** |
| 実行時間外でも表示される | 下記の確認手順へ |

### 実行時間外でも警告が消えない場合

DuckDB ファイルが何らかの理由でロックされたままになっている可能性があります。

```powershell
# DuckDB ファイルを開いているプロセスを確認
Get-Process python | Where-Object { $_.MainWindowTitle -ne "" }

# または lsof 相当（handle.exe が使える環境の場合）
# handle.exe kabusys.duckdb
```

プロセスが残存している場合はタスクマネージャーまたは `Stop-Process` で終了してから再試行してください。

---

## E-10. 復旧確認チェックリスト

復旧後は以下をすべて確認してから通常運用に戻ります。

| 確認項目 | 確認内容 | OK |
|---|---|---|
| 停止フラグ | `data\stop_requested.flag` が存在しない | ☐ |
| PID ファイル | `data\execution.pid` が存在・プロセス生存 | ☐ |
| API 接続 | kabuステーション の接続状態 = 正常（アイコン緑） | ☐ |
| ポジション整合 | DB（DuckDB）と口座のポジションが一致 | ☐ |
| Signal Queue | 必要なシグナルが `pending` 状態で存在 | ☐ |
| 未処理注文 | `status='sent'` で長時間放置の注文がない | ☐ |
| ログ | `ERROR` / `CRITICAL` メッセージが解消されている | ☐ |

---

## 関連ドキュメント

- `documents/08_Operations/FailureRecovery.md` — 障害対応の詳細設計（エンジニア向け完全版）
- `documents/08_Operations/TradingRunbook.md` — 日次運用手順
- [D_LiveOperation.md](./D_LiveOperation.md) — 本番運用の日次手順
