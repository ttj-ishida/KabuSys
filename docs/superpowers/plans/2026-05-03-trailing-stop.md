# Trailing Stop (ATR×2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `_generate_sell_signals()` に ATR×2 ベースのトレーリングストップを追加し、エントリー日以降の最高値から 2×ATR を超えて下落した含み益ポジションを自動クローズする。

**Architecture:** `_peak_close()` と `_atr_20d()` の2つのヘルパーを `signal_generator.py` に追加し、earnings_avoidance と time_exit の間に trailing_stop チェックを挿入する。peak_close は `position_entries + prices_daily` の JOIN で都度計算（スキーマ変更なし）。ATR は `prices_daily` の直近21行から True Range の平均を算出。パラメータ `trailing_stop_atr`（デフォルト2.0）を engine / run / report まで配線する。

**Tech Stack:** Python 3.10+, DuckDB, pytest

---

## File Structure

| ファイル | 変更種別 | 担当 |
|---------|---------|------|
| `src/kabusys/strategy/signal_generator.py` | Modify | 定数追加、ヘルパー追加、SELL ロジック追加、パラメータ追加 |
| `src/kabusys/backtest/engine.py` | Modify | `run_backtest()` パラメータ追加・バリデーション・配線 |
| `src/kabusys/backtest/run.py` | Modify | `--trailing-stop-atr` CLI 引数追加 |
| `src/kabusys/backtest/report.py` | Modify | `ReportMeta`・`build_report()`・`format_markdown()` 追加 |
| `tests/test_trailing_stop.py` | Create | ヘルパー単体テスト + 統合テスト |

---

### Task 1: `_atr_20d()` と `_peak_close()` ヘルパー実装

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py`（定数ブロック L69-74、ヘルパー節 ~L360）
- Create: `tests/test_trailing_stop.py`

- [ ] **Step 1: テストファイルを作成して失敗させる**

`tests/test_trailing_stop.py` を以下の内容で作成する。

```python
"""tests/test_trailing_stop.py — トレーリングストップ（ATR×2）テスト"""
from __future__ import annotations

import inspect
from datetime import date, timedelta

import pytest

from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from kabusys.strategy.signal_generator import _atr_20d, _peak_close, generate_signals


def _weekdays_before(d: date, n: int) -> list[date]:
    """d の前の n 営業日（月〜金）を昇順で返す。"""
    result: list[date] = []
    cur = d - timedelta(days=1)
    while len(result) < n:
        if cur.weekday() < 5:
            result.insert(0, cur)
        cur -= timedelta(days=1)
    return result


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


# ---------------------------------------------------------------------------
# _atr_20d ヘルパー
# ---------------------------------------------------------------------------


class TestAtr20d:
    def test_returns_correct_average(self, conn):
        """20営業日の履歴 + target_date の計 21 行があるとき ATR_20d を正しく計算する。

        high=1010, low=990, close=1000（前日 close も 1000）のとき
        TR = GREATEST(20, |1010-1000|, |990-1000|) = 20 → ATR = 20.0
        """
        code = "ATR1"
        target = date(2026, 4, 6)
        for d in _weekdays_before(target, 20) + [target]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
                "VALUES (?, ?, 1000.0, 1010.0, 990.0, 1000.0, 1000000)",
                [d, code],
            )
        result = _atr_20d(conn, code, target)
        assert result == pytest.approx(20.0)

    def test_returns_none_when_insufficient_data(self, conn):
        """履歴が 20 日未満（TR < 20 本）のとき None を返す。"""
        code = "ATR2"
        target = date(2026, 4, 6)
        # 10 days before + target = 11 rows → 10 TR values → None
        for d in _weekdays_before(target, 10) + [target]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
                "VALUES (?, ?, 1000.0, 1010.0, 990.0, 1000.0, 1000000)",
                [d, code],
            )
        result = _atr_20d(conn, code, target)
        assert result is None


# ---------------------------------------------------------------------------
# _peak_close ヘルパー
# ---------------------------------------------------------------------------


