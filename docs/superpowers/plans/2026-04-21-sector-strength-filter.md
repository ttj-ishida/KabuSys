# セクター相対強弱フィルタ実装プラン (Issue #172)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** セクター20営業日リターンを算出し、上位25%セクターのfinal_scoreに+0.03補正、下位25%セクターの新規BUYを禁止する。

**Architecture:** `signal_generator.py` に `_calc_sector_strengths()` ヘルパーを追加し、`generate_signals()` のステップ3c（セクター強弱分類）・ステップ4（スコア補正）・ステップ6（BUY抑制）へ統合する。ギャップリスクフィルタ（Issue #170）と同一パターン。変更は `signal_generator.py` と `tests/test_strategy.py` の2ファイルのみ。

**Tech Stack:** Python 3.10+, DuckDB（`:memory:` テスト用）, pytest

---

## ファイル構成

| ファイル | 変更内容 |
|---------|---------|
| `src/kabusys/strategy/signal_generator.py` | 定数2件追加、`_calc_sector_strengths` 新規追加、`generate_signals` にステップ3c/4/6の変更 |
| `tests/test_strategy.py` | `_calc_sector_strengths` 単体テスト5件 + `generate_signals` 統合テスト6件追加 |

---

## 背景知識（コードベース）

**`generate_signals` の現在のフロー（`src/kabusys/strategy/signal_generator.py:303`付近）:**
```
Step 1: features 読み込み
Step 2: AI スコア読み込み
Step 3: Bear レジーム判定 (_is_bear_regime)
Step 3b: breadth_stop 判定 (_is_breadth_stop)
Step 4: 各銘柄の final_score 計算（ループ）
Step 5: スコア降順ソート
Step 6: BUY ループ（ギャップフィルタ含む）
Step 7: SELL シグナル生成
Step 8: signals テーブルへ書き込み
```

**`stocks` テーブルスキーマ（`src/kabusys/data/schema.py:147`）:**
```sql
CREATE TABLE IF NOT EXISTS stocks (
    code        VARCHAR     NOT NULL,
    name        VARCHAR,
    market      VARCHAR,
    sector      VARCHAR,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (code)
)
```

**既存の定数（`signal_generator.py:47-58`）:**
```python
_DEFAULT_THRESHOLD: float = 0.60
_STOP_LOSS_RATE: float = -0.08
_GAP_UP_THRESHOLD: float = 0.05
_GAP_DOWN_THRESHOLD: float = -0.03
_GAP_THRESHOLD_EPSILON: float = 1e-9
```

**テストファイルの import（`tests/test_strategy.py:18-27`）:**
```python
from kabusys.strategy.signal_generator import (
    _compute_liquidity_score,
    _compute_momentum_score,
    _compute_value_score,
    _compute_volatility_score,
    _fetch_gap_ratios,
    _is_bear_regime,
    _sigmoid,
    generate_signals,
)
```

**既存テストヘルパー（`tests/test_strategy.py:45-74`）:**
```python
TARGET_DATE = date(2020, 6, 1)
_HISTORY_START = date(2019, 6, 1)

def _insert_price_history(conn, codes_and_params, start=_HISTORY_START, end=TARGET_DATE):
    # (code, close, turnover) を平日分挿入する
```

**`_calc_sector_strengths` の score計算（boost テスト用の参考値）:**
以下の features 設定で final_score ≈ 0.562 になる（threshold=0.58 で threshold 未満）:
```python
momentum_20=1.0, momentum_60=1.0, ma200_dev=0.0,
volatility_20=0.0, volume_ratio=0.0, per=NULL
```
→ s_mom = avg([sigmoid(1.0), sigmoid(1.0), sigmoid(0.0)]) = avg([0.731, 0.731, 0.5]) = 0.654
→ final = 0.40×0.654 + 0.60×0.5 = 0.5616
→ with boost: 0.5616 + 0.03 = 0.5916 > 0.58

---

## Task 1: `_calc_sector_strengths` ヘルパーと単体テスト

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py`
- Test: `tests/test_strategy.py`

- [ ] **Step 1: テストヘルパー関数を test_strategy.py に追加する**

`tests/test_strategy.py` の `_PREV_DATE = date(2020, 5, 29)` 行（765行目）の直前に追加：

```python
# ---------------------------------------------------------------------------
# セクター強弱テスト用ヘルパー
# ---------------------------------------------------------------------------

