# MVP: 夜間バッチ結果確認レポート最小仕様

- ステータス: 実装完了（Issue #193）
- 目的: 最初に実装する夜間バッチ結果確認レポートの最小仕様を 1 ページで定義する
- 対象: 実運用の夜間バッチ完了後、21:30 頃にユーザーが確認する運用レポート

---

## 1. この仕様で実装するもの

最初の実装では、以下だけを対象とする。

- 実行直後に確認できる `CLI summary`
- 保存用の `summary.json`
- 保存用の `report.md`

この段階では、LINE 通知、HTML レポート、ダッシュボード表示、自動グラフ生成は実装対象外とする。

---

## 2. このレポートの目的

このレポートの目的は 1 つだけである。

> 明日の朝、このまま自動執行を開始してよいかをユーザーが判断できること

そのため、レポートは詳細分析よりも、**成否・件数・最終判定が短時間で分かること** を優先する。

---

## 3. 出力タイミング

- `portfolio_construction_job` 完了後に生成する
- 目安時刻は 21:00-21:30
- 一部ジョブ失敗時でも必ず生成する

---

## 4. 最終判定ステータス

最初の実装では、以下の 3 段階だけを使う。

### `READY`

- 翌営業日の自動執行を開始してよい

### `READY_WITH_WARNINGS`

- 基本的には開始可能
- ただしユーザーが warning を確認して判断する

### `BLOCKED`

- 翌営業日の自動執行を開始してはいけない

---

## 5. `BLOCKED` の最小条件

以下のいずれかを満たした場合は `BLOCKED` とする。

- `data_update_job` 失敗
- `strategy_signal_job` 失敗
- `portfolio_construction_job` 失敗
- `signal_queue` 件数が 0

---

## 6. `READY_WITH_WARNINGS` の最小条件

以下は初期 warning 条件とする。

- `signals` 件数が 0
- `signal_queue` 件数が通常より少ない
- ニュース件数が極端に少ない
- 一部ジョブで再試行が発生した

件数閾値は初期実装では固定値または暫定設定値でよい。  
前日比や移動平均比較は、この段階では必須にしない。

---

## 7. 共通で必ず出す項目

### 7.1 実行情報

- 実行日
- レポート生成時刻
- 対象取引日
- 最終判定ステータス

### 7.2 ジョブ成否

以下の各ジョブについて、少なくとも `status` を出す。

- `data_update_job`
- `feature_generation_job`
- `ai_analysis_job`
- `strategy_signal_job`
- `portfolio_construction_job`

`status` の値:

- `success`
- `warning`
- `failed`

### 7.3 更新件数

最低限、以下を表示する。

- `prices_daily` 更新件数
- `news_articles` 更新件数
- `features` 更新件数
- `ai_scores` 更新件数
- `signals` 件数
- `signal_queue` 件数

### 7.4 翌営業日の準備サマリ

- BUY 件数
- SELL 件数
- 対象銘柄数

### 7.5 warning

- warning 一覧

---

## 8. `CLI summary` の最小仕様

`CLI summary` は、ユーザーが 1 分以内に状況を判断できることを目的とする。

表示項目:

- 実行日
- 対象取引日
- 最終判定ステータス
- 各ジョブの成否
- `signals` 件数
- `signal_queue` 件数
- BUY 件数
- SELL 件数
- warning 一覧

CLI では詳細ログや長い説明は出さない。

---

## 9. `summary.json` の最小仕様

`summary.json` は機械可読なサマリとして使う。

最低限、以下のトップレベルキーを持つ。

- `meta`
- `job_status`
- `counts`
- `preparation`
- `warnings`
- `final_decision`

想定例:

```json
{
  "meta": {},
  "job_status": {},
  "counts": {},
  "preparation": {},
  "warnings": [],
  "final_decision": "READY"
}
```

この段階では JSON スキーマ固定化までは行わないが、キー名は安定させる。

---

## 10. `report.md` の最小仕様

`report.md` は人間向け保存レポートとする。

章立ては固定で以下とする。

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

- 各ジョブの `status`

### Update Counts

- `prices_daily`
- `news_articles`
- `features`
- `ai_scores`
- `signals`
- `signal_queue`

### Next Trading Day Preparation

- BUY 件数
- SELL 件数
- 対象銘柄数

### Warnings

- warning を列挙する

### Final Decision

- `READY`
- `READY_WITH_WARNINGS`
- `BLOCKED`
- 必要なユーザーアクションを 1 行で示す

---

## 11. 推奨保存先

```text
artifacts/operations/night_batch/{run_date}/
  summary.json
  report.md
```

`run_date` は夜間バッチ実行日ベースでよい。

---

## 12. 今回は実装しないもの

以下は後続フェーズに回す。

- LINE 通知
- HTML レポート
- ダッシュボード表示
- 各ジョブの詳細エラーメッセージ全文
- 前日比比較
- 移動平均比較
- セクター別件数
- 想定発注金額合計
- 自動再実行連携
- `READY_WITH_WARNINGS` の高度な閾値制御

---

## 13. 実装完了の条件

以下を満たせば、この MVP は完了とする。

1. 夜間バッチ完了後に `CLI summary` が出る
2. `summary.json` が保存される
3. `report.md` が保存される
4. `READY / READY_WITH_WARNINGS / BLOCKED` が判定される
5. ユーザーが翌朝の自動執行可否を判断できる
