"""
ニュース収集モジュール

DataPlatform.md Section 3.1 に基づき、RSS フィードからニュース記事を収集し
raw_news テーブルに保存する。

処理フロー:
  1. RSS フィードを取得し、記事リストを構築する
  2. テキスト前処理（URL除去・空白正規化）
  3. raw_news テーブルへ冪等保存（ON CONFLICT DO NOTHING）
  4. 銘柄コードとの紐付け（news_symbols）

設計方針:
  - 記事IDはURLのSHA-256ハッシュ（先頭16文字）で生成し冪等性を保証する
  - RSS以外にも拡張しやすいよう fetch_rss を低レベル関数として切り出す
  - ネットワーク障害は呼び出し元でハンドリングさせ、関数内では変換エラーのみ吸収する
"""

from __future__ import annotations

import hashlib
import logging
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# デフォルト RSS ソース定義
# ---------------------------------------------------------------------------

# source_name -> RSS URL のデフォルトマッピング
DEFAULT_RSS_SOURCES: dict[str, str] = {
    "yahoo_finance": "https://news.yahoo.co.jp/rss/categories/business.xml",
}

# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

_URL_PATTERN = re.compile(r"https?://\S+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def _make_article_id(url: str) -> str:
    """URL から記事ID（SHA-256 先頭16文字）を生成する。

    Args:
        url: 記事URL。

    Returns:
        16文字の16進数文字列。
    """
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def preprocess_text(text: str | None) -> str:
    """テキストの前処理を行う。

    - URL を除去する
    - 連続する空白・改行を単一スペースに正規化する
    - 先頭・末尾の空白を削除する

    Args:
        text: 前処理対象の文字列。None の場合は空文字列を返す。

    Returns:
        前処理済みの文字列。
    """
    if not text:
        return ""
    text = _URL_PATTERN.sub("", text)
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def _parse_rss_datetime(date_str: str | None) -> datetime:
    """RSS の pubDate 文字列を UTC datetime に変換する。

    パース失敗時は現在時刻（UTC）を返す。

    Args:
        date_str: RFC 2822 形式の日時文字列（例: "Mon, 01 Jan 2024 00:00:00 +0900"）。

    Returns:
        UTC datetime オブジェクト。
    """
    if date_str:
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            pass
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# RSS 取得
# ---------------------------------------------------------------------------


def fetch_rss(
    url: str,
    source: str,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """RSS フィードを取得し、記事リストを返す。

    Args:
        url:     RSS フィードの URL。
        source:  ニュース媒体名（raw_news.source カラムに格納）。
        timeout: HTTP タイムアウト秒数（デフォルト 30 秒）。

    Returns:
        記事辞書のリスト。各辞書は以下のキーを持つ:
            - id (str): URLハッシュ由来の記事ID
            - datetime (datetime): 記事公開日時 (UTC naive)
            - source (str): ニュース媒体名
            - title (str): タイトル（前処理済み）
            - content (str): 本文または概要（前処理済み）
            - url (str): 元の記事URL

    Raises:
        urllib.error.URLError: HTTP リクエスト失敗時。
    """
    logger.info("fetch_rss: source=%s url=%s", source, url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "KabuSys-NewsCollector/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()

    root = ET.fromstring(raw)
    channel = root.find("channel")
    if channel is None:
        logger.warning("fetch_rss: <channel> not found in %s", url)
        return []

    articles: list[dict[str, Any]] = []
    for item in channel.findall("item"):
        link = (item.findtext("link") or "").strip()
        if not link:
            continue

        title = preprocess_text(item.findtext("title"))
        content = preprocess_text(item.findtext("description"))
        pub_date = _parse_rss_datetime(item.findtext("pubDate"))

        articles.append(
            {
                "id": _make_article_id(link),
                "datetime": pub_date,
                "source": source,
                "title": title,
                "content": content,
                "url": link,
            }
        )

    logger.info("fetch_rss: source=%s fetched=%d articles", source, len(articles))
    return articles


# ---------------------------------------------------------------------------
# DB 保存
# ---------------------------------------------------------------------------


def save_raw_news(
    conn: duckdb.DuckDBPyConnection,
    articles: list[dict[str, Any]],
) -> int:
    """記事リストを raw_news テーブルに保存する。

    既存 ID のレコードはスキップ（ON CONFLICT DO NOTHING）。

    Args:
        conn:     DuckDB 接続。
        articles: fetch_rss が返す記事辞書のリスト。

    Returns:
        新規保存したレコード数。
    """
    if not articles:
        return 0

    saved = 0
    for art in articles:
        if not art.get("id"):
            continue
        try:
            conn.execute(
                """
                INSERT INTO raw_news (id, datetime, source, title, content, url)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO NOTHING
                """,
                [
                    art["id"],
                    art["datetime"],
                    art.get("source", ""),
                    art.get("title", ""),
                    art.get("content", ""),
                    art.get("url", ""),
                ],
            )
            saved += 1
        except Exception:
            logger.exception("save_raw_news: レコード保存失敗 id=%s", art.get("id"))

    logger.info("save_raw_news: articles=%d saved=%d", len(articles), saved)
    return saved


def save_news_symbols(
    conn: duckdb.DuckDBPyConnection,
    news_id: str,
    codes: list[str],
) -> int:
    """news_symbols テーブルに記事と銘柄コードの紐付けを保存する。

    既存の (news_id, code) ペアはスキップ（ON CONFLICT DO NOTHING）。

    Args:
        conn:    DuckDB 接続。
        news_id: 記事ID。
        codes:   紐付ける銘柄コードのリスト。

    Returns:
        新規保存したレコード数。
    """
    if not codes:
        return 0

    saved = 0
    for code in codes:
        try:
            conn.execute(
                """
                INSERT INTO news_symbols (news_id, code)
                VALUES (?, ?)
                ON CONFLICT (news_id, code) DO NOTHING
                """,
                [news_id, code],
            )
            saved += 1
        except Exception:
            logger.exception(
                "save_news_symbols: 保存失敗 news_id=%s code=%s", news_id, code
            )

    return saved


# ---------------------------------------------------------------------------
# 銘柄コード抽出
# ---------------------------------------------------------------------------

# 日本株の銘柄コードは通常4桁の数字（例: "7203"、"6758"）
_CODE_PATTERN = re.compile(r"\b(\d{4})\b")


def extract_stock_codes(text: str, known_codes: set[str]) -> list[str]:
    """テキスト中に出現する銘柄コードを抽出する。

    4桁数字を候補として取り出し、known_codes に含まれるものだけを返す。
    重複は除去してリストで返す。

    Args:
        text:        検索対象テキスト（タイトル + 本文等）。
        known_codes: 有効な銘柄コードのセット。

    Returns:
        テキスト中に出現した銘柄コードのリスト（重複なし）。
    """
    candidates = _CODE_PATTERN.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for code in candidates:
        if code in known_codes and code not in seen:
            seen.add(code)
            result.append(code)
    return result


# ---------------------------------------------------------------------------
# 統合収集ジョブ
# ---------------------------------------------------------------------------


def run_news_collection(
    conn: duckdb.DuckDBPyConnection,
    sources: dict[str, str] | None = None,
    known_codes: set[str] | None = None,
    timeout: int = 30,
) -> dict[str, int]:
    """全 RSS ソースからニュースを収集し DB に保存する。

    Args:
        conn:        DuckDB 接続。
        sources:     {source_name: rss_url} の辞書。省略時は DEFAULT_RSS_SOURCES を使用。
        known_codes: 銘柄コード抽出に使用する有効コードのセット。None の場合は抽出をスキップ。
        timeout:     HTTP タイムアウト秒数。

    Returns:
        {source_name: 保存レコード数} の辞書。
    """
    if sources is None:
        sources = DEFAULT_RSS_SOURCES

    results: dict[str, int] = {}
    for source_name, rss_url in sources.items():
        try:
            articles = fetch_rss(rss_url, source=source_name, timeout=timeout)
            saved = save_raw_news(conn, articles)
            results[source_name] = saved

            if known_codes and articles:
                for art in articles:
                    combined = f"{art.get('title', '')} {art.get('content', '')}"
                    codes = extract_stock_codes(combined, known_codes)
                    if codes:
                        save_news_symbols(conn, art["id"], codes)

        except Exception:
            logger.exception("run_news_collection: ソース取得失敗 source=%s", source_name)
            results[source_name] = 0

    logger.info(
        "run_news_collection 完了: %s",
        ", ".join(f"{k}={v}" for k, v in results.items()),
    )
    return results
