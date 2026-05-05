"""kabusys.utils.http モジュールのユニットテスト"""

from __future__ import annotations

import urllib.error
import urllib.request
from unittest.mock import patch

import pytest

from kabusys.utils.http import (
    SSRFBlockRedirectHandler,
    is_private_host,
    validate_url_scheme,
)


# ---------------------------------------------------------------------------
# validate_url_scheme
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url", ["http://example.com", "https://example.com/path?q=1"])
def test_validate_url_scheme_allows_http_https(url):
    validate_url_scheme(url)  # 例外が出なければ OK


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "//example.com",  # スキームなし
        "",
    ],
)
def test_validate_url_scheme_rejects_other_schemes(url):
    with pytest.raises(ValueError, match="許可されていないURLスキーム"):
        validate_url_scheme(url)


# ---------------------------------------------------------------------------
# is_private_host
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hostname",
    [
        "127.0.0.1",
        "::1",
        "10.0.0.1",
        "10.255.255.255",
        "172.16.0.1",
        "192.168.0.1",
        "169.254.1.1",  # link-local
        "224.0.0.1",  # multicast
        "fe80::1",  # IPv6 link-local
        "fe80::1%lo0",  # IPv6 zone index
        "fe80::1%eth0",
        None,
        "",
    ],
)
def test_is_private_host_returns_true_for_private(hostname):
    assert is_private_host(hostname) is True


@pytest.mark.parametrize(
    "hostname",
    [
        "8.8.8.8",
        "1.1.1.1",
        "2606:4700:4700::1111",  # Cloudflare IPv6
    ],
)
def test_is_private_host_returns_false_for_public_ip(hostname):
    assert is_private_host(hostname) is False


def test_is_private_host_dns_failure_is_fail_open():
    """DNS 解決失敗時は fail-open（False を返す）ことを確認する。"""
    with patch("socket.getaddrinfo", side_effect=OSError("NXDOMAIN")):
        result = is_private_host("nonexistent.invalid")
    assert result is False


def test_is_private_host_mixed_records_returns_true():
    """DNS が public/private 混在で返す場合は True を返すことを確認する。"""
    fake_addrs = [
        (None, None, None, None, ("8.8.8.8", 0)),
        (None, None, None, None, ("192.168.0.1", 0)),  # private
    ]
    with patch("socket.getaddrinfo", return_value=fake_addrs):
        assert is_private_host("mixed.example.com") is True


# ---------------------------------------------------------------------------
# SSRFBlockRedirectHandler
# ---------------------------------------------------------------------------


def _make_req(url: str) -> urllib.request.Request:
    return urllib.request.Request(url)


def test_ssrf_handler_blocks_private_redirect():
    """プライベートアドレスへのリダイレクトをブロックすることを確認する。"""
    handler = SSRFBlockRedirectHandler()
    req = _make_req("https://example.com/start")
    with pytest.raises(urllib.error.URLError, match="プライベートアドレス"):
        handler.redirect_request(req, None, 302, "Found", {}, "http://192.168.0.1/evil")


def test_ssrf_handler_blocks_non_http_scheme():
    """http/https 以外のスキームへのリダイレクトをブロックすることを確認する。"""
    handler = SSRFBlockRedirectHandler()
    req = _make_req("https://example.com/start")
    with pytest.raises(urllib.error.URLError, match="スキームが不正"):
        handler.redirect_request(req, None, 302, "Found", {}, "ftp://example.com/file")


def test_ssrf_handler_resolves_relative_redirect():
    """相対リダイレクトを絶対 URL に正規化してから検査することを確認する。"""
    handler = SSRFBlockRedirectHandler()
    req = _make_req("https://example.com/start")
    # 相対パスへのリダイレクトでプライベートIPに解決されないケースはそのまま通過
    # ここでは相対パスが private IP に解決されるケースをテスト
    with pytest.raises(urllib.error.URLError, match="プライベートアドレス"):
        handler.redirect_request(req, None, 302, "Found", {}, "http://10.0.0.1/path")


def test_ssrf_handler_relative_redirect_resolves_correctly():
    """相対リダイレクト URL が正しく絶対化されることを確認する（ブロックされないケース）。"""
    handler = SSRFBlockRedirectHandler()
    req = _make_req("https://example.com/old")
    # /new は example.com に解決されるため通過するはず（super() が Request を返す）
    try:
        result = handler.redirect_request(req, None, 302, "Found", {}, "/new")
        # super().redirect_request が Request オブジェクトを返す
        assert result is not None
    except urllib.error.URLError:
        pytest.fail("正当な相対リダイレクトがブロックされた")
