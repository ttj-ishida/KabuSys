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
  - 記事IDはURL正規化後のSHA-256ハッシュ（先頭16文字）で生成し冪等性を保証する
    （utm_* などのトラッキングパラメータを除去してから正規化する）
  - defusedxml を使って XML Bomb 等の攻撃を防ぐ
  - HTTP/HTTPS スキーム以外のURLは拒否し SSRF を防ぐ
  - 受信サイズを最大 MAX_RESPONSE_BYTES に制限しメモリDoSを防ぐ
  - DB 保存は 1 トランザクションにまとめてオーバーヘッドを削減する
  - INSERT RETURNING で実際に挿入されたレコード数を正確に返す
"""

from __future__ import annotations

import hashlib
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, TypedDict

import duckdb
from defusedxml import ElementTree as ET

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

# デフォルト RSS ソース: {source_name: rss_url}
DEFAULT_RSS_SOURCES: dict[str, str] = {
    "yahoo_finance": "https://news.yahoo.co.jp/rss/categories/business.xml",
}

# 受信最大バイト数（10 MB）
MAX_RESPONSE_BYTES = 10 * 1024 * 1024

# URL から除去するトラッキングパラメータのプレフィックス
_TRACKING_PARAM_PREFIXES = ("utm_", "fbclid", "gclid", "ref_", "_ga")

# ---------------------------------------------------------------------------
# 型定義
# ---------------------------------------------------------------------------


class NewsArticle(TypedDict):
    """RSS フィードから取得した記事を表す型。"""

    id: str
    datetime: datetime
    source: str
    title: str
    content: str
    url: str


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

_URL_PATTERN = re.compile(r"https?://\S+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def _normalize_url(url: str) -> str:
    """URL を正規化してトラッキングパラメータを除去する。

    - スキームとホストを小文字化
    - utm_* / fbclid などの既知トラッキングパラメータを削除
    - フラグメント（#...）を削除
    - クエリパラメータをキーでソート

    Args:
        url: 正規化対象の URL 文字列。

    Returns:
        正規化後の URL 文字列。
    """
    parsed = urllib.parse.urlparse(url)
    query_params = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parsed.query)
        if not any(k.startswith(p) for p in _TRACKING_PARAM_PREFIXES)
    ]
    query_params.sort()
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        query=urllib.parse.urlencode(query_params),
        fragment="",
    )
    return urllib.parse.urlunparse(normalized)


def _make_article_id(url: str) -> str:
    """正規化 URL から記事ID（SHA-256 先頭16文字）を生成する。

    Args:
        url: 記事URL（正規化前）。

    Returns:
        16文字の16進数文字列。
    """
    return hashlib.sha256(_normalize_url(url).encode()).hexdigest()[:16]


def _validate_url_scheme(url: str) -> None:
    """URL のスキームが http または https であることを検証する。

    SSRF / ローカルファイル読み出しを防ぐため、http/https 以外を拒否する。

    Args:
        url: 検証対象の URL。

    Raises:
        ValueError: スキームが http/https でない場合。
    """
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"許可されていないURLスキーム: {scheme!r} (url={url!r})")


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
    """RSS の pubDate 文字列を UTC naive datetime に変換する。

    パース失敗時は warning ログを出力し、現在時刻（UTC naive）を返す。
    raw_news.datetime は NOT NULL のため None を返せない設計とする。

    Args:
        date_str: RFC 2822 形式の日時文字列（例: "Mon, 01 Jan 2024 00:00:00 +0900"）。

    Returns:
        UTC naive datetime オブジェクト。
    """
    if date_str:
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            logger.warning("_parse_rss_datetime: パース失敗 pubDate=%r、現在時刻で代替", date_str)
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# RSS 取得
# ---------------------------------------------------------------------------


def fetch_rss(
    url: str,
    source: str,
    timeout: int = 30,
) -> list[NewsArticle]:
    """RSS フィードを取得し、記事リストを返す。

    ネットワークエラー（urllib.error.URLError）は呼び出し元へ伝播させる。
    XMLパースエラー（ET.ParseError）はキャッチして warning ログを出力し空リストを返す。

    Args:
        url:     RSS フィードの URL（http/https のみ許可）。
        source:  ニュース媒体名（raw_news.source カラムに格納）。
        timeout: HTTP タイムアウト秒数（デフォルト 30 秒）。

    Returns:
        記事辞書のリスト。各辞書は NewsArticle 型に準拠する。

    Raises:
        ValueError: URL のスキームが http/https でない場合。
        urllib.error.URLError: HTTP リクエスト失敗時。
    """
    _validate_url_scheme(url)
    logger.info("fetch_rss: source=%s url=%s", source, url)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "KabuSys-NewsCollector/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(MAX_RESPONSE_BYTES)

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        logger.warning("fetch_rss: XMLパース失敗 source=%s url=%s", source, url)
        return []

    channel = root.find("channel")
    if channel is None:
        logger.warning("fetch_rss: <channel> not found in %s", url)
        return []

    articles: list[NewsArticle] = []
    for item in channel.findall("item"):
        link = (item.findtext("link") or "").strip()
        if not link:
            continue

        title = preprocess_text(item.findtext("title"))
        content = preprocess_text(item.findtext("description"))
        pub_date = _parse_rss_datetime(item.findtext("pubDate"))

        articles.append(
            NewsArticle(
                id=_make_article_id(link),
                datetime=pub_date,
                source=source,
                title=title,
                content=content,
                url=link,
            )
        )

    logger.info("fetch_rss: source=%s fetched=%d articles", source, len(articles))
    return articles


# ---------------------------------------------------------------------------
# DB 保存
# ---------------------------------------------------------------------------


def save_raw_news(
    conn: duckdb.DuckDBPyConnection,
    articles: list[NewsArticle],
) -> int:
    """記事リストを raw_news テーブルに保存する。

    INSERT ... RETURNING を使い、実際に挿入されたレコード数を正確に返す。
    全件を 1 トランザクションにまとめてオーバーヘッドを削減する。

    Args:
        conn:     DuckDB 接続。
        articles: fetch_rss が返す NewsArticle リスト。

    Returns:
        新規挿入したレコード数（ON CONFLICT でスキップされた分は含まない）。
    """
    if not articles:
        return 0

    saved = 0
    conn.begin()
    try:
        for art in articles:
            if not art.get("id"):
                continue
            result = conn.execute(
                """
                INSERT INTO raw_news (id, datetime, source, title, content, url)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO NOTHING
                RETURNING 1
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
            saved += len(result.fetchall())
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("save_raw_news: トランザクション失敗、ロールバック")
        raise

    logger.info("save_raw_news: articles=%d saved=%d", len(articles), saved)
    return saved


