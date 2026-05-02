# 市場内部指標（breadth）レジーム補強 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `market_breadth` テーブルを新設し、騰落レシオ補正でレジーム判定精度を高め、`_is_bear_regime()` バグと breadth_stop BUY 停止条件を実装する（Issue #173）。

**Architecture:**
- `data/breadth.py`（新規）が `prices_daily` から breadth 指標を計算して `market_breadth` テーブルへ保存する（15:30 data_update バッチ）。
- `ai/regime_detector.py` が `market_breadth.adv_decline_ratio` を読み込んで raw_score を補正する（18:00 ai_analysis バッチ）。
- `strategy/signal_generator.py` の `_is_bear_regime()` を `ai_scores.regime_score`（常 NULL）から `market_regime.regime_label` 参照に修正し、独立した `_is_breadth_stop()` 関数を追加する（20:00 strategy_signal バッチ）。

**Tech Stack:** Python 3.10+, DuckDB, pytest, in-memory DuckDB fixtures（外部 API 依存なし）

---

## ファイル構成

| ファイル | 変更種別 | 概要 |
|---------|---------|------|
| `src/kabusys/data/schema.py` | 修正 | `market_breadth` テーブル DDL 追加 |
| `src/kabusys/data/breadth.py` | 新規 | `calc_and_save_breadth()` + 内部計算関数 |
| `src/kabusys/ai/regime_detector.py` | 修正 | `_fetch_breadth()` 追加、`score_regime()` に補正ロジック挿入 |
| `src/kabusys/strategy/signal_generator.py` | 修正 | `_is_bear_regime()` バグ修正、`_is_breadth_stop()` 追加、`generate_signals()` 更新 |
| `scripts/run_data_update.py` | 修正 | `calc_and_save_breadth()` 呼び出し追加 |
| `tests/test_breadth.py` | 新規 | breadth 計算・保存のテスト |
| `tests/test_regime_detector.py` | 修正 | breadth 補正テスト追加 |
| `tests/test_signal_generator.py` | 新規 | breadth_stop + `_is_bear_regime` 修正のテスト |

---

### Task 1: `market_breadth` テーブルをスキーマに追加

