# Market Regime Detector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `score_regime(conn, target_date, api_key)` を実装し、ETF 1321 の 200 日 MA 乖離と LLM マクロセンチメントを合成した市場レジームスコアを `market_regime` テーブルへ日次書き込みする。

**Architecture:** `src/kabusys/ai/regime_detector.py` に新モジュールを作成。`news_nlp.py` の `calc_news_window()` を import して時間ウィンドウを共有するが、OpenAI 呼び出し関数は独自実装（モジュール間のプライベート関数結合を避けるため）。`market_regime` テーブルは `schema.py` に追加し、AI Scores（ai_scores）とは別テーブルで日次 1 行を管理する。

**Tech Stack:** Python 3.10+, DuckDB, openai SDK (RateLimitError / APIConnectionError / APITimeoutError / APIError), pytest, unittest.mock

---

## ファイル構成

| 操作 | パス | 役割 |
|------|------|------|
| 修正 | `src/kabusys/data/schema.py` | `market_regime` DDL 追加 + `_ALL_DDL` に追記 |
| 新規 | `src/kabusys/ai/__init__.py` | パッケージ初期化（空ファイル） |
| 新規 | `src/kabusys/ai/regime_detector.py` | `score_regime()` および内部ヘルパー |
| 新規 | `tests/test_regime_detector.py` | 全テスト |

---

## 前提確認

- `src/kabusys/ai/news_nlp.py` が main に存在し、`calc_news_window(target_date)` が公開関数として利用可能であること
- `prices_daily` テーブルに ETF コード `'1321'` のデータが入っている（バックテスト・本番ともに）
- `raw_news` テーブルが Raw Layer に存在する（`schema.py` で `_RAW_NEWS` として定義済み）

---

## Task 1: market_regime テーブルを schema.py に追加

**Files:**
- Modify: `src/kabusys/data/schema.py`
- Test: `tests/test_regime_detector.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_regime_detector.py` を新規作成：

```python
"""
市場レジーム判定モジュール テスト
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from kabusys.data.schema import init_schema


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """インメモリ DuckDB 接続（テスト毎に新規作成）。"""
    c = init_schema(":memory:")
    yield c
    c.close()


TARGET_DATE = date(2026, 3, 21)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _insert_price(conn, code: str, d: date, close: float) -> None:
    """prices_daily に1行挿入するヘルパー。"""
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d, code, close, close, close, close, 1_000_000],
    )


def _insert_prices_uniform(conn, code: str, days: int, close: float, before_date: date) -> None:
    """before_date の直前 days 日間を同一終値で挿入するヘルパー。"""
    for i in range(days, 0, -1):
        d = before_date - timedelta(days=i)
        _insert_price(conn, code, d, close)


def _insert_raw_news(conn, news_id: str, dt, title: str) -> None:
    """raw_news に1件挿入するヘルパー。"""
    conn.execute(
        "INSERT INTO raw_news (id, datetime, source, title) VALUES (?, ?, 'test', ?)",
        [news_id, dt, title],
    )


def _make_macro_response(score: float) -> MagicMock:
    """OpenAI レスポンスのモックを生成するヘルパー。"""
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps({"macro_sentiment": score})
    return mock_resp


# ---------------------------------------------------------------------------
# Task 1: market_regime テーブルの存在確認
# ---------------------------------------------------------------------------

def test_market_regime_table_exists(conn):
    """init_schema() 後に market_regime テーブルが存在する。"""
    row = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_name = 'market_regime'"
    ).fetchone()
    assert row is not None, "market_regime テーブルが存在しない"


def test_market_regime_columns(conn):
    """market_regime テーブルが必要なカラムを持つ。"""
    conn.execute(
        """
        INSERT INTO market_regime (date, regime_score, regime_label, ma200_ratio, macro_sentiment)
        VALUES (?, ?, ?, ?, ?)
        """,
        [date(2026, 1, 1), 0.5, "bull", 1.05, 0.3],
    )
    row = conn.execute(
        "SELECT date, regime_score, regime_label, ma200_ratio, macro_sentiment, created_at "
        "FROM market_regime WHERE date = ?",
        [date(2026, 1, 1)],
    ).fetchone()
    assert row is not None
    assert row[2] == "bull"
    assert abs(row[1] - 0.5) < 1e-9
    assert row[5] is not None  # created_at は自動設定
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_regime_detector.py::test_market_regime_table_exists -v
```

期待: `FAILED` — `market_regime` テーブルが存在しないため

- [ ] **Step 3: schema.py に DDL を追加**

`src/kabusys/data/schema.py` を開き、`_AI_SCORES` DDL の直後に追加：

