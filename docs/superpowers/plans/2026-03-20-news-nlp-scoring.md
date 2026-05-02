# ニュースNLPスコアリングエンジン Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `raw_news` テーブルのニュース記事を OpenAI API でセンチメント分析し、銘柄ごとのスコアを `ai_scores` テーブルへ書き込む `score_news()` 関数を実装する。

**Architecture:** `src/kabusys/ai/news_nlp.py` に実装。`raw_news + news_symbols` から前日 15:00 JST ～ 当日 08:30 JST の記事を読み込み、同一銘柄の全テキストを結合して gpt-4o-mini へバッチ送信（最大 20 銘柄/回）する。全チャンクの処理が終わってから `ai_scores` へ一括 DELETE→INSERT する。API は銘柄ごとに 1 スコアを返すため、LLM が全記事テキストを統合してスコアを算出する（= 実質的な平均化）。

**Tech Stack:** Python 3.10+, DuckDB 0.10, openai Python SDK (>=1.0), unittest.mock（テスト）

---

## ファイル構成

| 操作 | パス | 役割 |
|------|------|------|
| 新規作成 | `src/kabusys/ai/__init__.py` | `score_news` を公開 |
| 新規作成 | `src/kabusys/ai/news_nlp.py` | 実装本体 |
| 新規作成 | `tests/test_news_nlp.py` | 全テスト |
| 修正 | `requirements.txt` | `openai>=1.0,<2` を追加 |

---

## Task 1: openai パッケージの追加

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: requirements.txt に openai を追加**

```text
# requirements.txt の末尾に追加
openai>=1.0,<2
```

- [ ] **Step 2: インストールして確認**

```bash
pip install openai>=1.0,<2
python -c "import openai; print(openai.__version__)"
```

Expected: `1.x.x` のようなバージョン番号が表示される

- [ ] **Step 3: コミット**

```bash
git add requirements.txt
git commit -m "chore: add openai dependency for news NLP scoring"
```

---

## Task 2: テストファイルの骨格作成（全テストを失敗状態で追加）

**Files:**
- Create: `tests/test_news_nlp.py`

- [ ] **Step 1: テストファイルを作成**

