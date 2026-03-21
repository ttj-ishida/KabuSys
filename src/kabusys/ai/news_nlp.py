"""
ニュースNLPスコアリングモジュール

raw_news テーブルのニュース記事を OpenAI API（gpt-4o-mini）で
センチメント分析し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む。

処理フロー:
  1. タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST = UTC で前日 06:00 ～ 23:30）を計算
  2. raw_news + news_symbols から対象記事を銘柄ごとに集約
     （1銘柄あたり最新 _MAX_ARTICLES_PER_STOCK 記事・_MAX_CHARS_PER_STOCK 文字でトリム）
  3. 最大 20 銘柄ずつ OpenAI API へバッチ送信（gpt-4o-mini + JSON Mode）
  4. 429・ネットワーク断・タイムアウト・5xx はエクスポネンシャルバックオフでリトライ
  5. レスポンスをバリデーション（results キー・型・既知コード・スコア数値型）
  6. スコアを ±1.0 にクリップ
  7. 全チャンク処理後、ai_scores テーブルへスコア取得済みコードのみ置換
     （DELETE WHERE date=? AND code=ANY(codes) → INSERT）
     ※ code を絞ることで部分失敗時に他コードの既存スコアを保護する

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
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_BATCH_SIZE: int = 20              # 1回の API コールで処理する最大銘柄数
_MODEL: str = "gpt-4o-mini"        # 使用する OpenAI モデル
_SCORE_CLIP: float = 1.0           # スコアのクリップ範囲（±1.0）
_MAX_RETRIES: int = 3              # リトライ上限回数（429・ネットワーク断・5xx 共通）
_RETRY_BASE_SECONDS: float = 1.0   # バックオフ初回待機秒数（指数的に増加）

# 1銘柄あたりのトークン肥大化対策
_MAX_ARTICLES_PER_STOCK: int = 10   # 1銘柄に含める最大記事数（新しい順）
_MAX_CHARS_PER_STOCK: int = 3000    # 1銘柄に含める最大文字数（超過分はトリム）

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
    "必ず提示した全ての銘柄コードについて1つずつスコアを返してください。"
    "提示していない銘柄コードは絶対に返さないでください。"
    '出力は厳密なJSONのみとしてください: {"results": [{"code": "XXXX", "score": 0.0}, ...]}'
)


def calc_news_window(target_date: date) -> tuple[datetime, datetime]:
    """target_date に対するニュース収集ウィンドウ（UTC naive datetime）を返す。

    Returns:
        (window_start, window_end) タプル。
        window_start: 前日 15:00 JST = target_date の前日 06:00 UTC（含む）
        window_end:   当日 08:30 JST = target_date の前日 23:30 UTC（含まない・排他的）

    例:
        target_date=2026-03-20 → (2026-03-19 06:00, 2026-03-19 23:30)
    """
    window_start = datetime(
        target_date.year, target_date.month, target_date.day,
        _NEWS_WINDOW_START_HOUR, _NEWS_WINDOW_START_MINUTE,
    ) - timedelta(days=1)
    window_end = datetime(
        target_date.year, target_date.month, target_date.day,
        _NEWS_WINDOW_END_HOUR, _NEWS_WINDOW_END_MINUTE,
    ) - timedelta(days=1)
    return window_start, window_end


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
                     空文字列も未設定として扱う。

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

    # 2. タイムウィンドウ計算
    window_start, window_end = calc_news_window(target_date)

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
    client = OpenAI(api_key=resolved_key)

    # 5. チャンク単位で API コール
    all_scores: dict[str, float] = {}
    chunk_count = 0
    codes = list(article_map.keys())
    for i in range(0, len(codes), _BATCH_SIZE):
        chunk_codes = codes[i : i + _BATCH_SIZE]
        chunk_scores = _score_chunk(client, chunk_codes, article_map)
        chunk_count += 1
        all_scores.update(chunk_scores)

    logger.info(
        "score_news: チャンク数=%d スコア取得銘柄数=%d date=%s",
        chunk_count, len(all_scores), target_date,
    )

    if not all_scores:
        logger.info("score_news: スコア取得失敗 date=%s", target_date)
        return 0

    # 6. ai_scores テーブルへスコア取得済みコードのみ置換（DELETE → INSERT）
    # code を絞り込むことで、部分失敗時に他コードの既存スコアを消さない。
    # sentiment_score と ai_score は同値（現フェーズ）
    params = [
        (target_date, code, score, score)
        for code, score in all_scores.items()
    ]
    codes_to_write = list(all_scores.keys())
    conn.execute("BEGIN")
    try:
        # code = ANY(?) は DuckDB バージョンによりリスト型バインドが不安定なため
        # executemany で個別 DELETE する（最も互換性が高い）
        if codes_to_write:  # DuckDB 0.10: executemany に空リスト不可
            conn.executemany(
                "DELETE FROM ai_scores WHERE date = ? AND code = ?",
                [(target_date, c) for c in codes_to_write],
            )
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
    ウィンドウは [window_start, window_end) の半開区間（上端は含まない）。
    1銘柄あたり最新 _MAX_ARTICLES_PER_STOCK 件を取得する。

    Returns:
        {code: [text1, text2, ...]} の辞書。text = "タイトル 本文"
    """
    rows = conn.execute(
        """
        SELECT code, title, content
        FROM (
            SELECT ns.code, n.title, n.content,
                   row_number() OVER (PARTITION BY ns.code ORDER BY n.datetime DESC) AS rn
            FROM raw_news n
            JOIN news_symbols ns ON ns.news_id = n.id
            WHERE n.datetime >= ? AND n.datetime < ?
        ) t
        WHERE rn <= ?
        ORDER BY code, rn
        """,
        [window_start, window_end, _MAX_ARTICLES_PER_STOCK],
    ).fetchall()

    article_map: dict[str, list[str]] = {}
    for code, title, content in rows:
        texts = article_map.setdefault(code, [])
        text = f"{title or ''} {content or ''}".strip()
        texts.append(text)
    return article_map


