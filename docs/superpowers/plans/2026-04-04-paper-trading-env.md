# Paper Trading 環境構築 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `KABUSYS_ENV=paper_trading` で起動したとき、自動的に `MockBrokerClient` を使い `data/paper_trading.db` へ記録するPaper Trading環境を構築する。

**Architecture:** `BrokerClientFactory.create(settings)` が `Settings.is_paper / is_dev` に基づいて `MockBrokerClient` か `KabuStationClient` かを返す。既存の `create_broker_api()` をラップし、設定解決の責務を分離する。`ExecutionEngine.__init__` は変更しない。

**Tech Stack:** Python 3.10+, pytest, monkeypatch（環境変数テスト）

---

## ファイル構成

| ファイル | 種別 | 責務 |
|---|---|---|
| `src/kabusys/config.py` | 変更 | `paper_fill_mode`・`paper_sqlite_path` プロパティ追加（行 164〜166 付近） |
| `src/kabusys/execution/broker_factory.py` | 新規 | `BrokerClientFactory.create(settings)` — Settings に基づきブローカークライアントを生成 |
| `tests/test_broker_factory.py` | 新規 | 全10テストを収録 |

---

### Task 1: `config.py` に `paper_fill_mode` と `paper_sqlite_path` を追加

**Files:**
- Modify: `src/kabusys/config.py` （`sqlite_path` プロパティの直後、行 166 付近に追記）
- Test: `tests/test_broker_factory.py` （新規作成）

#### 背景

`config.py` の `Settings` クラスはプロパティごとに `os.environ.get()` で環境変数を読む。同じパターンで2つのプロパティを追加する。

- `paper_fill_mode`: `PAPER_FILL_MODE` 環境変数（デフォルト `"instant"`）。有効値: `instant / partial / never / reject`。無効値で `ValueError`。
- `paper_sqlite_path`: `PAPER_TRADING_SQLITE_PATH` 環境変数（デフォルト `"data/paper_trading.db"`）。`Path(...).expanduser()` を返す（`duckdb_path` / `sqlite_path` と同パターン）。

- [ ] **Step 1: テストファイルを新規作成し、失敗するテストを書く**

```python
# tests/test_broker_factory.py
import os
import pytest
from kabusys.config import Settings


class TestPaperFillMode:
    def test_default_is_instant(self, monkeypatch):
        monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
        assert Settings().paper_fill_mode == "instant"

    def test_partial(self, monkeypatch):
        monkeypatch.setenv("PAPER_FILL_MODE", "partial")
        assert Settings().paper_fill_mode == "partial"

    def test_never(self, monkeypatch):
        monkeypatch.setenv("PAPER_FILL_MODE", "never")
        assert Settings().paper_fill_mode == "never"

    def test_reject(self, monkeypatch):
        monkeypatch.setenv("PAPER_FILL_MODE", "reject")
        assert Settings().paper_fill_mode == "reject"

    def test_invalid_raises(self, monkeypatch):
        monkeypatch.setenv("PAPER_FILL_MODE", "bad_value")
        with pytest.raises(ValueError):
            Settings().paper_fill_mode


class TestPaperSqlitePath:
    def test_default_path(self, monkeypatch):
        monkeypatch.delenv("PAPER_TRADING_SQLITE_PATH", raising=False)
        path = Settings().paper_sqlite_path
        assert path.name == "paper_trading.db"
        assert "data" in str(path)

    def test_override(self, monkeypatch, tmp_path):
        custom = str(tmp_path / "custom.db")
        monkeypatch.setenv("PAPER_TRADING_SQLITE_PATH", custom)
        assert str(Settings().paper_sqlite_path) == custom
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_broker_factory.py::TestPaperFillMode tests/test_broker_factory.py::TestPaperSqlitePath -v
```

Expected: `AttributeError: 'Settings' object has no attribute 'paper_fill_mode'`

- [ ] **Step 3: `config.py` にプロパティを追加**

`sqlite_path` プロパティ（行 164〜166）の直後に以下を追記:

```python
    @property
    def paper_fill_mode(self) -> str:
        """Paper Trading 時の MockBrokerClient fill_mode。

        環境変数 PAPER_FILL_MODE で設定（デフォルト: "instant"）。
        有効値: "instant" | "partial" | "never" | "reject"
        """
        _valid = frozenset({"instant", "partial", "never", "reject"})
        mode = os.environ.get("PAPER_FILL_MODE", "instant")
        if mode not in _valid:
            raise ValueError(
                f"PAPER_FILL_MODE の値が不正です: '{mode}'. "
                f"有効な値: {sorted(_valid)}"
            )
        return mode

    @property
    def paper_sqlite_path(self) -> Path:
        """Paper Trading 用 SQLite DB のパス。

        環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能（デフォルト: data/paper_trading.db）。
        """
        return Path(
            os.environ.get("PAPER_TRADING_SQLITE_PATH", "data/paper_trading.db")
        ).expanduser()
```

