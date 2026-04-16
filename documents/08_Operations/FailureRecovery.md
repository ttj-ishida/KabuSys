# FailureRecovery.md

## 1. 目的

本ドキュメントは、日本株自動売買システムにおける **障害対応（Failure Recovery）** 手順を定義する。

目的:

- 障害発生時の迅速・安全な対応
- 自動売買の安全停止（Kill Switch）
- データ整合性の維持
- システム復旧手順の標準化

対象環境:

- Single Windows PC（KabuSys 稼働ノード）
- kabuステーション API
- Python 自動売買システム

---

## 2. 障害分類と優先度

| Category | 内容 | 優先度 |
|----------|------|--------|
| System Failure | PC 停止・OS 障害・再起動 | 🔴 最高 |
| API Failure | kabuステーション API 接続障害 | 🔴 最高 |
| Execution Failure | 注文送信エラー・Kill Switch 発動 | 🔴 最高 |
| Data Failure | Signal Queue 破損・DB 不整合 | 🟡 高 |
| Position Failure | DB ポジションと口座の不一致 | 🟡 高 |
| Monitoring Failure | 監視プロセス停止 | 🟢 中 |

---

## 3. 緊急停止（Kill Switch）

重大障害時または手動で自動売買を即時停止する手順。

### 3.1 自動 Kill Switch

ExecutionEngine が以下を検知した場合に自動発動:

- `max_drawdown` 超過
- `circuit_breaker` 発動（連続エラー `circuit_breaker_errors` 件以上）
- API 接続断が継続

ログに以下が出力される:

```
CRITICAL Kill Switch 発動 — reason=...
```

### 3.2 手動 Kill Switch

```cmd
cd C:\path\to\KabuSys
python scripts\stop_system.py
```

動作:

1. `data/stop_requested.flag` を作成
2. Execution / Monitoring プロセスが停止フラグを検知してグレースフル終了（最大 10 秒）
3. 10 秒以内に終了しない場合は `psutil.kill()` で強制終了
4. PID ファイル（`data/execution.pid`, `data/monitoring.pid`）を削除

### 3.3 Kill Switch 発動後の確認

```
1. kabuステーション画面でポジション・未約定注文を直接確認
2. ログで発動原因を特定（ERROR / CRITICAL メッセージ）
3. 原因が解消したら §8「Kill Switch 発動後の復旧」に従う
```

---

## 4. API 接続障害

### 症状

- kabuステーション API から応答なし
- `BrokerClient` のログに `ConnectionError` / `TimeoutError`
- `circuit_breaker` が発動してログに `CIRCUIT_BREAKER_OPEN` が出力される

### 対応手順

```
1. kabuステーション 画面を確認
   └─ ログイン状態・接続状態を確認

2. kabuステーション を再起動
   └─ タスクバーのアイコンから終了 → 再起動

3. API 再接続確認（自動リトライ）
   └─ ExecutionEngine は自動でリトライする（retry_attempts 回）
   └─ circuit_breaker がリセットされればセッション継続

4. それでも接続できない場合
   └─ python scripts\stop_system.py でシステム停止
   └─ kabuステーション 障害情報を確認（公式サイト・Twitter）
   └─ 接続回復後に §8 手順で再起動

5. 取引時間中に接続が回復した場合
   └─ python scripts\start_system.py --component execution
   └─ Signal Queue に pending シグナルが残っていれば発注再開
```

---

## 5. PC 再起動後のリコンシリエーション

### 症状

- Windows 自動更新・電源障害・OS クラッシュによる予期しない再起動
- Execution プロセスが `SIGKILL` 等で異常終了

### 復旧手順

```
1. PC 起動・kabuステーション 起動・ログイン

2. 停止フラグ確認
   └─ data\stop_requested.flag が存在する場合は削除
      （または start_system.py 実行時に自動クリアされる）

3. DB 整合性チェック
   └─ signal_queue に status='sent' で未約定のものがないか確認
   └─ positions テーブルと口座ポジションの一致確認

4. Execution 起動（リコンシリエーション自動実行）
   python scripts\start_system.py --component execution

   起動時に自動実行される処理:
   ├─ status='sent' の注文をブローカーAPI と突合
   ├─ 約定済み → status='filled' に更新
   ├─ キャンセル済み → status='cancelled' に更新
   └─ ポジション差分をログに記録

5. リコンシリエーション結果確認
   └─ ログで orders_no_status, position_discrepancies を確認
   └─ 差分がある場合は §9「ポジション不整合時の復旧」へ

6. Monitoring 起動
   python scripts\start_system.py --component monitoring
```

### 注意事項

- 市場時間内（09:00〜15:30）の再起動は特に注意
- 未発注の Signal Queue が残っている場合、起動後に即時発注が開始される
- Signal Queue をクリアしたい場合は §6 を参照

---

## 6. Signal Queue 破損時の再生成

### 症状

- `signal_queue` テーブルの読み込みエラー
- `pending` シグナルが異常に多い・少ない
- DB ファイルの破損

### 対応手順

```
1. Execution を停止（起動中の場合）
   python scripts\stop_system.py

2. Signal Queue をリセット
   python scripts\reset_signals.py

   動作: signal_queue テーブルを全削除し再作成

3. 夜間バッチを手動で再実行（順番通りに）
   python scripts\run_strategy_signal.py
   python scripts\run_portfolio_construction.py

4. 生成されたシグナルを確認
   └─ signal_queue に pending シグナルが入っていること

5. Execution を再起動
   python scripts\start_system.py --component execution
```