import datetime as _dt


def _insert_sector_test_data(
    conn: duckdb.DuckDBPyConnection,
    sector_data: list[tuple[str, str, float, float]],
    target_date: date = TARGET_DATE,
) -> None:
    """セクター強弱テスト用: stocks と prices_daily の最小セットを挿入する。

    Args:
        sector_data: [(code, sector, close_today, close_20d_ago), ...]
                     sector が空文字の場合は stocks に挿入しない。
        target_date: シグナル生成対象日（デフォルト TARGET_DATE）。
    """
    # 21 営業日分の日付を降順で生成（rn=1=target_date, rn=21=20営業日前）
    biz_dates: list[date] = []
    d = target_date
    while len(biz_dates) < 21:
        if d.weekday() < 5:
            biz_dates.append(d)
        d = d - _dt.timedelta(days=1)
    date_20d = biz_dates[20]  # 20 営業日前の日付

    for code, sector, close_today, close_20d_ago in sector_data:
        if sector:
            conn.execute(
                "INSERT INTO stocks (code, sector) VALUES (?, ?)",
                [code, sector],
            )
        # target_date の価格
        conn.execute(
            "INSERT INTO prices_daily "
            "(date, code, open, high, low, close, volume, turnover) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [target_date, code,
             close_today, close_today, close_today, close_today,
             1_000_000, 5e8],
        )
        # 20 営業日前の価格
        conn.execute(
            "INSERT INTO prices_daily "
            "(date, code, open, high, low, close, volume, turnover) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [date_20d, code,
             close_20d_ago, close_20d_ago, close_20d_ago, close_20d_ago,
             1_000_000, 5e8],
        )
        # 中間日付を埋める（biz_dates[1..19]、rn=2..20 が存在するために必要）
        for mid_d in biz_dates[1:20]:
            conn.execute(
                "INSERT INTO prices_daily "
                "(date, code, open, high, low, close, volume, turnover) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [mid_d, code,
                 close_today, close_today, close_today, close_today,
                 1_000_000, 5e8],
            )
```

- [ ] **Step 2: `_calc_sector_strengths` の import を追加する**

`tests/test_strategy.py` の import ブロック（18-27行目）を以下に更新：

```python
from kabusys.strategy.signal_generator import (
    _calc_sector_strengths,
    _compute_liquidity_score,
    _compute_momentum_score,
    _compute_value_score,
    _compute_volatility_score,
    _fetch_gap_ratios,
    _is_bear_regime,
    _sigmoid,
    generate_signals,
)
```

- [ ] **Step 3: 単体テストを test_strategy.py に追記する**

`tests/test_strategy.py` のセクター強弱テスト用ヘルパーの直後に追加：

```python
# ---------------------------------------------------------------------------
# _calc_sector_strengths 単体テスト
# ---------------------------------------------------------------------------


def test_calc_sector_strengths_basic(conn):
    """4セクター正常ケース: top/bottom 各1セクターが正しく分類される"""
    # セクターリターン: Tech=+10%, Food=+5%, Energy=+2%, Retail=-5%
    # → top={Tech}, bottom={Retail}
    _insert_sector_test_data(conn, [
        ("T1", "Tech",   1100.0, 1000.0),  # +10%
        ("T2", "Tech",   1100.0, 1000.0),
        ("F1", "Food",   1050.0, 1000.0),  # +5%
        ("E1", "Energy", 1020.0, 1000.0),  # +2%
        ("R1", "Retail",  950.0, 1000.0),  # -5%
    ])
    top, bottom, sector_map = _calc_sector_strengths(conn, TARGET_DATE)
    assert "Tech" in top
    assert "Retail" in bottom
    assert "Food" not in top and "Food" not in bottom
    assert "Energy" not in top and "Energy" not in bottom
    # sector_map に全銘柄が含まれる
    assert sector_map["T1"] == "Tech"
    assert sector_map["R1"] == "Retail"


