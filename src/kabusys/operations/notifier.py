"""notifier.py — LINE Messaging API による定期通知送信。

障害アラート（クールダウン付き）は monitoring/alert_manager.py を使用すること。
本モジュールは定期レポート等のシンプルな一方向プッシュを担う。
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
_MAX_MESSAGE_LEN = 5000
_TRUNCATION_SUFFIX = "...(省略)"


class NullNotifier:
    """通知を何もしない Null Object。

    以下のいずれかの場合に build_notifier() が返す:
    - LINE_NOTIFY_ENABLED=false（通知無効）
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が未設定（認証情報欠落フォールバック）

    Core 機能は NullNotifier.send() を呼んでも例外が発生しない。
    """

    def send(self, message: str) -> bool:  # noqa: ARG002
        logger.debug("NullNotifier: LINE 通知は無効のためスキップ")
        return False


class LineNotifier:
    """LINE Messaging API push message を送信する。

    token / user_id が空、または enabled=False の場合は送信せずログのみ出力する。
    """

    def __init__(self, token: str, user_id: str, enabled: bool = True) -> None:
        self._token = token
        self._user_id = user_id
        self._enabled = enabled

    def send(self, message: str) -> bool:
        """LINE push message を送信する。

        Returns:
            True: 送信成功
            False: スキップ（無効/未設定/エラー）
        """
        if not self._enabled:
            logger.debug("LineNotifier: disabled — skipping")
            return False
        if not self._token or not self._user_id:
            logger.warning("LineNotifier: token/user_id not configured — skipping")
            return False

        if len(message) > _MAX_MESSAGE_LEN:
            cutoff = _MAX_MESSAGE_LEN - len(_TRUNCATION_SUFFIX)
            message = message[:cutoff] + _TRUNCATION_SUFFIX

        try:
            resp = requests.post(
                _LINE_PUSH_URL,
                headers={"Authorization": f"Bearer {self._token}"},
                json={
                    "to": self._user_id,
                    "messages": [{"type": "text", "text": message}],
                },
                timeout=10,
            )
        except requests.exceptions.RequestException as exc:
            logger.error("LineNotifier: LINE API request failed: %s", exc)
            return False

        if resp.status_code < 200 or resp.status_code >= 300:
            logger.error(
                "LineNotifier: LINE API returned non-2xx status %d", resp.status_code
            )
            return False

        logger.info("LineNotifier: message sent (%d chars)", len(message))
        return True


from kabusys.config import Settings  # noqa: E402 — モジュール末尾配置（E402 抑制）


def build_notifier(settings: Settings) -> NullNotifier | LineNotifier:
    """Settings から Notifier を生成する。

    以下のいずれかに該当する場合は NullNotifier を返す:
    - LINE_NOTIFY_ENABLED=false
    - トークンまたはユーザーIDが未設定

    Core 機能は返り値の型を意識せず .send() を呼ぶだけでよい。
    """
    if not settings.line_notify_enabled:
        logger.info("build_notifier: LINE 通知は無効 (LINE_NOTIFY_ENABLED=false)")
        return NullNotifier()

    token = settings.line_channel_access_token
    user_id = settings.line_user_id
    if not token or not user_id:
        logger.warning(
            "build_notifier: LINE_NOTIFY_ENABLED=true だが"
            " LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が未設定のため NullNotifier にフォールバックします"
        )
        return NullNotifier()

    return LineNotifier(token=token, user_id=user_id, enabled=True)