```python
_MARKET_REGIME = """
CREATE TABLE IF NOT EXISTS market_regime (
    date             DATE      NOT NULL PRIMARY KEY,
    regime_score     DOUBLE    NOT NULL,
    regime_label     VARCHAR   NOT NULL,
    ma200_ratio      DOUBLE,
    macro_sentiment  DOUBLE,
    created_at       TIMESTAMP NOT NULL DEFAULT current_timestamp
)
"""
```

次に `_ALL_DDL` リストの `_AI_SCORES` の直後に `_MARKET_REGIME` を追加：

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
    # Feature
    _FEATURES,
    _AI_SCORES,
    _MARKET_REGIME,   # ← 追加
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

```bash
pytest tests/test_regime_detector.py::test_market_regime_table_exists tests/test_regime_detector.py::test_market_regime_columns -v
```

期待: `2 passed`

- [ ] **Step 5: 既存テストが壊れていないことを確認**

```bash
pytest tests/ -v --tb=short
```

期待: 既存テストがすべて pass

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/data/schema.py tests/test_regime_detector.py
git commit -m "feat: add market_regime table to schema and test fixture"
```

---

## Task 2: `_calc_ma200_ratio()` を実装

ETF 1321 の 200 日移動平均乖離を計算する内部関数。

**Files:**
- Create: `src/kabusys/ai/regime_detector.py`
- Create: `src/kabusys/ai/__init__.py`
- Test: `tests/test_regime_detector.py`

- [ ] **Step 1: 失敗するテストを追加**

`tests/test_regime_detector.py` に追記：

```python
# ---------------------------------------------------------------------------
# Task 2: _calc_ma200_ratio()
# ---------------------------------------------------------------------------

def test_bear_by_ma(conn):
    """1321 が 200MA を大きく下回る → ma200_ratio が 1.0 未満 → score が bear に十分低い。"""
    from kabusys.ai.regime_detector import _calc_ma200_ratio

    # 199 日は 100 円、最終日は 85 円（乖離 -15%）
    _insert_prices_uniform(conn, "1321", 199, 100.0, TARGET_DATE)
    _insert_price(conn, "1321", TARGET_DATE - timedelta(days=1), 85.0)

    ratio = _calc_ma200_ratio(conn, TARGET_DATE)

    # avg ≈ (199*100 + 85)/200 = 99.925, latest=85 → ratio≈0.8506
    assert ratio < 1.0, f"ratio={ratio} が 1.0 以上"
    # regime_score = 0.7*(ratio-1)*10 が -0.2 以下になることを確認
    score = 0.7 * (ratio - 1.0) * 10
    assert score <= -0.2, f"score={score} が -0.2 より大きい"


def test_bull_by_ma(conn):
    """1321 が 200MA を大きく上回る → ma200_ratio が 1.0 超 → score が bull に十分高い。"""
    from kabusys.ai.regime_detector import _calc_ma200_ratio

    # 199 日は 100 円、最終日は 130 円（乖離 +30%）
    _insert_prices_uniform(conn, "1321", 199, 100.0, TARGET_DATE)
    _insert_price(conn, "1321", TARGET_DATE - timedelta(days=1), 130.0)

    ratio = _calc_ma200_ratio(conn, TARGET_DATE)

    assert ratio > 1.0, f"ratio={ratio} が 1.0 以下"
    score = 0.7 * (ratio - 1.0) * 10
    assert score >= 0.2, f"score={score} が 0.2 より小さい"


def test_insufficient_prices(conn):
    """1321 のデータが _MA_WINDOW 日未満 → ma200_ratio=1.0 フォールバック。"""
    from kabusys.ai.regime_detector import _calc_ma200_ratio, _MA_WINDOW

    # 100 日分のみ挿入
    _insert_prices_uniform(conn, "1321", 100, 100.0, TARGET_DATE)

    ratio = _calc_ma200_ratio(conn, TARGET_DATE)
    assert ratio == 1.0, f"ratio={ratio}（期待: 1.0 フォールバック）"


