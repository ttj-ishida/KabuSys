# LINE通知基盤（LineNotifier）実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `LineNotifier` クラスと `build_notifier()` ファクトリを実装し、設定ベースで ON/OFF できる LINE 通知アドオン基盤を追加する。

**Architecture:** `operations/notifier.py` に `LineNotifier` を作成し、`send(message)` メソッド1つで LINE Messaging API に push する。`config.py` に `line_notify_enabled` プロパティを追加し、`build_notifier(settings)` で Settings から組み立てる。既存の `monitoring/alert_manager.py`（障害アラート）とは独立して共存する。

**Tech Stack:** Python 3.10+, `requests`, `unittest.mock.patch`

---

## ファイル構成

| 操作 | パス | 役割 |
|---|---|---|
| Modify | `src/kabusys/config.py` | `line_notify_enabled` プロパティ追加 |
| Create | `src/kabusys/operations/notifier.py` | `LineNotifier` クラス + `build_notifier()` |
| Create | `tests/test_notifier.py` | 全テスト（8件） |

---

### Task 1: Settings に `line_notify_enabled` を追加

**Files:**
- Modify: `src/kabusys/config.py:161-168`（`# --- LINE Messaging API ---` セクション）
- Test: `tests/test_notifier.py`（新規作成）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_notifier.py` を新規作成する:

```python
"""tests/test_notifier.py — LineNotifier ユニットテスト"""

from __future__ import annotations

import requests
from unittest.mock import MagicMock, patch

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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_notifier.py::TestLineNotifyEnabled -v
```

Expected: `AttributeError: 'Settings' object has no attribute 'line_notify_enabled'`

- [ ] **Step 3: `line_notify_enabled` プロパティを実装**

`src/kabusys/config.py` の `line_user_id` プロパティの直後（168行目付近）に追加する:

```python
    @property
    def line_user_id(self) -> str:
        return os.environ.get("LINE_USER_ID", "")

    @property
    def line_notify_enabled(self) -> bool:
        return os.environ.get("LINE_NOTIFY_ENABLED", "true").lower() not in (
            "false",
            "0",
            "no",
        )
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_notifier.py::TestLineNotifyEnabled -v
```

Expected: 5 passed

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/config.py tests/test_notifier.py
git commit -m "feat: Settings に line_notify_enabled を追加 (Issue #196)"
```

---

### Task 2: `LineNotifier` クラスを実装

**Files:**
- Create: `src/kabusys/operations/notifier.py`
- Modify: `tests/test_notifier.py`（テスト追加）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_notifier.py` の末尾に追加する:

```python
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
            mock_req.post.side_effect = requests.exceptions.ConnectionError("no network")
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_notifier.py::TestLineNotifierSend -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.operations.notifier'`

- [ ] **Step 3: `notifier.py` を実装**

`src/kabusys/operations/notifier.py` を新規作成する:

```python
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
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_notifier.py::TestLineNotifierSend -v
```

Expected: 7 passed

---

### Task 3: `build_notifier()` ファクトリを追加

**Files:**
- Modify: `src/kabusys/operations/notifier.py`（末尾に追加）
- Modify: `tests/test_notifier.py`（テスト追加）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_notifier.py` の末尾に追加する:

```python
from kabusys.operations.notifier import build_notifier  # noqa: E402


class TestBuildNotifier:
    def test_build_notifier_from_settings(self, monkeypatch):
        """`build_notifier()` が Settings から正しく構築される"""
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "mytoken")
        monkeypatch.setenv("LINE_USER_ID", "myuserid")
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "true")
        n = build_notifier(Settings())
        assert n._token == "mytoken"
        assert n._user_id == "myuserid"
        assert n._enabled is True

    def test_build_notifier_disabled_when_env_false(self, monkeypatch):
        """`LINE_NOTIFY_ENABLED=false` → enabled=False"""
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("LINE_USER_ID", "uid")
        monkeypatch.setenv("LINE_NOTIFY_ENABLED", "false")
        n = build_notifier(Settings())
        assert n._enabled is False
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_notifier.py::TestBuildNotifier -v
```

Expected: `ImportError: cannot import name 'build_notifier'`

- [ ] **Step 3: `build_notifier()` を実装**

`src/kabusys/operations/notifier.py` の末尾に追加する（`LineNotifier` クラスの直後）:

```python
from kabusys.config import Settings  # noqa: E402 — 循環 import 回避のため末尾 import


def build_notifier(settings: Settings) -> LineNotifier:
    """Settings から LineNotifier を生成する。"""
    return LineNotifier(
        token=settings.line_channel_access_token,
        user_id=settings.line_user_id,
        enabled=settings.line_notify_enabled,
    )
```

**注意:** `from kabusys.config import Settings` は循環インポートを避けるため関数定義の直前（モジュール末尾）に置く。もし循環インポートが発生する場合は `build_notifier` 内で `from kabusys.config import Settings` を局所インポートに変更する。

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_notifier.py -v
```

Expected: 14 passed (Task 1の5件 + Task 2の7件 + Task 3の2件)

- [ ] **Step 5: ruff チェック**

```bash
python -m ruff check src/kabusys/operations/notifier.py tests/test_notifier.py
python -m ruff format --check src/kabusys/operations/notifier.py tests/test_notifier.py
```

Expected: `All checks passed!` / `N files already formatted`

ruff format が差分を出した場合は `python -m ruff format` を実行してから再チェックする。

- [ ] **Step 6: 全テストで回帰なし確認**

```bash
python -m pytest tests/test_notifier.py tests/test_alert_manager.py -v
```

Expected: 全テスト pass（`test_alert_manager.py` の既存テストも壊れていないこと）

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/operations/notifier.py src/kabusys/config.py tests/test_notifier.py
git commit -m "feat: LineNotifier と build_notifier() を実装 (Issue #196)"
```