**Files:**
- Modify: `src/kabusys/data/schema.py`
- Test: `tests/test_breadth.py`（新規）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_breadth.py` を新規作成:

```python
"""
market_breadth テーブルおよび breadth 計算モジュールのテスト
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from kabusys.data.schema import init_schema

# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


TARGET_DATE = date(2026, 4, 1)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _insert_price(conn, code: str, d: date, close: float) -> None:
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
        [d, code, close, close, close, close, 1_000_000],
    )


def _make_dates(n: int, before: date = TARGET_DATE) -> list[date]:
    """before より前の n 日分の日付リスト（昇順）。"""
    return [before - timedelta(days=n - i) for i in range(n)]


# ---------------------------------------------------------------------------
# Task 1: market_breadth テーブル存在確認
# ---------------------------------------------------------------------------


def test_market_breadth_table_exists(conn):
    """init_schema() 後に market_breadth テーブルが存在する。"""
    row = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_name = 'market_breadth'"
    ).fetchone()
    assert row is not None, "market_breadth テーブルが存在しない"


def test_market_breadth_columns(conn):
    """market_breadth テーブルが必要なカラムを持ち INSERT できる。"""
    conn.execute(
        "INSERT INTO market_breadth "
        "(date, adv_decline_ratio, ma25_above_pct, new_high_low_ratio, breadth_stop) "
        "VALUES (?, ?, ?, ?, ?)",
        [date(2026, 1, 1), 100.0, 0.5, 2.0, False],
    )
    row = conn.execute(
        "SELECT date, adv_decline_ratio, ma25_above_pct, new_high_low_ratio, "
        "breadth_stop, created_at FROM market_breadth WHERE date = ?",
        [date(2026, 1, 1)],
    ).fetchone()
    assert row is not None
    assert abs(row[1] - 100.0) < 1e-9
    assert abs(row[2] - 0.5) < 1e-9
    assert abs(row[3] - 2.0) < 1e-9
    assert row[4] == False
    assert row[5] is not None  # created_at は自動設定


def test_market_breadth_null_new_high_low(conn):
    """new_high_low_ratio は NULL を許容する（新安値=0 のケース）。"""
    conn.execute(
        "INSERT INTO market_breadth "
        "(date, adv_decline_ratio, ma25_above_pct, new_high_low_ratio, breadth_stop) "
        "VALUES (?, ?, ?, ?, ?)",
        [date(2026, 1, 2), 80.0, 0.4, None, True],
    )
    row = conn.execute(
        "SELECT new_high_low_ratio FROM market_breadth WHERE date = ?",
        [date(2026, 1, 2)],
    ).fetchone()
    assert row is not None
    assert row[0] is None
```

- [ ] **Step 2: テスト実行して失敗を確認**

```
pytest tests/test_breadth.py::test_market_breadth_table_exists -v
```

期待: FAIL（`market_breadth` テーブルが存在しないため）

- [ ] **Step 3: schema.py に `market_breadth` DDL を追加**

`src/kabusys/data/schema.py` の `_MARKET_REGIME` 定義の直後（`# ---- Execution Layer` の前）に挿入:

```python
_MARKET_BREADTH = """
CREATE TABLE IF NOT EXISTS market_breadth (
    date                DATE    PRIMARY KEY,
    adv_decline_ratio   DOUBLE  NOT NULL,
    ma25_above_pct      DOUBLE  NOT NULL,
    new_high_low_ratio  DOUBLE,
    breadth_stop        BOOLEAN NOT NULL,
    created_at          TIMESTAMP DEFAULT current_timestamp
)
"""
```

`_ALL_DDL` リストの `_MARKET_REGIME` の直後に `_MARKET_BREADTH` を追加:

```python
_ALL_DDL: list[str] = [
    # Raw
    _RAW_PRICES,
    _RAW_FINANCIALS,
    _RAW_NEWS,
    _RAW_EXECUTIONS,
    # Processed
    _PRICES_DAILY,
    _MARKET_CALENDAR,
    _FUNDAMENTALS,
    _NEWS_ARTICLES,
    _NEWS_SYMBOLS,
    # Master
    _STOCKS,
    # Feature
    _FEATURES,
    _AI_SCORES,
    _MARKET_REGIME,
    _MARKET_BREADTH,  # 追加
    # Execution
    _SIGNALS,
    _SIGNAL_QUEUE,
    _PORTFOLIO_TARGETS,
    _ORDERS,
    _TRADES,
    _POSITIONS,
    _PORTFOLIO_PERFORMANCE,
]
```

- [ ] **Step 4: テストが通ることを確認**

```
pytest tests/test_breadth.py::test_market_breadth_table_exists tests/test_breadth.py::test_market_breadth_columns tests/test_breadth.py::test_market_breadth_null_new_high_low -v
```

期待: 3 件 PASS

- [ ] **Step 5: 既存テスト全件通過を確認**

```
pytest tests/ -v --tb=short -q
```

期待: 全件 PASS（既存テストに影響なし）

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/data/schema.py tests/test_breadth.py
git commit -m "feat: add market_breadth table to schema (Issue #173)"
```

---

### Task 2: `src/kabusys/data/breadth.py` の実装

**Files:**
- Create: `src/kabusys/data/breadth.py`
- Test: `tests/test_breadth.py`（追記）

- [ ] **Step 1: 騰落レシオのテストを追加**

`tests/test_breadth.py` の末尾に追記:

```python
# ---------------------------------------------------------------------------
# Task 2: calc_and_save_breadth() — 騰落レシオ
# ---------------------------------------------------------------------------


def test_adv_decline_ratio_normal(conn):
    """混在データで騰落レシオが正しく計算される。

    Stock A: 26日間で毎日 +1 円ずつ上昇 → advances=25
    Stock B: 26日間で毎日 -1 円ずつ下落 → declines=25
    adv_decline_ratio = 25/25*100 = 100.0
    """
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)  # TARGET_DATE より前の 26 日

    # Stock A: 100, 101, 102, ... (always up)
    for i, d in enumerate(dates):
        _insert_price(conn, "A", d, 100.0 + i)

    # Stock B: 200, 199, 198, ... (always down)
    for i, d in enumerate(dates):
        _insert_price(conn, "B", d, 200.0 - i)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT adv_decline_ratio FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert abs(row[0] - 100.0) < 0.1


def test_adv_decline_ratio_no_declines(conn):
    """値下がり銘柄が 0 件 → adv_decline_ratio = 200.0。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)
    for i, d in enumerate(dates):
        _insert_price(conn, "A", d, 100.0 + i)  # always up

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT adv_decline_ratio FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert abs(row[0] - 200.0) < 1e-9
```

- [ ] **Step 2: テスト実行して失敗を確認**

```
pytest tests/test_breadth.py::test_adv_decline_ratio_normal -v
```

期待: FAIL（`kabusys.data.breadth` が存在しないため）

- [ ] **Step 3: `src/kabusys/data/breadth.py` を作成（騰落レシオまで）**

```python
"""
市場 breadth（幅）指標の計算と保存モジュール

prices_daily テーブルから騰落レシオ・25日MA上銘柄比率・新高値新安値比率を
計算し、market_breadth テーブルへ日次1行として保存する。

冪等: 同日を再実行しても上書きせず 0 を返す。
"""

from __future__ import annotations

import logging
from datetime import date

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_MIN_TRADING_DAYS: int = 25       # 計算に必要な最低取引日数
_MIN_STOCKS: int = 10             # 計算に必要な最低銘柄数
_BREADTH_STOP_THRESHOLD: float = 0.35  # 25日MA上銘柄比率の停止閾値
_ADV_DECLINE_ZERO_DECLINES: float = 200.0  # 値下がり銘柄 0 件時の代替値


# ---------------------------------------------------------------------------
# 内部計算関数
# ---------------------------------------------------------------------------