class TestPeakClose:
    def test_returns_max_close_since_entry(self, conn):
        """エントリー日以降の最高 close を返す。"""
        code = "PEAK1"
        entry = date(2026, 4, 6)
        target = date(2026, 4, 8)
        conn.execute(
            "INSERT INTO position_entries (code, entry_date, sell_date) VALUES (?, ?, NULL)",
            [code, entry],
        )
        for d, c in [
            (date(2026, 4, 6), 100.0),
            (date(2026, 4, 7), 120.0),
            (date(2026, 4, 8), 110.0),
        ]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
                [d, code, c, c * 1.05, c * 0.95, c],
            )
        result = _peak_close(conn, code, target)
        assert result == pytest.approx(120.0)

    def test_returns_none_when_no_open_entry(self, conn):
        """オープンなエントリーが存在しない場合 None を返す。"""
        code = "PEAK2"
        target = date(2026, 4, 8)
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
            "VALUES (?, ?, 100.0, 110.0, 90.0, 100.0, 1000000)",
            [target, code],
        )
        result = _peak_close(conn, code, target)
        assert result is None
```

- [ ] **Step 2: テストが ImportError で失敗することを確認する**

```bash
pytest tests/test_trailing_stop.py::TestAtr20d -v
```

Expected: `ImportError: cannot import name '_atr_20d'`

- [ ] **Step 3: `_TRAILING_STOP_ATR_MULT` 定数を signal_generator.py に追加する**

`src/kabusys/strategy/signal_generator.py` の L72（`_REENTRY_COOLDOWN_DAYS` の直前）に以下を挿入する。

```python
_TRAILING_STOP_ATR_MULT: float = (
    2.0  # peak_close から ATR × N 下落で trailing_stop SELL を発動
)
```

- [ ] **Step 4: `_atr_20d()` ヘルパーを追加する**

`src/kabusys/strategy/signal_generator.py` の `# 保有日数 / 再エントリー制限ヘルパー` セクションの直前（~L302）に以下を追加する。

```python
# ---------------------------------------------------------------------------
# ATR / ピーク価格ヘルパー（トレーリングストップ用）
# ---------------------------------------------------------------------------


def _atr_20d(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
) -> float | None:
    """直近 20 本の Average True Range（ATR）を返す。

    True Range = GREATEST(high − low, |high − prev_close|, |low − prev_close|)
    20 本未満のデータしかない場合は None を返す。
    """
    row = conn.execute(
        """
        WITH recent AS (
            SELECT date, high, low, close
            FROM prices_daily
            WHERE code = ? AND date <= ?
            ORDER BY date DESC
            LIMIT 21
        ),
        with_prev AS (
            SELECT
                high,
                low,
                LAG(close) OVER (ORDER BY date) AS prev_close
            FROM recent
        ),
        tr AS (
            SELECT GREATEST(
                high - low,
                ABS(high - prev_close),
                ABS(low  - prev_close)
            ) AS true_range
            FROM with_prev
            WHERE prev_close IS NOT NULL
        )
        SELECT AVG(true_range), COUNT(*) FROM tr
        """,
        [code, target_date],
    ).fetchone()
    if row is None or row[1] is None or int(row[1]) < 20:
        return None
    return float(row[0])
```

- [ ] **Step 5: `_peak_close()` ヘルパーを追加する**

`_atr_20d()` の直後に続けて追加する。

```python
def _peak_close(
    conn: duckdb.DuckDBPyConnection,
    code: str,
    target_date: date,
) -> float | None:
    """エントリー日（最古のオープンエントリー）以降 target_date までの最高 close を返す。

    オープンな position_entries が存在しない場合は None を返す。
    """
    row = conn.execute(
        """
        SELECT MAX(pd.close)
        FROM position_entries pe
        JOIN prices_daily pd
          ON pd.code = pe.code
         AND pd.date >= pe.entry_date
         AND pd.date <= ?
        WHERE pe.code = ?
          AND pe.sell_date IS NULL
        """,
        [target_date, code],
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return float(row[0])
```

- [ ] **Step 6: テストを実行して通ることを確認する**

```bash
pytest tests/test_trailing_stop.py::TestAtr20d tests/test_trailing_stop.py::TestPeakClose -v
```

Expected: 4 tests PASS

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_trailing_stop.py
git commit -m "feat: _atr_20d / _peak_close ヘルパー追加 (Issue #182)"
```

---

### Task 2: trailing_stop ロジックを `_generate_sell_signals()` / `generate_signals()` に追加

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py`
- Modify: `tests/test_trailing_stop.py`

- [ ] **Step 1: 統合テストを test_trailing_stop.py に追加する（失敗することを先に確認）**

