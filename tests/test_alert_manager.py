"""tests/test_alert_manager.py — AlertManager ユニットテスト"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import requests

from kabusys.monitoring.alert_manager import AlertManager

LINE_API_URL = "https://api.line.me/v2/bot/message/push"


class TestAlertManagerNotify:
    def test_sends_message_when_token_set(self):
        """トークンあり → requests.post が呼ばれ True を返す"""
        manager = AlertManager(channel_access_token="token123", user_id="uid123")
        with patch("kabusys.monitoring.alert_manager.requests") as mock_requests:
            mock_requests.post.return_value = MagicMock(status_code=200)
            result = manager.notify("テストメッセージ", level="INFO", category="TEST")
        assert result is True
        mock_requests.post.assert_called_once()
        call_kwargs = mock_requests.post.call_args
        assert call_kwargs[0][0] == LINE_API_URL
        assert "テストメッセージ" in call_kwargs[1]["json"]["messages"][0]["text"]

    def test_skips_when_token_empty(self):
        """トークン空 → スキップ・False 返却・例外なし"""
        manager = AlertManager(channel_access_token="", user_id="")
        result = manager.notify("テスト", level="WARNING")
        assert result is False

    def test_cooldown_suppresses_duplicate_within_window(self):
        """同一 (level, category) の cooldown 内 → スキップ"""
        manager = AlertManager(channel_access_token="token", user_id="uid", cooldown_minutes=30)
        with patch("kabusys.monitoring.alert_manager.requests") as mock_requests:
            mock_requests.post.return_value = MagicMock(status_code=200)
            manager.notify("first", level="CRITICAL", category="DRAWDOWN")
            result = manager.notify("second", level="CRITICAL", category="DRAWDOWN")
        assert result is False
        assert mock_requests.post.call_count == 1

    def test_sends_after_cooldown_expires(self):
        """cooldown 経過後 → 送信"""
        manager = AlertManager(channel_access_token="token", user_id="uid", cooldown_minutes=30)
        # 31分前の時刻を直接セット
        past = datetime.now(tz=timezone.utc) - timedelta(minutes=31)
        manager._last_sent[("CRITICAL", "DRAWDOWN")] = past
        with patch("kabusys.monitoring.alert_manager.requests") as mock_requests:
            mock_requests.post.return_value = MagicMock(status_code=200)
            result = manager.notify("msg", level="CRITICAL", category="DRAWDOWN")
        assert result is True
        mock_requests.post.assert_called_once()

    def test_different_categories_do_not_share_cooldown(self):
        """同一 level・異なる category → クールダウン非干渉（両方送信）"""
        manager = AlertManager(channel_access_token="token", user_id="uid", cooldown_minutes=30)
        with patch("kabusys.monitoring.alert_manager.requests") as mock_requests:
            mock_requests.post.return_value = MagicMock(status_code=200)
            r1 = manager.notify("msg1", level="CRITICAL", category="DRAWDOWN")
            r2 = manager.notify("msg2", level="CRITICAL", category="PROCESS")
        assert r1 is True
        assert r2 is True
        assert mock_requests.post.call_count == 2

    def test_request_exception_returns_false_no_propagation(self):
        """requests.exceptions.RequestException → False 返却・例外非伝播"""
        manager = AlertManager(channel_access_token="token", user_id="uid")
        with patch("kabusys.monitoring.alert_manager.requests") as mock_requests:
            mock_requests.post.side_effect = requests.exceptions.ConnectionError("no network")
            mock_requests.exceptions.RequestException = requests.exceptions.RequestException
            result = manager.notify("msg", level="CRITICAL")
        assert result is False

    def test_non_2xx_response_returns_false(self):
        """非 2xx レスポンス → False 返却・例外非伝播"""
        manager = AlertManager(channel_access_token="token", user_id="uid")
        with patch("kabusys.monitoring.alert_manager.requests") as mock_requests:
            mock_requests.post.return_value = MagicMock(status_code=429)
            result = manager.notify("msg", level="WARNING")
        assert result is False