```python
"""
ニュースNLPスコアリングエンジン テスト

score_news() の動作を検証する。
OpenAI API は unittest.mock でモックし、実際の API コールは発生させない。

集計の仕様:
  - 同一銘柄の全記事テキストを結合して API に送信する
  - API は銘柄ごとに 1 スコアを返す（LLM が全記事を統合評価）
  - 返されたスコアを ±1.0 にクリップして ai_scores に書き込む
"""

from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import duckdb
import pytest

from kabusys.data.schema import init_schema


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    """インメモリ DuckDB 接続（テスト毎に新規作成）。"""
    c = duckdb.connect(":memory:")
    init_schema(c)
    yield c
    c.close()


TARGET_DATE = date(2026, 3, 20)
# TARGET_DATE=2026-03-20 の場合のウィンドウ（UTC）:
#   window_start = 2026-03-19 06:00 UTC（前日 15:00 JST）
#   window_end   = 2026-03-19 23:30 UTC（当日 08:30 JST = 前日 23:30 UTC）
_WINDOW_DT = datetime(2026, 3, 19, 20, 0, 0)  # ウィンドウ内の UTC 時刻


def _insert_article(conn, news_id: str, dt: datetime, title: str, content: str = "") -> None:
    """raw_news に1件挿入するヘルパー。"""
    conn.execute(
        "INSERT INTO raw_news (id, datetime, source, title, content, url) "
        "VALUES (?, ?, 'test', ?, ?, 'http://example.com')",
        [news_id, dt, title, content],
    )


def _link_code(conn, news_id: str, code: str) -> None:
    """news_symbols に銘柄紐付けを挿入するヘルパー。"""
    conn.execute(
        "INSERT INTO news_symbols (news_id, code) VALUES (?, ?)",
        [news_id, code],
    )


def _make_api_response(results: list[dict]) -> MagicMock:
    """OpenAI API レスポンスのモックオブジェクトを生成する。"""
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps({"results": results})
    return mock_resp


# ---------------------------------------------------------------------------
# テスト
# ---------------------------------------------------------------------------


def test_score_news_basic(conn):
    """正常系：記事あり → ai_scores に書き込まれる。"""
    from kabusys.ai.news_nlp import score_news

    _insert_article(conn, "art1", _WINDOW_DT, "トヨタが業績上方修正")
    _link_code(conn, "art1", "7203")

    mock_resp = _make_api_response([{"code": "7203", "score": 0.8}])
    with patch("kabusys.ai.news_nlp._call_openai_api", return_value=mock_resp):
        count = score_news(conn, TARGET_DATE, api_key="test-key")

    assert count == 1
    row = conn.execute(
        "SELECT sentiment_score, ai_score FROM ai_scores WHERE date = ? AND code = ?",
        [TARGET_DATE, "7203"],
    ).fetchone()
    assert row is not None
    assert abs(row[0] - 0.8) < 1e-9
    assert abs(row[1] - 0.8) < 1e-9


def test_score_news_idempotent(conn):
    """同日2回実行後のレコード数が1回目と同一で、スコアが2回目の値に更新される。"""
    from kabusys.ai.news_nlp import score_news

    _insert_article(conn, "art1", _WINDOW_DT, "ソニー新製品")
    _link_code(conn, "art1", "6758")

    with patch("kabusys.ai.news_nlp._call_openai_api",
               return_value=_make_api_response([{"code": "6758", "score": 0.5}])):
        score_news(conn, TARGET_DATE, api_key="test-key")

    with patch("kabusys.ai.news_nlp._call_openai_api",
               return_value=_make_api_response([{"code": "6758", "score": 0.9}])):
        score_news(conn, TARGET_DATE, api_key="test-key")

    rows = conn.execute(
        "SELECT sentiment_score FROM ai_scores WHERE date = ?", [TARGET_DATE]
    ).fetchall()
    assert len(rows) == 1
    assert abs(rows[0][0] - 0.9) < 1e-9


def test_score_news_no_articles(conn):
    """記事なし → 0件・エラーなし。"""
    from kabusys.ai.news_nlp import score_news

    count = score_news(conn, TARGET_DATE, api_key="test-key")
    assert count == 0


def test_score_news_api_failure(conn):
    """API 例外 → スキップしてシステム継続。0件書き込み。"""
    from kabusys.ai.news_nlp import score_news

    _insert_article(conn, "art1", _WINDOW_DT, "任天堂決算")
    _link_code(conn, "art1", "7974")

    with patch("kabusys.ai.news_nlp._call_openai_api", side_effect=Exception("API error")):
        count = score_news(conn, TARGET_DATE, api_key="test-key")

    assert count == 0
    assert conn.execute("SELECT COUNT(*) FROM ai_scores WHERE date = ?", [TARGET_DATE]).fetchone()[0] == 0


def test_score_news_json_parse_error(conn):
    """不正 JSON レスポンス → スキップして継続。"""
    from kabusys.ai.news_nlp import score_news

    _insert_article(conn, "art1", _WINDOW_DT, "パナソニック")
    _link_code(conn, "art1", "6752")

    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "これは不正なJSON{"

    with patch("kabusys.ai.news_nlp._call_openai_api", return_value=mock_resp):
        count = score_news(conn, TARGET_DATE, api_key="test-key")

    assert count == 0


def test_score_news_score_clipping(conn):
    """範囲外スコア（1.5）→ 1.0 にクリップ。"""
    from kabusys.ai.news_nlp import score_news

    _insert_article(conn, "art1", _WINDOW_DT, "三菱UFJ")
    _link_code(conn, "art1", "8306")

    with patch("kabusys.ai.news_nlp._call_openai_api",
               return_value=_make_api_response([{"code": "8306", "score": 1.5}])):
        score_news(conn, TARGET_DATE, api_key="test-key")

    row = conn.execute(
        "SELECT sentiment_score FROM ai_scores WHERE date = ? AND code = ?",
        [TARGET_DATE, "8306"],
    ).fetchone()
    assert row is not None
    assert abs(row[0] - 1.0) < 1e-9


def test_score_news_score_clipping_negative(conn):
    """範囲外スコア（-2.0）→ -1.0 にクリップ。"""
    from kabusys.ai.news_nlp import score_news

    _insert_article(conn, "art1", _WINDOW_DT, "三菱UFJ悪材料")
    _link_code(conn, "art1", "8306")

    with patch("kabusys.ai.news_nlp._call_openai_api",
               return_value=_make_api_response([{"code": "8306", "score": -2.0}])):
        score_news(conn, TARGET_DATE, api_key="test-key")

    row = conn.execute(
        "SELECT sentiment_score FROM ai_scores WHERE date = ? AND code = ?",
        [TARGET_DATE, "8306"],
    ).fetchone()
    assert row is not None
    assert abs(row[0] - (-1.0)) < 1e-9


def test_score_news_multi_article_same_code(conn):
    """同銘柄に複数記事 → 全テキスト結合して API に送信し、返ってきた 1 スコアが書き込まれる。"""
    from kabusys.ai.news_nlp import score_news

    _insert_article(conn, "art1", _WINDOW_DT, "トヨタ記事1", "本文A")
    _insert_article(conn, "art2", _WINDOW_DT, "トヨタ記事2", "本文B")
    _link_code(conn, "art1", "7203")
    _link_code(conn, "art2", "7203")

    captured_content = {}

    def capture_call(client, messages):
        captured_content["user"] = messages[-1]["content"]
        return _make_api_response([{"code": "7203", "score": 0.6}])

    with patch("kabusys.ai.news_nlp._call_openai_api", side_effect=capture_call):
        count = score_news(conn, TARGET_DATE, api_key="test-key")

    assert count == 1
    # 両方の記事テキストがプロンプトに含まれること
    assert "トヨタ記事1" in captured_content["user"]
    assert "トヨタ記事2" in captured_content["user"]
    row = conn.execute(
        "SELECT sentiment_score FROM ai_scores WHERE date = ? AND code = ?",
        [TARGET_DATE, "7203"],
    ).fetchone()
    assert abs(row[0] - 0.6) < 1e-9


def test_score_news_chunk_split(conn):
    """21銘柄 → 2チャンクに分割して API を計2回コール。"""
    from kabusys.ai.news_nlp import score_news

    codes = [f"{1000 + i}" for i in range(21)]
    for i, code in enumerate(codes):
        _insert_article(conn, f"art{i}", _WINDOW_DT, f"記事{i}")
        _link_code(conn, f"art{i}", code)

    with patch("kabusys.ai.news_nlp._call_openai_api") as mock_api:
        mock_api.side_effect = [
            _make_api_response([{"code": c, "score": 0.1} for c in codes[:20]]),
            _make_api_response([{"code": c, "score": 0.1} for c in codes[20:]]),
        ]
        count = score_news(conn, TARGET_DATE, api_key="test-key")

    assert mock_api.call_count == 2
    assert count == 21


def test_score_news_partial_chunk_failure(conn):
    """2チャンク中1チャンク失敗 → 成功チャンクのスコアのみ書き込まれる。"""
    from kabusys.ai.news_nlp import score_news

    codes = [f"{1000 + i}" for i in range(21)]
    for i, code in enumerate(codes):
        _insert_article(conn, f"art{i}", _WINDOW_DT, f"記事{i}")
        _link_code(conn, f"art{i}", code)

    with patch("kabusys.ai.news_nlp._call_openai_api") as mock_api:
        mock_api.side_effect = [
            _make_api_response([{"code": c, "score": 0.5} for c in codes[:20]]),
            Exception("chunk 2 failed"),
        ]
        count = score_news(conn, TARGET_DATE, api_key="test-key")

    # チャンク1の20銘柄だけ書き込まれる
    assert count == 20
    saved_codes = {
        r[0] for r in conn.execute(
            "SELECT code FROM ai_scores WHERE date = ?", [TARGET_DATE]
        ).fetchall()
    }
    assert saved_codes == set(codes[:20])
    assert codes[20] not in saved_codes


def test_score_news_no_api_key(conn):
    """api_key 未設定・環境変数なし → ValueError。"""
    import os
    from kabusys.ai.news_nlp import score_news

    env_backup = os.environ.pop("OPENAI_API_KEY", None)
    try:
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            score_news(conn, TARGET_DATE, api_key=None)
    finally:
        if env_backup is not None:
            os.environ["OPENAI_API_KEY"] = env_backup


def test_score_news_response_validation_missing_key(conn):
    """`"results"` キー欠損レスポンス → スキップして継続。"""
    from kabusys.ai.news_nlp import score_news

    _insert_article(conn, "art1", _WINDOW_DT, "キーエンス")
    _link_code(conn, "art1", "6861")

    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps({"data": []})

    with patch("kabusys.ai.news_nlp._call_openai_api", return_value=mock_resp):
        count = score_news(conn, TARGET_DATE, api_key="test-key")

    assert count == 0


def test_score_news_response_validation_unknown_code(conn):
    """リクエスト外の銘柄コードを返してきた場合 → 無視（書き込まれない）。"""
    from kabusys.ai.news_nlp import score_news

    _insert_article(conn, "art1", _WINDOW_DT, "リクルート")
    _link_code(conn, "art1", "6098")

    # 6098 をリクエストしたが、9999（未知コード）が返ってきた
    with patch("kabusys.ai.news_nlp._call_openai_api",
               return_value=_make_api_response([{"code": "9999", "score": 0.5}])):
        count = score_news(conn, TARGET_DATE, api_key="test-key")

    assert count == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM ai_scores WHERE date = ? AND code = ?", [TARGET_DATE, "9999"]
    ).fetchone()[0] == 0
```

