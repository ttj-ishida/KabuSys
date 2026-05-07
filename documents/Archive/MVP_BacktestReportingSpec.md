# MVP: バックテスト最小レポート仕様

- ステータス: 実装完了（Issue #228 / PR #243）
- 目的: 最初に実装するバックテスト結果レポートの最小仕様を1ページで定義する
- 対象: 標準バックテスト (`portfolio_backtest`) / 個別銘柄指定バックテスト (`targeted_backtest`)

---

## 1. この仕様で実装するもの

最初の実装では、以下だけを対象とする。

- 実行直後に確認できる `CLI summary`
- 保存用の `summary.json`
- 保存用の `report.md`
- 明細用の `trades.csv`
- 日次損益推移用の `daily_equity.csv`

この段階では、HTML レポート、画像生成、比較レポート、自動グラフ出力は実装対象外とする。

---

## 2. レポートの基本方針

- 標準バックテストと個別銘柄指定バックテストで、共通の出力骨格を使う
- ただし重視する項目は変える
- レポートは必ず再現条件を含む
- warning を標準出力に含め、誤読を防ぐ

---

## 3. 出力ファイル

保存先:

```text
artifacts/backtests/{run_id}/
  summary.json
  report.md
  trades.csv
  daily_equity.csv
```

`run_id` は一意であること。最低限、再実行時に同じ結果を追跡できる識別子として使う。

---

## 4. 共通で必ず出す項目

### 4.1 実行条件

- `run_id`
- `report_type`
- 実行日時
- 開始日
- 終了日
- 初期資金
- `slippage_rate`
- `commission_rate`
- `allocation_method`

### 4.2 スコープ情報

- `scope_mode`
- `scope_codes`
- `preserve_universe_filters`
- `effective_universe_size`

### 4.3 headline metrics

- 初期資産
- 最終資産
- 総リターン
- CAGR
- Sharpe Ratio
- Max Drawdown
- 総トレード数
- 勝率
- Payoff Ratio

### 4.4 warning

最低限、以下を自動表示する。

- 個別銘柄指定結果は標準ポートフォリオ戦略の代替評価ではない
- `manual_raw_universe` を使った結果は実運用採否の根拠に使わない
- 総トレード数が少ない場合は統計的信頼性が低い

トレード数閾値は暫定で `10件未満` を warning 対象とする。

---

## 5. `CLI summary` の最小仕様

`CLI summary` は実行直後に短時間で確認するための要約とする。

表示項目:

- `run_id`
- `report_type`
- 検証期間
- 最終資産
- 総リターン
- CAGR
- Sharpe Ratio
- Max Drawdown
- 総トレード数
- 勝率
- warning 一覧

CLI では表や長い明細は出さない。

---

## 6. `summary.json` の最小仕様

`summary.json` は機械可読なサマリとして使う。

最低限、以下のトップレベルキーを持つ。

- `meta`
- `scope`
- `headline`
- `warnings`

想定例:

```json
{
  "meta": {},
  "scope": {},
  "headline": {},
  "warnings": []
}
```

この段階では JSON スキーマ固定化までは行わないが、キー名は安定させる。

---

## 7. `report.md` の最小仕様

`report.md` は人間向け保存レポートとする。

章立ては固定で以下とする。

1. Overview
2. Scope
3. Headline Metrics
4. Trade Summary
5. Warnings

### Overview

- 実行日時
- 検証期間
- `report_type`
- 初期資金

### Scope

- `scope_mode`
- `scope_codes`
- `preserve_universe_filters`
- `effective_universe_size`

### Headline Metrics

- 初期資産
- 最終資産
- 総リターン
- CAGR
- Sharpe Ratio
- Max Drawdown
- 総トレード数
- 勝率
- Payoff Ratio

### Trade Summary

共通:

- 平均利益
- 平均損失
- 手数料合計

標準バックテストでは追加で以下を出す。

- 平均保有銘柄数
- 最大保有銘柄数

個別銘柄指定バックテストでは追加で以下を出す。

- BUY シグナル回数
- SELL シグナル回数
- 見送り回数

### Warnings

- warning を列挙する

この段階では、グラフ画像や月次リターン表は `report.md` に含めない。

---

## 8. CSV の最小仕様

### `trades.csv`

最低限の列:

- `date`
- `code`
- `side`
- `shares`
- `price`
- `commission`
- `realized_pnl`

### `daily_equity.csv`

最低限の列:

- `date`
- `cash`
- `portfolio_value`

この段階では保有銘柄内訳は含めなくてよい。

---

## 9. 標準バックテストと個別銘柄指定での最小差分

### `portfolio_backtest`

最低限追加する項目:

- 平均保有銘柄数
- 最大保有銘柄数

### `targeted_backtest`

最低限追加する項目:

- BUY シグナル回数
- SELL シグナル回数
- 見送り回数

見送り理由内訳までは、この初期実装では必須にしない。

---

## 10. 今回は実装しないもの

以下は後続フェーズに回す。

- HTML レポート
- グラフ画像の生成
- 月次リターン表のファイル出力
- セクター分析
- regime 別成績
- breadth_stop 集計
- 寄与分析
- 見送り理由内訳
- 比較レポート
- `BacktestReport` 専用クラスの導入

初期実装では、まず `BacktestResult` から直接レポートを組み立てる方針でもよい。

---

## 11. 実装完了の条件

以下を満たせば、この MVP は完了とする。

1. バックテスト実行後に `CLI summary` が出る
2. `summary.json` が保存される
3. `report.md` が保存される
4. `trades.csv` と `daily_equity.csv` が保存される
5. 標準バックテストと個別銘柄指定バックテストの両方で同じ仕組みが動く
6. warning が最低限機能する
