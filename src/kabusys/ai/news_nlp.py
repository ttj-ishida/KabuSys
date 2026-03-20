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

    # 4. OpenAI クライアント生成
    from openai import OpenAI
    client = OpenAI(api_key=resolved_key)

    # 5. チャンク単位で API コール
    all_scores: dict[str, float] = {}
    api_call_count = 0
    codes = list(article_map.keys())
    for i in range(0, len(codes), _BATCH_SIZE):
        chunk_codes = codes[i : i + _BATCH_SIZE]
        chunk_scores = _score_chunk(client, chunk_codes, article_map)
        api_call_count += 1
        all_scores.update(chunk_scores)

    logger.info(
        "score_news: OpenAI API コール数=%d スコア取得銘柄数=%d date=%s",
        api_call_count, len(all_scores), target_date,
    )

    if not all_scores:
        logger.info("score_news: スコア取得失敗 date=%s", target_date)
        return 0

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

    logger.info(
        "score_news: 完了 書込み銘柄数=%d date=%s",
        len(all_scores),
        target_date,
    )
    return len(all_scores)


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


def _call_openai_api(client: Any, messages: list[dict]) -> Any:
    """OpenAI Chat Completions API を呼び出す。

    テスト時は unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api") で差し替える。
    """
    return client.chat.completions.create(
        model=_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
    )


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
