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
MAX_PAGES = 200
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

    対象テーブル: id="main-list-table"
    実際の列構成（CSS クラス名で識別）:
      kjTime   : 時刻
      kjCode   : 銘柄コード（4〜5桁）
      kjName   : 会社名
      kjTitle  : 表題（<a href="...">タイトル</a> 形式。href が PDF リンク）
      kjXbrl   : XBRL（無視）
      kjPlace  : 市場区分（無視）
      kjHistroy: 更新履歴（無視）
    """

    # パース対象とするセマンティッククラス名
    _TARGET_CLASSES = frozenset({"kjTime", "kjCode", "kjName", "kjTitle"})

    def __init__(self) -> None:
        super().__init__()
        self._in_main_table = False
        self._in_td = False
        self._current_sem_class: str | None = None  # kjTime / kjCode / kjName / kjTitle
        self._cell_texts: list[str] = []
        self._cell_href: str | None = None
        # 現在行のデータ: {semantic_class: (text, href)}
        self._current_data: dict[str, tuple[str, str | None]] = {}
        self.rows: list[dict[str, tuple[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "table":
            if attrs_dict.get("id") == "main-list-table":
                self._in_main_table = True
        elif tag == "tr" and self._in_main_table:
            self._current_data = {}
        elif tag == "td" and self._in_main_table:
            cls_str = attrs_dict.get("class", "")
            sem = next((c for c in cls_str.split() if c in self._TARGET_CLASSES), None)
            if sem:
                self._in_td = True
                self._current_sem_class = sem
                self._cell_texts = []
                self._cell_href = None
        elif tag == "a" and self._in_td:
            href = attrs_dict.get("href")
            if href:
                self._cell_href = href

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._in_main_table:
            self._in_main_table = False
        elif tag == "td" and self._in_td:
            sem = self._current_sem_class
            if sem:
                text = "".join(self._cell_texts).strip()
                self._current_data[sem] = (text, self._cell_href)
            self._in_td = False
            self._current_sem_class = None
        elif tag == "tr" and self._in_main_table:
            if self._current_data:
                self.rows.append(self._current_data)
                self._current_data = {}

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
        "140120241031413060.pdf?foo=bar" → "140120241031413060"
    """
    if not href:
        return None
    filename = href.split("?", 1)[0].rsplit("/", 1)[-1]
    m = _DOC_ID_PATTERN.search(filename)
    return m.group(1) if m else None


def _build_document_url(href: str | None) -> str | None:
    """href を完全な TDnet ドキュメント URL に変換する。"""
    if not href:
        return None
    clean = href.split("?", 1)[0]
    return urllib.parse.urljoin(f"{TDNET_BASE_URL}/", clean)


def _parse_tdnet_html(html: str, target_date: date) -> list[RawDisclosure]:
    """TDnet 開示一覧 HTML をパースして RawDisclosure リストを返す。

    id="main-list-table" の各行から CSS クラス名で値を取得する。
    タイトルと PDF href は同一セル（kjTitle の <a href>）にある。
    コードが数字のみでない行はスキップする（念のため保険）。
    """
    parser = _TDnetTableParser()
    parser.feed(html)

    disclosures: list[RawDisclosure] = []
    for row_data in parser.rows:
        # kjCode と kjTitle が揃っていない行はスキップ
        if "kjCode" not in row_data or "kjTitle" not in row_data:
            continue

        time_str, _ = row_data.get("kjTime", ("", None))
        code_str, _ = row_data.get("kjCode", ("", None))
        company_str, _ = row_data.get("kjName", ("", None))
        title_str, href = row_data.get("kjTitle", ("", None))

        # コードが数字以外の場合はスキップ（ヘッダー行等の保険）
        if not code_str.strip().isdigit():
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
    if not parsed.hostname or _is_private_host(parsed.hostname):
        raise ValueError(f"許可されていないホスト（プライベートアドレス）: url={url!r}")

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
        },
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
    else:
        logger.warning(
            "fetch_tdnet_disclosures: MAX_PAGES到達 date=%s total=%d",
            target_date,
            len(all_disclosures),
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
