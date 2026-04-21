# セクター相対強弱フィルタ 設計仕様書 (Issue #172)

## 概要

各セクターの20営業日リターンを算出し、弱含みセクター（下位25%）への新規BUYを禁止し、
強含みセクター（上位25%）のfinal_scoreに+0.03の補正を加える。
セクター集中制限（apply_sector_cap）とは独立したロジックとして実装する。

## ルール

| 分類 | 条件 | 処理 |
|------|------|------|
| 上位 25% セクター | セクター20日リターン 上位 ceil(N×0.25) 位 | final_score += 0.03 |
| 下位 25% セクター | セクター20日リターン 下位 ceil(N×0.25) 位 | 新規 BUY 禁止 |
| 中立帯（25〜75%） | 上記以外 | 変更なし |
| セクター未登録 | stocks.sector が NULL / 空文字 | 変更なし（安全側） |

N = 有効セクター数（20日前データが存在するセクターのみ）

## アーキテクチャ

### 変更ファイル
- **変更**: `src/kabusys/strategy/signal_generator.py`
- **変更**: `tests/test_strategy.py`

変更はこの2ファイルのみ。ギャップリスクフィルタ（Issue #170）と同じパターン。

### 新規定数

```python
_SECTOR_BOOST: float = 0.03    # 上位 25% セクター銘柄への final_score 加算量
_SECTOR_QUARTILE: float = 0.25 # 上位・下位の区切り割合
```

### 新規ヘルパー関数

```python
def _calc_sector_strengths(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> tuple[frozenset[str], frozenset[str], dict[str, str]]:
    """セクター20日リターンを算出し、上位・下位セクターと銘柄→セクターマップを返す。

    Returns:
        (top_sectors, bottom_sectors, sector_map)
        - top_sectors: 上位 SECTOR_QUARTILE のセクター名集合
        - bottom_sectors: 下位 SECTOR_QUARTILE のセクター名集合
        - sector_map: {code: sector}（stocks テーブル全銘柄）
    """
```

**SQL ロジック（概略）:**

```sql
WITH biz_dates AS (
    -- prices_daily の営業日を逆順に番号付け（1=target_date, 21=20営業日前）
    SELECT date, ROW_NUMBER() OVER (ORDER BY date DESC) AS rn
    FROM (SELECT DISTINCT date FROM prices_daily WHERE date <= ?)
),
date_20d AS (
    SELECT date FROM biz_dates WHERE rn = 21
),
sector_returns AS (
    SELECT
        s.sector,
        AVG(CAST(cur.close AS DOUBLE) / CAST(prev.close AS DOUBLE) - 1.0) AS ret
    FROM stocks s
    JOIN prices_daily cur ON cur.code = s.code AND cur.date = ?
    JOIN prices_daily prev ON prev.code = s.code
        AND prev.date = (SELECT date FROM date_20d)
    WHERE NULLIF(TRIM(s.sector), '') IS NOT NULL
      AND CAST(cur.close AS DOUBLE) > 0
      AND CAST(prev.close AS DOUBLE) > 0
    GROUP BY s.sector
)
SELECT sector, ret FROM sector_returns ORDER BY ret DESC
```

**Python 分類ロジック:**

```python
import math

rows = conn.execute(sql, [target_date, target_date]).fetchall()
# rows: [(sector, ret), ...] 降順ソート済み

n = len(rows)
if n == 0:
    return frozenset(), frozenset(), sector_map

top_n = max(1, math.ceil(n * _SECTOR_QUARTILE))
bottom_n = max(1, math.ceil(n * _SECTOR_QUARTILE))

top_sectors = frozenset(s for s, _ in rows[:top_n])
bottom_sectors = frozenset(s for s, _ in rows[-bottom_n:])

# オーバーラップ（n=1 の場合など）→ 両方空に
if top_sectors & bottom_sectors:
    top_sectors = frozenset()
    bottom_sectors = frozenset()
```

**sector_map 取得（同一関数内で実施）:**

```python
sector_rows = conn.execute(
    "SELECT code, NULLIF(TRIM(sector), '') FROM stocks"
).fetchall()
sector_map = {code: sec for code, sec in sector_rows if sec}
```

### generate_signals への統合