def test_calc_sector_strengths_single_sector(conn):
    """有効セクターが1つ → top と bottom が同一 → 両方 frozenset() を返す"""
    _insert_sector_test_data(conn, [
        ("A1", "Tech", 1100.0, 1000.0),
        ("A2", "Tech", 1200.0, 1000.0),
    ])
    top, bottom, sector_map = _calc_sector_strengths(conn, TARGET_DATE)
    assert top == frozenset()
    assert bottom == frozenset()
    # sector_map は正常に返る
    assert sector_map["A1"] == "Tech"


def test_calc_sector_strengths_no_20d_data(conn):
    """20営業日前のデータがない → rows 空 → (frozenset, frozenset, map) を返す"""
    # prices_daily に1日分しか入れない（21日分の distinct date がない）
    conn.execute(
        "INSERT INTO stocks (code, sector) VALUES (?, ?)", ["A", "Tech"]
    )
    conn.execute(
        "INSERT INTO prices_daily "
        "(date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [TARGET_DATE, "A", 1000.0, 1000.0, 1000.0, 1000.0, 1_000_000, 5e8],
    )
    top, bottom, sector_map = _calc_sector_strengths(conn, TARGET_DATE)
    assert top == frozenset()
    assert bottom == frozenset()
    # sector_map は取得できる
    assert sector_map.get("A") == "Tech"


def test_calc_sector_strengths_unknown_sector_excluded(conn):
    """sector=NULL の銘柄は sector_map に含まれない（安全側）"""
    # sector ありの銘柄と sector なしの銘柄を混在させる
    _insert_sector_test_data(conn, [
        ("A", "Tech",  1100.0, 1000.0),
        ("B", "Food",   950.0, 1000.0),
    ])
    # sector なし銘柄（stocks に挿入しない → sector_map に含まれない）
    conn.execute(
        "INSERT INTO prices_daily "
        "(date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [TARGET_DATE, "C", 1050.0, 1050.0, 1050.0, 1050.0, 1_000_000, 5e8],
    )
    top, bottom, sector_map = _calc_sector_strengths(conn, TARGET_DATE)
    assert "C" not in sector_map
    assert "A" in sector_map


def test_calc_sector_strengths_empty_stocks(conn):
    """stocks テーブルが空 → (frozenset, frozenset, {}) を返す"""
    top, bottom, sector_map = _calc_sector_strengths(conn, TARGET_DATE)
    assert top == frozenset()
    assert bottom == frozenset()
    assert sector_map == {}