`tests/test_trailing_stop.py` の末尾に以下を追加する。

```python
# ---------------------------------------------------------------------------
# 統合テスト用ヘルパー
# ---------------------------------------------------------------------------

TARGET_DATE = date(2026, 4, 6)  # Monday


def _insert_prices_history(
    conn,
    code: str,
    base_close: float = 1000.0,
    spread: float = 20.0,
    n_history: int = 20,
) -> date:
    """TARGET_DATE の前 n_history 営業日分の価格を挿入し、最古の日付を返す。

    spread=20 (high=base+10, low=base-10, prev_close=base) のとき
    TR = GREATEST(20, 10, 10) = 20 → ATR_20d = 20.0
    """
    history_dates = _weekdays_before(TARGET_DATE, n_history)
    for d in history_dates:
        c = base_close
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
            [d, code, c, c + spread / 2, c - spread / 2, c],
        )
    return history_dates[0]


def _insert_target_price(conn, code: str, close: float) -> None:
    """TARGET_DATE の価格を挿入する（高値 = close+10, 安値 = close-10）。"""
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
        [TARGET_DATE, code, close, close + 10, close - 10, close],
    )


def _setup_env(conn, code: str, close: float, avg_price: float = 850.0) -> None:
    """trailing_stop テストの共通セットアップ。

    - 20 日分の履歴（close=1000, spread=20 → ATR≈20, peak_close=1000）
    - TARGET_DATE の価格: close=close
    - avg_price=avg_price（850 < 1000=peak → 含み益条件を満たす）
    """
    entry_date = _insert_prices_history(conn, code)
    _insert_target_price(conn, code, close)
    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, 0.5, 'bull')",
        [TARGET_DATE],
    )
    conn.execute(
        "INSERT INTO market_breadth "
        "(date, adv_decline_ratio, ma25_above_pct, breadth_stop) VALUES (?, 100.0, 0.5, false)",
        [TARGET_DATE],
    )
    conn.execute(
        "INSERT INTO features "
        "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
        "VALUES (?, ?, 3.0, 3.0, 0.5, 3.0, 3.0, 3.0)",
        [TARGET_DATE, code],
    )
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, ?, 100, ?)",
        [TARGET_DATE, code, avg_price],
    )
    conn.execute(
        "INSERT INTO position_entries (code, entry_date, sell_date) VALUES (?, ?, NULL)",
        [code, entry_date],
    )


def _sell_codes(conn, d: date) -> set[str]:
    rows = conn.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'", [d]
    ).fetchall()
    return {r[0] for r in rows}


# ---------------------------------------------------------------------------
# trailing_stop 発動テスト
# ---------------------------------------------------------------------------


class TestTrailingStopFires:
    def test_fires_when_close_below_threshold(self, conn):
        """close < peak - 2×ATR のとき trailing_stop SELL が発生する。

        peak=1000, ATR≈24（target_date の大きな TR を含む）, threshold≈951
        close=900 < threshold → SELL が発生すること。
        """
        code = "TS_FIRE1"
        _setup_env(conn, code, close=900.0)
        generate_signals(conn, TARGET_DATE, trailing_stop_atr=2.0)
        assert code in _sell_codes(conn, TARGET_DATE)


class TestTrailingStopSuppressed:
    def test_no_sell_when_close_above_threshold(self, conn):
        """close が peak - 2×ATR より大きいとき SELL が発生しない。

        peak=1000, ATR≈20, threshold≈960
        close=995 > threshold → SELL が発生しないこと。
        """
        code = "TS_SUPP1"
        _setup_env(conn, code, close=995.0)
        generate_signals(conn, TARGET_DATE, trailing_stop_atr=2.0)
        assert code not in _sell_codes(conn, TARGET_DATE)


class TestTrailingStopNoProfitNoFire:
    def test_no_fire_when_peak_not_above_avg_price(self, conn):
        """peak_close <= avg_price のとき（含み益なし）trailing_stop は発動しない。

        avg_price=1100 > peak_close=1000 → 含み益条件を満たさないため SELL なし。
        """
        code = "TS_NOPROFIT"
        _setup_env(conn, code, close=900.0, avg_price=1100.0)
        generate_signals(conn, TARGET_DATE, trailing_stop_atr=2.0)
        assert code not in _sell_codes(conn, TARGET_DATE)


class TestTrailingStopBypassesMinHolding:
    def test_fires_despite_min_holding_days(self, conn):
        """held < min_holding_days であっても trailing_stop は発動する。"""
        code = "TS_BYPASS"
        _setup_env(conn, code, close=900.0)
        generate_signals(conn, TARGET_DATE, min_holding_days=30, trailing_stop_atr=2.0)
        assert code in _sell_codes(conn, TARGET_DATE)


class TestTrailingStopInBearRegime:
    def test_fires_in_bear_regime(self, conn):
        """Bear レジームでも trailing_stop が発動する。"""
        code = "TS_BEAR"
        entry_date = _insert_prices_history(conn, code)
        _insert_target_price(conn, code, 900.0)
        conn.execute(
            "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, -0.8, 'bear')",
            [TARGET_DATE],
        )
        conn.execute(
            "INSERT INTO market_breadth "
            "(date, adv_decline_ratio, ma25_above_pct, breadth_stop) VALUES (?, 100.0, 0.5, false)",
            [TARGET_DATE],
        )
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, 0.5, 3.0, 3.0, 3.0)",
            [TARGET_DATE, code],
        )
        conn.execute(
            "INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, ?, 100, 850.0)",
            [TARGET_DATE, code],
        )
        conn.execute(
            "INSERT INTO position_entries (code, entry_date, sell_date) VALUES (?, ?, NULL)",
            [code, entry_date],
        )
        generate_signals(conn, TARGET_DATE, trailing_stop_atr=2.0)
        assert code in _sell_codes(conn, TARGET_DATE)


# ---------------------------------------------------------------------------
# バリデーション
# ---------------------------------------------------------------------------


class TestTrailingStopValidation:
    def test_generate_signals_raises_on_zero(self, conn):
        with pytest.raises(ValueError, match="正の値"):
            generate_signals(conn, TARGET_DATE, trailing_stop_atr=0.0)

    def test_generate_signals_raises_on_negative(self, conn):
        with pytest.raises(ValueError, match="正の値"):
            generate_signals(conn, TARGET_DATE, trailing_stop_atr=-1.0)

    def test_run_backtest_raises_on_zero(self):
        c = init_schema(":memory:")
        try:
            with pytest.raises(ValueError, match="正の値"):
                run_backtest(
                    c,
                    start_date=date(2025, 1, 6),
                    end_date=date(2025, 1, 7),
                    trailing_stop_atr=0.0,
                )
        finally:
            c.close()


# ---------------------------------------------------------------------------
# シグネチャ・デフォルト値
# ---------------------------------------------------------------------------


class TestTrailingStopDefault:
    def test_generate_signals_has_trailing_stop_atr_param(self):
        sig = inspect.signature(generate_signals)
        assert "trailing_stop_atr" in sig.parameters

    def test_run_backtest_has_trailing_stop_atr_param(self):
        sig = inspect.signature(run_backtest)
        assert "trailing_stop_atr" in sig.parameters

    def test_generate_signals_default_is_2_0(self):
        sig = inspect.signature(generate_signals)
        assert sig.parameters["trailing_stop_atr"].default == pytest.approx(2.0)

    def test_run_backtest_default_is_2_0(self):
        sig = inspect.signature(run_backtest)
        assert sig.parameters["trailing_stop_atr"].default == pytest.approx(2.0)
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_trailing_stop.py::TestTrailingStopFires -v
```