- [ ] **Step 2: テストが import エラーで失敗することを確認（実装前なので当然）**

```bash
python -m pytest tests/test_news_nlp.py -q --tb=line 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'kabusys.ai'`

- [ ] **Step 3: コミット**

```bash
git add tests/test_news_nlp.py
git commit -m "test: add failing tests for news NLP scoring engine"
```

---

## Task 3: モジュール骨格作成（import が通る最小構成）

**Files:**
- Create: `src/kabusys/ai/__init__.py`
- Create: `src/kabusys/ai/news_nlp.py`（スタブ）

- [ ] **Step 1: `src/kabusys/ai/__init__.py` を作成**

```python
from .news_nlp import score_news

__all__ = ["score_news"]
```

- [ ] **Step 2: `src/kabusys/ai/news_nlp.py` にスタブを作成**

```python
"""
ニュースNLPスコアリングモジュール

raw_news テーブルのニュース記事を OpenAI API（gpt-4o-mini）で
センチメント分析し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む。

処理フロー:
  1. タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST = UTC で前日 06:00 ～ 23:30）を計算
  2. raw_news + news_symbols から対象記事を銘柄ごとに集約
  3. 最大 20 銘柄ずつ OpenAI API へバッチ送信（gpt-4o-mini + JSON Mode）
  4. HTTP 429 はエクスポネンシャルバックオフでリトライ、その他例外はスキップ
  5. レスポンスをバリデーション（results キー・型・既知コード・スコア数値型）
  6. スコアを ±1.0 にクリップ
  7. 全チャンク処理後、ai_scores テーブルへ日付単位の置換（DELETE → INSERT）

設計方針:
  - datetime.today() / date.today() を参照しない（ルックアヘッドバイアス防止）
  - API 失敗時はスキップして継続（フェイルセーフ）
  - executemany 前に params が空でないことを確認（DuckDB 0.10 の制約）
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from datetime import date, datetime, timedelta
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_BATCH_SIZE: int = 20              # 1回の API コールで処理する最大銘柄数
_MODEL: str = "gpt-4o-mini"        # 使用する OpenAI モデル
_SCORE_CLIP: float = 1.0           # スコアのクリップ範囲（±1.0）
_MAX_RETRIES: int = 3              # レート制限時の最大リトライ回数
_RETRY_BASE_SECONDS: float = 1.0   # バックオフ初回待機秒数（指数的に増加）

# ニュース対象時間ウィンドウ（JST 基準、UTC 変換して DB 比較に使用）
# target_date の前日 15:00 JST = target_date の前日 06:00 UTC
_NEWS_WINDOW_START_HOUR: int = 6
_NEWS_WINDOW_START_MINUTE: int = 0
# target_date の当日 08:30 JST = target_date の前日 23:30 UTC
_NEWS_WINDOW_END_HOUR: int = 23
_NEWS_WINDOW_END_MINUTE: int = 30

_SYSTEM_PROMPT = (
    "あなたは日本株の金融アナリストです。"
    "各ニュースのセンチメントを -1.0〜1.0 のスコアで評価してください。"
    "1.0=非常にポジティブ、0.0=中立、-1.0=非常にネガティブ。"
    '必ず JSON 形式で返してください: {"results": [{"code": "XXXX", "score": 0.0}, ...]}'
)


def score_news(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    api_key: str | None = None,
) -> int:
    """raw_news を読み込み、センチメントスコアを ai_scores へ書き込む。

    Args:
        conn:        DuckDB 接続。raw_news / news_symbols / ai_scores テーブルを参照。
        target_date: スコア生成日。前日 15:00 JST 〜 当日 08:30 JST の記事を対象。
                     内部では datetime.today() を参照しない（ルックアヘッドバイアス防止）。
        api_key:     OpenAI API キー。None の場合は環境変数 OPENAI_API_KEY を参照。

    Returns:
        ai_scores テーブルへ書き込んだ銘柄数。

    Raises:
        ValueError: api_key が未設定かつ環境変数 OPENAI_API_KEY も未設定の場合。
    """
    raise NotImplementedError
```

