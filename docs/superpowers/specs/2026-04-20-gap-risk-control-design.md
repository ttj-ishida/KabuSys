# 設計仕様: ギャップリスク制御

- **Issue**: #170
- **作成日**: 2026-04-20
- **ステータス**: 承認済み

---

## 1. 目的

新規 BUY シグナル生成時に、当日の始値と前日終値の乖離（ギャップ）が過大な銘柄を個別に抑制する。
短期の価格飛躍が大きい銘柄への不利なエントリーを防ぎ、約定コストとスリッページリスクを低減する。

---

## 2. ルール定義

| 条件 | 閾値 | 判定 |
|-----|------|------|
| ギャップアップ過大 | `open_today / close_prev - 1 > +0.05`（+5% **超**） | BUY 抑制 |
| ギャップダウン過大 | `open_today / close_prev - 1 <= -0.03`（-3% **以下**） | BUY 抑制 |
| 上記以外 | — | BUY 許可 |

境界値の扱い:
- ちょうど `+5.0%`（gap_ratio = 0.05）→ BUY 許可（超ではないため）
- ちょうど `-3.0%`（gap_ratio = -0.03）→ BUY 抑制（以下に含まれるため）

SELL シグナルはギャップ条件に関わらず通常通り生成する（執行優先）。

---

## 3. アーキテクチャ

`signal_generator.py` のみ変更。新規ファイル・スキーマ変更なし。

```
generate_signals(conn, target_date)
  ステップ3:  Bear レジームチェック（既存）
  ステップ3b: breadth_stop チェック（既存 #173）
  ステップ3c: gap_ratios 一括取得（新規）← _fetch_gap_ratios()
  ステップ6:  BUY 生成ループ内でギャップ判定（新規）← _is_gap_excessive()
```

`target_date` の当日 open と前日 close は `prices_daily` から取得する。
既存の `_is_bear_regime()` / `_is_breadth_stop()` と同じ設計パターン。

---

## 4. 実装詳細

### 4.1 新規定数

```python
_GAP_UP_THRESHOLD   = 0.05   # gap_ratio > 0.05 でギャップアップ過大
_GAP_DOWN_THRESHOLD = -0.03  # gap_ratio <= -0.03 でギャップダウン過大
```

### 4.2 新規関数 `_fetch_gap_ratios`

```python
def _fetch_gap_ratios(
    conn: duckdb.DuckDBPyConnection,
    codes: list[str],
    target_date: date,
) -> dict[str, float]:
    """target_date の open / 前日 close - 1.0 を銘柄ごとに返す。

    Returns:
        {code: gap_ratio} — データ欠損銘柄はキーなし（BUY 許可・安全側）。
    """
    if not codes:
        return {}
    rows = conn.execute(
        """
        SELECT t.code,
               CAST(t.open AS DOUBLE) / CAST(p.close AS DOUBLE) - 1.0
        FROM prices_daily t
        JOIN prices_daily p
          ON p.code = t.code
         AND p.date = (
             SELECT MAX(date) FROM prices_daily
             WHERE code = t.code AND date < ?
         )
        WHERE t.date = ?
          AND t.code = ANY(?)
          AND CAST(p.close AS DOUBLE) > 0
        """,
        [target_date, target_date, codes],
    ).fetchall()
    return {code: ratio for code, ratio in rows}
```

### 4.3 ステップ6の変更（BUY シグナル生成）

```python
# [3c] ギャップ比率を一括取得
gap_ratios = _fetch_gap_ratios(conn, [r["code"] for r in scored], target_date)

# [6] BUY シグナル生成（Bear / breadth_stop / gap フィルタ）
buy_signals: list[dict] = []
if not regime_is_bear and not breadth_stop:
    for rank, r in enumerate(scored, 1):
        if r["score"] < threshold:
            continue
        gap = gap_ratios.get(r["code"])
        if gap is not None and (
            gap > _GAP_UP_THRESHOLD or gap <= _GAP_DOWN_THRESHOLD
        ):
            logger.info(
                "gap filter: %s gap=%.2f%% — BUY を抑制 date=%s",
                r["code"],
                gap * 100,
                target_date,
            )
            continue
        buy_signals.append({"code": r["code"], "score": r["score"], "rank": rank})
```

---

## 5. エラー処理

- `prices_daily` に `target_date` の open データなし → `_fetch_gap_ratios` の結果にキーなし → BUY 許可（安全側）
- 前日データなし（初回上場直後など）→ 同上、BUY 許可
- `prev_close = 0` → SQL の `AND CAST(p.close AS DOUBLE) > 0` でゼロ除算を排除

---

## 6. テスト

### `tests/test_signal_generator.py`（既存ファイルに追加）

| テスト名 | 検証内容 |
|---------|---------|
| `test_gap_up_suppresses_buy` | gap +5.1% → BUY 抑制 |
| `test_gap_down_suppresses_buy` | gap -3.0% → BUY 抑制（境界値: 以下に含む） |
| `test_gap_up_at_threshold_allows_buy` | gap ちょうど +5.0% → BUY 許可（超ではない） |
| `test_gap_down_just_above_threshold_allows_buy` | gap -2.9% → BUY 許可 |
| `test_gap_missing_data_allows_buy` | 前日データなし → BUY 許可（安全側） |
| `test_sell_not_affected_by_gap` | gap 過大でも SELL は通常生成される |

全テストはインメモリ DuckDB + `prices_daily` テーブルで動作し、外部 API 依存なし。

---

## 7. 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `src/kabusys/strategy/signal_generator.py` | 定数追加・`_fetch_gap_ratios` 追加・ステップ6変更 |
| `tests/test_signal_generator.py` | ギャップフィルタテスト追加 |
