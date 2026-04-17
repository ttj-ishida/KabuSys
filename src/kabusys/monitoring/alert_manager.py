"""alert_manager.py — LINE Messaging API による一方向プッシュ通知。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


class AlertManager:
    """LINE Messaging API push message を送信する。

    channel_access_token / user_id が空の場合は送信せずログのみ出力する。
    同一 (level, category) に対するクールダウン管理をメモリ内で行う。
    """

    def __init__(
        self,
        channel_access_token: str,
        user_id: str,
        cooldown_minutes: int = 30,
    ) -> None:
        self._token = channel_access_token
        self._user_id = user_id
        self._cooldown = timedelta(minutes=cooldown_minutes)
        self._last_sent: dict[tuple[str, str], datetime] = {}

    def notify(self, message: str, level: str = "INFO", category: str = "") -> bool:
        """LINE push message を送信する。

        Returns:
            True: 送信成功
            False: スキップ（トークン未設定 / cooldown / エラー）
        """
        if not self._token or not self._user_id:
            logger.warning(
                "LINE token/user_id not configured — skipping alert: [%s] %s",
                level,
                message,
            )
            return False

        key = (level, category)
        now = datetime.now(tz=timezone.utc)
        last = self._last_sent.get(key)
        if last is not None and now - last < self._cooldown:
            logger.debug(
                "Alert cooldown active for (%s, %s) — skipping", level, category
            )
            return False

        now_jst = datetime.now(tz=timezone(timedelta(hours=9)))
        text = f"[{level}] KabuSys 監視アラート\n{message}\n{now_jst.strftime('%Y-%m-%d %H:%M:%S JST')}"

        try:
            resp = requests.post(
                LINE_PUSH_URL,
                headers={"Authorization": f"Bearer {self._token}"},
                json={
                    "to": self._user_id,
                    "messages": [{"type": "text", "text": text}],
                },
                timeout=10,
            )
        except requests.exceptions.RequestException as exc:
            logger.error("LINE API request failed: %s", exc)
            return False

        if resp.status_code < 200 or resp.status_code >= 300:
            logger.error("LINE API returned non-2xx status %d", resp.status_code)
            return False

        self._last_sent[key] = now
        logger.info("LINE alert sent: [%s] %s", level, message)
        return True