- [ ] **Step 3: import エラーが解消されたことを確認**

```bash
python -m pytest tests/test_news_nlp.py::test_score_news_no_articles -q --tb=short
```

Expected: FAILED with `NotImplementedError`（ModuleNotFoundError ではない）

- [ ] **Step 4: コミット**

```bash
git add src/kabusys/ai/__init__.py src/kabusys/ai/news_nlp.py
git commit -m "feat: add news_nlp module skeleton"
```

---

## Task 4: API キー解決・タイムウィンドウ・記事取得の実装

**Files:**
- Modify: `src/kabusys/ai/news_nlp.py`

- [ ] **Step 1: `score_news()` の前半と `_fetch_articles()` を実装**

`score_news()` の `raise NotImplementedError` を以下で置き換える：

```python
    # 1. API キー解決
    resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not resolved_key:
        raise ValueError(
            "OpenAI API キーが未設定です。api_key 引数または環境変数 OPENAI_API_KEY を設定してください。"
        )

    # 2. タイムウィンドウ計算（JST 基準、UTC 変換）
    # target_date の前日 15:00 JST = target_date の日付で 06:00 UTC を作成し -1日
    # 例: target_date=2026-03-20 → window_start=2026-03-19 06:00 UTC
    window_start = datetime(
        target_date.year, target_date.month, target_date.day,
        _NEWS_WINDOW_START_HOUR, _NEWS_WINDOW_START_MINUTE,
    ) - timedelta(days=1)
    # target_date の当日 08:30 JST = target_date の日付で 23:30 UTC を作成し -1日
    # 例: target_date=2026-03-20 → window_end=2026-03-19 23:30 UTC
    window_end = datetime(
        target_date.year, target_date.month, target_date.day,
        _NEWS_WINDOW_END_HOUR, _NEWS_WINDOW_END_MINUTE,
    ) - timedelta(days=1)

    # 3. 記事を銘柄コードごとに集約
    article_map = _fetch_articles(conn, window_start, window_end)
    if not article_map:
        logger.info("score_news: 対象記事なし date=%s", target_date)
        return 0

    logger.info(
        "score_news: 対象記事数=%d 対象銘柄数=%d date=%s",
        sum(len(v) for v in article_map.values()),
        len(article_map),
        target_date,
    )
    raise NotImplementedError  # Task 5 で置き換え
```

