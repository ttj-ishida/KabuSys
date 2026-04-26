"""
J-Quants Bulk Download API クライアント

J-Quants Bulk Download API から以下の操作を提供する。
  - list_files:          利用可能なファイル一覧を取得
  - get_presigned_url:   ファイルキーから presigned URL を取得
  - download_file:       presigned URL からローカルへダウンロード（リトライ付き）

設計原則:
  - 認証は `x-api-key` ヘッダー（V1 の Bearer token とは異なる）
  - リトライロジック付き（指数バックオフ、最大 3 回）
  - 標準ライブラリ（urllib.request）のみを使用し、外部依存を最小化
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.jquants.com/v2"
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0


class BulkApiError(RuntimeError):
    """Bulk API 呼び出し失敗。"""


def _bulk_get(path: str, api_key: str, caller: str = "") -> dict:
    """GET /v2/bulk/<path> → JSON dict"""
    url = _BASE_URL + path
    req = urllib.request.Request(url, headers={"x-api-key": api_key})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        prefix = f"{caller}: " if caller else ""
        raise BulkApiError(f"{prefix}{path}: HTTP {exc.code} {exc.reason}") from exc
    except Exception as exc:
        prefix = f"{caller}: " if caller else ""
        raise BulkApiError(f"{prefix}{path}: {exc}") from exc


def list_files(endpoint: str, api_key: str) -> list[dict]:
    """GET /v2/bulk/list?endpoint=<ep> → [{key, date, ...}, ...]"""
    encoded = urllib.parse.quote(endpoint, safe="")
    data = _bulk_get(f"/bulk/list?endpoint={encoded}", api_key, caller="list_files")
    return data.get("files", [])


def get_presigned_url(file_key: str, api_key: str) -> str:
    """GET /v2/bulk/get?key=<key> → presigned URL（有効期限5分）"""
    encoded = urllib.parse.quote(file_key, safe="")
    data = _bulk_get(f"/bulk/get?key={encoded}", api_key, caller="get_presigned_url")
    try:
        return data["url"]
    except KeyError as exc:
        raise BulkApiError(
            f"get_presigned_url: response missing 'url' key: {data}"
        ) from exc


def download_file(presigned_url: str, dest: Path) -> Path:
    """presigned URL → gzip CSV をローカルに保存。最大3回リトライ。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(_MAX_RETRIES):
        try:
            with urllib.request.urlopen(presigned_url) as resp:
                dest.write_bytes(resp.read())
            logger.debug("ダウンロード完了: %s", dest)
            return dest
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            if attempt + 1 >= _MAX_RETRIES:
                raise BulkApiError(
                    f"download_file 失敗（{_MAX_RETRIES}回）: {exc}"
                ) from exc
            wait = _RETRY_BACKOFF_BASE**attempt
            logger.warning(
                "ダウンロード失敗（%d/%d）: %s — %.0fs後にリトライ",
                attempt + 1,
                _MAX_RETRIES,
                exc,
                wait,
            )
            time.sleep(wait)
    raise BulkApiError("download_file: 到達不能コード")  # pragma: no cover
