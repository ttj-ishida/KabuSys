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
    c = init_schema(":memory:")
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


# ---------------------------------------------------------------------------
# calc_news_window() のテスト
# ---------------------------------------------------------------------------


def test_calc_news_window_values():
    """target_date=2026-03-20 → (2026-03-19 06:00, 2026-03-19 23:30) を返す。"""
    from datetime import datetime
    from kabusys.ai.news_nlp import calc_news_window

    start, end = calc_news_window(TARGET_DATE)
    assert start == datetime(2026, 3, 19, 6, 0, 0)
    assert end == datetime(2026, 3, 19, 23, 30, 0)


def test_calc_news_window_boundary_inclusive_start(conn):
    """ウィンドウ開始時刻ちょうどの記事は対象に含まれる。"""
    from datetime import datetime
    from kabusys.ai.news_nlp import score_news, calc_news_window

    window_start, _ = calc_news_window(TARGET_DATE)
    # window_start ちょうど（含む）
    _insert_article(conn, "art_start", window_start, "開始時刻記事")
    _link_code(conn, "art_start", "1111")

    mock_resp = _make_api_response([{"code": "1111", "score": 0.5}])
    with patch("kabusys.ai.news_nlp._call_openai_api", return_value=mock_resp):
        count = score_news(conn, TARGET_DATE, api_key="test-key")

    assert count == 1


def test_calc_news_window_boundary_exclusive_end(conn):
    """ウィンドウ終了時刻ちょうどの記事は対象外（排他的上端）。"""
    from kabusys.ai.news_nlp import score_news, calc_news_window

    _, window_end = calc_news_window(TARGET_DATE)
    # window_end ちょうど（含まない）
    _insert_article(conn, "art_end", window_end, "終了時刻記事")
    _link_code(conn, "art_end", "2222")

    with patch("kabusys.ai.news_nlp._call_openai_api") as mock_api:
        count = score_news(conn, TARGET_DATE, api_key="test-key")

    # 対象記事がないため API 未コール・0件
    assert count == 0
    mock_api.assert_not_called()