同ファイルの末尾に `_fetch_articles()` を追加：

```python
def _fetch_articles(
    conn: duckdb.DuckDBPyConnection,
    window_start: datetime,
    window_end: datetime,
) -> dict[str, list[str]]:
    """指定時間ウィンドウの記事を銘柄コードごとに集約して返す。

    raw_news.datetime は UTC で保存されている前提。

    Returns:
        {code: [text1, text2, ...]} の辞書。text = "タイトル 本文"
    """
    rows = conn.execute(
        """
        SELECT ns.code, n.title, n.content
        FROM raw_news n
        JOIN news_symbols ns ON ns.news_id = n.id
        WHERE n.datetime >= ? AND n.datetime < ?
        """,
        [window_start, window_end],
    ).fetchall()

    article_map: dict[str, list[str]] = {}
    for code, title, content in rows:
        text = f"{title or ''} {content or ''}".strip()
        article_map.setdefault(code, []).append(text)
    return article_map
```

- [ ] **Step 2: api_key 未設定テストと記事なしテストが通ることを確認**

```bash
python -m pytest tests/test_news_nlp.py::test_score_news_no_api_key tests/test_news_nlp.py::test_score_news_no_articles -v
```

Expected: 2件 PASSED

---

## Task 5: OpenAI API 呼び出し・バリデーション・スコア抽出の実装

