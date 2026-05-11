"""tests/test_notifier.py — LineNotifier ユニットテスト"""

from __future__ import annotations

from kabusys.config import Settings


class TestLineNotifyEnabled:
    def test_defaults_to_false_when_not_set(self, monkeypatch):
        """LINE_NOTIFY_ENABLED 未設定 → False（安全側デフォルト）"""
        monkeypatch.delenv("LINE_NOTIFY_ENABLED", raising=False)
        assert Settings().line_notify_enabled is False

    def test_true_when_set_to_true(self, monkeypatch):
        """LINE_NOTIFY_ENABLED=true → True"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "true")
        assert Settings().line_notify_enabled is True

    def test_true_when_set_to_1(self, monkeypatch):
        """LINE_NOTIFY_ENABLED=1 → True"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "1")
        assert Settings().line_notify_enabled is True

    def test_false_when_set_to_false(self, monkeypatch):
        """LINE_NOTIFY_ENABLED=false → False"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "false")
        assert Settings().line_notify_enabled is False

    def test_false_when_set_to_off(self, monkeypatch):
        """LINE_NOTIFY_ENABLED=off → False（許容リスト方式）"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "off")
        assert Settings().line_notify_enabled is False

    def test_false_when_empty_string(self, monkeypatch):
        """LINE_NOTIFY_ENABLED=（空文字）→ False（許容リスト方式）"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "")
        assert Settings().line_notify_enabled is False


from unittest.mock import MagicMock, patch  # noqa: E402

import requests  # noqa: E402

from kabusys.operations.notifier import LineNotifier  # noqa: E402

_LINE_API_URL = "https://api.line.me/v2/bot/message/push"


def _notifier(**kwargs) -> LineNotifier:
    defaults = {"token": "tok123", "user_id": "uid123", "enabled": True}
    defaults.update(kwargs)
    return LineNotifier(**defaults)


class TestLineNotifierSend:
    def test_send_disabled_returns_false(self):
        """`enabled=False` → False、API 未呼び出し"""
        n = _notifier(enabled=False)
        with patch("kabusys.operations.notifier.requests") as mock_req:
            result = n.send("hello")
        assert result is False
        mock_req.post.assert_not_called()

    def test_send_no_token_returns_false(self):
        """`token=""` → False、API 未呼び出し"""
        n = _notifier(token="")
        with patch("kabusys.operations.notifier.requests") as mock_req:
            result = n.send("hello")
        assert result is False
        mock_req.post.assert_not_called()

    def test_send_no_user_id_returns_false(self):
        """`user_id=""` → False、API 未呼び出し"""
        n = _notifier(user_id="")
        with patch("kabusys.operations.notifier.requests") as mock_req:
            result = n.send("hello")
        assert result is False
        mock_req.post.assert_not_called()

    def test_send_success(self):
        """正常送信 → True、ペイロード検証"""
        n = _notifier()
        with patch("kabusys.operations.notifier.requests") as mock_req:
            mock_req.post.return_value = MagicMock(status_code=200)
            result = n.send("テストメッセージ")
        assert result is True
        call_kwargs = mock_req.post.call_args
        assert call_kwargs[0][0] == _LINE_API_URL
        assert call_kwargs[1]["json"]["to"] == "uid123"
        assert call_kwargs[1]["json"]["messages"][0]["text"] == "テストメッセージ"
        assert "Bearer tok123" in call_kwargs[1]["headers"]["Authorization"]

    def test_send_api_error_returns_false(self):
        """4xx/5xx → False"""
        n = _notifier()
        with patch("kabusys.operations.notifier.requests") as mock_req:
            mock_req.post.return_value = MagicMock(status_code=400)
            result = n.send("hello")
        assert result is False

    def test_send_request_exception_returns_false(self):
        """接続エラー → False、例外非伝播"""
        n = _notifier()
        with patch("kabusys.operations.notifier.requests") as mock_req:
            mock_req.post.side_effect = requests.exceptions.ConnectionError(
                "no network"
            )
            mock_req.exceptions.RequestException = requests.exceptions.RequestException
            result = n.send("hello")
        assert result is False

    def test_send_truncates_long_message(self):
        """5,000 文字超 → 切り詰めて送信、末尾に '...(省略)'"""
        n = _notifier()
        long_msg = "A" * 5100
        with patch("kabusys.operations.notifier.requests") as mock_req:
            mock_req.post.return_value = MagicMock(status_code=200)
            n.send(long_msg)
        sent_text = mock_req.post.call_args[1]["json"]["messages"][0]["text"]
        assert len(sent_text) <= 5000
        assert sent_text.endswith("...(省略)")


from kabusys.operations.notifier import NullNotifier, build_notifier  # noqa: E402


class TestNullNotifier:
    def test_send_always_returns_false(self):
        """NullNotifier.send() は常に False を返し例外を発生させない"""
        n = NullNotifier()
        assert n.send("any message") is False

    def test_send_empty_message(self):
        """空メッセージでも False を返す"""
        assert NullNotifier().send("") is False


class TestBuildNotifier:
    def test_build_notifier_enabled_returns_line_notifier(self, monkeypatch):
        """`LINE_NOTIFY_ENABLED=true` かつ認証情報あり → LineNotifier を返す"""
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "mytoken")
        monkeypatch.setenv("LINE_USER_ID", "myuserid")
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "true")
        n = build_notifier(Settings())
        assert isinstance(n, LineNotifier)
        assert n._token == "mytoken"
        assert n._user_id == "myuserid"

    def test_build_notifier_disabled_returns_null_notifier(self, monkeypatch):
        """`LINE_NOTIFY_ENABLED=false` → NullNotifier を返す"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "false")
        n = build_notifier(Settings())
        assert isinstance(n, NullNotifier)

    def test_build_notifier_null_notifier_send_safe(self, monkeypatch):
        """`LINE_NOTIFY_ENABLED=false` → send() が例外を出さない"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "false")
        n = build_notifier(Settings())
        assert n.send("test") is False

    def test_build_notifier_missing_token_falls_back_to_null(self, monkeypatch):
        """`LINE_NOTIFY_ENABLED=true` だがトークン未設定 → NullNotifier にフォールバック"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "true")
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        monkeypatch.setenv("LINE_USER_ID", "uid")
        n = build_notifier(Settings())
        assert isinstance(n, NullNotifier)

    def test_build_notifier_missing_user_id_falls_back_to_null(self, monkeypatch):
        """`LINE_NOTIFY_ENABLED=true` だがユーザーID未設定 → NullNotifier にフォールバック"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "true")
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("LINE_USER_ID", "")
        n = build_notifier(Settings())
        assert isinstance(n, NullNotifier)
        assert n.send("msg") is False
