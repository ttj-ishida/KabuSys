# Paper Trading 環境構築 設計仕様

**Issue:** #42
**対象フェーズ:** Phase 8
**作成日:** 2026-04-04

---

## 背景・目的

バックテストで合格した戦略を、本番と同じ `ExecutionEngine` ロジックのまま模擬環境で稼働させる。`config.py` には既に `KABUSYS_ENV=paper_trading` と `is_paper` プロパティが存在し、`MockBrokerClient` も完成済み。不足しているのは「設定に応じてブローカークライアントを切り替える Factory」と「Paper Trading 専用 DB」の接続のみ。

---

## スコープ

| ファイル | 変更種別 |
|---|---|
| `src/kabusys/execution/broker_factory.py` | 新規作成 |
| `src/kabusys/config.py` | 変更（`paper_fill_mode` プロパティ追加） |
| `src/kabusys/execution/execution_engine.py` | 変更（`from_settings()` クラスメソッド追加） |
| `tests/test_broker_factory.py` | 新規作成 |

---

## 設計

### 1. `config.py`: `paper_fill_mode` プロパティ追加

```python
@property
def paper_fill_mode(self) -> str:
    """Paper Trading 時の MockBrokerClient fill_mode。
    
    環境変数 PAPER_FILL_MODE で設定（デフォルト: "instant"）。
    有効値: "instant" | "partial"
    """
    mode = os.getenv("PAPER_FILL_MODE", "instant")
    if mode not in ("instant", "partial"):
        raise ValueError(
            f"PAPER_FILL_MODE must be 'instant' or 'partial', got {mode!r}"
        )
    return mode
```

### 2. `broker_factory.py`: BrokerClientFactory 新設

```python
from kabusys.execution.broker_api import BrokerAPIProtocol
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.config import Settings


class BrokerClientFactory:
    @staticmethod
    def create(settings: Settings) -> BrokerAPIProtocol:
        """設定に応じてブローカークライアントを生成する。

        - is_paper or is_dev → MockBrokerClient(fill_mode=settings.paper_fill_mode)
        - is_live → KabuStationClient（将来実装）
        """
        if settings.is_paper or settings.is_dev:
            return MockBrokerClient(fill_mode=settings.paper_fill_mode)
        raise NotImplementedError("Live broker client is not yet implemented")
```

### 3. `execution_engine.py`: `from_settings()` クラスメソッド追加

既存の `__init__()` は変更しない。`from_settings()` をファクトリメソッドとして追加し、設定から自動的にブローカークライアントと DB パスを解決する。

```python
@classmethod
def from_settings(
    cls,
    settings: Settings,
    conn: sqlite3.Connection,
    **kwargs,
) -> "ExecutionEngine":
    """設定からExecutionEngineを生成する。

    - is_paper → MockBrokerClient + paper_trading.db
    - is_live  → KabuStationClient + trading.db（将来実装）
    """
    broker = BrokerClientFactory.create(settings)
    return cls(broker=broker, conn=conn, **kwargs)
```

Paper Trading 用 DB パス: `data/paper_trading.db`（呼び出し元が `sqlite3.connect("data/paper_trading.db")` で接続して渡す）

### 4. データ永続化

Paper Trading の注文・ポジション・監視データは `data/paper_trading.db` に保存する。スキーマは既存の `init_monitoring_db()` と同じ初期化ロジックを使用。`data/monitoring.db`（本番）とは完全分離し、混在リスクを排除する。

---

## エラーハンドリング

- `PAPER_FILL_MODE` に無効値が設定された場合: `ValueError` を raise してシステム起動を阻止
- `is_live` 時に `BrokerClientFactory.create()` を呼び出した場合: `NotImplementedError`（本番クライアント実装まで）

---

## テスト

| テスト名 | 検証内容 |
|---|---|
| `test_creates_mock_client_in_paper_mode` | `KABUSYS_ENV=paper_trading` → `MockBrokerClient` インスタンスを返す |
| `test_creates_mock_client_in_dev_mode` | `KABUSYS_ENV=development` → `MockBrokerClient` インスタンスを返す |
| `test_fill_mode_from_env` | `PAPER_FILL_MODE=partial` → `fill_mode="partial"` の MockBrokerClient |
| `test_fill_mode_default_instant` | `PAPER_FILL_MODE` 未設定 → `fill_mode="instant"` |
| `test_invalid_fill_mode_raises` | `PAPER_FILL_MODE=bad` → `ValueError` |
| `test_live_mode_raises_not_implemented` | `KABUSYS_ENV=live` → `NotImplementedError` |
| `test_from_settings_paper_returns_mock` | `from_settings(paper_settings, conn)` → broker が `MockBrokerClient` |

---

## 非スコープ

- 本番ブローカークライアント（`KabuStationClient`）の実装
- Streamlit ダッシュボードの Paper Trading 専用表示
- Paper Trading 期間中の自動レポート生成
