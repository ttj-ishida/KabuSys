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
from datetime import date, datetime
from typing import Any

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

_ETF_CODE: str = "1321"
_MA_WINDOW: int = 200
_MA_SCALE: float = 10.0
_MA_WEIGHT: float = 0.7
_MACRO_WEIGHT: float = 0.3
_BULL_THRESHOLD: float = 0.2
_BEAR_THRESHOLD: float = 0.2
_MAX_MACRO_ARTICLES: int = 20
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


def _fetch_macro_news(
    conn: duckdb.DuckDBPyConnection,
    window_start: datetime,
    window_end: datetime,
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


def _call_openai_api(client: Any, messages: list[dict]) -> Any:
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


def _score_macro(client: Any, titles: list[str]) -> float:
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


# ---------------------------------------------------------------------------
# パブリック API
# ---------------------------------------------------------------------------

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