```

- [ ] **Step 4: テストが FAIL することを確認する**

```bash
cd C:/Users/tetsu/Projects/KabuSys/.worktrees/issue-172-sector-filter
python -m pytest tests/test_strategy.py::test_calc_sector_strengths_basic -v
```

Expected: `ImportError: cannot import name '_calc_sector_strengths'`

- [ ] **Step 5: 定数を `signal_generator.py` に追加する**

`signal_generator.py` の `_GAP_THRESHOLD_EPSILON: float = 1e-9` 行（58行目）の直後に追加：

```python
_SECTOR_BOOST: float = 0.03    # 上位 _SECTOR_QUARTILE セクター銘柄への final_score 加算量
_SECTOR_QUARTILE: float = 0.25 # 上位・下位の区切り割合（各 ceil(N×0.25) セクター）
```

- [ ] **Step 6: `_calc_sector_strengths` 関数を `signal_generator.py` に追加する**

`_fetch_gap_ratios` 関数（155行目付近）の直後、`_generate_sell_signals` の前に追加：

```python
def _calc_sector_strengths(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> tuple[frozenset[str], frozenset[str], dict[str, str]]:
    """セクター20営業日リターンを算出し、上位・下位セクターと銘柄→セクターマップを返す。

    stocks テーブルの全銘柄 × prices_daily で等加重セクターリターンを計算し、
    上位 _SECTOR_QUARTILE / 下位 _SECTOR_QUARTILE のセクターを分類する。

    データ欠損・セクター未登録銘柄は安全側（BUY 許可・スコアブーストなし）に倒す。

    Returns:
        (top_sectors, bottom_sectors, sector_map)
        - top_sectors:    上位 _SECTOR_QUARTILE セクター名の frozenset
        - bottom_sectors: 下位 _SECTOR_QUARTILE セクター名の frozenset
        - sector_map:     {code: sector}（NULL/空文字のセクターは除外）

    Note: 有効セクターが1つの場合は top と bottom が同一になるためフィルタ無効。
    """
    # sector_map を取得（NULL / 空白のみは除外）
    sector_rows = conn.execute(
        "SELECT code, NULLIF(TRIM(sector), '') FROM stocks"
    ).fetchall()
    sector_map: dict[str, str] = {code: sec for code, sec in sector_rows if sec}

    if not sector_map:
        return frozenset(), frozenset(), {}

    # セクター別20営業日等加重リターンを算出
    # biz_dates: prices_daily の distinct date を降順番号付け（rn=1=target_date, rn=21=20営業日前）
    rows = conn.execute(
        """
        WITH biz_dates AS (
            SELECT date,
                   ROW_NUMBER() OVER (ORDER BY date DESC) AS rn
            FROM (SELECT DISTINCT date FROM prices_daily WHERE date <= ?)
        ),
        date_20d AS (
            SELECT date FROM biz_dates WHERE rn = 21
        )
        SELECT
            s.sector,
            AVG(CAST(cur.close AS DOUBLE) / CAST(prev.close AS DOUBLE) - 1.0) AS ret
        FROM stocks s
        JOIN prices_daily cur
          ON cur.code = s.code AND cur.date = ?
        JOIN prices_daily prev
          ON prev.code = s.code
         AND prev.date = (SELECT date FROM date_20d)
        WHERE NULLIF(TRIM(s.sector), '') IS NOT NULL
          AND CAST(cur.close AS DOUBLE) > 0
          AND CAST(prev.close AS DOUBLE) > 0
        GROUP BY s.sector
        ORDER BY ret DESC
        """,
        [target_date, target_date],
    ).fetchall()

    if not rows:
        return frozenset(), frozenset(), sector_map

    n = len(rows)
    top_n = max(1, math.ceil(n * _SECTOR_QUARTILE))
    bottom_n = max(1, math.ceil(n * _SECTOR_QUARTILE))

    top_sectors = frozenset(s for s, _ in rows[:top_n])
    bottom_sectors = frozenset(s for s, _ in rows[-bottom_n:])

    # オーバーラップ（n=1 など top と bottom が同一セクターを含む）→ 両方空
    if top_sectors & bottom_sectors:
        logger.debug(
            "_calc_sector_strengths: top/bottom オーバーラップ（セクター数=%d）"
            " — フィルタ無効 date=%s",
            n,
            target_date,
        )
        return frozenset(), frozenset(), sector_map

    logger.info(
        "_calc_sector_strengths: top=%s bottom=%s date=%s",
        sorted(top_sectors),
        sorted(bottom_sectors),
        target_date,
    )
    return top_sectors, bottom_sectors, sector_map
```

- [ ] **Step 7: 単体テストが PASS することを確認する**

```bash
python -m pytest tests/test_strategy.py::test_calc_sector_strengths_basic \
  tests/test_strategy.py::test_calc_sector_strengths_single_sector \
  tests/test_strategy.py::test_calc_sector_strengths_no_20d_data \
  tests/test_strategy.py::test_calc_sector_strengths_unknown_sector_excluded \
  tests/test_strategy.py::test_calc_sector_strengths_empty_stocks -v
```

Expected: 5 passed

- [ ] **Step 8: 全テストが通ることを確認する**

```bash
python -m pytest tests/ -q
```

Expected: 830+ passed, 0 failed

- [ ] **Step 9: コミットする**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_strategy.py
git commit -m "feat: add _calc_sector_strengths helper with unit tests (Issue #172)"
```

---

## Task 2: `generate_signals` への統合と統合テスト

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py`
- Test: `tests/test_strategy.py`

- [ ] **Step 1: 統合テストを test_strategy.py に追記する**

既存のセクター単体テストの末尾（`test_calc_sector_strengths_empty_stocks` の後）に追加：

```python
# ---------------------------------------------------------------------------
# generate_signals — セクター強弱フィルタ統合テスト
# ---------------------------------------------------------------------------


def test_sector_bottom_suppresses_buy(conn):
    """下位セクター銘柄の BUY が抑制される"""
    # 4 セクター: Tech(+10%), Food(+5%), Energy(+2%), Retail(-5%)
    # → bottom = {Retail}
    # 各セクター2銘柄: R1, R2 は Retail (bottom) → BUY 抑制
    # T1 は Tech (top) → BUY 通過（スコアブースト付き）
    _insert_sector_test_data(conn, [
        ("T1", "Tech",   1100.0, 1000.0),
        ("T2", "Tech",   1100.0, 1000.0),
        ("F1", "Food",   1050.0, 1000.0),
        ("F2", "Food",   1050.0, 1000.0),
        ("E1", "Energy", 1020.0, 1000.0),
        ("E2", "Energy", 1020.0, 1000.0),
        ("R1", "Retail",  950.0, 1000.0),
        ("R2", "Retail",  950.0, 1000.0),
    ])
    # features に高スコアを設定（全銘柄 BUY 候補）
    for code in ["T1", "T2", "F1", "F2", "E1", "E2", "R1", "R2"]:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, 0.0, 0.0, 20.0, 0.0)",
            [TARGET_DATE, code],
        )
    generate_signals(conn, TARGET_DATE)
    buy_codes = {
        row[0]
        for row in conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [TARGET_DATE],
        ).fetchall()
    }
    assert "R1" not in buy_codes, "Retail（下位セクター）は BUY 抑制されるべき"
    assert "R2" not in buy_codes, "Retail（下位セクター）は BUY 抑制されるべき"
    assert "T1" in buy_codes, "Tech（上位セクター）は BUY 通過するべき"