**Files:**
- Modify: `src/kabusys/ai/news_nlp.py`

- [ ] **Step 1: `_call_openai_api()` を追加（テスト時のモック差し替えポイント）**

```python
def _call_openai_api(client: Any, messages: list[dict]) -> Any:
    """OpenAI Chat Completions API を呼び出す。

    テスト時は unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api") で差し替える。
    """
    return client.chat.completions.create(
        model=_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
    )
```

- [ ] **Step 2: `_validate_and_extract()` を追加（バリデーション + スコア抽出）**

```python
def _validate_and_extract(resp: Any, requested_codes: set[str]) -> dict[str, float]:
    """API レスポンスをバリデーションし、有効なスコア辞書を返す。

    バリデーション失敗時は空辞書を返す（例外は発生させない）。
    スコアは ±_SCORE_CLIP にクリップする。

    バリデーション手順:
      1. JSON パース成功
      2. "results" キーが存在し list 型
      3. 各要素が dict で "code" と "score" キーを持つ
      4. "code" が requested_codes に含まれる（未知コードは無視）
      5. "score" が数値に変換可能かつ有限値
    """
    try:
        raw = json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, AttributeError, IndexError) as e:
        logger.warning("score_news: JSONパース失敗 → スキップ: %s", e)
        return {}

    results = raw.get("results")
    if not isinstance(results, list):
        logger.warning("score_news: レスポンスに 'results' リストがない → スキップ")
        return {}

    scores: dict[str, float] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        raw_score = item.get("score")
        if code not in requested_codes:
            continue  # 未知コードは無視
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            logger.warning("score_news: code=%s のスコアが数値でない: %r", code, raw_score)
            continue
        if not math.isfinite(score):
            continue
        scores[code] = max(-_SCORE_CLIP, min(_SCORE_CLIP, score))

    return scores
```

- [ ] **Step 3: `_score_chunk()` を追加（1チャンクの API コール + リトライ）**

```python
def _score_chunk(
    client: Any,
    chunk_codes: list[str],
    article_map: dict[str, list[str]],
) -> dict[str, float]:
    """1チャンク（最大 _BATCH_SIZE 銘柄）のスコアを取得して返す。

    同一銘柄の全記事テキストを結合してプロンプトに含め、
    LLM が全記事を統合評価した 1 スコアを返す（実質的な平均化）。

    HTTP 429 に対してエクスポネンシャルバックオフ（最大 _MAX_RETRIES 回）。
    それ以外の例外はリトライしない。失敗時は空辞書を返す。
    """
    import openai as _openai

    # 銘柄ごとの全記事テキストを結合してプロンプトを構築
    user_lines = [
        f"銘柄{code}: {' '.join(article_map[code])}"
        for code in chunk_codes
    ]
    user_content = (
        "以下の記事について銘柄ごとにセンチメントスコアを返してください。\n\n"
        + "\n".join(user_lines)
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = _call_openai_api(client, messages)
            break
        except _openai.RateLimitError as e:
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BASE_SECONDS * (2 ** attempt)
                logger.warning(
                    "score_news: レート制限 429 リトライ %d/%d (%.1f秒待機)",
                    attempt + 1, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
            else:
                logger.warning("score_news: レート制限リトライ上限超過 → スキップ: %s", e)
                return {}
        except Exception as e:
            logger.warning("score_news: API呼び出し失敗 → スキップ: %s", e)
            return {}

    return _validate_and_extract(resp, set(chunk_codes))
```

- [ ] **Step 4: コミット（中間コミット）**

```bash
git add src/kabusys/ai/news_nlp.py
git commit -m "feat: add OpenAI API call, validation, and chunk scoring logic"
```

---

## Task 6: score_news() のメインループと DB 書き込みを完成

**Files:**
- Modify: `src/kabusys/ai/news_nlp.py`

- [ ] **Step 1: `score_news()` の残り部分を実装**

`score_news()` 内の `raise NotImplementedError  # Task 5 で置き換え` を以下で置き換える：