```
[Step 3b] breadth_stop 判定  ← 既存
[Step 3c] セクター強弱分類   ← 新規
    if not regime_is_bear and not breadth_stop:
        top_sectors, bottom_sectors, sector_map = _calc_sector_strengths(conn, target_date)
    else:
        top_sectors = bottom_sectors = frozenset(); sector_map = {}
    # サマリーログ（INFO）: 上位/下位セクター名と件数

[Step 4] final_score 計算    ← 既存 + セクターブースト追加
    final_score = weighted_sum(...)
    sector = sector_map.get(code, "")
    if sector and sector in top_sectors:
        final_score += _SECTOR_BOOST
        # ※クリップなし（閾値判定に上限は不要）

[Step 5] スコア降順ソート    ← 既存（ブースト後スコアでソートされる）

[Step 6] BUY ループ          ← 既存 + 下位セクター抑制追加
    # ギャップフィルタの後
    sector = sector_map.get(r["code"], "")
    if sector and sector in bottom_sectors:
        logger.debug("sector filter: %s sector=%s — BUY 抑制 date=%s", ...)
        sector_suppressed += 1
        continue
    # サマリーログ（INFO）: 抑制件数
```

## エッジケース処理

| ケース | 挙動 |
|--------|------|
| 有効セクター数 = 0 | フィルタ無効（全銘柄通過） |
| 有効セクター数 = 1 | top と bottom が同一セクター → オーバーラップ判定 → 両方空 → フィルタ無効 |
| 有効セクター数 = 2 | top 1セクター、bottom 1セクター（異なる）→ 正常分類 |
| 20日前データなし（株式） | そのセクターの算出から除外（他銘柄で平均） |
| 20日前データなしの結果セクターゼロ | フィルタ無効 |
| stocks テーブル空 | sector_map = {} → 全銘柄 sector="" → フィルタ無効 |
| regime_is_bear = True | _calc_sector_strengths を呼ばない（最適化） |
| breadth_stop = True | 同上 |
| セクター未登録銘柄 | sector="" → top/bottom の判定をスキップ（安全側: BUY許可・ブーストなし） |

## ログ設計

```
INFO  generate_signals: sector filter — top=[Food,IT,...] bottom=[Mining,Retail,...] date=YYYY-MM-DD
INFO  generate_signals: sector filter — X 銘柄を下位セクターで抑制 Y 銘柄をスコアブースト date=YYYY-MM-DD
DEBUG sector filter: <code> sector=<sector> — BUY 抑制 date=YYYY-MM-DD
DEBUG sector boost: <code> sector=<sector> score=<old>→<new> date=YYYY-MM-DD
```

## テスト設計

### `_calc_sector_strengths` 単体テスト

| テスト名 | 概要 |
|---------|------|
| `test_calc_sector_strengths_basic` | 4セクター、各2銘柄 → top/bottom 各1セクター正常分類 |
| `test_calc_sector_strengths_single_sector` | 1セクターのみ → (frozenset(), frozenset(), map) |
| `test_calc_sector_strengths_no_20d_data` | 20日前データなし → (frozenset(), frozenset(), map) |
| `test_calc_sector_strengths_unknown_sector` | sector=NULL/空 銘柄 → sector_map に含まれない |
| `test_calc_sector_strengths_empty_stocks` | stocks テーブル空 → (frozenset(), frozenset(), {}) |

### generate_signals 統合テスト

| テスト名 | 概要 |
|---------|------|
| `test_sector_boost_pushes_score_above_threshold` | スコアブーストで閾値未満→閾値超えになりBUY生成 |
| `test_sector_bottom_suppresses_buy` | 下位セクター銘柄のBUYが抑制される |
| `test_sector_unknown_not_affected` | セクター未登録銘柄はブースト・抑制なし |
| `test_sector_filter_skipped_in_bear` | regime_is_bear=True でセクターフィルタが適用されない |
| `test_sector_sell_not_affected` | SELL シグナルはセクターフィルタ対象外 |
| `test_sector_top_bottom_overlap_neutral` | 有効セクター1つ → フィルタ無効（全通過） |

## SELL への影響

SELL シグナルは `_generate_sell_signals()` で生成され、セクターフィルタを適用しない（Issue #172 の仕様通り）。

## 既存機能との関係

- **apply_sector_cap（セクター集中制限）**: 別ロジック。portfolio 構築フェーズで適用。本フィルタと独立して動作。
- **ギャップリスクフィルタ**: BUY ループ内でギャップ判定の後にセクター判定を実施。両方が抑制条件でも問題なし。
- **Bear レジーム / breadth_stop**: これらが True の場合は _calc_sector_strengths を呼ばない（BUY が全件抑制されるため不要）。
