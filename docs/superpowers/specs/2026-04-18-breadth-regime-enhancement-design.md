# 設計仕様: 市場内部指標（breadth）によるレジーム補強

- **Issue**: #173
- **作成日**: 2026-04-18
- **ステータス**: 承認済み

---

## 1. 目的

現在のレジーム判定（ETF 1321 の 200日MA乖離 × 0.7 + マクロニュース LLM × 0.3）に、
市場全体の breadth 指標を追加し、判定精度を高める。

あわせて `signal_generator.py` の `_is_bear_regime()` バグ（`ai_scores.regime_score` が
常 NULL のため Bear 判定が常に False）を修正する。

---

## 2. 追加する breadth 指標

| 指標 | 計算方法 | 用途 |
|-----|---------|------|
| 騰落レシオ（25日） | `advances_25 / declines_25 × 100` | `regime_score` 補正 |
| 25日MA上銘柄比率 | `close > ma25` の銘柄数 / 全銘柄数 | BUY 全件停止の閾値 |
| 新高値/新安値比率 | 52週高値銘柄数 / 52週安値銘柄数 | 将来利用のため記録 |
| breadth_stop（bool） | `ma25_above_pct < 0.35` | BUY シグナル停止フラグ |

計算対象: `prices_daily` テーブル（J-Quants から取得した東証上場全銘柄の日足データ）

---

## 3. アーキテクチャ

Option A を採用: breadth 計算は `data/` 層に独立モジュールとして実装。

```
[15:30 data_update バッチ]
  run_data_update.py
    └─ run_prices_etl()            既存
    └─ calc_and_save_breadth()     新規（data/breadth.py）
                                       ↓
                              market_breadth テーブル（日次1行）

[18:00 ai_analysis バッチ]
  run_ai_analysis.py
    └─ score_regime()              既存 + breadth 補正追加
         1. MA200乖離 × 0.7 + マクロ × 0.3 → raw_score（既存）
         2. market_breadth.adv_decline_ratio を読み込み
            < 80  → raw_score -= 0.2
            > 120 → raw_score += 0.1
         3. clip(-1.0, 1.0) → regime_score
         4. bull / neutral / bear 再判定
                                       ↓
                              market_regime テーブル（既存・変更なし）

[20:00 strategy_signal バッチ]
  generate_signals()
    1. market_breadth.breadth_stop=True → BUY を全件スキップ、SELL は通常通り
    2. _is_bear_regime() バグ修正:
       ai_scores.regime_score（常 NULL）→ market_regime.regime_label を参照
```

---

## 4. スキーマ変更

### 新テーブル: `market_breadth`（`schema.py` に追加）

```sql
CREATE TABLE IF NOT EXISTS market_breadth (
    date                DATE    PRIMARY KEY,
    adv_decline_ratio   DOUBLE  NOT NULL,
    ma25_above_pct      DOUBLE  NOT NULL,
    new_high_low_ratio  DOUBLE,            -- 新安値=0 の場合は NULL
    breadth_stop        BOOLEAN NOT NULL,
    created_at          TIMESTAMP DEFAULT current_timestamp
)
```

既存テーブルへの変更なし。

---

## 5. 新規モジュール: `src/kabusys/data/breadth.py`

### 公開 API

```python
def calc_and_save_breadth(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> int:
    """target_date の breadth 指標を prices_daily から計算し market_breadth に保存する。

    Returns:
        1 = 保存成功、0 = 既存スキップ or データ不足

    冪等: 同日を再実行しても上書きせず 0 を返す。
    """
```

### 計算仕様

**騰落レシオ（25日）**
- 対象: `target_date` の直近 25 営業日
- `advances_25` = 各日の値上がり銘柄数（`close > prev_close`）の合計
- `declines_25` = 各日の値下がり銘柄数（`close < prev_close`）の合計
- `adv_decline_ratio = advances_25 / declines_25 × 100`
- `declines_25 = 0` の場合は `200.0`（極端な強気として扱う）

**25日MA上銘柄比率**
- `ma25_i` = 各銘柄の直近 25 日終値の単純平均
- `ma25_above_pct = (close_i > ma25_i の銘柄数) / 全銘柄数`

**新高値/新安値比率**
- `new_high` = `close == 直近 250 営業日の最高値` の銘柄数
- `new_low`  = `close == 直近 250 営業日の最安値` の銘柄数
- `new_high_low_ratio = new_high / new_low`
- `new_low = 0` の場合は `NULL`

**breadth_stop**
- `ma25_above_pct < 0.35`

### エラー処理

- `prices_daily` に 25 日分未満のデータ → `0` を返してスキップ（WARNING ログ）
- 計算対象銘柄数 < 10 件 → `0` を返してスキップ（WARNING ログ）

---

## 6. 変更ファイル詳細

### `src/kabusys/ai/regime_detector.py`

