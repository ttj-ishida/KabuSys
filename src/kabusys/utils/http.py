"""
HTTP ユーティリティ（SSRF 対策共通モジュール）

複数の収集モジュール（news_collector / tdnet_collector / edinet_collector 等）で
共通利用する SSRF 対策ユーティリティを公開 API として提供する。

SSRF 対策の設計方針:
  - URL スキームを http / https に限定
  - プライベート・ループバック・リンクローカルアドレスへのアクセスを拒否
  - DNS 解決後の A/AAAA レコード全件を検査（リダイレクト先を含む）
  - リダイレクト時も同様の検証を適用（_SSRFBlockRedirectHandler）
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request


def validate_url_scheme(url: str) -> None:
    """URL のスキームが http または https であることを検証する。

    SSRF / ローカルファイル読み出しを防ぐため、http/https 以外を拒否する。

    Raises:
        ValueError: スキームが http/https でない場合。
    """
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"許可されていないURLスキーム: {scheme!r} (url={url!r})")


def is_private_host(hostname: str | None) -> bool:
    """ホスト/IP がプライベート・ループバック・リンクローカルかを判定する。

    IP アドレスは直接判定し、ホスト名は DNS 解決して全 A/AAAA レコードを検査する。
    DNS 解決失敗時は安全側（非プライベート）とみなして通過させる。

    Args:
        hostname: 検査対象のホスト名または IP アドレス文字列。None の場合は True を返す。

    Returns:
        プライベート/ループバック/リンクローカル/マルチキャストの場合 True。
    """
    if not hostname:
        return True
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
    except ValueError:
        pass
    try:
        for info in socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
                return True
    except (OSError, ValueError):
        pass
    return False


class SSRFBlockRedirectHandler(urllib.request.HTTPRedirectHandler):
    """リダイレクト時にスキームとプライベートアドレスを事前検証するハンドラ。

    接続前にリダイレクト先を検査することで、内部ネットワークへの到達を防ぐ。
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme.lower() not in ("http", "https"):
            raise urllib.error.URLError(f"リダイレクト先のスキームが不正: {newurl!r}")
        if is_private_host(parsed.hostname):
            raise urllib.error.URLError(
                f"リダイレクト先がプライベートアドレス: {newurl!r}"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)