def test_sector_boost_pushes_score_above_threshold(conn):
    """上位セクター補正 +0.03 でスコアが閾値を超えて BUY が生成される"""
    # Tech が top セクター（+10%）、Food が bottom（-5%）
    # A: Tech (上位) → boost で閾値超え → BUY
    # B: Energy (中立) → boost なし → BUY なし
    _insert_sector_test_data(conn, [
        ("A",  "Tech",   1100.0, 1000.0),  # top sector (+10%)
        ("B",  "Energy", 1000.0, 1000.0),  # neutral (0%)
        ("C",  "Food",    950.0, 1000.0),  # bottom sector (-5%)
        ("D",  "Retail", 1020.0, 1000.0),  # for 4th sector
    ])
    # A, B の features を threshold=0.58 の直下になるよう設定
    # momentum_20=1.0, momentum_60=1.0 → final_score ≈ 0.5616 < 0.58
    for code in ["A", "B", "C", "D"]:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 1.0, 1.0, 0.0, 0.0, NULL, 0.0)",
            [TARGET_DATE, code],
        )
    # threshold=0.58 で実行（default 0.60 より低く設定してブーストの効果を確認）
    generate_signals(conn, TARGET_DATE, threshold=0.58)
    buy_codes = {
        row[0]
        for row in conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [TARGET_DATE],
        ).fetchall()
    }
    assert "A" in buy_codes, "Tech（上位セクター +0.03 boost）→ 0.5916 > 0.58 で BUY"
    assert "B" not in buy_codes, "Energy（中立）→ 0.5616 < 0.58 で BUY なし"


def test_sector_unknown_not_affected(conn):
    """セクター未登録銘柄はブーストも抑制もされない"""
    # Tech(top) と Unknown(未登録) の2セクター
    # Unknown は stocks に登録しない → sector_map に含まれない
    _insert_sector_test_data(conn, [
        ("T1", "Tech",   1100.0, 1000.0),  # top sector
        ("T2", "Tech",   1100.0, 1000.0),
        ("U1", "Food",    950.0, 1000.0),  # bottom sector
        ("U2", "Food",    950.0, 1000.0),
    ])
    # X は stocks に登録しない（sector 不明）
    conn.execute(
        "INSERT INTO prices_daily "
        "(date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [TARGET_DATE, "X", 1100.0, 1100.0, 1100.0, 1100.0, 1_000_000, 5e8],
    )
    for code in ["T1", "T2", "U1", "U2", "X"]:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, 0.0, 0.0, 20.0, 0.0)",
            [TARGET_DATE, code],
        )
    generate_signals(conn, TARGET_DATE)
    buy_codes = {
        row[0]
        for row in conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [TARGET_DATE],
        ).fetchall()
    }
    # X は bottom セクターでも top セクターでもない → BUY 通過
    assert "X" in buy_codes, "セクター未登録銘柄は抑制されない"
    # U1, U2 は Food (bottom) → 抑制
    assert "U1" not in buy_codes
    assert "U2" not in buy_codes


