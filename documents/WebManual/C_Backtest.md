# C. バックテスト — WebManual

- **対象**: 過去データで戦略の有効性を検証したい方
- **目的**: バックテストを実行し、結果を評価する

---

## C-B-1. バックテストとは

KabuSys のバックテストは、実運用と同じ `generate_signals()` ロジックを使い、インメモリ DB 上で過去の株価データを再生します。ペーパートレードや本番 DB を汚染しません。

---

## C-B-2. 基本実行

```powershell
python -m kabusys.backtest.run `
    --start 2023-01-01 `
    --end 2024-12-31 `
    --db data/kabusys.duckdb
```

---

## C-B-3. 主なオプション

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

## C-B-4. 対象銘柄を絞る（Targeted Backtest）

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

## C-B-5. 詳細リファレンス

技術仕様・モジュール構成・インメモリ DB の詳細は設計ドキュメントを参照してください。

→ `documents/05_Backtest/BacktestFramework.md`