def _call_openai_api(client: Any, messages: list[dict]) -> Any:
    """OpenAI Chat Completions API を呼び出す。

    テスト時は unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api") で差し替える。
    """
    return client.chat.completions.create(
        model=_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
        timeout=30,
    )


def _validate_and_extract(resp: Any, requested_codes: set[str]) -> dict[str, float]:
    """API レスポンスをバリデーションし、有効なスコア辞書を返す。

    バリデーション失敗時は空辞書を返す（例外は発生させない）。
    スコアは ±_SCORE_CLIP にクリップする。

    バリデーション手順:
      1. JSON パース成功（JSON mode でも前後に余計なテキストが混ざる場合は {} を抽出）
      2. "results" キーが存在し list 型
      3. 各要素が dict で "code" と "score" キーを持つ
      4. "code" が requested_codes に含まれる（未知コードは無視）
      5. "score" が数値に変換可能かつ有限値
    """
    try:
        content = resp.choices[0].message.content
        try:
            raw = json.loads(content)
        except json.JSONDecodeError:
            # JSON mode でも稀に前後テキストが混ざる場合の復元（最外の {} を抽出）
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end > start:
                raw = json.loads(content[start:end + 1])
            else:
                raise
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
        code_raw = item.get("code")
        # LLM が整数で返すケースに備えて str に正規化してから照合する
        code = str(code_raw).strip() if code_raw is not None else None
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

    同一銘柄の全記事テキストを結合（_MAX_CHARS_PER_STOCK 文字でトリム）して
    プロンプトに含め、LLM が全記事を統合評価した 1 スコアを返す。

    リトライ対象: 429（レート制限）・ネットワーク断・タイムアウト・5xx サーバーエラー。
    それ以外の例外はリトライしない。失敗時は空辞書を返す。
    """
    # 銘柄ごとの全記事テキストを結合・トリムしてプロンプトを構築
    user_lines = []
    for code in chunk_codes:
        combined = ' '.join(article_map[code])
        if len(combined) > _MAX_CHARS_PER_STOCK:
            combined = combined[:_MAX_CHARS_PER_STOCK] + '…'
        user_lines.append(f"銘柄{code}: {combined}")

    user_content = (
        "以下の記事について銘柄ごとにセンチメントスコアを返してください。\n\n"
        + "\n".join(user_lines)
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    # _MAX_RETRIES 回のリトライ（初回試行含め最大 _MAX_RETRIES + 1 回）
    # attempt: 0 = 初回, 1..._MAX_RETRIES = 各リトライ
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = _call_openai_api(client, messages)
            break
        except (RateLimitError, APIConnectionError, APITimeoutError) as e:
            if attempt >= _MAX_RETRIES:
                logger.warning("score_news: リトライ上限超過 → スキップ: %s", e)
                return {}
            wait = _RETRY_BASE_SECONDS * (2 ** attempt)
            logger.warning(
                "score_news: 一時エラー(%s) リトライ %d/%d (%.1f秒待機)",
                type(e).__name__, attempt + 1, _MAX_RETRIES, wait,
            )
            time.sleep(wait)
        except APIError as e:
            # status_code が無い APIError は安全側（5xx扱い）でリトライ対象にする
            if getattr(e, 'status_code', 500) < 500 or attempt >= _MAX_RETRIES:
                logger.warning("score_news: API エラー → スキップ: %s", e)
                return {}
            wait = _RETRY_BASE_SECONDS * (2 ** attempt)
            logger.warning(
                "score_news: サーバーエラー(5xx) リトライ %d/%d (%.1f秒待機)",
                attempt + 1, _MAX_RETRIES, wait,
            )
            time.sleep(wait)
        except Exception as e:
            logger.warning("score_news: API呼び出し失敗 → スキップ: %s", e)
            return {}

    return _validate_and_extract(resp, set(chunk_codes))
