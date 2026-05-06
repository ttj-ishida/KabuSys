# TODO: 夜間バッチ結果確認レポート設計メモ

- ステータス: **実装完了**（Issue #193）
- 実装: `src/kabusys/operations/night_batch_report.py`（READY/READY_WITH_WARNINGS/BLOCKED 判定、CLI/JSON/Markdown 出力）
- 保存先: `artifacts/night_batch/{date}/summary.json`, `report.md`, `warnings.json`
- 目的: 実運用において、21:30 の夜間バッチ結果確認をユーザーが安全かつ短時間で行えるように、通知・レポート仕様を整理する
- 対象: 夜間バッチ運用、翌営業日の売買準備確認
- 注意: 本ファイルは開発・設計検討用の暫定メモであり、現行の正式仕様書そのものではない

---

## 1. 背景

実運用では、夜間バッチが以下の順で実行される。

1. `data_update_job`
2. `feature_generation_job`
3. `ai_analysis_job`
4. `strategy_signal_job`
5. `portfolio_construction_job`

その後、21:30 頃にユーザーが「翌営業日の準備が完了しているか」を確認する運用を想定している。

しかし現状設計では、夜間バッチの完了結果をユーザーへまとめて通知する**運用レポート仕様**が明文化されていない。

このため、以下の問題がある。

- バッチごとの成功 / 失敗が一目で分からない
- 翌日の `Signal Queue` が妥当かを短時間で判断しづらい
- 一部成功 / 一部失敗時の扱いが曖昧
- 「運用開始してよいか」の最終判定基準が統一されていない

---

## 2. このレポートの位置づけ

このレポートは、バックテストレポートとは別物とする。

### 2.1 バックテストレポートとの違い

- バックテストレポート
  - 目的: 戦略の性能評価、比較、研究
  - 指標: CAGR, Sharpe, Max Drawdown, trades など
- 夜間バッチ結果確認レポート
  - 目的: 翌営業日に安全に運用開始できるかを判断する
  - 指標: ジョブ成否、更新件数、シグナル件数、Signal Queue 状態、warning

### 2.2 位置づけ

このレポートは、**運用レポート** である。

目的は次の1点に集約される。

> 明日の朝、このまま自動執行を開始してよいかをユーザーが判断できること

---

## 3. レポートの出力タイミング

### 基本タイミング

- `portfolio_construction_job` 完了後
- 目安時刻: 21:00-21:30

### 生成条件

- 夜間バッチの最後のジョブが終了した時点で生成する
- 一部ジョブ失敗時でも生成する
- 失敗時は `BLOCKED` または `READY_WITH_WARNINGS` として判定を出す

---

## 4. レポートで最終的に伝えるべきこと

このレポートは、最低限以下の問いに答えられなければならない。

1. どのジョブが成功し、どのジョブが失敗したか
2. どの程度のデータが更新されたか
3. 翌営業日のシグナルと発注キューが作成されているか
4. 明日の自動執行を開始してよいか
5. ユーザーが手動確認すべき異常があるか

---

## 5. 最終判定ステータス

### 5.1 `READY`

意味:

- 翌営業日の自動執行を開始してよい

条件例:

- 必須ジョブがすべて成功
- `Signal Queue` が正常作成済み
- warning がない、または軽微

### 5.2 `READY_WITH_WARNINGS`

意味:

- 基本的には翌営業日の自動執行を開始可能
- ただし、ユーザーが warning を確認したうえで判断する

条件例:

- 一部件数が少ない
- シグナル件数が平常より少ない
- 一部補助情報が欠損
- 軽微なジョブ再試行が発生

### 5.3 `BLOCKED`

意味:

- 翌営業日の自動執行を開始してはいけない

条件例:

- 必須ジョブ失敗
- `Signal Queue` 空
- ポートフォリオ構築失敗
- データ更新が未完了
- シグナル生成が未完了

---

## 6. レポートの最小出力項目

### 6.1 実行情報

- 実行日
- レポート生成時刻
- 対象取引日
- 最終判定ステータス

### 6.2 ジョブ成否一覧

各ジョブについて以下を出す。

- ジョブ名
- ステータス
  - `success`
  - `warning`
  - `failed`
  - `skipped`
- 開始時刻
- 終了時刻
- 実行時間

対象ジョブ:

- `data_update_job`
- `feature_generation_job`
- `ai_analysis_job`
- `strategy_signal_job`
- `portfolio_construction_job`

### 6.3 更新件数

最低限、以下を表示する。

- `prices_daily` 更新件数
- `news_articles` 更新件数
- `fundamentals` 更新件数
- `features` 更新件数
- `ai_scores` 更新件数
- `signals` 生成件数
- `signal_queue` 生成件数

### 6.4 翌営業日の準備サマリ