Expected: `TypeError` または `pytest.raises` が `AssertionError`（`trailing_stop_atr` パラメータが存在しない）

- [ ] **Step 3: `_generate_sell_signals()` のシグネチャとドキュメントを更新する**

`src/kabusys/strategy/signal_generator.py` の `_generate_sell_signals()` 定義（~L387）を以下に変更する。

```python
def _generate_sell_signals(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    score_map: dict[str, float],
    threshold: float,
    is_bear: bool = False,
    min_holding_days: int = _MIN_HOLDING_DAYS,
    max_holding_days: int = _MAX_HOLDING_DAYS,
    trailing_stop_atr: float = _TRAILING_STOP_ATR_MULT,
) -> list[dict[str, Any]]:
    """保有ポジションに対してエグジット条件を判定し、SELL シグナルを返す。

    実装済みの条件 (StrategyModel.md Section 5.2):
      1. ストップロス: 終値 / avg_price - 1 < -8%
      2. 時間決済: 保有営業日数 >= max_holding_days
      3. トレーリングストップ: close < peak_close − trailing_stop_atr × ATR_20d（含み益あり時）
      4. スコア低下: final_score が threshold 未満

    Args:
        conn:                DuckDB 接続。
        target_date:         シグナル生成対象日。
        score_map:           {code: final_score} の辞書。
        threshold:           BUY/SELL 判定の閾値。
        is_bear:             True のとき最低保有日数チェックをスキップする（Bear レジーム例外）。
        min_holding_days:    SELL を抑制する最低保有営業日数（デフォルト: _MIN_HOLDING_DAYS）。
        max_holding_days:    この営業日数以上保有した銘柄に time_exit SELL を発動（デフォルト: _MAX_HOLDING_DAYS）。
                             ストップロス・決算回避より低優先。min_holding_days は無視して発火する。
        trailing_stop_atr:   ATR 乗数。peak_close − N×ATR を下回ったら SELL（含み益ありの場合のみ）。
```

