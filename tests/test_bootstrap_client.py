from __future__ import annotations

import gzip
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from kabusys.data.bootstrap.bulk_client import (
    list_files,
    get_presigned_url,
    download_file,
    BulkApiError,
)


def _make_response(body: bytes, status: int = 200):
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_list_files_returns_list():
    payload = json.dumps(
        {
            "data": [
                {"Key": "k1", "Size": 1024, "LastModified": "2024-01-01T00:00:00Z"},
                {"Key": "k2", "Size": 2048, "LastModified": "2024-01-02T00:00:00Z"},
            ]
        }
    ).encode()
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value = _make_response(payload)
        result = list_files("/equities/bars/daily", "my_api_key")
    assert result == [
        {"Key": "k1", "Size": 1024, "LastModified": "2024-01-01T00:00:00Z"},
        {"Key": "k2", "Size": 2048, "LastModified": "2024-01-02T00:00:00Z"},
    ]
    req = mock_open.call_args[0][0]
    assert req.get_header("X-api-key") == "my_api_key"


def test_list_files_raises_on_http_error():
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.side_effect = urllib.error.HTTPError(
            url="", code=500, msg="Internal Server Error", hdrs=None, fp=None
        )
        with pytest.raises(BulkApiError, match="list_files"):
            list_files("/equities/bars/daily", "key")


def test_get_presigned_url_returns_url():
    payload = json.dumps({"url": "https://s3.example.com/presigned?token=abc"}).encode()
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value = _make_response(payload)
        url = get_presigned_url("some_file_key", "my_api_key")
    assert url == "https://s3.example.com/presigned?token=abc"


def test_download_file_saves_to_dest(tmp_path):
    content = gzip.compress(b"Date,Code,O\n2024-01-01,7203,2800\n")
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value = _make_response(content)
        dest = tmp_path / "output.csv.gz"
        result = download_file("https://s3.example.com/presigned", dest)
    assert result == dest
    assert dest.exists()
    assert dest.read_bytes() == content


def test_get_presigned_url_raises_on_missing_url_key():
    payload = json.dumps({"error": "not found"}).encode()
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value = _make_response(payload)
        with pytest.raises(BulkApiError, match="missing 'url' key"):
            get_presigned_url("some_key", "my_api_key")


def test_download_file_retries_on_error(tmp_path):
    content = gzip.compress(b"Date,Code,O\n2024-01-01,7203,2800\n")
    dest = tmp_path / "output.csv.gz"
    responses = [
        urllib.error.HTTPError(url="", code=500, msg="err", hdrs=None, fp=None),
        _make_response(content),
    ]
    with patch("urllib.request.urlopen", side_effect=responses):
        with patch("time.sleep"):  # sleepをスキップ
            result = download_file("https://s3.example.com/presigned", dest)
    assert result == dest
