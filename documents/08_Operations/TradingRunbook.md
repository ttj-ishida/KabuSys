# TradingRunbook.md

## 1. 目的

本ドキュメントは、日本株自動売買システムの **日次運用手順（Trading Runbook）** を定義する。

目的:

- 日々の運用作業の標準化
- 手動確認ポイントの整理
- アラート発生時の対応フローの明確化
- 安定した自動売買運用

対象環境:

- Single Windows PC（KabuSys 稼働ノード）
- Python 自動売買システム
- kabuステーション API
- J-Quants データ

---

## 2. 日次運用タイムライン

```
07:50  PC・kabuステーション起動確認
08:00  Pre-Market Checklist（手動確認）
08:30  Execution 起動（Task Scheduler 自動）
09:00  Monitoring 起動（Task Scheduler 自動） / 前場オープン
09:00-11:30  前場取引監視
11:30-12:30  昼休み（注文受付停止）
12:30-15:00  後場取引監視
15:00  市場クローズ（現物株）/ Market Close 確認
15:30  data_update バッチ（Task Scheduler 自動）
16:00  feature_gen バッチ（Task Scheduler 自動）
18:00  ai_analysis バッチ（Task Scheduler 自動）
20:00  strategy_signal バッチ（Task Scheduler 自動）
21:00  portfolio_construction バッチ（Task Scheduler 自動）
21:30  夜間バッチ結果確認（手動）
```

---

## 3. Pre-Market Checklist（08:00）

市場オープン前に以下を確認する。

| 項目 | 確認内容 | 確認方法 |
|------|---------|---------|
| PC 状態 | Windows 稼働・スリープ解除済み | 目視 |
| kabuステーション | 起動・ログイン済み | 画面確認 |
| API 接続 | kabuステーション API 応答あり | kabuステーション 画面の接続状態 |
| J-Quants データ | 前日分データが DuckDB に入っていること | `data_update` バッチのログ確認 |
| Signal Queue | 本日の `pending` シグナルが存在すること | SQLite / DuckDB 確認 |
| ポジション | DB のポジションと証券口座が一致していること | kabuステーション ポジション画面と比較 |
| 停止フラグ | `data/stop_requested.flag` が存在しないこと | エクスプローラーで確認 |
| Task Scheduler | KabuSys_* タスクが `Ready` 状態であること | タスクスケジューラ画面 |

**ポジション確認コマンド（手動実行）:**

```powershell
Get-ScheduledTask -TaskName "KabuSys_*" | Select-Object TaskName, State
```

問題があれば Execution 起動前に解消すること。

---

## 4. Execution 起動（08:30）

Task Scheduler が自動実行する。手動起動が必要な場合は以下を使用する。

**手動起動:**

```cmd
cd C:\path\to\KabuSys
python scripts\start_system.py --component execution
```

**両コンポーネント一括起動:**

```cmd
python scripts\start_system.py
```

**起動確認:**

```cmd
# PID ファイルが作成されていることを確認
type data\execution.pid
```

起動時の自動処理（`run_execution.py` 内）:

1. 停止フラグ（`data/stop_requested.flag`）が存在しない場合のみ起動
2. 自動リコンシリエーション実行
   - `OrderSent` 状態の注文をブローカーと突合・同期
   - ポジション差分をログに記録
3. Signal Queue の `pending` シグナルを読み込み発注開始

> `orders_no_status > 0` または `position_discrepancies > 0` がログに出た場合は手動確認を実施すること。  
> 詳細: `FailureRecovery.md` §5「PC 再起動後のリコンシリエーション」

**手動停止（緊急時）:**

```cmd
python scripts\stop_system.py
```

---

## 5. 市場中の監視（前場 09:00-11:30 / 後場 12:30-15:00）

> **TSE 現物株の取引時間**: 前場 09:00-11:30、後場 12:30-15:00。昼休み（11:30-12:30）は注文受付停止。15:00 以降は API での新規発注不可。

### 5.1 システム処理（自動）

- シグナル取得・発注（前場・後場）
- 約定確認・ポジション更新
- リスクチェック（ドローダウン監視）
- Kill Switch 判定（DD 上限超過 / API 断絶）

### 5.2 監視項目

| 項目 | 監視内容 | 判断基準 |
|------|---------|---------|
| 注文エラー | `rejected` 注文の有無 | 3 件以上連続で手動確認 |
| API 接続 | kabuステーション 接続状態 | 5 分以上切断で手動対応 |
| ドローダウン | 日次 DD | 10% 超過で Kill Switch 検討 |
| Execution プロセス | PID ファイル存在確認 | `data/execution.pid` が消えたら再起動 |
| Monitoring プロセス | PID ファイル存在確認 | `data/monitoring.pid` が消えたら再起動 |

### 5.3 ログ確認

ログは標準出力（Task Scheduler 経由では Windows イベントログ）に出力される。  
`logging.basicConfig` で `%(asctime)s %(levelname)s %(message)s` 形式。

主要なログキーワード:

| キーワード | 意味 |
|-----------|------|
| `停止フラグを検知` | グレースフル停止が開始された |
| `Kill Switch` | 緊急停止が発動された |
| `position_discrepancies` | ポジション不整合が検出された |
| `orders_no_status` | 状態不明の注文がある（リコンシリエーション要） |
| `CIRCUIT_BREAKER_OPEN` | サーキットブレーカが発動 |
| `ERROR` / `CRITICAL` | 即時確認が必要 |