- [ ] **Step 4: earnings_avoidance ブロックの直後に trailing_stop チェックを挿入する**

`src/kabusys/strategy/signal_generator.py` の earnings_avoidance `continue`（~L493）の直後、time_exit `held = _held_days` の直前に以下を挿入する。

```python
        # トレーリングストップ（含み益保護）: min_holding_days を無視して発火
        # peak_close > avg_price のとき（含み益あり）のみ適用
        _peak = _peak_close(conn, code, target_date)
        if _peak is not None and _peak > avg_price:
            _atr = _atr_20d(conn, code, target_date)
            if _atr is not None and close < _peak - trailing_stop_atr * _atr:
                logger.debug(
                    "_generate_sell_signals: %s trailing_stop"
                    " close=%.2f peak=%.2f atr=%.2f mult=%.1f date=%s",
                    code,
                    close,
                    _peak,
                    _atr,
                    trailing_stop_atr,
                    target_date,
                )
                sell_signals.append(
                    {
                        "code": code,
                        "score": final_score,
                        "reason": "trailing_stop",
                    }
                )
                continue
```

- [ ] **Step 5: `generate_signals()` のシグネチャにパラメータを追加し、バリデーションと呼び出しを更新する**

`src/kabusys/strategy/signal_generator.py` で以下の3か所を変更する。

**5a: シグネチャ**（~L560）

```python
def generate_signals(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    threshold: float = _DEFAULT_THRESHOLD,
    weights: dict[str, float] | None = None,
    event_dates: dict[date, str] | None = None,
    scope: "BacktestScope | None" = None,
    min_holding_days: int = _MIN_HOLDING_DAYS,
    max_holding_days: int = _MAX_HOLDING_DAYS,
    trailing_stop_atr: float = _TRAILING_STOP_ATR_MULT,
) -> int:
```

**5b: docstring の Args に追記**（`max_holding_days` 説明の直後）

```
        trailing_stop_atr: ATR 乗数。peak_close − N×ATR を下回ったら trailing_stop SELL。
                           正の値を指定すること（デフォルト: _TRAILING_STOP_ATR_MULT）。
```

**5c: バリデーション**（`max_holding_days` の警告ログの直後 ~L599）

```python
    if trailing_stop_atr <= 0:
        raise ValueError(
            f"trailing_stop_atr は正の値を指定してください: {trailing_stop_atr}"
        )
```

**5d: `_generate_sell_signals()` 呼び出し**（~L841）

```python
    sell_signals = _generate_sell_signals(
        conn,
        target_date,
        score_map,
        threshold,
        is_bear=regime_is_bear,
        min_holding_days=min_holding_days,
        max_holding_days=max_holding_days,
        trailing_stop_atr=trailing_stop_atr,
    )
```

- [ ] **Step 6: テストを実行して通ることを確認する**

```bash
pytest tests/test_trailing_stop.py -v
```

Expected: 全テスト PASS

- [ ] **Step 7: 全テストスイートを実行する**

```bash
pytest --tb=short -q
```

Expected: 全テスト PASS（既存テストに回帰なし）

