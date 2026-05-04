# PBR・配当利回り特徴量実装 設計書 (Issue #185)

## 概要

`features` テーブルの `pbr` / `div_yield` カラムは定義済みだが値が NULL のまま。
本実装では J-Quants からのデータ取得パイプライン追加 → `features` への書き込み → `_compute_value_score()` の拡張を行い、バリュースコアを PER・PBR・配当利回りの3指標加重平均に更新する。

## 設計方針

### スコア統合方式

3指標を 0〜1 に正規化して**加重平均**する。重みと正規化基準値はすべて設定ファイルで管理し、コードに埋め込まない。

```toml
# config/strategy.toml
[value_score.weights]
per       = 0.50
pbr       = 0.30
div_yield = 0.20

[value_score.normalization]
per_mid       = 20.0   # PER がこの値のとき score = 0.5
pbr_mid       = 1.5    # PBR がこの値のとき score = 0.5
div_yield_max = 3.0    # この配当利回り(%)で score = 1.0（上限）
```

データ欠損時は有効な指標のみで重み正規化して計算する（全欠損時は `None`）。

### 配当利回りの定義

`div_yield = (直近12ヶ月の div_rate 合計 / close) × 100`

`dividends.ex_date` が `target_date - 1年` 〜 `target_date` の範囲に入るレコードの `div_rate` を合計する。

### PBR の定義

`pbr = close / bps`

`bps`（1株純資産）は J-Quants `/fins/statements` の `BookValuePerShare` フィールドから取得する。
`raw_financials` テーブルに `bps` カラムを追加して保存する。

## 変更ファイル

### `config/strategy.toml`（新規）

- `[value_score.weights]` — per / pbr / div_yield の重み（合計 1.0）
- `[value_score.normalization]` — per_mid / pbr_mid / div_yield_max の基準値

### `src/kabusys/data/schema.py`

- `raw_financials` の `CREATE TABLE` 定義に `bps DECIMAL(18,4)` を追加
- `_migrate_raw_financials_add_bps()` ヘルパーを追加（既存 DB への `ALTER TABLE` 対応）
- `init_schema()` から migration ヘルパーを呼び出す

### `src/kabusys/data/jquants_client.py`

- `save_financial_statements()` のタプル生成に `_to_float(r.get("BookValuePerShare"))` を追加
- INSERT 文に `bps` カラムを追加（`ON CONFLICT DO UPDATE` で既存レコードも更新）

### `src/kabusys/data/pipeline.py`

- `run_dividends_etl(conn, target_date, id_token, date_from, backfill_days)` を追加
  - `/fins/dividend` エンドポイントから差分取得
  - `dividends` テーブルに冪等 upsert（`ON CONFLICT DO UPDATE SET div_rate=...`）
  - 実装パターンは既存 `run_financials_etl()` と同一
- `run_all_etl()` が存在する場合は `run_dividends_etl()` を追加呼び出し

### `src/kabusys/research/factor_research.py`

- `calc_value()` を拡張して `pbr` / `div_yield` を追加計算

```sql
WITH latest_fin AS (
    SELECT code, eps, roe, bps
    FROM (
        SELECT code, eps, roe, bps,
               ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) AS rn
        FROM raw_financials WHERE report_date <= ?
    ) t WHERE rn = 1
),
annual_div AS (
    SELECT code, SUM(div_rate) AS annual_div
    FROM dividends
    WHERE ex_date BETWEEN (CAST(? AS DATE) - INTERVAL 1 YEAR) AND ?
    GROUP BY code
),
price_on_date AS (
    SELECT code, close FROM prices_daily WHERE date = ?
)
SELECT
    ? AS date,
    p.code,
    CASE WHEN f.eps  IS NOT NULL AND f.eps  <> 0 THEN p.close / f.eps  END AS per,
    f.roe,
    CASE WHEN f.bps  IS NOT NULL AND f.bps  >  0 THEN p.close / f.bps  END AS pbr,
    CASE WHEN d.annual_div IS NOT NULL AND p.close > 0
         THEN (d.annual_div / p.close) * 100 END AS div_yield
FROM price_on_date p
LEFT JOIN latest_fin f ON p.code = f.code
LEFT JOIN annual_div d ON p.code = d.code
ORDER BY p.code
```

