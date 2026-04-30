"""tests/test_notifier.py — LineNotifier ユニットテスト"""

from __future__ import annotations

from kabusys.config import Settings


class TestLineNotifyEnabled:
    def test_defaults_to_true_when_not_set(self, monkeypatch):
        """LINE_NOTIFY_ENABLED 未設定 → True"""
        monkeypatch.delenv("LINE_NOTIFY_ENABLED", raising=False)
        assert Settings().line_notify_enabled is True

    def test_false_when_set_to_false(self, monkeypatch):
        """LINE_NOTIFY_ENABLED=false → False"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "false")
        assert Settings().line_notify_enabled is False

    def test_false_when_set_to_0(self, monkeypatch):
        """LINE_NOTIFY_ENABLED=0 → False"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "0")
        assert Settings().line_notify_enabled is False

    def test_false_when_set_to_no(self, monkeypatch):
        """LINE_NOTIFY_ENABLED=no → False"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "no")
        assert Settings().line_notify_enabled is False

    def test_true_when_set_to_true(self, monkeypatch):
        """LINE_NOTIFY_ENABLED=true → True"""
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "true")
        assert Settings().line_notify_enabled is True