- [ ] **Step 8: コミット**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_trailing_stop.py
git commit -m "feat: トレーリングストップ（ATR×2）を _generate_sell_signals に実装 (Issue #182)"
```

---

### Task 3: engine.py / run.py / report.py への `trailing_stop_atr` パラメータ配線

**Files:**
- Modify: `src/kabusys/backtest/engine.py`
- Modify: `src/kabusys/backtest/run.py`
- Modify: `src/kabusys/backtest/report.py`

- [ ] **Step 1: `engine.py` の `run_backtest()` を更新する**

`src/kabusys/backtest/engine.py` で以下を変更する。

**1a: シグネチャ**（~L392）— `max_holding_days: int = 60,` の直後に追加

```python
    trailing_stop_atr: float = 2.0,
```

**1b: docstring の Args に追記**（`max_holding_days` 説明の直後）

```
        trailing_stop_atr: ATR 乗数。peak_close − N×ATR を下回った含み益ポジションを
                           trailing_stop SELL する（デフォルト 2.0）。正の値を指定すること。
```

**1c: バリデーション**（`max_holding_days` の `raise ValueError` の直後 ~L454）

```python
    if trailing_stop_atr <= 0:
        raise ValueError(
            f"trailing_stop_atr は正の値を指定してください: {trailing_stop_atr}"
        )
```

**1d: `generate_signals()` 呼び出し**（~L547-L554）

```python
            generate_signals(
                bt_conn,
                target_date=trading_day,
                event_dates=event_dates or {},
                scope=backtest_scope,
                min_holding_days=min_holding_days,
                max_holding_days=max_holding_days,
                trailing_stop_atr=trailing_stop_atr,
            )
```

- [ ] **Step 2: `run.py` の CLI 引数・呼び出しを更新する**

`src/kabusys/backtest/run.py` で以下を変更する。

**2a: CLI 引数**（`--max-holding-days` 引数の直後 ~L142）

```python
    parser.add_argument(
        "--trailing-stop-atr",
        type=float,
        default=2.0,
        help=(
            "Trailing stop ATR multiplier. Position drops more than N×ATR from peak "
            "triggers a trailing_stop SELL (only when in profit). [default: %(default)s]"
        ),
    )
```

**2b: `run_backtest()` 呼び出し**（~L207）— `max_holding_days=args.max_holding_days,` の直後に追加

```python
            trailing_stop_atr=args.trailing_stop_atr,
```

**2c: `build_report()` 呼び出し**（~L227）— `max_holding_days=getattr(args, "max_holding_days", 60),` の直後に追加

```python
        trailing_stop_atr=getattr(args, "trailing_stop_atr", 2.0),
```

- [ ] **Step 3: `report.py` の `ReportMeta`・`build_report()`・`format_markdown()` を更新する**

`src/kabusys/backtest/report.py` で以下を変更する。

**3a: `ReportMeta` フィールド**（`max_holding_days: int = 60` の直後 ~L50）

```python
    trailing_stop_atr: float = 2.0
```

**3b: `build_report()` シグネチャ**（`max_holding_days: int = 60,` の直後 ~L135）

```python
    trailing_stop_atr: float = 2.0,
```

**3c: `ReportMeta(...)` 初期化**（`max_holding_days=max_holding_days,` の直後 ~L199）

```python
        trailing_stop_atr=trailing_stop_atr,
```

**3d: `format_markdown()` の設定テーブル**（`f"| Max Holding Days | {m.max_holding_days} |",` の直後 ~L331）

```python
        f"| Trailing Stop ATR | {m.trailing_stop_atr} |",
```

- [ ] **Step 4: 全テストスイートを実行する**

```bash
pytest --tb=short -q
```

Expected: 全テスト PASS

- [ ] **Step 5: ruff でフォーマット・lint を確認する**

```bash
python -m ruff format src/kabusys/strategy/signal_generator.py \
    src/kabusys/backtest/engine.py src/kabusys/backtest/run.py \
    src/kabusys/backtest/report.py tests/test_trailing_stop.py
python -m ruff check src/kabusys/strategy/signal_generator.py \
    src/kabusys/backtest/engine.py src/kabusys/backtest/run.py \
    src/kabusys/backtest/report.py tests/test_trailing_stop.py
```

Expected: `All checks passed!`

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/backtest/engine.py src/kabusys/backtest/run.py src/kabusys/backtest/report.py
git commit -m "feat: trailing_stop_atr を engine / run / report に配線 (Issue #182)"
```
