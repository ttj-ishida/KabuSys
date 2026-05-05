"""
EDINET 法定開示収集モジュール（アドオン機能）

EDINET API v2 から当日提出の開示書類一覧を取得し、
raw_disclosures テーブルに保存する。

設計方針:
  - ENABLE_EDINET=false の場合はジョブ全体をスキップ（アドオン機能）
  - SSRF 保護は tdnet_collector.py と同じパターン
  - ON CONFLICT DO NOTHING で冪等な挿入
  - TDnet と同一の raw_disclosures テーブルに source='edinet' で保存
  - save_raw_disclosures は tdnet_collector から再利用

対象書類種別（初期）:
  120: 有価証券報告書
  130: 四半期報告書
  140: 臨時報告書
  150: 訂正臨時報告書
  170: 大量保有報告書
  171: 大量保有報告書（特例対象）
  172: 変更報告書

EDINET API v2 エンドポイント:
  GET https://api.edinet-fsa.go.jp/api/v2/documents.json
  パラメータ: date=YYYY-MM-DD, type=2, Subscription-Key=<api_key>
  認証: Subscription-Key クエリパラメータ
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import TypedDict

import duckdb

from kabusys.data.tdnet_collector import RawDisclosure, save_raw_disclosures
from kabusys.utils.http import (
    SSRFBlockRedirectHandler as _SSRFBlockRedirectHandler,
    is_private_host as _is_private_host,
    validate_url_scheme as _validate_url_scheme,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

EDINET_API_BASE = "https://api.edinet-fsa.go.jp/api/v2"
EDINET_DOCUMENTS_URL = f"{EDINET_API_BASE}/documents.json"
EDINET_DOCUMENT_URL_TEMPLATE = f"{EDINET_API_BASE}/documents/{{doc_id}}"

MAX_RESPONSE_BYTES = 10 * 1024 * 1024

# 収集対象の書類種別コード
_TARGET_DOC_TYPES: frozenset[str] = frozenset(
    {
        "120",  # 有価証券報告書
        "130",  # 四半期報告書
        "140",  # 臨時報告書
        "150",  # 訂正臨時報告書
        "170",  # 大量保有報告書
        "171",  # 大量保有報告書（特例対象）
        "172",  # 変更報告書
    }
)

# submitDateTime のパース順序（秒付き → 分まで → ISO形式）
_SUBMIT_DT_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# 型
# ---------------------------------------------------------------------------


class _EdinetDocument(TypedDict):
    """EDINET API レスポンスの results 配列の1要素。"""

    docID: str
    edinetCode: str
    docType: str
    filerName: str
    submitDateTime: str
    docDescription: str
    pdfFlag: str
    xbrlFlag: str
    withdrawalStatus: str


# ---------------------------------------------------------------------------
# HTTP 取得
# ---------------------------------------------------------------------------


def _fetch_edinet_json(url: str, timeout: int = 30) -> bytes:
    """EDINET API から JSON を取得して bytes を返す。

    Subscription-Key は呼び出し元でクエリパラメータとして URL に含まれている。
    SSRF 保護を適用する。テストでは monkeypatch でこの関数を差し替える。
    """
    _validate_url_scheme(url)
    parsed = urllib.parse.urlparse(url)
    if not parsed.hostname or _is_private_host(parsed.hostname):
        raise ValueError(f"許可されていないホスト: url={url!r}")

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    opener = urllib.request.build_opener(_SSRFBlockRedirectHandler)
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        logger.warning("_fetch_edinet_json: レスポンスサイズ超過 url=%s", url)
        return b""
    return raw


def _parse_submit_datetime(submit_dt_str: str, target_date: date) -> datetime:
    """submitDateTime 文字列を datetime に変換する。

    複数フォーマットを順に試み、すべて失敗した場合は target_date の 0:00 を返す。
    """
    for fmt in _SUBMIT_DT_FORMATS:
        try:
            return datetime.strptime(submit_dt_str, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(submit_dt_str)
    except ValueError:
        pass
    return datetime.combine(target_date, datetime.min.time())


# ---------------------------------------------------------------------------
# パース
# ---------------------------------------------------------------------------


def _parse_edinet_response(raw: bytes, target_date: date) -> list[RawDisclosure]:
    """EDINET API レスポンスをパースして RawDisclosure リストを返す。

    - withdrawalStatus != "0" の取り下げ済み書類は除外する
    - _TARGET_DOC_TYPES に含まれない書類種別は除外する
    - code (銘柄コード) は EDINET API から直接取得できないため None
    """
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.exception("_parse_edinet_response: JSON デコード失敗")
        return []

    status = str(data.get("metadata", {}).get("status", ""))
    if status != "200":
        logger.warning("_parse_edinet_response: API ステータス異常 status=%s", status)
        return []

    results: list[_EdinetDocument] = data.get("results", [])
    disclosures: list[RawDisclosure] = []

    for doc in results:
        # 取り下げ済みは除外
        if str(doc.get("withdrawalStatus", "0")) != "0":
            continue

        doc_type = str(doc.get("docType", ""))
        if doc_type not in _TARGET_DOC_TYPES:
            continue

        doc_id: str = doc.get("docID", "")
        if not doc_id:
            continue

        submit_dt_str: str = doc.get("submitDateTime", "")
        disclosed_at = _parse_submit_datetime(submit_dt_str, target_date)

        doc_description: str = doc.get("docDescription", "")
        filer_name: str = doc.get("filerName", "")
        pdf_flag: str = doc.get("pdfFlag", "0")

        file_type = "2" if pdf_flag == "1" else "1"
        document_url = (
            f"{EDINET_DOCUMENT_URL_TEMPLATE.format(doc_id=doc_id)}?type={file_type}"
        )

        disclosures.append(
            RawDisclosure(
                id=doc_id,
                disclosed_at=disclosed_at,
                code=None,  # EDINET API は銘柄コードを直接返さない
                company_name=filer_name or None,
                title=doc_description or None,
                document_url=document_url,
                document_type=doc_type,
                source="edinet",
            )
        )

    return disclosures


# ---------------------------------------------------------------------------
# 収集関数
# ---------------------------------------------------------------------------


def fetch_edinet_disclosures(
    target_date: date,
    api_key: str = "",
    timeout: int = 30,
) -> list[RawDisclosure]:
    """指定日の EDINET 開示一覧を取得して返す。

    Args:
        target_date: 収集対象日。
        api_key:     EDINET API サブスクリプションキー（Subscription-Key）。
        timeout:     HTTP タイムアウト秒数。

    Returns:
        取得した RawDisclosure リスト。API エラー時は空リスト。
    """
    date_str = target_date.strftime("%Y-%m-%d")
    params: dict[str, str] = {"date": date_str, "type": "2"}
    if api_key:
        params["Subscription-Key"] = api_key
    url = f"{EDINET_DOCUMENTS_URL}?{urllib.parse.urlencode(params)}"
    logger.info("fetch_edinet_disclosures: date=%s", date_str)

    try:
        raw = _fetch_edinet_json(url, timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            logger.error(
                "fetch_edinet_disclosures: EDINET API 認証エラー (HTTP %d)。"
                "EDINET_API_KEY を確認してください。",
                e.code,
            )
        else:
            logger.warning("fetch_edinet_disclosures: HTTPエラー code=%d", e.code)
        return []
    except Exception:
        logger.exception("fetch_edinet_disclosures: 取得失敗")
        return []

    if not raw:
        return []

    disclosures = _parse_edinet_response(raw, target_date)
    logger.info(
        "fetch_edinet_disclosures: date=%s total=%d", target_date, len(disclosures)
    )
    return disclosures


# ---------------------------------------------------------------------------
# 統合収集ジョブ
# ---------------------------------------------------------------------------


def run_edinet_collection(
    conn: duckdb.DuckDBPyConnection,
    target_date: date | None = None,
    api_key: str = "",
    timeout: int = 30,
) -> int:
    """EDINET 開示を収集して raw_disclosures に保存するジョブ。

    Args:
        conn:        DuckDB 接続。
        target_date: 収集対象日。省略時は今日。
        api_key:     EDINET API サブスクリプションキー。
        timeout:     HTTP タイムアウト秒数。

    Returns:
        新規挿入件数。
    """
    from datetime import date as date_cls

    if target_date is None:
        target_date = date_cls.today()

    disclosures = fetch_edinet_disclosures(
        target_date, api_key=api_key, timeout=timeout
    )
    saved = save_raw_disclosures(conn, disclosures)
    logger.info("run_edinet_collection: date=%s saved=%d", target_date, saved)
    return saved