- 戻り値の `list[dict]` に `pbr` / `div_yield` キーを追加
- `"PBR・配当利回りは現バージョンでは未実装。"` コメントを削除

### `src/kabusys/strategy/signal_generator.py`

- `_load_value_config()` ヘルパーを追加（`config/strategy.toml` を `tomllib` で読み込む）
  - ファイルが存在しない場合はデフォルト値（per=0.50/pbr=0.30/div_yield=0.20、per_mid=20/pbr_mid=1.5/div_yield_max=3.0）にフォールバック
- `_compute_value_score(feat, config)` に `config` 引数を追加し、3指標を加重平均するよう拡張

```python
def _compute_value_score(feat: dict[str, Any], config: dict) -> float | None:
    w = config["weights"]
    n = config["normalization"]
    scores: dict[str, float] = {}
    per = feat.get("per")
    if per is not None and per > 0 and math.isfinite(per):
        scores["per"] = 1.0 / (1.0 + per / n["per_mid"])
    pbr = feat.get("pbr")
    if pbr is not None and pbr > 0 and math.isfinite(pbr):
        scores["pbr"] = 1.0 / (1.0 + pbr / n["pbr_mid"])
    dy = feat.get("div_yield")
    if dy is not None and dy > 0 and math.isfinite(dy):
        scores["div_yield"] = min(dy / n["div_yield_max"], 1.0)
    if not scores:
        return None
    total_w = sum(w[k] for k in scores)
    return sum(w[k] * v for k, v in scores.items()) / total_w
```

- `generate_signals()` 内の `_compute_value_score()` 呼び出し箇所に `config` を渡す

### `tests/test_pbr_div_yield.py`（新規）

- `TestBpsExtraction`: `save_financial_statements()` が `BookValuePerShare` を `raw_financials.bps` に保存すること
- `TestDividendsEtl`: `run_dividends_etl()` が冪等に upsert すること
- `TestCalcValuePbr`: `pbr = close / bps` が正しく計算されること
- `TestCalcValueDivYield`: 直近12ヶ月の配当合計から `div_yield` が計算されること
- `TestCalcValueMissingBps`: `bps = NULL` のとき `pbr = NULL`
- `TestCalcValueNoDividends`: 配当レコードなしのとき `div_yield = NULL`
- `TestValueScoreAllThree`: 3指標すべて有効なとき加重平均が正しいこと
- `TestValueScorePartial`: PBR 欠損時に残り2指標で重み正規化して計算されること
- `TestValueScoreConfigDriven`: 設定ファイルの基準値変更がスコアに反映されること

### `tests/test_signal_generator.py`（既存）

- `_compute_value_score()` の呼び出し箇所を `config` 引数付きに更新

## パラメータ一覧

| パラメータ | デフォルト | 設定箇所 | 説明 |
|-----------|-----------|---------|------|
| `value_score.weights.per` | 0.50 | `config/strategy.toml` | PER の重み |
| `value_score.weights.pbr` | 0.30 | `config/strategy.toml` | PBR の重み |
| `value_score.weights.div_yield` | 0.20 | `config/strategy.toml` | 配当利回りの重み |
| `value_score.normalization.per_mid` | 20.0 | `config/strategy.toml` | PER score=0.5 の基準値 |
| `value_score.normalization.pbr_mid` | 1.5 | `config/strategy.toml` | PBR score=0.5 の基準値（東証平均付近） |
| `value_score.normalization.div_yield_max` | 3.0 | `config/strategy.toml` | 配当利回り score=1.0 の上限（%） |

## 設計上の決定事項

1. **加重平均 + 設定ファイル管理**: 将来の戦略方針変更（PER 重視・配当重視など）を `config/strategy.toml` の1行変更で対応可能。
2. **欠損耐性**: データが揃わない指標は除外し、残りの指標で重み正規化して計算。全欠損時のみ `None`。
3. **raw_financials 拡張**: BPS を既存の財務データテーブルに追加。新テーブル作成不要。
4. **スキーママイグレーション**: `init_schema()` 内で `ALTER TABLE IF NOT EXISTS ADD COLUMN` を実行し、既存 DB を安全に更新。
5. **配当の集計期間**: `dividends.ex_date` ベースで直近12ヶ月を集計。配当落ち日基準が最も一般的かつ正確。
6. **設定ファイル欠損フォールバック**: `config/strategy.toml` が存在しない環境でもデフォルト値で動作する。