def test_no_prices(conn):
    """1321 のデータが 0 件 → ma200_ratio=1.0 フォールバック。"""
    from kabusys.ai.regime_detector import _calc_ma200_ratio

    ratio = _calc_ma200_ratio(conn, TARGET_DATE)
    assert ratio == 1.0
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_regime_detector.py::test_bear_by_ma -v
```

期待: `FAILED` — `kabusys.ai.regime_detector` が存在しないため

- [ ] **Step 3: `__init__.py` と `regime_detector.py` の骨格を作成**

`src/kabusys/ai/__init__.py`（空ファイル）を作成。

`src/kabusys/ai/regime_detector.py` を新規作成：

```python
"""
市場レジーム判定モジュール

ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と
マクロ経済ニュースの LLM センチメント（重み30%）を合成して
市場レジーム（'bull' / 'neutral' / 'bear'）を日次で判定する。

処理フロー:
  1. API キー解決（引数 or 環境変数 OPENAI_API_KEY）
  2. prices_daily から 1321 の終値を取得し ma200_ratio を計算
  3. raw_news からマクロキーワードでフィルタしたタイトルを取得
  4. OpenAI API（gpt-4o-mini）でマクロセンチメントを評価（記事あり時のみ）
  5. レジームスコアを合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
  6. market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）

設計方針:
  - datetime.today() / date.today() を参照しない（ルックアヘッドバイアス防止）
  - prices_daily クエリは date < target_date の排他条件でルックアヘッドを防止
  - API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）
  - OpenAI 呼び出し関数は news_nlp からインポートせず独自実装（モジュール結合防止）
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import date

import duckdb
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from kabusys.ai.news_nlp import calc_news_window

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_ETF_CODE: str = "1321"          # 日経225連動型 ETF
_MA_WINDOW: int = 200             # 移動平均期間（日数）
_MA_SCALE: float = 10.0           # MA乖離のスケーリング係数（±10%乖離で±MA_WEIGHTに飽和）
_MA_WEIGHT: float = 0.7           # スコア合成での 200MA の重み
_MACRO_WEIGHT: float = 0.3        # マクロセンチメントの重み
_BULL_THRESHOLD: float = 0.2      # これ以上 → 'bull'
_BEAR_THRESHOLD: float = 0.2      # これ以下（-0.2）→ 'bear'
_MAX_MACRO_ARTICLES: int = 20     # LLM に渡すマクロ記事数上限
_MODEL: str = "gpt-4o-mini"
_MAX_RETRIES: int = 3
_RETRY_BASE_SECONDS: float = 1.0

_MACRO_KEYWORDS: list[str] = [
    # 日本
    "日銀", "日本銀行", "金利", "利上げ", "利下げ", "政策金利",
    "為替", "円安", "円高", "為替介入", "インフレ", "物価", "GDP",
    # 米国・グローバル
    "Fed", "FOMC", "CPI", "PPI", "雇用統計", "失業率",
    "米国債", "リセッション", "景気後退",
]

_SYSTEM_PROMPT = (
    "あなたは日本株の市場アナリストです。"
    "以下のマクロ経済ニュースを読み、日本株市場全体のセンチメントを "
    "-1.0〜1.0 のスコアで評価してください。"
    "1.0=非常にポジティブ（強気）、0.0=中立、-1.0=非常にネガティブ（弱気）。"
    '出力は厳密なJSONのみとしてください: {"macro_sentiment": 0.0}'
)


# ---------------------------------------------------------------------------
# 内部関数
# ---------------------------------------------------------------------------

def _calc_ma200_ratio(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> float:
    """ETF 1321 の直近 _MA_WINDOW 日の終値から 200 日 MA 乖離を計算する。

    ルックアヘッドバイアス防止のため target_date 未満（排他）のデータのみ使用。
    データが _MA_WINDOW 日未満の場合は 1.0（中立）を返し WARNING ログを出す。

    Returns:
        ma200_ratio: 最新終値 / 200 日単純移動平均。中立時は 1.0。
    """
    rows = conn.execute(
        """
        SELECT close FROM prices_daily
        WHERE code = ? AND date < ?
        ORDER BY date DESC LIMIT ?
        """,
        [_ETF_CODE, target_date, _MA_WINDOW],
    ).fetchall()

    if not rows:
        logger.warning(
            "_calc_ma200_ratio: 1321 のデータなし target_date=%s, ma200_ratio=1.0 を使用",
            target_date,
        )
        return 1.0

    if len(rows) < _MA_WINDOW:
        logger.warning(
            "_calc_ma200_ratio: データ不足 %d 日 (必要: %d), ma200_ratio=1.0 を使用",
            len(rows),
            _MA_WINDOW,
        )
        return 1.0

    closes = [float(r[0]) for r in rows]
    # rows は DESC 順（最新が先頭）
    latest_close = closes[0]
    ma200 = sum(closes) / len(closes)
    return latest_close / ma200
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_regime_detector.py::test_bear_by_ma tests/test_regime_detector.py::test_bull_by_ma tests/test_regime_detector.py::test_insufficient_prices tests/test_regime_detector.py::test_no_prices -v
```

期待: `4 passed`

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/ai/__init__.py src/kabusys/ai/regime_detector.py tests/test_regime_detector.py
git commit -m "feat: implement _calc_ma200_ratio with lookahead-bias prevention"
```

---

## Task 3: `_fetch_macro_news()` を実装

マクロキーワードで raw_news をフィルタし、タイトルリストを返す内部関数。

**Files:**
- Modify: `src/kabusys/ai/regime_detector.py`
- Test: `tests/test_regime_detector.py`

- [ ] **Step 1: 失敗するテストを追加**

```python
# ---------------------------------------------------------------------------
# Task 3: _fetch_macro_news()
# ---------------------------------------------------------------------------

from datetime import datetime as dt_class

# news_nlp.calc_news_window に合わせたウィンドウ（TARGET_DATE=2026-03-21 の場合）
# window_start = 2026-03-20 06:00 UTC, window_end = 2026-03-20 23:30 UTC
_MACRO_WINDOW_DT = dt_class(2026, 3, 20, 12, 0, 0)   # ウィンドウ内
_OUT_OF_WINDOW_DT = dt_class(2026, 3, 18, 12, 0, 0)  # ウィンドウ外


def test_fetch_macro_news_keyword_match(conn):
    """マクロキーワードを含む記事のみが返される。"""
    from kabusys.ai.regime_detector import _fetch_macro_news
    from kabusys.ai.news_nlp import calc_news_window

    window_start, window_end = calc_news_window(TARGET_DATE)
    _insert_raw_news(conn, "n1", _MACRO_WINDOW_DT, "日銀が政策金利を引き上げ")
    _insert_raw_news(conn, "n2", _MACRO_WINDOW_DT, "トヨタが業績上方修正")  # マクロ外

    titles = _fetch_macro_news(conn, window_start, window_end)

    assert len(titles) == 1
    assert "日銀が政策金利を引き上げ" in titles


def test_fetch_macro_news_no_match(conn):
    """マクロキーワードなし → 空リストを返す。"""
    from kabusys.ai.regime_detector import _fetch_macro_news
    from kabusys.ai.news_nlp import calc_news_window

    window_start, window_end = calc_news_window(TARGET_DATE)
    _insert_raw_news(conn, "n1", _MACRO_WINDOW_DT, "ソニーが新製品発表")

    titles = _fetch_macro_news(conn, window_start, window_end)
    assert titles == []


def test_fetch_macro_news_out_of_window(conn):
    """ウィンドウ外の記事は含まれない。"""
    from kabusys.ai.regime_detector import _fetch_macro_news
    from kabusys.ai.news_nlp import calc_news_window

    window_start, window_end = calc_news_window(TARGET_DATE)
    _insert_raw_news(conn, "n1", _OUT_OF_WINDOW_DT, "FOMCが利上げを決定")  # 古すぎる

    titles = _fetch_macro_news(conn, window_start, window_end)
    assert titles == []


def test_fetch_macro_news_limit(conn):
    """_MAX_MACRO_ARTICLES 件を超える場合は上限で切り捨てる。"""
    from kabusys.ai.regime_detector import _fetch_macro_news, _MAX_MACRO_ARTICLES
    from kabusys.ai.news_nlp import calc_news_window

    window_start, window_end = calc_news_window(TARGET_DATE)
    for i in range(_MAX_MACRO_ARTICLES + 5):
        _insert_raw_news(conn, f"n{i}", _MACRO_WINDOW_DT, f"日銀が会合 {i}")

    titles = _fetch_macro_news(conn, window_start, window_end)
    assert len(titles) <= _MAX_MACRO_ARTICLES
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_regime_detector.py::test_fetch_macro_news_keyword_match -v
```

期待: `FAILED` — `_fetch_macro_news` が未定義

- [ ] **Step 3: `_fetch_macro_news()` を実装**

`regime_detector.py` に追加：

```python
def _fetch_macro_news(
    conn: duckdb.DuckDBPyConnection,
    window_start,
    window_end,
) -> list[str]:
    """raw_news からマクロキーワードに一致するタイトルを取得する。

    ウィンドウは [window_start, window_end) の半開区間。
    0 件の場合は空リストを返す（LLM コールなし）。

    Returns:
        タイトル文字列のリスト（最大 _MAX_MACRO_ARTICLES 件、新しい順）。
    """
    if not _MACRO_KEYWORDS:
        return []

    conditions = " OR ".join(["title LIKE ?" for _ in _MACRO_KEYWORDS])
    like_params = [f"%{kw}%" for kw in _MACRO_KEYWORDS]

    rows = conn.execute(
        f"""
        SELECT title FROM raw_news
        WHERE datetime >= ? AND datetime < ?
          AND ({conditions})
        ORDER BY datetime DESC LIMIT ?
        """,
        [window_start, window_end] + like_params + [_MAX_MACRO_ARTICLES],
    ).fetchall()

    return [r[0] for r in rows if r[0]]
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_regime_detector.py::test_fetch_macro_news_keyword_match tests/test_regime_detector.py::test_fetch_macro_news_no_match tests/test_regime_detector.py::test_fetch_macro_news_out_of_window tests/test_regime_detector.py::test_fetch_macro_news_limit -v
```

期待: `4 passed`

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/ai/regime_detector.py tests/test_regime_detector.py
git commit -m "feat: implement _fetch_macro_news with keyword filter and window"
```

---

## Task 4: `_call_openai_api()` と `_score_macro()` を実装

OpenAI API 呼び出しとリトライ処理を担う内部関数。

**Files:**
- Modify: `src/kabusys/ai/regime_detector.py`
- Test: `tests/test_regime_detector.py`

- [ ] **Step 1: 失敗するテストを追加**

```python
# ---------------------------------------------------------------------------
# Task 4: _score_macro()
# ---------------------------------------------------------------------------

def test_score_macro_returns_float(conn):
    """正常系：LLM が {"macro_sentiment": -0.7} を返す → -0.7 が返される。"""
    from kabusys.ai.regime_detector import _score_macro

    mock_client = MagicMock()
    mock_resp = _make_macro_response(-0.7)
    with patch("kabusys.ai.regime_detector._call_openai_api", return_value=mock_resp):
        score = _score_macro(mock_client, ["日銀が利上げ"])

    assert abs(score - (-0.7)) < 1e-9


def test_score_macro_no_titles(conn):
    """タイトルリストが空 → LLM を呼ばず 0.0 を返す。"""
    from kabusys.ai.regime_detector import _score_macro

    mock_client = MagicMock()
    with patch("kabusys.ai.regime_detector._call_openai_api") as mock_api:
        score = _score_macro(mock_client, [])

    mock_api.assert_not_called()
    assert score == 0.0


def test_score_macro_api_failure_fallback():
    """API 失敗（全リトライ消費）→ macro_sentiment=0.0 で継続。"""
    from kabusys.ai.regime_detector import _score_macro
    from openai import APIConnectionError

    mock_client = MagicMock()
    with patch(
        "kabusys.ai.regime_detector._call_openai_api",
        side_effect=APIConnectionError(request=MagicMock()),
    ):
        score = _score_macro(mock_client, ["Fed が利上げ"])

    assert score == 0.0


def test_score_macro_json_parse_failure():
    """JSON パース失敗 → 0.0 フォールバック。"""
    from kabusys.ai.regime_detector import _score_macro

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "invalid json"
    with patch("kabusys.ai.regime_detector._call_openai_api", return_value=mock_resp):
        score = _score_macro(mock_client, ["CPI が予想超え"])

    assert score == 0.0


def test_score_macro_clip():
    """スコアが範囲外 → ±1.0 にクリップされる。"""
    from kabusys.ai.regime_detector import _score_macro

    mock_client = MagicMock()
    mock_resp = _make_macro_response(2.5)  # 範囲外
    with patch("kabusys.ai.regime_detector._call_openai_api", return_value=mock_resp):
        score = _score_macro(mock_client, ["リセッション懸念"])

    assert score == 1.0
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_regime_detector.py::test_score_macro_returns_float -v
```

期待: `FAILED` — `_score_macro` が未定義

- [ ] **Step 3: `_call_openai_api()` と `_score_macro()` を実装**

`regime_detector.py` に追加：

```python
def _call_openai_api(client: "OpenAI", messages: list[dict]) -> object:
    """OpenAI Chat Completions API を呼び出す。

    テスト時は unittest.mock.patch("kabusys.ai.regime_detector._call_openai_api") で差し替える。
    news_nlp._call_openai_api とは意図的に別実装（モジュール間でプライベート関数を共有しない）。
    """
    return client.chat.completions.create(
        model=_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
        timeout=30,
    )


def _score_macro(client: "OpenAI", titles: list[str]) -> float:
    """マクロニュースタイトルを LLM に渡し、市場センチメントスコアを返す。

    titles が空の場合は LLM を呼ばず 0.0 を返す。
    API 失敗・JSON パース失敗時は 0.0 にフォールバックし WARNING ログを出す（例外を上げない）。

    Returns:
        macro_sentiment: -1.0〜1.0 のスコア（クリップ済み）。
    """
    if not titles:
        return 0.0

    user_content = "\n".join(f"- {t}" for t in titles)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    for attempt in range(_MAX_RETRIES):
        try:
            resp = _call_openai_api(client, messages)
            content = resp.choices[0].message.content
            data = json.loads(content)
            raw_score = float(data["macro_sentiment"])
            return max(-1.0, min(1.0, raw_score))
        except (RateLimitError, APIConnectionError, APITimeoutError) as exc:
            if attempt >= _MAX_RETRIES - 1:
                logger.warning(
                    "_score_macro: API失敗（全リトライ消費）: %s, macro_sentiment=0.0", exc
                )
                return 0.0
            wait = _RETRY_BASE_SECONDS * (2 ** attempt)
            logger.warning("_score_macro: リトライ %d/%d: %s", attempt + 1, _MAX_RETRIES, exc)
            time.sleep(wait)
        except APIError as exc:
            status = getattr(exc, "status_code", 500)
            if status is not None and 500 <= status < 600:
                if attempt >= _MAX_RETRIES - 1:
                    logger.warning(
                        "_score_macro: API失敗（全リトライ消費）: %s, macro_sentiment=0.0", exc
                    )
                    return 0.0
                wait = _RETRY_BASE_SECONDS * (2 ** attempt)
                logger.warning(
                    "_score_macro: リトライ %d/%d: %s", attempt + 1, _MAX_RETRIES, exc
                )
                time.sleep(wait)
            else:
                logger.warning(
                    "_score_macro: API失敗（非5xx）: %s, macro_sentiment=0.0", exc
                )
                return 0.0
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            logger.warning(
                "_score_macro: レスポンスパース失敗: %s, macro_sentiment=0.0", exc
            )
            return 0.0

    return 0.0
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_regime_detector.py::test_score_macro_returns_float tests/test_regime_detector.py::test_score_macro_no_titles tests/test_regime_detector.py::test_score_macro_api_failure_fallback tests/test_regime_detector.py::test_score_macro_json_parse_failure tests/test_regime_detector.py::test_score_macro_clip -v
```

期待: `5 passed`

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/ai/regime_detector.py tests/test_regime_detector.py
git commit -m "feat: implement _call_openai_api and _score_macro with retry"
```

---

## Task 5: `score_regime()` メイン関数を実装

スコア合成・ラベル決定・DB 書き込みをすべて行う公開関数。

**Files:**
- Modify: `src/kabusys/ai/regime_detector.py`
- Test: `tests/test_regime_detector.py`

- [ ] **Step 1: 失敗するテストを追加**

```python
# ---------------------------------------------------------------------------
# Task 5: score_regime()
# ---------------------------------------------------------------------------

def test_bear_by_ma_end_to_end(conn):
    """test_bear_by_ma と同条件 → score_regime が 'bear' を market_regime に書く。"""
    from kabusys.ai.regime_detector import score_regime

    _insert_prices_uniform(conn, "1321", 199, 100.0, TARGET_DATE)
    _insert_price(conn, "1321", TARGET_DATE - timedelta(days=1), 85.0)

    mock_resp = _make_macro_response(0.0)
    with patch("kabusys.ai.regime_detector._call_openai_api", return_value=mock_resp):
        result = score_regime(conn, TARGET_DATE, api_key="test-key")

    assert result == 1
    row = conn.execute(
        "SELECT regime_label, regime_score, ma200_ratio, macro_sentiment "
        "FROM market_regime WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert row[0] == "bear"
    assert row[2] < 1.0    # ma200_ratio が 1.0 未満
    assert row[3] == 0.0   # マクロニュースなしのためLLMを呼んでも 0.0


def test_bull_by_ma_end_to_end(conn):
    """1321 が 200MA を大きく上回る → 'bull' ラベルが書き込まれる。"""
    from kabusys.ai.regime_detector import score_regime

    _insert_prices_uniform(conn, "1321", 199, 100.0, TARGET_DATE)
    _insert_price(conn, "1321", TARGET_DATE - timedelta(days=1), 130.0)

    with patch("kabusys.ai.regime_detector._call_openai_api", return_value=_make_macro_response(0.0)):
        result = score_regime(conn, TARGET_DATE, api_key="test-key")

    assert result == 1
    row = conn.execute(
        "SELECT regime_label FROM market_regime WHERE date = ?", [TARGET_DATE]
    ).fetchone()
    assert row[0] == "bull"


def test_macro_pushes_to_bear(conn):
    """MA は中立（ratio=1.0）、マクロ LLM が -1.0 → 'bear'。"""
    from kabusys.ai.regime_detector import score_regime

    # 200 日すべて同一価格（ratio=1.0 → MA 寄与=0.0）
    _insert_prices_uniform(conn, "1321", 200, 100.0, TARGET_DATE)
    # マクロニュースを挿入（キーワードにマッチするもの）
    _insert_raw_news(conn, "n1", _MACRO_WINDOW_DT, "Fed がリセッション警告")

    mock_resp = _make_macro_response(-1.0)
    with patch("kabusys.ai.regime_detector._call_openai_api", return_value=mock_resp):
        score_regime(conn, TARGET_DATE, api_key="test-key")

    row = conn.execute(
        "SELECT regime_label, regime_score, macro_sentiment FROM market_regime WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    # score = 0.7*0.0 + 0.3*(-1.0) = -0.3 → 'bear'
    assert row[0] == "bear"
    assert row[2] == -1.0


def test_no_macro_news(conn):
    """マクロニュース 0 件 → macro_sentiment=0.0、MA のみで判定。"""
    from kabusys.ai.regime_detector import score_regime

    # 200 日全部同一価格（ratio=1.0）
    _insert_prices_uniform(conn, "1321", 200, 100.0, TARGET_DATE)
    # raw_news には非マクロ記事のみ
    _insert_raw_news(conn, "n1", _MACRO_WINDOW_DT, "トヨタが業績発表")

    with patch("kabusys.ai.regime_detector._call_openai_api") as mock_api:
        score_regime(conn, TARGET_DATE, api_key="test-key")

    # LLM が呼ばれていないこと（マクロ記事 0 件のため）
    mock_api.assert_not_called()

    row = conn.execute(
        "SELECT regime_label, macro_sentiment FROM market_regime WHERE date = ?", [TARGET_DATE]
    ).fetchone()
    assert row[1] == 0.0
    assert row[0] == "neutral"  # ratio=1.0 → score=0.0 → neutral


def test_idempotent(conn):
    """同日 2 回実行 → レコード 1 件のみ、2 回目の値に更新される。"""
    from kabusys.ai.regime_detector import score_regime

    _insert_prices_uniform(conn, "1321", 200, 100.0, TARGET_DATE)

    with patch("kabusys.ai.regime_detector._call_openai_api", return_value=_make_macro_response(0.0)):
        score_regime(conn, TARGET_DATE, api_key="test-key")
        # 2 回目は micro な価格変化あり → 若干異なるスコアになりうるが、行数は 1
        score_regime(conn, TARGET_DATE, api_key="test-key")

    count = conn.execute(
        "SELECT COUNT(*) FROM market_regime WHERE date = ?", [TARGET_DATE]
    ).fetchone()[0]
    assert count == 1


def test_api_failure(conn):
    """API 例外 → macro_sentiment=0.0 で処理継続、regime_label が確定する。"""
    from kabusys.ai.regime_detector import score_regime
    from openai import APIConnectionError

    _insert_prices_uniform(conn, "1321", 200, 100.0, TARGET_DATE)
    _insert_raw_news(conn, "n1", _MACRO_WINDOW_DT, "FOMC が声明発表")

    with patch(
        "kabusys.ai.regime_detector._call_openai_api",
        side_effect=APIConnectionError(request=MagicMock()),
    ):
        result = score_regime(conn, TARGET_DATE, api_key="test-key")

    assert result == 1
    row = conn.execute(
        "SELECT regime_label, macro_sentiment FROM market_regime WHERE date = ?", [TARGET_DATE]
    ).fetchone()
    assert row is not None
    assert row[1] == 0.0     # フォールバック
    assert row[0] == "neutral"  # ratio=1.0, macro=0.0 → score=0.0 → neutral


def test_no_api_key(conn):
    """API キー未設定 → ValueError を raise。"""
    from kabusys.ai.regime_detector import score_regime
    import os

    # 環境変数を一時的に削除
    env_backup = os.environ.pop("OPENAI_API_KEY", None)
    try:
        with pytest.raises(ValueError, match="API キー"):
            score_regime(conn, TARGET_DATE, api_key=None)
    finally:
        if env_backup is not None:
            os.environ["OPENAI_API_KEY"] = env_backup


def test_db_write_failure(conn):
    """DB 書き込み失敗 → ROLLBACK して例外が上位に伝播、market_regime に行なし。"""
    from kabusys.ai.regime_detector import score_regime

    _insert_prices_uniform(conn, "1321", 200, 100.0, TARGET_DATE)

    with patch("kabusys.ai.regime_detector._call_openai_api", return_value=_make_macro_response(0.0)):
        with patch.object(
            conn,
            "execute",
            wraps=conn.execute,
            side_effect=_make_execute_fail_on_insert(conn),
        ):
            with pytest.raises(Exception):
                score_regime(conn, TARGET_DATE, api_key="test-key")

    count = conn.execute(
        "SELECT COUNT(*) FROM market_regime WHERE date = ?", [TARGET_DATE]
    ).fetchone()[0]
    assert count == 0


def _make_execute_fail_on_insert(original_conn):
    """INSERT INTO market_regime が呼ばれたときだけ例外を発生させるヘルパー。"""
    original_execute = original_conn.execute

    def side_effect(sql, params=None):
        if "INSERT INTO market_regime" in sql:
            raise RuntimeError("DB 書き込みエラー（テスト用）")
        if params is not None:
            return original_execute(sql, params)
        return original_execute(sql)

    return side_effect
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_regime_detector.py::test_bear_by_ma_end_to_end -v
```

期待: `FAILED` — `score_regime` が未定義

- [ ] **Step 3: `score_regime()` を実装**

`regime_detector.py` に追加：

```python
def score_regime(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    api_key: str | None = None,
) -> int:
    """市場レジームスコアを計算し market_regime テーブルへ書き込む。

    Args:
        conn:        DuckDB 接続。prices_daily / raw_news / market_regime を参照。
        target_date: 判定対象日。内部では datetime.today() を参照しない（ルックアヘッドバイアス防止）。
        api_key:     OpenAI API キー。None の場合は環境変数 OPENAI_API_KEY を参照。

    Returns:
        1（成功）

    Raises:
        ValueError: api_key が未設定かつ環境変数 OPENAI_API_KEY も未設定の場合。
        Exception:  DB 書き込み失敗時（ROLLBACK 後に上位へ伝播）。
    """
    # [1] API キー解決
    resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not resolved_key:
        raise ValueError(
            "OpenAI API キーが未設定です。api_key 引数または環境変数 OPENAI_API_KEY を設定してください。"
        )

    # [2] 1321 の 200 日 MA 乖離を計算
    ma200_ratio = _calc_ma200_ratio(conn, target_date)

    # [3] マクロニュース取得
    window_start, window_end = calc_news_window(target_date)
    titles = _fetch_macro_news(conn, window_start, window_end)

    # [4] LLM でマクロセンチメントを評価（記事あり時のみ）
    client = OpenAI(api_key=resolved_key)
    macro_sentiment = _score_macro(client, titles)

    # [5] レジームスコア合成
    raw_score = _MA_WEIGHT * (ma200_ratio - 1.0) * _MA_SCALE + _MACRO_WEIGHT * macro_sentiment
    regime_score = max(-1.0, min(1.0, raw_score))

    if regime_score >= _BULL_THRESHOLD:
        regime_label = "bull"
    elif regime_score <= -_BEAR_THRESHOLD:
        regime_label = "bear"
    else:
        regime_label = "neutral"

    # [6] market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    conn.execute("BEGIN")
    try:
        conn.execute("DELETE FROM market_regime WHERE date = ?", [target_date])
        conn.execute(
            """
            INSERT INTO market_regime (date, regime_score, regime_label, ma200_ratio, macro_sentiment)
            VALUES (?, ?, ?, ?, ?)
            """,
            [target_date, regime_score, regime_label, ma200_ratio, macro_sentiment],
        )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception as rb_exc:
            logger.warning("score_regime: ROLLBACK failed: %s", rb_exc)
        raise

    logger.info(
        "score_regime: 完了 date=%s label=%s score=%.3f ma200_ratio=%.4f macro=%.3f",
        target_date, regime_label, regime_score, ma200_ratio, macro_sentiment,
    )
    return 1
```

- [ ] **Step 4: 全テストが通ることを確認**

```bash
pytest tests/test_regime_detector.py -v
```

期待: すべて `passed`（`test_db_write_failure` は mock 設計上スキップされる場合は確認後調整）

- [ ] **Step 5: 既存テストが壊れていないことを確認**

```bash
pytest tests/ -v --tb=short
```

期待: すべて `passed`

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/ai/regime_detector.py tests/test_regime_detector.py
git commit -m "feat: implement score_regime - market regime detection engine"
```

---

## 完了後の確認

- [ ] `pytest tests/ -v` がすべて pass
- [ ] `src/kabusys/ai/regime_detector.py` が `score_regime()` を公開している
- [ ] `schema.py` の `init_schema()` が `market_regime` テーブルを作成する
- [ ] `test_regime_detector.py` がスペック記載の全テストケースをカバーしている:
  - `test_bear_by_ma_end_to_end` ✓
  - `test_bull_by_ma_end_to_end` ✓
  - `test_macro_pushes_to_bear` ✓
  - `test_no_macro_news` ✓
  - `test_idempotent` ✓
  - `test_api_failure` ✓
  - `test_no_api_key` ✓
  - `test_db_write_failure` ✓
  - `test_insufficient_prices` ✓

---

## 実装上の注意事項

1. **ルックアヘッドバイアス防止**: `prices_daily` クエリは必ず `date < target_date`（排他）を使うこと
2. **`datetime.today()` / `date.today()` 禁止**: CLAUDE.md の制約
3. **AI は発注しない**: `score_regime()` はスコア生成のみ。`market_regime` テーブルへの書き込みで完結
4. **冪等性**: DELETE → INSERT のパターンで同日 2 回実行しても 1 行のみ保持
5. **フェイルセーフ**: API 失敗は WARNING ログ + `macro_sentiment=0.0` で継続。DB 書き込み失敗のみ例外を上位に伝播