---

## 6. アラート対応フロー

### 6.1 アラートの種類と優先度

| アラート | 優先度 | 初動対応 |
|---------|--------|---------|
| Max Drawdown 超過 | 🔴 最高 | 即時 Kill Switch → 手動確認 |
| API 接続断 | 🔴 最高 | kabuステーション 再起動 → 再接続確認 |
| Execution プロセス停止 | 🔴 高 | `start_system.py --component execution` |
| `rejected` 注文多発 | 🟡 中 | 注文ログ確認 → 原因特定 |
| Night Batch 失敗 | 🟡 中 | ログ確認 → 手動再実行 |
| Signal Queue 空 | 🟡 中 | `portfolio_construction` バッチ再実行 |
| Monitoring プロセス停止 | 🟢 低 | `start_system.py --component monitoring` |

### 6.2 共通対応フロー

```
1. ログ確認
   └─ ERROR / CRITICAL メッセージを特定

2. 状態確認
   ├─ PID ファイル確認（data/*.pid）
   ├─ 停止フラグ確認（data/stop_requested.flag）
   └─ DB 整合性（signal_queue, positions）

3. 判断
   ├─ 軽微 → ログに記録して継続監視
   ├─ 中程度 → 該当コンポーネント再起動
   └─ 重大 → Kill Switch 発動（§8 参照）

4. 復旧後確認
   └─ FailureRecovery.md §11「復旧確認チェックリスト」に従う
```

---

## 7. Market Close 確認（15:00）

市場クローズ後に以下を確認する。

| 項目 | 確認内容 |
|------|---------|
| 未約定注文 | `signal_queue` に `pending` が残っていないか |
| ポジション更新 | `positions` テーブルが最新状態か |
| 日次損益 | `portfolio_performance` テーブルに本日分が記録されているか |
| Execution 停止 | 取引時間外は不要なので `stop_system.py` で停止しても良い |

**手動でポジション更新を確認する場合（DuckDB）:**

```cmd
duckdb data\kabusys.duckdb "SELECT * FROM positions ORDER BY code"
```

> 15:00 以降に `start_system.py` を実行しても、kabuステーション API が注文受付外のため発注は行われない。

---

## 8. 緊急停止（Kill Switch）

### 8.1 自動発動条件

ExecutionEngine が以下を検知した場合に自動発動:

- 最大ドローダウン（`max_drawdown`）超過
- API 接続断（`circuit_breaker` 発動）
- `circuit_breaker_errors` 件以上の連続エラー

### 8.2 手動発動

```cmd
python scripts\stop_system.py
```

停止フラグ（`data/stop_requested.flag`）を作成し、Execution / Monitoring がグレースフルに終了する（最大 10 秒）。  
10 秒以内に終了しない場合は強制終了（`psutil.Process(pid).kill()`）される。

再起動する際は停止フラグが残っているため、`--clear-stop-flag` を明示指定する必要がある。

```cmd
python scripts\start_system.py --clear-stop-flag
```

### 8.3 発動後の確認

```
1. ログで Kill Switch 発動の原因を確認
2. ポジションを証券口座で直接確認（手動）
3. 原因が解消したら FailureRecovery.md §9 に従い復旧
4. 翌日の Runbook を通常通り実行
```

---

## 9. 夜間処理確認（21:30〜）

以下の Task Scheduler ジョブが正常完了したかを確認する。

| ジョブ名 | 実行時刻 | スクリプト | 確認内容 |
|---------|---------|----------|---------|
| KabuSys_DataUpdate | 15:30 | `run_data_update.py` | DuckDB に当日データが追加されているか |
| KabuSys_FeatureGen | 16:00 | `run_feature_gen.py` | `features` テーブルが更新されているか |
| KabuSys_AiAnalysis | 18:00 | `run_ai_analysis.py` | `news_scores`, `regime_scores` が更新されているか |
| KabuSys_StrategySignal | 20:00 | `run_strategy_signal.py` | `signals` テーブルに本日の BUY シグナルがあるか |
| KabuSys_PortfolioConstruction | 21:00 | `run_portfolio_construction.py` | `signal_queue` に `pending` シグナルが入っているか |

**Task Scheduler の実行履歴確認（PowerShell）:**

```powershell
Get-ScheduledTask -TaskName "KabuSys_*" | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, LastTaskResult
```

`LastTaskResult = 0` が正常終了。それ以外はログを確認すること。

**夜間バッチ手動再実行（異常時）:**

```cmd
# 例: portfolio_construction を手動再実行
python scripts\run_portfolio_construction.py
```

---

## 10. 日次レポート確認

Market Close 後（または翌朝）に確認する。

| 項目 | 確認方法 |
|------|---------|
| 日次リターン | `portfolio_performance` テーブル |
| ポジション一覧 | `positions` テーブル |
| 取引履歴 | `orders` テーブル（SQLite） |
| ドローダウン | `portfolio_performance` の `drawdown` カラム |

---

## 11. まとめ

このRunbookにより **安定した自動売買運用を実現する。**

関連ドキュメント:

- `FailureRecovery.md` — 障害発生時の詳細復旧手順
- `Monitoring.md` — 監視基盤の設計
- `documents/09_Deployment/` — デプロイメント構成
- `documents/10_Runtime/` — ジョブスケジュール定義