def test_sector_filter_skipped_in_bear(conn):
    """Bear レジーム時はセクターフィルタが適用されない（_calc_sector_strengths 呼ばれない）"""
    _insert_sector_test_data(conn, [
        ("A", "Tech",   1100.0, 1000.0),
        ("B", "Retail",  950.0, 1000.0),
    ])
    # Bear レジームを設定
    conn.execute(
        "INSERT INTO market_regime (date, regime_label, regime_score) VALUES (?, 'bear', -0.5)",
        [TARGET_DATE],
    )
    for code in ["A", "B"]:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, 0.0, 0.0, 20.0, 0.0)",
            [TARGET_DATE, code],
        )
    count = generate_signals(conn, TARGET_DATE)
    # Bear なので BUY は 0
    buy_count = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
    ).fetchone()[0]
    assert buy_count == 0, "Bear レジームでは BUY が生成されない"


def test_sector_sell_not_affected(conn):
    """SELL シグナルはセクターフィルタの対象外"""
    _insert_sector_test_data(conn, [
        ("A", "Retail", 950.0, 1000.0),  # bottom sector
    ])
    # 保有ポジション（A を保有中）
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) "
        "VALUES (?, ?, ?, ?)",
        [TARGET_DATE, "A", 100, 1200.0],
    )
    # A の価格をストップロス水準に設定（close = 1200 * 0.9 = 1080）
    conn.execute(
        "INSERT INTO prices_daily "
        "(date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [TARGET_DATE, "A", 1080.0, 1080.0, 1080.0, 1080.0, 1_000_000, 5e8],
    )
    conn.execute(
        "INSERT INTO features "
        "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
        "VALUES (?, ?, -3.0, -3.0, 0.0, 0.0, 20.0, 0.0)",
        [TARGET_DATE, "A"],
    )
    generate_signals(conn, TARGET_DATE)
    sell_count = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE date = ? AND side = 'sell' AND code = 'A'",
        [TARGET_DATE],
    ).fetchone()[0]
    assert sell_count == 1, "SELL はセクターフィルタの対象外"


def test_sector_single_sector_no_filter(conn):
    """有効セクターが1つの場合はフィルタが無効（BUY は通常通り生成される）"""
    _insert_sector_test_data(conn, [
        ("A", "Tech", 1100.0, 1000.0),
        ("B", "Tech", 1200.0, 1000.0),
    ])
    for code in ["A", "B"]:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, 0.0, 0.0, 20.0, 0.0)",
            [TARGET_DATE, code],
        )
    generate_signals(conn, TARGET_DATE)
    buy_codes = {
        row[0]
        for row in conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [TARGET_DATE],
        ).fetchall()
    }
    # セクターが1つ → フィルタ無効 → 高スコアの両銘柄が BUY
    assert "A" in buy_codes
    assert "B" in buy_codes
```

- [ ] **Step 2: 統合テストが FAIL することを確認する**

```bash
python -m pytest tests/test_strategy.py::test_sector_bottom_suppresses_buy -v
```

Expected: FAIL（`_calc_sector_strengths` は存在するが `generate_signals` に統合されていない）

- [ ] **Step 3: `generate_signals` にステップ 3c を追加する（セクター強弱分類）**

`signal_generator.py` の breadth_stop 判定ブロック末尾（`"generate_signals: breadth_stop=True..."` の logger.warning の後）に追加：

```python
    # 3c. セクター強弱分類（Bear レジーム / breadth_stop では BUY 不要なためスキップ）
    top_sectors: frozenset[str] = frozenset()
    bottom_sectors: frozenset[str] = frozenset()
    sector_map: dict[str, str] = {}
    if not regime_is_bear and not breadth_stop:
        top_sectors, bottom_sectors, sector_map = _calc_sector_strengths(conn, target_date)
        boosted_count = 0