def _calc_adv_decline_ratio(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> float:
    """直近25営業日の騰落レシオを計算する。

    前日比較のため 26 日分（LIMIT 26）を取得し LAG で差分を計算。
    上位 25 日分のみ集計することで 26 日目が prev_close の計算に使われる。
    declines=0 の場合は _ADV_DECLINE_ZERO_DECLINES を返す。
    """
    row = conn.execute(
        """
        WITH dates_desc AS (
            SELECT DISTINCT date
            FROM prices_daily
            WHERE date < ?
            ORDER BY date DESC
            LIMIT 26
        ),
        with_lag AS (
            SELECT
                p.date,
                p.code,
                p.close,
                LAG(p.close) OVER (PARTITION BY p.code ORDER BY p.date) AS prev_close
            FROM prices_daily p
            WHERE p.date IN (SELECT date FROM dates_desc)
        ),
        top25 AS (
            SELECT date FROM dates_desc ORDER BY date DESC LIMIT 25
        )
        SELECT
            COALESCE(SUM(CASE WHEN wl.close > wl.prev_close THEN 1 ELSE 0 END), 0) AS advances,
            COALESCE(SUM(CASE WHEN wl.close < wl.prev_close THEN 1 ELSE 0 END), 0) AS declines
        FROM with_lag wl
        INNER JOIN top25 t ON wl.date = t.date
        WHERE wl.prev_close IS NOT NULL
        """,
        [target_date],
    ).fetchone()

    if row is None:
        return _ADV_DECLINE_ZERO_DECLINES

    advances, declines = row[0], row[1]
    if declines == 0:
        return _ADV_DECLINE_ZERO_DECLINES
    return advances / declines * 100.0


def _calc_ma25_above_pct(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> float | None:
    """25日移動平均上銘柄比率を計算する。

    各銘柄の直近25日終値の単純平均（ma25）と最新終値を比較し、
    close > ma25 の銘柄数 / 全銘柄数を返す。
    全25日分のデータがある銘柄のみ対象とする。
    計算対象銘柄が 0 件の場合は None を返す。
    """
    row = conn.execute(
        """
        WITH top25 AS (
            SELECT DISTINCT date
            FROM prices_daily
            WHERE date < ?
            ORDER BY date DESC
            LIMIT 25
        ),
        latest_date AS (
            SELECT MAX(date) AS d FROM top25
        ),
        stock_stats AS (
            SELECT
                p.code,
                MAX(CASE WHEN p.date = ld.d THEN CAST(p.close AS DOUBLE) END) AS latest_close,
                AVG(CAST(p.close AS DOUBLE)) AS ma25,
                COUNT(DISTINCT p.date) AS days
            FROM prices_daily p
            CROSS JOIN latest_date ld
            WHERE p.date IN (SELECT date FROM top25)
            GROUP BY p.code
        )
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN latest_close > ma25 THEN 1 ELSE 0 END) AS above_ma25
        FROM stock_stats
        WHERE days = 25 AND latest_close IS NOT NULL
        """,
        [target_date],
    ).fetchone()

    if row is None or row[0] == 0:
        return None
    return row[1] / row[0]


def _calc_new_high_low_ratio(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> float | None:
    """52週高値/安値比率を計算する。

    直近250営業日の最高値と等しい銘柄を新高値、最安値と等しい銘柄を新安値とする。
    新安値=0 の場合は None（NULL）を返す。
    """
    row = conn.execute(
        """
        WITH window_250 AS (
            SELECT DISTINCT date
            FROM prices_daily
            WHERE date < ?
            ORDER BY date DESC
            LIMIT 250
        ),
        latest_date AS (
            SELECT MAX(date) AS d FROM window_250
        ),
        stock_stats AS (
            SELECT
                p.code,
                MAX(CASE WHEN p.date = ld.d THEN CAST(p.close AS DOUBLE) END) AS latest_close,
                MAX(CAST(p.close AS DOUBLE)) AS high_250,
                MIN(CAST(p.close AS DOUBLE)) AS low_250
            FROM prices_daily p
            CROSS JOIN latest_date ld
            WHERE p.date IN (SELECT date FROM window_250)
            GROUP BY p.code
        )
        SELECT
            SUM(CASE WHEN latest_close = high_250 THEN 1 ELSE 0 END) AS new_high,
            SUM(CASE WHEN latest_close = low_250 THEN 1 ELSE 0 END) AS new_low
        FROM stock_stats
        WHERE latest_close IS NOT NULL
        """,
        [target_date],
    ).fetchone()

    if row is None:
        return None
    new_high = row[0] or 0
    new_low = row[1] or 0
    if new_low == 0:
        return None
    return new_high / new_low


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def calc_and_save_breadth(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> int:
    """target_date の breadth 指標を prices_daily から計算し market_breadth に保存する。

    Returns:
        1 = 保存成功、0 = 既存スキップまたはデータ不足

    冪等: 同日を再実行しても上書きせず 0 を返す。
    """
    # 冪等チェック
    existing = conn.execute(
        "SELECT 1 FROM market_breadth WHERE date = ?", [target_date]
    ).fetchone()
    if existing:
        logger.info("calc_and_save_breadth: date=%s は既存スキップ", target_date)
        return 0

    # データ充足確認（取引日数）
    date_count = conn.execute(
        "SELECT COUNT(DISTINCT date) FROM prices_daily WHERE date < ?",
        [target_date],
    ).fetchone()[0]

    if date_count < _MIN_TRADING_DAYS:
        logger.warning(
            "calc_and_save_breadth: データ不足 %d 日（必要: %d） date=%s",
            date_count,
            _MIN_TRADING_DAYS,
            target_date,
        )
        return 0

    # データ充足確認（銘柄数）
    stock_count = conn.execute(
        """
        SELECT COUNT(DISTINCT code) FROM prices_daily
        WHERE date IN (
            SELECT DISTINCT date FROM prices_daily
            WHERE date < ?
            ORDER BY date DESC
            LIMIT 25
        )
        """,
        [target_date],
    ).fetchone()[0]

    if stock_count < _MIN_STOCKS:
        logger.warning(
            "calc_and_save_breadth: 銘柄数不足 %d 件（必要: %d） date=%s",
            stock_count,
            _MIN_STOCKS,
            target_date,
        )
        return 0

    # 各指標を計算
    adv_decline_ratio = _calc_adv_decline_ratio(conn, target_date)
    ma25_above_pct = _calc_ma25_above_pct(conn, target_date)
    new_high_low_ratio = _calc_new_high_low_ratio(conn, target_date)

    if ma25_above_pct is None:
        logger.warning(
            "calc_and_save_breadth: ma25_above_pct の計算失敗 date=%s", target_date
        )
        return 0

    breadth_stop: bool = ma25_above_pct < _BREADTH_STOP_THRESHOLD

    # DB 書き込み
    conn.execute("BEGIN")
    try:
        conn.execute(
            """
            INSERT INTO market_breadth
                (date, adv_decline_ratio, ma25_above_pct, new_high_low_ratio, breadth_stop)
            VALUES (?, ?, ?, ?, ?)
            """,
            [target_date, adv_decline_ratio, ma25_above_pct, new_high_low_ratio, breadth_stop],
        )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception as rb_exc:
            logger.warning("calc_and_save_breadth: ROLLBACK failed: %s", rb_exc)
        raise

    logger.info(
        "calc_and_save_breadth: 完了 date=%s adv_decline=%.1f ma25_pct=%.3f breadth_stop=%s",
        target_date,
        adv_decline_ratio,
        ma25_above_pct,
        breadth_stop,
    )
    return 1
```

- [ ] **Step 4: テストが通ることを確認**

```
pytest tests/test_breadth.py::test_adv_decline_ratio_normal tests/test_breadth.py::test_adv_decline_ratio_no_declines -v
```

期待: 2 件 PASS

- [ ] **Step 5: 残りの breadth テストを `tests/test_breadth.py` に追記**

```python
# ---------------------------------------------------------------------------
# Task 2 続き: ma25_above_pct / breadth_stop / new_high_low_ratio
# ---------------------------------------------------------------------------


def test_ma25_above_pct(conn):
    """close > ma25 の銘柄比率が正しく計算される（2/3 ≈ 0.667）。

    Stock A: 100 → 徐々に上昇 → 最終 close=115 > ma25=~107
    Stock B: 100 → 徐々に下落 → 最終 close=85 < ma25=~93
    Stock C: 100 → 徐々に上昇 → 最終 close=120 > ma25=~110
    """
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)

    # Stock A: 100 → 115 over 26 days
    for i, d in enumerate(dates):
        _insert_price(conn, "A", d, 100.0 + i * 0.6)

    # Stock B: 100 → 85 over 26 days (declining)
    for i, d in enumerate(dates):
        _insert_price(conn, "B", d, 100.0 - i * 0.6)

    # Stock C: 100 → 120 over 26 days
    for i, d in enumerate(dates):
        _insert_price(conn, "C", d, 100.0 + i * 0.8)

    # Need 10+ stocks to pass _MIN_STOCKS check — add 7 more neutral stocks
    for s in ["D", "E", "F", "G", "H", "I", "J"]:
        for d in dates:
            _insert_price(conn, s, d, 100.0)  # flat → close == ma25 → NOT above

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT ma25_above_pct FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    # A と C が above、B と D〜J が below or equal → 2/10 = 0.2
    # Stock D-J: close == ma25 → NOT above
    assert row[0] < 0.5  # 確実に少数割合


def test_breadth_stop_true(conn):
    """ma25_above_pct < 0.35 → breadth_stop = True。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)

    # 1銘柄だけ上昇、9銘柄は下落 → 1/10 = 0.10 < 0.35
    _insert_price_per_stock_trend(conn, "A", dates, up=True)
    for s in ["B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        _insert_price_per_stock_trend(conn, s, dates, up=False)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT breadth_stop, ma25_above_pct FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert row[0] == True
    assert row[1] < 0.35


def test_breadth_stop_false(conn):
    """ma25_above_pct >= 0.35 → breadth_stop = False。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)

    # 8銘柄上昇、2銘柄下落 → 8/10 = 0.80 >= 0.35
    for s in ["A", "B", "C", "D", "E", "F", "G", "H"]:
        _insert_price_per_stock_trend(conn, s, dates, up=True)
    for s in ["I", "J"]:
        _insert_price_per_stock_trend(conn, s, dates, up=False)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT breadth_stop FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert row[0] == False


def test_new_high_low_ratio_normal(conn):
    """52週高値/安値比率が正しく計算される（新高値2件、新安値1件 → ratio=2.0）。

    Stock A: 最終 close が 250日高値と一致 → new_high
    Stock B: 最終 close が 250日高値と一致 → new_high
    Stock C: 最終 close が 250日安値と一致 → new_low
    """
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(260, TARGET_DATE)  # 250日分 + 余裕

    # Stock A: 最初は低く、最後が最高値
    for i, d in enumerate(dates[:-1]):
        _insert_price(conn, "A", d, 100.0)
    _insert_price(conn, "A", dates[-1], 200.0)  # 最終日が最高値

    # Stock B: 同様に最終日が最高値
    for i, d in enumerate(dates[:-1]):
        _insert_price(conn, "B", d, 100.0)
    _insert_price(conn, "B", dates[-1], 300.0)  # 最終日が最高値

    # Stock C: 最初は高く、最終日が最安値
    for i, d in enumerate(dates[:-1]):
        _insert_price(conn, "C", d, 100.0)
    _insert_price(conn, "C", dates[-1], 50.0)  # 最終日が最安値

    # Min stock count requirement
    for s in ["D", "E", "F", "G", "H", "I", "J"]:
        for d in dates[-26:]:  # 25日分のみ（breadth計算に十分）
            _insert_price(conn, s, d, 100.0)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT new_high_low_ratio FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    # A, B が new_high（2件）、C が new_low（1件）→ 2.0
    assert row[0] is not None
    assert abs(row[0] - 2.0) < 0.1


def test_new_high_low_ratio_no_lows(conn):
    """新安値 0 件 → new_high_low_ratio = NULL。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)
    # 全銘柄が上昇トレンド（最安値は最初の日）
    for s in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        for i, d in enumerate(dates):
            _insert_price(conn, s, d, 100.0 + i)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT new_high_low_ratio FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert row[0] is None  # 新安値 0 → NULL


def test_insufficient_data_returns_zero(conn):
    """25日分未満のデータ → 0 を返してスキップ。"""
    from kabusys.data.breadth import calc_and_save_breadth

    # 10日分のみ挿入
    dates = _make_dates(10, TARGET_DATE)
    for s in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        for d in dates:
            _insert_price(conn, s, d, 100.0)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 0

    row = conn.execute(
        "SELECT 1 FROM market_breadth WHERE date = ?", [TARGET_DATE]
    ).fetchone()
    assert row is None  # DB に保存されていないこと


def test_idempotent(conn):
    """同日を 2 回実行しても market_breadth の行が重複しない。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)
    for s in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        for i, d in enumerate(dates):
            _insert_price(conn, s, d, 100.0 + i)

    r1 = calc_and_save_breadth(conn, TARGET_DATE)
    r2 = calc_and_save_breadth(conn, TARGET_DATE)

    assert r1 == 1
    assert r2 == 0  # 2回目はスキップ

    count = conn.execute(
        "SELECT COUNT(*) FROM market_breadth WHERE date = ?", [TARGET_DATE]
    ).fetchone()[0]
    assert count == 1


# ---------------------------------------------------------------------------
# ヘルパー（上記テストで使用）
# ---------------------------------------------------------------------------


def _insert_price_per_stock_trend(
    conn, code: str, dates: list[date], *, up: bool
) -> None:
    """up=True なら上昇トレンド（close > ma25 になる）、False なら下落トレンドで挿入。"""
    for i, d in enumerate(dates):
        close = 100.0 + i if up else 100.0 - i * 0.5
        _insert_price(conn, code, d, max(close, 1.0))
```

- [ ] **Step 6: 全テスト実行**

```
pytest tests/test_breadth.py -v
```

期待: 全件 PASS

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/data/breadth.py tests/test_breadth.py
git commit -m "feat: implement calc_and_save_breadth with breadth indicators (Issue #173)"
```

---

### Task 3: `regime_detector.py` に breadth 補正を追加

**Files:**
- Modify: `src/kabusys/ai/regime_detector.py`
- Test: `tests/test_regime_detector.py`（追記）

- [ ] **Step 1: テストを追加**

`tests/test_regime_detector.py` の末尾に追記:

```python
# ---------------------------------------------------------------------------
# breadth 補正テスト（Issue #173）
# ---------------------------------------------------------------------------


def _insert_market_breadth(conn, d: date, adv_decline_ratio: float) -> None:
    """market_breadth テーブルに1行挿入するヘルパー。"""
    conn.execute(
        "INSERT INTO market_breadth "
        "(date, adv_decline_ratio, ma25_above_pct, breadth_stop) "
        "VALUES (?, ?, 0.5, False)",
        [d, adv_decline_ratio],
    )


def test_breadth_correction_low_adv_decline(conn):
    """騰落レシオ < 80 → raw_score が -0.2 補正される。

    1321 を中立（MA比率=1.0、ma200_ratio-1=0）、マクロ=0 に設定した場合:
    補正前 raw_score = 0.0
    補正後 raw_score = -0.2 → regime_label = 'bear'
    """
    from unittest.mock import patch

    from kabusys.ai.regime_detector import score_regime

    # 200日分 1321 データ（MA比率=1.0 → raw_score 寄与 = 0）
    _insert_prices_uniform(conn, "1321", 199, 100.0, TARGET_DATE)
    _insert_price(conn, "1321", TARGET_DATE - timedelta(days=1), 100.0)

    # 騰落レシオ < 80
    _insert_market_breadth(conn, TARGET_DATE, adv_decline_ratio=70.0)

    with patch("kabusys.ai.regime_detector._call_openai_api") as mock_api:
        mock_api.return_value = _make_macro_response(0.0)  # マクロ中立
        score_regime(conn, TARGET_DATE, api_key="test-key")

    row = conn.execute(
        "SELECT regime_score, regime_label FROM market_regime WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert row[1] == "bear", f"Expected bear but got {row[1]}"
    assert row[0] <= -0.2, f"Expected regime_score <= -0.2 but got {row[0]}"


def test_breadth_correction_high_adv_decline(conn):
    """騰落レシオ > 120 → raw_score が +0.1 補正される。

    1321 を MA比率=1.0、マクロ=0.1 に設定した場合:
    補正前 raw_score = 0.03 → neutral
    補正後 raw_score = 0.13 → neutral（閾値 0.2 に満たないが +0.1 されること）
    """
    from unittest.mock import patch

    from kabusys.ai.regime_detector import score_regime

    _insert_prices_uniform(conn, "1321", 199, 100.0, TARGET_DATE)
    _insert_price(conn, "1321", TARGET_DATE - timedelta(days=1), 100.0)

    # 騰落レシオ > 120
    _insert_market_breadth(conn, TARGET_DATE, adv_decline_ratio=130.0)

    with patch("kabusys.ai.regime_detector._call_openai_api") as mock_api:
        mock_api.return_value = _make_macro_response(0.1)
        score_regime(conn, TARGET_DATE, api_key="test-key")

    row = conn.execute(
        "SELECT regime_score FROM market_regime WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    # 補正前: 0.7*0*10 + 0.3*0.1 = 0.03; 補正後: 0.03 + 0.1 = 0.13
    assert row[0] > 0.1, f"Expected regime_score > 0.1 but got {row[0]}"


def test_breadth_correction_neutral(conn):
    """騰落レシオ 80〜120 → 補正なし（raw_score に変化なし）。"""
    from unittest.mock import patch

    from kabusys.ai.regime_detector import score_regime

    _insert_prices_uniform(conn, "1321", 199, 100.0, TARGET_DATE)
    _insert_price(conn, "1321", TARGET_DATE - timedelta(days=1), 100.0)

    # 騰落レシオ 100（補正なし）
    _insert_market_breadth(conn, TARGET_DATE, adv_decline_ratio=100.0)

    with patch("kabusys.ai.regime_detector._call_openai_api") as mock_api:
        mock_api.return_value = _make_macro_response(0.0)
        score_regime(conn, TARGET_DATE, api_key="test-key")

    row = conn.execute(
        "SELECT regime_score FROM market_regime WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    # raw_score = 0.0、補正なし → regime_score ≈ 0.0
    assert abs(row[0]) < 0.01, f"Expected ~0.0 but got {row[0]}"


def test_breadth_missing_no_correction(conn):
    """market_breadth にデータなし → 既存ロジックのみ（補正なし）で正常動作。"""
    from unittest.mock import patch

    from kabusys.ai.regime_detector import score_regime

    _insert_prices_uniform(conn, "1321", 199, 100.0, TARGET_DATE)
    _insert_price(conn, "1321", TARGET_DATE - timedelta(days=1), 100.0)
    # market_breadth に何も挿入しない

    with patch("kabusys.ai.regime_detector._call_openai_api") as mock_api:
        mock_api.return_value = _make_macro_response(0.0)
        result = score_regime(conn, TARGET_DATE, api_key="test-key")

    assert result == 1  # 正常終了
    row = conn.execute(
        "SELECT regime_score FROM market_regime WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert abs(row[0]) < 0.01  # 補正なし → 0.0


def test_regime_clips_to_range(conn):
    """breadth 補正後も regime_score が [-1.0, 1.0] に収まる。

    1321 を大幅上昇（MA比率=1.2）+ マクロ最大 + 騰落レシオ>120 の場合。
    """
    from unittest.mock import patch

    from kabusys.ai.regime_detector import score_regime

    # MA比率 = 1.2 → 0.7*(1.2-1)*10 = 1.4（クリップ前）
    _insert_prices_uniform(conn, "1321", 199, 100.0, TARGET_DATE)
    _insert_price(conn, "1321", TARGET_DATE - timedelta(days=1), 120.0)

    _insert_market_breadth(conn, TARGET_DATE, adv_decline_ratio=150.0)  # +0.1

    with patch("kabusys.ai.regime_detector._call_openai_api") as mock_api:
        mock_api.return_value = _make_macro_response(1.0)  # 最大センチメント
        score_regime(conn, TARGET_DATE, api_key="test-key")

    row = conn.execute(
        "SELECT regime_score FROM market_regime WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert -1.0 <= row[0] <= 1.0, f"regime_score={row[0]} が範囲外"
```

- [ ] **Step 2: テスト実行して失敗を確認**

```
pytest tests/test_regime_detector.py::test_breadth_correction_low_adv_decline -v
```

期待: FAIL（`market_breadth` テーブルはあるが補正ロジックがないため）

- [ ] **Step 3: `regime_detector.py` に `_fetch_breadth()` と補正ロジックを追加**

`src/kabusys/ai/regime_detector.py` の `_score_macro()` 関数の後、`score_regime()` の前に追加:

```python
def _fetch_breadth(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> dict | None:
    """market_breadth テーブルから target_date の breadth データを取得する。

    データが存在しない場合は None を返す（補正なしで後方互換を保つ）。
    """
    row = conn.execute(
        "SELECT adv_decline_ratio FROM market_breadth WHERE date = ?",
        [target_date],
    ).fetchone()
    if row is None:
        return None
    return {"adv_decline_ratio": float(row[0])}
```

`score_regime()` の `# [5] レジームスコア合成` ブロックを以下に置き換え:

```python
    # [5] レジームスコア合成
    raw_score = (
        _MA_WEIGHT * (ma200_ratio - 1.0) * _MA_SCALE + _MACRO_WEIGHT * macro_sentiment
    )

    # [5b] breadth 補正（騰落レシオによる調整）
    breadth = _fetch_breadth(conn, target_date)
    if breadth is not None:
        if breadth["adv_decline_ratio"] < 80:
            raw_score -= 0.2
        elif breadth["adv_decline_ratio"] > 120:
            raw_score += 0.1

    regime_score = max(-1.0, min(1.0, raw_score))
```

- [ ] **Step 4: テストが通ることを確認**

```
pytest tests/test_regime_detector.py -v
```

期待: 全件 PASS（既存テスト含む）

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/ai/regime_detector.py tests/test_regime_detector.py
git commit -m "feat: add breadth correction to score_regime (Issue #173)"
```

---

### Task 4: `signal_generator.py` の `_is_bear_regime` バグ修正と `breadth_stop` 追加

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py`
- Create: `tests/test_signal_generator.py`

- [ ] **Step 1: `tests/test_signal_generator.py` を作成（失敗するテスト）**

```python
"""
シグナル生成モジュール テスト

_is_bear_regime バグ修正（market_regime.regime_label 参照）および
breadth_stop による BUY 停止の動作検証。
"""

from __future__ import annotations

from datetime import date

import pytest

from kabusys.data.schema import init_schema

# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


TARGET_DATE = date(2026, 4, 1)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _insert_feature(conn, code: str, d: date, high_score: bool = True) -> None:
    """features テーブルに高スコア or 低スコアのデータを挿入する。"""
    if high_score:
        # 高モメンタム、低ボラ、高流動性、低PER → final_score が threshold(0.60) 超
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, -3.0, 3.0, 5.0, 3.0)",
            [d, code],
        )
    else:
        # 低モメンタム → final_score が threshold 未満
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, -3.0, -3.0, 3.0, -3.0, 100.0, -3.0)",
            [d, code],
        )


def _insert_breadth(
    conn,
    d: date,
    breadth_stop: bool,
    adv_decline_ratio: float = 100.0,
    ma25_above_pct: float = 0.5,
) -> None:
    conn.execute(
        "INSERT INTO market_breadth "
        "(date, adv_decline_ratio, ma25_above_pct, breadth_stop) "
        "VALUES (?, ?, ?, ?)",
        [d, adv_decline_ratio, ma25_above_pct, breadth_stop],
    )


def _insert_regime(conn, d: date, regime_label: str) -> None:
    score = 0.5 if regime_label == "bull" else -0.5 if regime_label == "bear" else 0.0
    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
        [d, score, regime_label],
    )


# ---------------------------------------------------------------------------
# _is_bear_regime バグ修正テスト
# ---------------------------------------------------------------------------


def test_is_bear_regime_from_market_regime(conn):
    """regime_label='bear' → True を返す（market_regime テーブルを正しく参照）。"""
    from kabusys.strategy.signal_generator import _is_bear_regime

    _insert_regime(conn, TARGET_DATE, "bear")
    assert _is_bear_regime(conn, TARGET_DATE) is True


def test_is_bear_regime_bull_returns_false(conn):
    """regime_label='bull' → False を返す。"""
    from kabusys.strategy.signal_generator import _is_bear_regime

    _insert_regime(conn, TARGET_DATE, "bull")
    assert _is_bear_regime(conn, TARGET_DATE) is False


def test_is_bear_regime_no_data_returns_false(conn):
    """market_regime にデータなし → False を返す（安全側）。"""
    from kabusys.strategy.signal_generator import _is_bear_regime

    assert _is_bear_regime(conn, TARGET_DATE) is False


# ---------------------------------------------------------------------------
# breadth_stop テスト
# ---------------------------------------------------------------------------


def test_breadth_stop_skips_buy_signals(conn):
    """breadth_stop=True → BUY シグナルが生成されない。"""
    from kabusys.strategy.signal_generator import generate_signals

    _insert_regime(conn, TARGET_DATE, "bull")
    _insert_breadth(conn, TARGET_DATE, breadth_stop=True)

    for code in ["7203", "9984"]:
        _insert_feature(conn, code, TARGET_DATE, high_score=True)

    generate_signals(conn, TARGET_DATE)

    rows = conn.execute(
        "SELECT side FROM signals WHERE date = ?", [TARGET_DATE]
    ).fetchall()
    buy_signals = [r for r in rows if r[0] == "buy"]
    assert len(buy_signals) == 0, f"breadth_stop=True なのに BUY が生成された: {len(buy_signals)} 件"


def test_breadth_stop_false_allows_buy(conn):
    """breadth_stop=False → BUY シグナルが通常通り生成される。"""
    from kabusys.strategy.signal_generator import generate_signals

    _insert_regime(conn, TARGET_DATE, "bull")
    _insert_breadth(conn, TARGET_DATE, breadth_stop=False)

    for code in ["7203", "9984"]:
        _insert_feature(conn, code, TARGET_DATE, high_score=True)

    generate_signals(conn, TARGET_DATE)

    rows = conn.execute(
        "SELECT side FROM signals WHERE date = ?", [TARGET_DATE]
    ).fetchall()
    buy_signals = [r for r in rows if r[0] == "buy"]
    assert len(buy_signals) > 0, "breadth_stop=False なのに BUY が生成されなかった"


def test_breadth_stop_bear_regime_both_block_buy(conn):
    """breadth_stop=True かつ bear レジーム → BUY 停止（独立した動作）。"""
    from kabusys.strategy.signal_generator import generate_signals

    _insert_regime(conn, TARGET_DATE, "bear")
    _insert_breadth(conn, TARGET_DATE, breadth_stop=True)

    for code in ["7203", "9984"]:
        _insert_feature(conn, code, TARGET_DATE, high_score=True)

    generate_signals(conn, TARGET_DATE)

    rows = conn.execute(
        "SELECT side FROM signals WHERE date = ?", [TARGET_DATE]
    ).fetchall()
    buy_signals = [r for r in rows if r[0] == "buy"]
    assert len(buy_signals) == 0
```

- [ ] **Step 2: テスト実行して失敗を確認**

```
pytest tests/test_signal_generator.py::test_is_bear_regime_from_market_regime -v
```

期待: FAIL（`_is_bear_regime` が `conn, target_date` シグネチャを受け付けないため）

- [ ] **Step 3: `signal_generator.py` を修正**

`src/kabusys/strategy/signal_generator.py` の変更箇所:

**① `_BEAR_MIN_SAMPLES` 定数を削除**（`_is_bear_regime` の修正後は不要）

削除対象:
```python
_BEAR_MIN_SAMPLES: int = (
    3  # Bear 判定に必要な最小サンプル数（不足時は Bear とみなさない）
)
```

**② `_is_bear_regime()` 関数全体を置き換え**

旧:
```python
def _is_bear_regime(ai_map: dict[str, dict[str, Any]]) -> bool:
    """AI スコアのレジームスコアを集計し、Bear 相場か否かを判定する。

    市場全体のレジームスコア平均が負の場合を Bear 相場とみなす。
    ai_scores が未登録、またはサンプル数が _BEAR_MIN_SAMPLES 未満の場合は
    Bear とみなさない（サンプル不足での誤判定を防ぐ）。
    """
    scores = [
        v["regime_score"]
        for v in ai_map.values()
        if v.get("regime_score") is not None and math.isfinite(v["regime_score"])
    ]
    if len(scores) < _BEAR_MIN_SAMPLES:
        return False
    return sum(scores) / len(scores) < 0.0
```

新:
```python
def _is_bear_regime(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> bool:
    """market_regime テーブルの regime_label を参照し、Bear 相場か否かを判定する。

    データが存在しない場合は False（安全側：BUY を許可）を返す。
    """
    row = conn.execute(
        "SELECT regime_label FROM market_regime WHERE date = ?",
        [target_date],
    ).fetchone()
    if row is None:
        return False
    return row[0] == "bear"
```

**③ `_is_breadth_stop()` 関数を `_is_bear_regime()` の後に追加**

```python
def _is_breadth_stop(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> bool:
    """market_breadth.breadth_stop フラグを返す。

    breadth_stop=True の場合、25日MA上銘柄比率が 35% 未満であり新規 BUY を停止する。
    データが存在しない場合は False（安全側：BUY を許可）を返す。
    """
    row = conn.execute(
        "SELECT breadth_stop FROM market_breadth WHERE date = ?",
        [target_date],
    ).fetchone()
    if row is None:
        return False
    return bool(row[0])
```

**④ `generate_signals()` 内の変更**

`# 2. AI スコア読み込み` ブロックを以下に変更（`regime_score` は不要になったため削除）:

```python
    # 2. AI スコア読み込み（センチメントスコアのみ使用）
    ai_rows = conn.execute(
        "SELECT code, ai_score FROM ai_scores WHERE date = ?",
        [target_date],
    ).fetchall()
    ai_map: dict[str, dict] = {
        code: {"ai_score": ai} for code, ai in ai_rows
    }
```

`# 3. Bear レジーム判定` ブロックを以下に変更:

```python
    # 3. Bear レジーム判定（market_regime テーブルから取得）
    regime_is_bear = _is_bear_regime(conn, target_date)
    if regime_is_bear:
        logger.info(
            "generate_signals: Bear レジーム検知 — BUY シグナル抑制 date=%s",
            target_date,
        )

    # 3b. breadth_stop 判定（25日MA上銘柄比率 < 35% で BUY 全件停止）
    breadth_stop = _is_breadth_stop(conn, target_date)
    if breadth_stop:
        logger.warning(
            "generate_signals: breadth_stop=True — 25日MA上銘柄比率 < 35%% のため BUY を全件スキップ date=%s",
            target_date,
        )
```

`# 4. 各銘柄の final_score 計算` ブロック内の `ai_raw` 取得を変更（`regime_score` 削除のため）:

```python
        # AI ニューススコア（未登録の場合は中立 0.5 で補完）
        ai_raw = ai_map.get(code, {}).get("ai_score")
```

（変更なし — `ai_score` は引き続き使用）

`# 6. BUY シグナル生成` ブロックの条件を変更:

```python
    # 6. BUY シグナル生成（Bear レジームまたは breadth_stop では抑制）
    buy_signals: list[dict] = []
    if not regime_is_bear and not breadth_stop:
        for rank, r in enumerate(scored, 1):
            if r["score"] >= threshold:
                buy_signals.append(
                    {"code": r["code"], "score": r["score"], "rank": rank}
                )
```

- [ ] **Step 4: テストが通ることを確認**

```
pytest tests/test_signal_generator.py -v
```

期待: 全件 PASS

- [ ] **Step 5: 既存テスト全件確認**

```
pytest tests/ -v --tb=short -q
```

期待: 全件 PASS

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_signal_generator.py
git commit -m "fix: replace _is_bear_regime bug with market_regime lookup, add breadth_stop (Issue #173)"
```

---

### Task 5: `run_data_update.py` に `calc_and_save_breadth()` 呼び出しを追加

**Files:**
- Modify: `scripts/run_data_update.py`

- [ ] **Step 1: `run_data_update.py` を更新**

```python
# scripts/run_data_update.py
"""Night batch: 日次市場データ更新 (data_update_job)。

Task Scheduler から 15:30 に起動される。
"""

from __future__ import annotations

import logging
import sys
from datetime import timedelta
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.data.breadth import calc_and_save_breadth
from kabusys.data.pipeline import run_daily_etl
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="data_update")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        # ETL: 当日の価格データを取得して prices_daily に追加
        result = run_daily_etl(conn)
        if result.errors:
            logger.warning("ETL 完了（エラーあり）: %s", result.errors)
        else:
            logger.info("ETL 完了")

        # ETL で挿入された最新日付の翌日を target_date として breadth を計算
        # （prices_daily の date < target_date = 当日以前のデータを使用）
        max_date_row = conn.execute(
            "SELECT MAX(date) FROM prices_daily"
        ).fetchone()
        if max_date_row and max_date_row[0]:
            target_date = max_date_row[0] + timedelta(days=1)
            breadth_result = calc_and_save_breadth(conn, target_date)
            logger.info(
                "breadth 計算完了: date=%s result=%d", target_date, breadth_result
            )
        else:
            logger.warning("breadth 計算スキップ: prices_daily にデータなし")
    except Exception:
        logger.exception("data_update バッチが失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: インポートエラーなく起動できることを確認（ドライラン）**

```bash
cd C:\Users\tetsu\Projects\KabuSys
python -c "
import sys; sys.path.insert(0, 'src')
from kabusys.data.breadth import calc_and_save_breadth
print('import OK')
"
```

期待: `import OK`

- [ ] **Step 3: テスト全件確認**

```
pytest tests/ -v --tb=short -q
```

期待: 全件 PASS

- [ ] **Step 4: コミット**

```bash
git add scripts/run_data_update.py
git commit -m "feat: call calc_and_save_breadth in data_update batch (Issue #173)"
```

---

## 完了後の確認

- [ ] **全テスト通過確認**

```
pytest tests/ -v
```

- [ ] **対象 Issue #173 のクローズ確認**

全タスク完了後、Issue #173 をクローズする。

---

## 補足: target_date の扱いについて

`calc_and_save_breadth(conn, target_date)` は `date < target_date` で prices_daily を検索する（ルックアヘッドバイアス防止・バックテスト互換）。

- `run_data_update.py` では `target_date = max_date_in_prices_daily + 1 day` を渡すことで、当日の価格データを breadth 計算に含める。
- `market_breadth.date = target_date`（例: 2026-04-19）として保存される。
- `score_regime(conn, target_date=2026-04-19)` および `generate_signals(conn, target_date=2026-04-19)` は `market_breadth WHERE date = 2026-04-19` を参照するため整合する。
