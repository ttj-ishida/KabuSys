"""
HTTP ユーティリティ（SSRF 対策共通モジュール）

複数の収集モジュール（news_collector / tdnet_collector / edinet_collector 等）で
共通利用する SSRF 対策ユーティリティを公開 API として提供する。

SSRF 対策の設計方針:
  - URL スキームを http / https に限定
  - プライベート・ループバック・リンクローカルアドレスへのアクセスを拒否
  - DNS 解決後の A/AAAA レコード全件を検査（リダイレクト先を含む）
  - IPv6 ゾーンインデックス（fe80::1%eth0 等）は % 以降を除去して判定
  - リダイレクト時も同様の検証を適用（SSRFBlockRedirectHandler）
  - 相対リダイレクト URL は urljoin で絶対化してから検査
  - DNS 解決失敗時のデフォルト挙動は fail-open（非プライベートとみなして通過）
    → fail_closed=True で fail-closed に切り替え可能
  - strict=True でブロック条件を「グローバル到達不可なものすべて」に強化
    （unspecified / reserved / documentation / CGNAT 等も対象になる）
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request

__all__ = ["validate_url_scheme", "is_private_host", "SSRFBlockRedirectHandler"]


def validate_url_scheme(url: str) -> None:
    """URL のスキームが http または https であることを検証する。

    SSRF / ローカルファイル読み出しを防ぐため、http/https 以外を拒否する。

    Raises:
        ValueError: スキームが http/https でない場合。
    """
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"許可されていないURLスキーム: {scheme!r} (url={url!r})")


def is_private_host(
    hostname: str | None,
    *,
    strict: bool = False,
    fail_closed: bool = False,
) -> bool:
    """ホスト/IP がプライベート・ループバック・リンクローカルかを判定する。

    IP アドレスは直接判定し、ホスト名は DNS 解決して全 A/AAAA レコードを検査する。
    IPv6 ゾーンインデックス（fe80::1%eth0）は % 以降を除去してから解析する。

    Args:
        hostname:    検査対象のホスト名または IP アドレス文字列。None の場合は True を返す。
        strict:      True のとき「グローバル到達不可（not ip.is_global）」を基準にする。
                     unspecified / reserved / documentation / CGNAT 等も追加でブロックされる。
                     False（デフォルト）は private / loopback / link-local / multicast のみ。
        fail_closed: True のとき DNS 解決失敗をブロック（True を返す）。
                     False（デフォルト）は fail-open（解決失敗時は通過）。

    Returns:
        ブロック対象と判定した場合 True。
    """
    if not hostname:
        return True

    def _is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        if strict:
            return not ip.is_global
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast

    # ゾーンインデックスを除去して IP アドレスとして解析
    hostname_clean = hostname.split("%", 1)[0]
    try:
        ip = ipaddress.ip_address(hostname_clean)
        return _is_blocked(ip)
    except ValueError:
        pass
    # ホスト名の場合: DNS 解決して全 A/AAAA レコードを検査
    try:
        for info in socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP):
            ip_str = info[4][0].split("%", 1)[0]
            ip = ipaddress.ip_address(ip_str)
            if _is_blocked(ip):
                return True
    except (OSError, ValueError):
        return fail_closed
    return False


class SSRFBlockRedirectHandler(urllib.request.HTTPRedirectHandler):
    """リダイレクト時にスキームとプライベートアドレスを事前検証するハンドラ。

    接続前にリダイレクト先を検査することで、内部ネットワークへの到達を防ぐ。
    相対リダイレクト URL は元のリクエスト URL を基準に絶対化してから検査する。
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        abs_url = urllib.parse.urljoin(req.get_full_url(), newurl)
        parsed = urllib.parse.urlparse(abs_url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise urllib.error.URLError(f"リダイレクト先のスキームが不正: {abs_url!r}")
        if is_private_host(parsed.hostname):
            raise urllib.error.URLError(
                f"リダイレクト先がプライベートアドレス: {abs_url!r}"
            )
        return super().redirect_request(req, fp, code, msg, headers, abs_url)