- BUY 件数
- SELL 件数
- 対象銘柄数
- 想定発注件数

将来候補:

- 想定発注金額合計
- セクター別件数
- 最大ポジション比率

### 6.5 warning 一覧

最低限、warning を列挙する。

例:

- `signals = 0`
- `signal_queue = 0`
- `prices_daily` 更新件数が前日比で急減
- ニュース取得件数が極端に少ない
- AI スコア件数が通常より少ない
- 一部ジョブが再試行後に成功

---

## 7. ユーザーが見て判断するポイント

このレポートを見たユーザーは、最低限以下を判断できる必要がある。

- 明朝の自動執行を継続してよいか
- 手動再実行が必要か
- どのジョブに問題があったか
- 問題がデータ不足なのか、ロジック失敗なのか、単なる件数低下なのか

---

## 8. 通知・出力形式

### 8.1 最初に実装したい形式

- `CLI summary`
- `JSON`
- `Markdown`

### 8.2 将来候補

- LINE 通知
- HTML レポート
- ダッシュボード表示

### 8.3 推奨保存先

```text
artifacts/operations/night_batch/{run_date}/
  summary.json
  report.md
  warnings.json
```

---

## 9. CLI summary の最小仕様

CLI summary では、短時間で判断できることを優先する。

表示項目:

- 実行日
- 対象取引日
- 最終判定ステータス
- 各ジョブの成否
- `signals` 件数
- `signal_queue` 件数
- warning 件数
- warning の要約

---

## 10. Markdown レポートの最小仕様

章立て案:

1. Overview
2. Job Status
3. Update Counts
4. Next Trading Day Preparation
5. Warnings
6. Final Decision

### Overview

- 実行日
- レポート生成時刻
- 対象取引日
- 最終判定

### Job Status

- 各ジョブの成否、開始、終了、実行時間

### Update Counts

- 各テーブルの更新件数

### Next Trading Day Preparation

- BUY 件数
- SELL 件数
- 対象銘柄数
- `signal_queue` 件数

### Warnings

- warning の詳細一覧

### Final Decision

- `READY`
- `READY_WITH_WARNINGS`
- `BLOCKED`

ユーザーへのアクション指示も入れる。

---

## 11. warning ルールの初期案

### 11.1 `READY_WITH_WARNINGS`

候補:

- `signals` 件数が閾値未満
- `signal_queue` 件数が閾値未満
- ニュース件数が平常より少ない
- AI スコア件数が平常より少ない
- 軽微な再試行があった

### 11.2 `BLOCKED`

候補:

- `data_update_job` 失敗
- `strategy_signal_job` 失敗
- `portfolio_construction_job` 失敗
- `signal_queue = 0`
- 必須データが未更新

---

## 12. 実装時に必要な追加データ

このレポートを作るには、各ジョブが以下を返すか保存する必要がある。

- 開始時刻
- 終了時刻
- ステータス
- 再試行有無
- 更新件数
- warning / error メッセージ

必要に応じて、ジョブ共通の実行結果構造を定義する。

想定例:

```python
@dataclass
class JobRunResult:
    job_name: str
    status: str
    started_at: datetime
    finished_at: datetime
    duration_sec: float
    updated_rows: dict[str, int]
    warnings: list[str]
    errors: list[str]
```

---

## 13. まず決めるべき仕様

### 優先度高

1. 最終判定ステータスの定義
2. 必須ジョブの範囲
3. `READY_WITH_WARNINGS` と `BLOCKED` の閾値
4. 最小出力項目
5. 保存先

### 優先度中

1. JSON スキーマ
2. Markdown の章立て固定
3. LINE 通知の要否

### 優先度低

1. ダッシュボード連携
2. 件数の前日比・移動平均比較
3. 自動再実行ポリシー連携

---

## 14. 反映対象候補

### `documents/10_Runtime/RuntimeJobSchedule.md`

- 夜間バッチ完了後のレポート生成を追記する
- 21:30 のユーザー確認フローを明文化する

### `documents/08_Operations/TradingRunbook.md`

- 夜間バッチ結果確認の確認観点を追記する
- `READY / READY_WITH_WARNINGS / BLOCKED` に応じた行動指針を追加する

### `documents/10_Runtime/WebManual_OperationsCycle.md`

- 「夜間バッチ結果確認」でユーザーに提示されるレポートの存在を追記する

---

## 15. 反映後の状態イメージ

設計反映後の到達イメージは以下。

- 21:30 にユーザーが見るべき運用レポートが定義される
- 各ジョブの成否と更新件数が一目で分かる
- 翌営業日の自動執行を開始してよいかを明示的に判断できる
- warning と block 条件が統一される
- 夜間バッチ失敗時の対応が標準化される
