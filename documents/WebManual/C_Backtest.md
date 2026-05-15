# C. バックテスト — WebManual

- **対象**: 過去データで戦略の有効性を検証したい方
- **目的**: バックテストを実行し、結果を評価する

---

## C-B-1. バックテストとは

KabuSys のバックテストは、実運用と同じ `generate_signals()` ロジックを使い、インメモリ DB 上で過去の株価データを再生します。ペーパートレードや本番 DB を汚染しません。

---

## C-B-2. 事前準備 — 特徴量のバックフィル

バックテストは `features` テーブルにデータが存在することを前提とします。
初めてバックテストを実行する際、または対象期間を拡張した場合は、先に `backfill_features.py` で特徴量を生成してください。

```powershell
# ステップ 1: 価格・財務データを取得（初回または差分更新）
python -m kabusys.data.bootstrap

# ステップ 2: 特徴量を期間一括生成
python scripts/backfill_features.py --start 2022-01-01 --end 2024-12-31

# ステップ 3: バックテスト実行
python -m kabusys.backtest.run --start 2022-01-01 --end 2024-12-31 --db data/kabusys.duckdb
```

### backfill_features.py のオプション

| オプション | 説明 |
|---|---|
| `--start` / `--end` | 対象期間（必須） |
| `--db` | DuckDB ファイルパス（省略時は設定ファイルのデフォルト） |
| `--force` | 既存データを上書きする（省略時は既存データがある日をスキップ） |
| `--dry-run` | 対象日付の一覧を表示するのみ（DB への書き込みなし） |

> **ヒント:** 価格データが存在しない日は自動的にスキップされます。スキップ数が多い場合は先に `bootstrap` を実行してください。

---

## C-B-4. 基本実行

```powershell
python -m kabusys.backtest.run `
    --start 2023-01-01 `
    --end 2024-12-31 `
    --db data/kabusys.duckdb
```

---

## C-B-5. 主なオプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--cash` | `10000000` | 初期資金（円）。実口座残高に合わせて変更可能。 |
| `--allocation-method` | `risk_based` | 資金配分方式: `risk_based` / `equal` / `score` |
| `--max-positions` | `10` | 最大同時保有銘柄数 |
| `--max-utilization` | `0.70` | 最大投下資金比率（全ポジション合計の上限） |
| `--risk-pct` | `0.005` | 1トレードあたり許容リスク率（`risk_based` 時） |
| `--stop-loss-pct` | `0.08` | 損切り率（株数計算用） |
| `--min-holding-days` | `5` | 最低保有営業日数 |
| `--max-holding-days` | `60` | 最大保有営業日数（超えると time_exit SELL） |
| `--trailing-stop-atr` | `2.0` | トレーリングストップの ATR 乗数 |
| `--output-format` | `summary` | 出力形式: `summary` / `json` / `markdown` / `all` |
| `--output-dir` | ―　| レポートの保存先ディレクトリ（`--output-format all` 時） |

**初期資金を変更する例:**

```powershell
python -m kabusys.backtest.run `
    --start 2023-01-01 `
    --end 2024-12-31 `
    --cash 5000000 `
    --db data/kabusys.duckdb
```

---

## C-B-6. 対象銘柄を絞る（Targeted Backtest）

特定銘柄のみで検証する場合は `--scope-mode manual_codes` を使います。

```powershell
python -m kabusys.backtest.run `
    --start 2023-01-01 `
    --end 2024-12-31 `
    --db data/kabusys.duckdb `
    --scope-mode manual_codes `
    --codes 7203 9984 6758
```

---

## C-B-7. strategy_config.yaml でチューニングできるパラメータ

バックテストは実運用と同じ `strategy_config.yaml` を読み込みます。以下のパラメータを変更すると、バックテスト結果に反映されます。

| パラメータ | デフォルト | 説明 |
|---|---|---|
| `strategy.threshold` | `0.60` | BUY シグナル生成の final_score 閾値 |
| `strategy.stop_loss_rate` | `-0.08` | ストップロス閾値（終値 / avg_price − 1 がこれ以下で SELL） |
| `strategy.min_holding_days` | `5` | スコア低下による SELL を抑制する最低保有営業日数 |
| `strategy.max_holding_days` | `60` | 最大保有営業日数（超えると time_exit SELL） |
| `strategy.trailing_stop_atr_mult` | `2.0` | トレーリングストップの ATR 乗数 |
| `strategy.rsi_overbought_threshold` | `70.0` | RSI(14) 過熱判定閾値。この値を**超えた**銘柄は BUY を抑制（範囲: 50 < x ≤ 100）。`100.0` に設定するとフィルタ無効 |
| `strategy.gap_up_threshold` | `0.05` | ギャップアップ閾値（この比率を超えた寄り高は BUY 抑制） |
| `strategy.gap_down_threshold` | `-0.03` | ギャップダウン閾値（この比率以下の寄り安は BUY 抑制） |
| `portfolio.max_positions` | `8` | 最大保有銘柄数 |

**RSI フィルタのチューニング例:**

```yaml
# strategy_config.yaml
strategy:
  rsi_overbought_threshold: 75.0   # 過熱判定をやや緩めに設定（デフォルト: 70.0）
  # rsi_overbought_threshold: 100.0  # RSI フィルタを完全に無効化する場合
```

---

## C-B-8. 詳細リファレンス

技術仕様・モジュール構成・インメモリ DB の詳細は設計ドキュメントを参照してください。

→ `documents/05_Backtest/BacktestFramework.md`
