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
    """before_date の直前 days 日間を同一終値で挿入するヘルパー。

    挿入される日付は before_date - (days+1) から before_date - 2 までの days 日間。
    before_date - 1 は呼び出し側が別途 _insert_price で最終値をセットできるよう空けておく。
    """
    for i in range(days + 1, 1, -1):
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


# ---------------------------------------------------------------------------
# Task 4: _score_macro()
# ---------------------------------------------------------------------------

def test_score_macro_returns_float():
    """正常系：LLM が {"macro_sentiment": -0.7} を返す → -0.7 が返される。"""
    from kabusys.ai.regime_detector import _score_macro

    mock_client = MagicMock()
    mock_resp = _make_macro_response(-0.7)
    with patch("kabusys.ai.regime_detector._call_openai_api", return_value=mock_resp):
        score = _score_macro(mock_client, ["日銀が利上げ"])

    assert abs(score - (-0.7)) < 1e-9


def test_score_macro_no_titles():
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
        score = _score_macro(mock_client, ["Fed が利上げ"], _sleep_fn=lambda _: None)

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
    ), patch("kabusys.ai.regime_detector._RETRY_BASE_SECONDS", 0):
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
        with pytest.raises(ValueError):
            score_regime(conn, TARGET_DATE, api_key=None)
    finally:
        if env_backup is not None:
            os.environ["OPENAI_API_KEY"] = env_backup


class _FailOnInsertConn:
    """INSERT INTO market_regime のみ失敗させる DuckDB 接続ラッパー。

    DuckDB の C 拡張接続オブジェクトは execute が読み取り専用属性のため
    patch.object が使えない。代わりにこのラッパーで委譲し、INSERT 時のみ例外を投げる。
    """

    def __init__(self, real_conn):
        self._real = real_conn

    def execute(self, sql, params=None):
        if "INSERT INTO market_regime" in sql:
            raise RuntimeError("DB 書き込みエラー（テスト用）")
        if params is not None:
            return self._real.execute(sql, params)
        return self._real.execute(sql)

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_db_write_failure(conn):
    """DB 書き込み失敗 → ROLLBACK して例外が上位に伝播、market_regime に行なし。"""
    from kabusys.ai.regime_detector import score_regime

    _insert_prices_uniform(conn, "1321", 200, 100.0, TARGET_DATE)

    failing_conn = _FailOnInsertConn(conn)

    with patch("kabusys.ai.regime_detector._call_openai_api", return_value=_make_macro_response(0.0)):
        with pytest.raises(Exception):
            score_regime(failing_conn, TARGET_DATE, api_key="test-key")

    count = conn.execute(
        "SELECT COUNT(*) FROM market_regime WHERE date = ?", [TARGET_DATE]
    ).fetchone()[0]
    assert count == 0