```

- [ ] **Step 4: `generate_signals` のステップ 4（final_score 計算）にセクターブーストを追加する**

`signal_generator.py` の `scored.append({"code": code, "score": final_score})` 行（423行目付近）の直前に追加：

```python
        # セクター強弱スコア補正（上位セクターは +_SECTOR_BOOST）
        sector = sector_map.get(code, "")
        if sector and sector in top_sectors:
            old_score = final_score
            final_score += _SECTOR_BOOST
            logger.debug(
                "sector boost: %s sector=%s score %.4f→%.4f date=%s",
                code,
                sector,
                old_score,
                final_score,
                target_date,
            )
            boosted_count += 1
```

次に、ステップ 4 のループ終了後（`scored.sort(...)` の直前）にサマリーログを追加：

```python
    if not regime_is_bear and not breadth_stop and boosted_count:
        logger.info(
            "generate_signals: sector boost — %d 銘柄をスコアブースト date=%s",
            boosted_count,
            target_date,
        )
```

- [ ] **Step 5: `generate_signals` のステップ 6（BUY ループ）にセクター抑制を追加する**

`signal_generator.py` の `gap_suppressed = 0` 行（436行目付近）の直後に追加：

```python
        sector_suppressed = 0
```

次に、BUY ループ内のギャップフィルタ `continue` の直後（`buy_signals.append(...)` の直前）に追加：

```python
            # セクター下位フィルタ
            sector = sector_map.get(r["code"], "")
            if sector and sector in bottom_sectors:
                logger.debug(
                    "sector filter: %s sector=%s — BUY を抑制 date=%s",
                    r["code"],
                    sector,
                    target_date,
                )
                sector_suppressed += 1
                continue
```

最後に、既存の `if gap_suppressed:` ブロックの直後にサマリーログを追加：

```python
        if sector_suppressed:
            logger.info(
                "generate_signals: sector filter — %d 銘柄を下位セクターで抑制 date=%s",
                sector_suppressed,
                target_date,
            )
```

- [ ] **Step 6: 統合テストが PASS することを確認する**

```bash
python -m pytest tests/test_strategy.py::test_sector_bottom_suppresses_buy \
  tests/test_strategy.py::test_sector_boost_pushes_score_above_threshold \
  tests/test_strategy.py::test_sector_unknown_not_affected \
  tests/test_strategy.py::test_sector_filter_skipped_in_bear \
  tests/test_strategy.py::test_sector_sell_not_affected \
  tests/test_strategy.py::test_sector_single_sector_no_filter -v
```

Expected: 6 passed

- [ ] **Step 7: 全テストが通ることを確認する**

```bash
python -m pytest tests/ -q
```

Expected: 841+ passed（830 既存 + 11 新規）, 0 failed

- [ ] **Step 8: lint チェックを通す**

```bash
python -m ruff check . && python -m ruff format --check .
```

Expected: `All checks passed!`

- [ ] **Step 9: コミットする**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_strategy.py
git commit -m "feat: integrate sector strength filter into generate_signals (Issue #172)"
```

---

## 完了確認チェックリスト

- [ ] `_calc_sector_strengths` の単体テスト 5 件がすべて PASS
- [ ] `generate_signals` の統合テスト 6 件がすべて PASS
- [ ] `python -m pytest tests/ -q` で全テスト PASS
- [ ] `python -m ruff check .` でエラーなし
- [ ] `generate_signals` のモジュール docstring（8-15行目）にステップ 3c の記述を追加

```
  3. Bear レジームフィルタ（Bear 相場では BUY シグナルを抑制）
  3b. breadth_stop フィルタ（25日MA上銘柄比率 < 35% で BUY 全件停止）
  3c. セクター相対強弱フィルタ（下位25%セクター BUY 抑制 / 上位25% スコア +0.03）  ← 追加
  4. final_score = 重み付き合算（StrategyModel.md Section 4.1）+ セクターブースト
```