### 注意事項

- `reset_signals.py` は `signal_queue` テーブルを **全削除** する
- 当日の発注済み注文（`status='sent'` / `status='filled'`）はこのテーブルには存在しない（`orders` テーブルで管理）
- 取引時間外での実施を推奨

---

## 7. ポジション不整合時の復旧

### 症状

- DB の `positions` テーブルと kabuステーション の口座ポジションが一致しない
- リコンシリエーションログに `position_discrepancies > 0` が出力される

### 対応手順

```
1. Execution を停止（取引を一時停止）
   python scripts\stop_system.py

2. kabuステーション で実際のポジションを確認
   └─ 銘柄・数量・平均取得単価を記録

3. DB の positions テーブルを確認
   duckdb data\market.duckdb "SELECT * FROM positions ORDER BY code"

4. 差分の原因特定
   ├─ 約定処理の漏れ → orders テーブルを確認
   └─ 手動取引による差分 → 手動で DB を修正

5. positions テーブルを修正
   └─ DuckDB CLI または Python スクリプトで直接更新

6. portfolio_targets を再計算
   python scripts\run_portfolio_construction.py

7. Execution を再起動
   python scripts\start_system.py --component execution

8. リコンシリエーション結果を確認
   └─ position_discrepancies = 0 になっていること
```

---

## 8. Kill Switch 発動後の復旧

### 前提

Kill Switch 発動後は `data/stop_requested.flag` が存在するため、`start_system.py` 実行時に自動クリアされる。

### 復旧手順

```
1. Kill Switch 発動原因を特定
   └─ ログで CRITICAL / Kill Switch メッセージを確認
   └─ 原因を以下に分類:
      (a) ドローダウン超過 → §8.1
      (b) API 接続断       → §4 を先に解消
      (c) 異常注文         → orders テーブルを確認

2. ポジション確認（kabuステーション 画面で直接確認）
   └─ 未約定注文が残っていないか

3. リスク状況の評価
   └─ ドローダウンが許容範囲内に戻っているか確認
   └─ 当日の残り取引時間と損益を評価

4. 翌日以降に再開する場合（推奨）
   └─ そのまま終業（停止フラグは残したまま）
   └─ 翌朝の TradingRunbook.md §3 Pre-Market Checklist から再開

5. 当日中に再開する場合
   python scripts\start_system.py --component execution
   └─ Signal Queue に pending シグナルが残っていれば発注再開
   └─ リコンシリエーション自動実行を確認
```

#### 8.1 ドローダウン超過後の再開判断基準

| 状態 | 対応 |
|------|------|
| DD が `max_drawdown` 以内に回復 | 再開可能 |
| DD が `max_drawdown` を超えたまま | 翌日以降まで待機 |
| 原因が特定・解消済み | 再開可能 |
| 原因不明 | 再開しない（調査優先） |

---

## 9. その他の障害

### 9.1 注文エラー（order rejected）

```
1. orders テーブルで rejected 注文を確認
2. 原因確認（資金不足・銘柄コードエラー・注文数量エラー等）
3. signal_queue の対象シグナルを status='failed' に更新
4. 必要に応じて手動発注
```

### 9.2 夜間バッチ失敗

```
1. Task Scheduler の実行履歴で LastTaskResult を確認
   Get-ScheduledTask -TaskName "KabuSys_*" | Get-ScheduledTaskInfo

2. 失敗したスクリプトを手動再実行
   python scripts\run_<failed_job>.py

3. 依存関係に注意して順番通りに再実行
   run_data_update.py
   → run_feature_gen.py
   → run_ai_analysis.py
   → run_strategy_signal.py
   → run_portfolio_construction.py
```

### 9.3 Monitoring プロセス停止

```
python scripts\start_system.py --component monitoring
```

Monitoring は発注には関与しないため、停止中も Execution は継続動作する。

### 9.4 特徴量データ破損

```
python scripts\rebuild_features.py
```

`prices_daily` を元に特徴量を全再計算する。

---

## 10. 復旧確認チェックリスト

復旧後は以下をすべて確認してから通常運用に戻る。

| 項目 | 確認内容 | OK |
|------|---------|-----|
| 停止フラグ | `data/stop_requested.flag` が存在しない | ☐ |
| PID ファイル | `data/execution.pid` が存在・プロセス生存 | ☐ |
| API 接続 | kabuステーション 接続状態 = 正常 | ☐ |
| ポジション | DB と口座が一致 | ☐ |
| Signal Queue | 必要なシグナルが `pending` 状態で存在 | ☐ |
| 未処理注文 | `status='sent'` で長時間放置の注文がない | ☐ |
| ログ | ERROR / CRITICAL メッセージが解消されている | ☐ |

---

## 11. まとめ

Failure Recovery 設計の原則:

- **Fail Safe**: 不確定時は安全側に倒す（停止 > 継続）
- **Kill Switch**: 損失拡大を即時停止できる機構を常に維持
- **Data Integrity**: ポジションとDB の整合性を最優先で回復
- **Manual Override**: 自動化に頼らず手動確認で最終判断

関連ドキュメント:

- `TradingRunbook.md` — 日次運用手順
- `Monitoring.md` — 監視基盤の設計