```python
    # 4. OpenAI クライアント初期化
    import openai as _openai
    client = _openai.OpenAI(api_key=resolved_key)

    # 5. チャンク分割して API コール（全チャンクの結果を all_scores に集約）
    codes = list(article_map.keys())
    all_scores: dict[str, float] = {}
    api_call_count = 0
    for i in range(0, len(codes), _BATCH_SIZE):
        chunk = codes[i : i + _BATCH_SIZE]
        chunk_scores = _score_chunk(client, chunk, article_map)
        all_scores.update(chunk_scores)
        api_call_count += 1

    logger.info(
        "score_news: OpenAI API コール数=%d スコア取得銘柄数=%d date=%s",
        api_call_count, len(all_scores), target_date,
    )

    # 6. ai_scores テーブルへ日付単位の置換（DELETE → INSERT）
    # sentiment_score と ai_score は同値（現フェーズ）
    params = [
        (target_date, code, score, score)
        for code, score in all_scores.items()
    ]
    conn.execute("BEGIN")
    try:
        conn.execute("DELETE FROM ai_scores WHERE date = ?", [target_date])
        if params:  # DuckDB 0.10: executemany に空リスト不可
            conn.executemany(
                """
                INSERT INTO ai_scores (date, code, sentiment_score, ai_score)
                VALUES (?, ?, ?, ?)
                """,
                params,
            )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception as rb_exc:
            logger.warning("score_news: ROLLBACK failed: %s", rb_exc)
        raise

    count = len(all_scores)
    logger.info("score_news: ai_scores 書き込み完了 count=%d date=%s", count, target_date)
    return count
```

- [ ] **Step 2: 全テストを実行して全件パスを確認**

```bash
python -m pytest tests/test_news_nlp.py -v
```

Expected: 13件 PASSED

失敗したテストがあれば、エラーメッセージを確認して修正してから次へ進む。

- [ ] **Step 3: 既存テストへの影響がないことを確認**

```bash
python -m pytest tests/ -q
```

Expected: 全テスト PASSED（既存 53 件 + 新規 13 件 = 計 66 件以上）

- [ ] **Step 4: コミット**

```bash
git add src/kabusys/ai/__init__.py src/kabusys/ai/news_nlp.py tests/test_news_nlp.py
git commit -m "feat: implement score_news - news NLP scoring engine (#16)

- raw_news + news_symbols から前日 15:00〜当日 08:30 JST の記事を読み込み
- 同一銘柄の全テキストを結合して OpenAI gpt-4o-mini へバッチ送信（最大 20 銘柄/コール）
- HTTP 429 エクスポネンシャルバックオフ（最大 3 回）
- レスポンスバリデーション（results キー・型チェック・未知コード除外・数値型確認）
- スコアを ±1.0 にクリップして ai_scores へ DELETE+INSERT（冪等）"
```

---

## Task 7: PR 作成

- [ ] **Step 1: リモートにプッシュ**

```bash
git push origin HEAD
```

- [ ] **Step 2: GitHub API で PR を作成**

```python
import urllib.request, json

token = open("Keys").read().splitlines()[5].strip()
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
}

# 現在のブランチ名を確認してから使用
body = {
    "title": "feat: ニュースNLPスコアリングエンジン実装 (#16)",
    "body": (
        "## Summary\n"
        "- `src/kabusys/ai/news_nlp.py` を実装\n"
        "- OpenAI gpt-4o-mini でニュースセンチメント分析\n"
        "- `ai_scores` テーブルへ冪等書き込み（DELETE→INSERT）\n"
        "- API 障害時はスキップして継続（フェイルセーフ）\n\n"
        "## Test plan\n"
        "- [ ] 全テストがパスすること（`python -m pytest tests/ -q`）\n"
        "- [ ] `test_news_nlp.py` の 13 件が全件 PASSED\n\n"
        "Closes #16"
    ),
    "head": "feature/16-news-nlp-scoring",  # ブランチ名に合わせて変更
    "base": "main",
}
req = urllib.request.Request(
    "https://api.github.com/repos/ttj-ishida/KabuSys/pulls",
    data=json.dumps(body).encode(),
    headers=headers,
    method="POST",
)
with urllib.request.urlopen(req) as r:
    pr = json.loads(r.read())
print(f"PR #{pr['number']}: {pr['html_url']}")
```