def save_news_symbols(
    conn: duckdb.DuckDBPyConnection,
    news_id: str,
    codes: list[str],
) -> int:
    """news_symbols テーブルに記事と銘柄コードの紐付けを保存する。

    INSERT ... RETURNING を使い、実際に挿入されたレコード数を正確に返す。
    全件を 1 トランザクションにまとめる。

    Args:
        conn:    DuckDB 接続。
        news_id: 記事ID。
        codes:   紐付ける銘柄コードのリスト。

    Returns:
        新規挿入したレコード数（ON CONFLICT でスキップされた分は含まない）。
    """
    if not codes:
        return 0

    saved = 0
    conn.begin()
    try:
        for code in codes:
            result = conn.execute(
                """
                INSERT INTO news_symbols (news_id, code)
                VALUES (?, ?)
                ON CONFLICT (news_id, code) DO NOTHING
                RETURNING 1
                """,
                [news_id, code],
            )
            saved += len(result.fetchall())
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("save_news_symbols: トランザクション失敗 news_id=%s", news_id)
        raise

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

    各ソースは独立してエラーハンドリングし、1 ソース失敗しても他ソースは継続する。

    Args:
        conn:        DuckDB 接続。
        sources:     {source_name: rss_url} の辞書。省略時は DEFAULT_RSS_SOURCES を使用。
        known_codes: 銘柄コード抽出に使用する有効コードのセット。None の場合は抽出をスキップ。
        timeout:     HTTP タイムアウト秒数。

    Returns:
        {source_name: 新規保存レコード数} の辞書。
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
