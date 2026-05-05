"""
TDnet 適時開示収集モジュール

適時開示情報閲覧サービス (TDnet) の開示一覧 HTML を日次で全件取得し、
raw_disclosures テーブルに保存する。

設計方針:
  - HTML パースは stdlib html.parser を使用（外部依存ゼロ）
  - SSRF 保護は news_collector.py と同じ _validate_url_scheme / _is_private_host パターン
  - ON CONFLICT DO NOTHING で冪等な挿入
  - ページネーション: I_list_001_YYYYMMDD.html, I_list_002_... を空行まで継続取得
  - TDnet の31日掲載制限を考慮し、毎日実行して差分を積み上げる
"""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time
from html.parser import HTMLParser
from typing import TypedDict

import duckdb

from kabusys.data.news_collector import (
    _SSRFBlockRedirectHandler,
    _is_private_host,
    _validate_url_scheme,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

TDNET_BASE_URL = "https://www.release.tdnet.info/inbs"
MAX_PAGES = 50
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
_INSERT_CHUNK_SIZE = 500

_DOC_ID_PATTERN = re.compile(r"(\d{14,20})(?:\.pdf|\.html)?$", re.IGNORECASE)

# ---------------------------------------------------------------------------
# 型定義
# ---------------------------------------------------------------------------


class RawDisclosure(TypedDict):
    """TDnet / EDINET から取得した生の開示情報を表す型。"""

    id: str
    disclosed_at: datetime
    code: str | None
    company_name: str | None
    title: str | None
    document_url: str | None
    document_type: str | None
    source: str


# ---------------------------------------------------------------------------
# HTML パーサー
# ---------------------------------------------------------------------------


class _TDnetTableParser(HTMLParser):
    """TDnet 開示一覧ページの HTML テーブルをパースする。

    列順: 時刻 | コード | 会社名 | 表題 | PDF/HTML リンク
    """

    def __init__(self) -> None:
        super().__init__()
        self._in_td = False
        self._cell_texts: list[str] = []
        self._cell_href: str | None = None
        self._current_row: list[tuple[str, str | None]] = []
        self.rows: list[list[tuple[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "td":
            self._in_td = True
            self._cell_texts = []
            self._cell_href = None
        elif tag == "a" and self._in_td:
            href = dict(attrs).get("href")
            if href:
                self._cell_href = href

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._in_td:
            text = "".join(self._cell_texts).strip()
            self._current_row.append((text, self._cell_href))
            self._in_td = False
        elif tag == "tr":
            if self._current_row:
                self.rows.append(self._current_row)
                self._current_row = []

    def handle_data(self, data: str) -> None:
        if self._in_td:
            self._cell_texts.append(data)


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------


def _extract_disclosure_id(href: str | None) -> str | None:
    """PDF/HTML の href から開示ID（数字部分）を抽出する。

    例: "140120241031413060.pdf" → "140120241031413060"
        "/inbs/140120241031413060.pdf" → "140120241031413060"
    """
    if not href:
        return None
    filename = href.rsplit("/", 1)[-1]
    m = _DOC_ID_PATTERN.search(filename)
    return m.group(1) if m else None


def _build_document_url(href: str | None) -> str | None:
    """href を完全な TDnet ドキュメント URL に変換する。"""
    if not href:
        return None
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return f"https://www.release.tdnet.info{href}"
    return f"{TDNET_BASE_URL}/{href}"


def _parse_tdnet_html(html: str, target_date: date) -> list[RawDisclosure]:
    """TDnet 開示一覧 HTML をパースして RawDisclosure リストを返す。

    列解釈: 列0=時刻, 列1=コード, 列2=会社名, 列3=表題, 列4=PDFリンク
    コードが4桁数字でない行（ヘッダー等）はスキップする。
    """
    parser = _TDnetTableParser()
    parser.feed(html)

    disclosures: list[RawDisclosure] = []
    for row in parser.rows:
        if len(row) < 4:
            continue

        time_str, _ = row[0]
        code_str, _ = row[1]
        company_str, _ = row[2]
        title_str, _ = row[3]
        href = row[4][1] if len(row) >= 5 else None

        if not re.fullmatch(r"\d{4}", code_str.strip()):
            continue

        doc_id = _extract_disclosure_id(href)
        if not doc_id:
            import hashlib

            raw = f"{target_date}|{code_str}|{title_str}"
            doc_id = "tdnet_" + hashlib.sha256(raw.encode()).hexdigest()[:16]

        try:
            h, m = map(int, time_str.strip().split(":"))
            disclosed_at = datetime.combine(target_date, time(h, m))
        except (ValueError, AttributeError):
            disclosed_at = datetime.combine(target_date, time(0, 0))

        doc_url = _build_document_url(href)
        disclosures.append(
            RawDisclosure(
                id=doc_id,
                disclosed_at=disclosed_at,
                code=code_str.strip() if code_str.strip() else None,
                company_name=company_str.strip() if company_str.strip() else None,
                title=title_str.strip() if title_str.strip() else None,
                document_url=doc_url,
                document_type=None,
                source="tdnet",
            )
        )

    return disclosures


# ---------------------------------------------------------------------------
# HTTP 取得
# ---------------------------------------------------------------------------


def _fetch_page(url: str, timeout: int = 30) -> str:
    """TDnet の HTML ページを取得して文字列で返す。

    SSRF 保護（スキーム検証・プライベートアドレス拒否）を適用する。
    テストでは monkeypatch でこの関数を差し替える。
    """
    _validate_url_scheme(url)
    parsed = urllib.parse.urlparse(url)
    if _is_private_host(parsed.hostname):
        raise ValueError(f"許可されていないホスト（プライベートアドレス）: url={url!r}")

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "KabuSys-TDnetCollector/1.0"},
    )
    opener = urllib.request.build_opener(_SSRFBlockRedirectHandler)
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            logger.warning("_fetch_page: レスポンスサイズ超過 url=%s", url)
            return ""
    for enc in ("utf-8", "shift_jis", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def fetch_tdnet_disclosures(
    target_date: date,
    timeout: int = 30,
) -> list[RawDisclosure]:
    """指定日の TDnet 開示一覧を全ページ取得して返す。

    I_list_001_YYYYMMDD.html から順にページを取得し、
    開示行が 0 件のページに達したら終了する。
    """
    date_str = target_date.strftime("%Y%m%d")
    all_disclosures: list[RawDisclosure] = []

    for page in range(1, MAX_PAGES + 1):
        page_str = f"{page:03d}"
        url = f"{TDNET_BASE_URL}/I_list_{page_str}_{date_str}.html"
        logger.info("fetch_tdnet_disclosures: url=%s", url)
        try:
            html = _fetch_page(url, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            logger.warning(
                "fetch_tdnet_disclosures: HTTPエラー page=%d code=%d", page, e.code
            )
            break
        except Exception:
            logger.exception("fetch_tdnet_disclosures: 取得失敗 page=%d", page)
            break

        page_disclosures = _parse_tdnet_html(html, target_date)
        if not page_disclosures:
            break

        all_disclosures.extend(page_disclosures)
        logger.info(
            "fetch_tdnet_disclosures: page=%d fetched=%d", page, len(page_disclosures)
        )

    logger.info(
        "fetch_tdnet_disclosures: date=%s total=%d", target_date, len(all_disclosures)
    )
    return all_disclosures


# ---------------------------------------------------------------------------
# DB 保存
# ---------------------------------------------------------------------------


def save_raw_disclosures(
    conn: duckdb.DuckDBPyConnection,
    disclosures: list[RawDisclosure],
) -> int:
    """開示リストを raw_disclosures テーブルに保存する。

    ON CONFLICT (id) DO NOTHING で冪等。INSERT RETURNING で実際の挿入件数を返す。
    """
    rows = [
        (
            d["id"],
            d["disclosed_at"],
            d.get("code"),
            d.get("company_name"),
            d.get("title"),
            d.get("document_url"),
            d.get("document_type"),
            d.get("source", "tdnet"),
        )
        for d in disclosures
        if d.get("id")
    ]
    if not rows:
        return 0

    saved = 0
    conn.begin()
    try:
        for i in range(0, len(rows), _INSERT_CHUNK_SIZE):
            chunk = rows[i : i + _INSERT_CHUNK_SIZE]
            placeholders = ", ".join("(?, ?, ?, ?, ?, ?, ?, ?)" for _ in chunk)
            flat = [v for row in chunk for v in row]
            result = conn.execute(
                "INSERT INTO raw_disclosures "  # noqa: S608
                "(id, disclosed_at, code, company_name, title, document_url, document_type, source) "
                f"VALUES {placeholders} "
                "ON CONFLICT (id) DO NOTHING RETURNING id",
                flat,
            )
            saved += len(result.fetchall())
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("save_raw_disclosures: トランザクション失敗、ロールバック")
        raise

    logger.info("save_raw_disclosures: input=%d saved=%d", len(disclosures), saved)
    return saved


# ---------------------------------------------------------------------------
# 統合収集ジョブ
# ---------------------------------------------------------------------------


def run_tdnet_collection(
    conn: duckdb.DuckDBPyConnection,
    target_date: date | None = None,
    timeout: int = 30,
) -> int:
    """TDnet 開示を収集して raw_disclosures に保存するジョブ。

    Args:
        conn:        DuckDB 接続。
        target_date: 収集対象日。省略時は今日。
        timeout:     HTTP タイムアウト秒数。

    Returns:
        新規挿入件数。
    """
    from datetime import date as date_cls

    if target_date is None:
        target_date = date_cls.today()

    disclosures = fetch_tdnet_disclosures(target_date, timeout=timeout)
    saved = save_raw_disclosures(conn, disclosures)
    logger.info("run_tdnet_collection: date=%s saved=%d", target_date, saved)
    return saved