追加場所: `# --- データベース ---` セクション内、`sqlite_path` の直後（`pid_file_path` の前）。

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_broker_factory.py::TestPaperFillMode tests/test_broker_factory.py::TestPaperSqlitePath -v
```

Expected: 7 passed

- [ ] **Step 5: 既存テスト全体が壊れていないことを確認**

```bash
python -m pytest tests/ -q --tb=short --ignore=tests/test_generated.py
```

Expected: 全テスト passed（追加7件を含む）

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/config.py tests/test_broker_factory.py
git commit -m "feat: add paper_fill_mode and paper_sqlite_path to Settings (Issue #42)"
```

---

### Task 2: `BrokerClientFactory` を新設

**Files:**
- Create: `src/kabusys/execution/broker_factory.py`
- Test: `tests/test_broker_factory.py` （Task 1 で作成済み、追記）

#### 背景

`broker_api.py` には既に `create_broker_api(mock: bool, **kwargs)` が存在する。`BrokerClientFactory` はこれをラップし、`Settings` オブジェクトからパラメータを解決する責務のみを持つ。

```
BrokerClientFactory.create(settings)
  ├── is_paper or is_dev → create_broker_api(mock=True, fill_mode=settings.paper_fill_mode)
  ├── is_live            → NotImplementedError
  └── else               → ValueError
```

- [ ] **Step 1: `TestBrokerClientFactory` クラスをテストファイルに追記（失敗するテスト）**

```python
# tests/test_broker_factory.py に追記

from kabusys.execution.broker_factory import BrokerClientFactory
from kabusys.execution.mock_client import MockBrokerClient


class TestBrokerClientFactory:
    def test_paper_mode_returns_mock(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, MockBrokerClient)

    def test_dev_mode_returns_mock(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "development")
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, MockBrokerClient)

    def test_fill_mode_applied(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.setenv("PAPER_FILL_MODE", "partial")
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, MockBrokerClient)
        assert broker.fill_mode == "partial"

    def test_fill_mode_default_instant(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
        broker = BrokerClientFactory.create(Settings())
        assert broker.fill_mode == "instant"

    def test_live_mode_raises_not_implemented(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "live")
        with pytest.raises(NotImplementedError):
            BrokerClientFactory.create(Settings())

    def test_unknown_env_raises_value_error(self, monkeypatch):
        # Settings.env が ValueError を投げることを確認
        # (KABUSYS_ENV 検証は Settings.env が担う)
        monkeypatch.setenv("KABUSYS_ENV", "unknown_env")
        with pytest.raises(ValueError):
            BrokerClientFactory.create(Settings())
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_broker_factory.py::TestBrokerClientFactory -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.execution.broker_factory'`

- [ ] **Step 3: `broker_factory.py` を新規作成**

```python
# src/kabusys/execution/broker_factory.py
"""broker_factory.py — 設定に応じたブローカークライアントを生成するファクトリ。"""
from __future__ import annotations

from kabusys.execution.broker_api import BrokerAPIProtocol, create_broker_api
from kabusys.config import Settings


class BrokerClientFactory:
    """設定に応じてブローカークライアントを生成するファクトリ。

    既存の create_broker_api() をラップし、Settings からパラメータを解決する。
    ExecutionEngine は BrokerAPIProtocol を受け取るだけでよく、
    環境判定ロジックをこのクラスに集約する。
    """

    @staticmethod
    def create(settings: Settings) -> BrokerAPIProtocol:
        """設定に応じたブローカークライアントを返す。

        - is_paper or is_dev → MockBrokerClient(fill_mode=settings.paper_fill_mode)
        - is_live            → NotImplementedError（将来実装）
        - それ以外           → ValueError
        """
        if settings.is_paper or settings.is_dev:
            return create_broker_api(mock=True, fill_mode=settings.paper_fill_mode)
        if settings.is_live:
            raise NotImplementedError(
                "Live broker client (KabuStationClient) は未実装です。"
                "KABUSYS_ENV=paper_trading または development を使用してください。"
            )
        raise ValueError(f"未知の KABUSYS_ENV: {settings.env!r}")
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_broker_factory.py::TestBrokerClientFactory -v
```

Expected: 6 passed

- [ ] **Step 5: 全テスト（15件）が通ることを確認**

```bash
python -m pytest tests/test_broker_factory.py -v
```

Expected: 13 passed

- [ ] **Step 6: 既存テスト全体が壊れていないことを確認**

```bash
python -m pytest tests/ -q --tb=short --ignore=tests/test_generated.py
```

Expected: 全テスト passed

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/execution/broker_factory.py tests/test_broker_factory.py
git commit -m "feat: add BrokerClientFactory for paper trading mode (Issue #42)"
```