`score_regime()` 内に breadth 補正ロジックを追加:

```python
# 既存
raw_score = _MA_WEIGHT * (ma200_ratio - 1.0) * _MA_SCALE + _MACRO_WEIGHT * macro_sentiment

# 新規追加
breadth = _fetch_breadth(conn, target_date)
if breadth is not None:
    if breadth["adv_decline_ratio"] < 80:
        raw_score -= 0.2
    elif breadth["adv_decline_ratio"] > 120:
        raw_score += 0.1

# 既存（変更なし）
regime_score = max(-1.0, min(1.0, raw_score))
```

- `market_breadth` にデータがない場合（`breadth is None`）は補正なしで後方互換を保つ
- `_fetch_breadth()` はモジュール内部の関数として実装

### `src/kabusys/strategy/signal_generator.py`

**① breadth_stop チェック（新規追加）**

`generate_signals()` の BUY シグナル生成前に挿入:

```python
if _is_breadth_stop(conn, target_date):
    logger.warning(
        "breadth_stop=True: 25日MA上銘柄比率 < 35%% — 新規 BUY を全件スキップ"
    )
    return _generate_sell_signals(conn, target_date, score_map, threshold)
```

**② `_is_bear_regime()` バグ修正**

```python
# 修正前（ai_scores.regime_score は常 NULL のため常に False）
def _is_bear_regime(ai_map: dict) -> bool: ...

# 修正後（market_regime.regime_label を直接参照）
def _is_bear_regime(conn: duckdb.DuckDBPyConnection, target_date: date) -> bool:
    row = conn.execute(
        "SELECT regime_label FROM market_regime WHERE date = ?", [target_date]
    ).fetchone()
    if row is None:
        return False  # データなし → 安全側（BUY 許可）
    return row[0] == "bear"
```

### `scripts/run_data_update.py`

`run_prices_etl()` の後に `calc_and_save_breadth()` の呼び出しを追加。

---

## 7. テスト

### `tests/test_breadth.py`（新規）

| テスト | 検証内容 |
|-------|---------|
| `test_adv_decline_ratio_normal` | 混在データで騰落レシオが正しく計算される |
| `test_adv_decline_ratio_no_declines` | 値下がり 0 件 → 200.0 |
| `test_ma25_above_pct` | close > ma25 の銘柄比率が正しく計算される |
| `test_new_high_low_ratio_normal` | 52週高値/安値比率が正しく計算される |
| `test_new_high_low_ratio_no_lows` | 新安値 0 件 → NULL |
| `test_breadth_stop_true` | ma25_above_pct < 0.35 → True |
| `test_breadth_stop_false` | ma25_above_pct >= 0.35 → False |
| `test_insufficient_data_returns_zero` | 25 日分未満 → 0 を返す |
| `test_idempotent` | 同日 2 回実行しても DB 行が重複しない |

### `tests/test_regime_detector.py`（既存に追加）

| テスト | 検証内容 |
|-------|---------|
| `test_breadth_correction_low_adv_decline` | 騰落レシオ < 80 → raw_score が -0.2 補正 |
| `test_breadth_correction_high_adv_decline` | 騰落レシオ > 120 → raw_score が +0.1 補正 |
| `test_breadth_correction_neutral` | 騰落レシオ 80〜120 → 補正なし |
| `test_breadth_missing_no_correction` | `market_breadth` データなし → 既存ロジックのみ |
| `test_regime_clips_to_range` | 補正後も regime_score が [-1.0, 1.0] に収まる |

### `tests/test_signal_generator.py`（既存に追加）

| テスト | 検証内容 |
|-------|---------|
| `test_breadth_stop_skips_buy_signals` | breadth_stop=True → BUY=0、SELL は通常通り |
| `test_breadth_stop_false_allows_buy` | breadth_stop=False → BUY が通常通り生成 |
| `test_is_bear_regime_from_market_regime` | regime_label='bear' → True |
| `test_is_bear_regime_bull_returns_false` | regime_label='bull' → False |
| `test_is_bear_regime_no_data_returns_false` | データなし → False |

全テストはインメモリ DuckDB + `init_schema()` で動作し、外部 API 依存なし。

---

## 8. 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `src/kabusys/data/schema.py` | `market_breadth` テーブル追加 |
| `src/kabusys/data/breadth.py` | 新規 |
| `src/kabusys/ai/regime_detector.py` | breadth 補正ロジック追加 |
| `src/kabusys/strategy/signal_generator.py` | breadth_stop + `_is_bear_regime` バグ修正 |
| `scripts/run_data_update.py` | `calc_and_save_breadth()` 呼び出し追加 |
| `tests/test_breadth.py` | 新規 |
| `tests/test_regime_detector.py` | breadth 補正テスト追加 |
| `tests/test_signal_generator.py` | breadth_stop テスト追加 |
