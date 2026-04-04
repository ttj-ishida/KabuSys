# Paper Trading 環境構築 設計仕様

**Issue:** #42
**対象フェーズ:** Phase 8
**作成日:** 2026-04-04

---

## 背景・目的

バックテストで合格した戦略を、本番と同じ `ExecutionEngine` ロジックのまま模擬環境で稼働させる。`config.py` には既に `KABUSYS_ENV=paper_trading` と `is_paper` プロパティが存在し、`MockBrokerClient` も完成済み。不足しているのは「設定に応じてブローカークライアントを切り替える Factory」と「Paper Trading 専用 DB のパス設定」のみ。

---

## スコープ

| ファイル | 変更種別 |
|---|---|
| `src/kabusys/execution/broker_factory.py` | 新規作成 |
| `src/kabusys/config.py` | 変更（`paper_fill_mode`・`paper_sqlite_path` プロパティ追加） |
| `tests/test_broker_factory.py` | 新規作成 |

**変更しないファイル:** `execution_engine.py`（`__init__` は変更不要。呼び出し元が `BrokerClientFactory.create(settings)` でブローカーを生成して渡す）

---

## 設計

### 1. `config.py`: 新規プロパティ2件追加

#### `paper_fill_mode`

```python
@property
def paper_fill_mode(self) -> str:
    """Paper Trading 時の MockBrokerClient fill_mode。

    環境変数 PAPER_FILL_MODE で設定（デフォルト: "instant"）。
    有効値: "instant" | "partial" | "never" | "reject"
    - instant: 全注文を即時約定（通常の Paper Trading 用）
    - partial: 50% 即時約定、残りは手動 fill（部分約定テスト用）
    - never:   注文は受付のみで約定しない（保留ロジックテスト用）
    - reject:  全注文を拒否（エラーハンドリングテスト用）
    """
    valid = {"instant", "partial", "never", "reject"}
    mode = os.getenv("PAPER_FILL_MODE", "instant")
    if mode not in valid:
        raise ValueError(
            f"PAPER_FILL_MODE must be one of {sorted(valid)}, got {mode!r}"
        )
    return mode
```

#### `paper_sqlite_path`

```python
@property
def paper_sqlite_path(self) -> Path:
    """Paper Trading 用 SQLite DB のパス。

    環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能（デフォルト: data/paper_trading.db）。
    """
    return Path(
        os.getenv("PAPER_TRADING_SQLITE_PATH", "data/paper_trading.db")
    ).expanduser()
```

### 2. `broker_factory.py`: BrokerClientFactory 新設

`broker_api.py` には既に `create_broker_api(mock: bool, **kwargs)` が存在する。`BrokerClientFactory` はこの関数を内部で利用し、`Settings` オブジェクトからパラメータを解決する責務を担う。

```python
from kabusys.execution.broker_api import BrokerAPIProtocol, create_broker_api
from kabusys.config import Settings


class BrokerClientFactory:
    """設定に応じてブローカークライアントを生成するファクトリ。

    既存の create_broker_api() をラップし、Settings からパラメータを解決する。
    """

    @staticmethod
    def create(settings: Settings) -> BrokerAPIProtocol:
        """設定に応じたブローカークライアントを返す。

        - is_paper or is_dev → MockBrokerClient(fill_mode=settings.paper_fill_mode)
        - is_live            → KabuStationClient（将来実装）
        - それ以外           → ValueError
        """
        if settings.is_paper or settings.is_dev:
            return create_broker_api(mock=True, fill_mode=settings.paper_fill_mode)
        if settings.is_live:
            raise NotImplementedError(
                "Live broker client (KabuStationClient) is not yet implemented"
            )
        raise ValueError(f"Unknown KABUSYS_ENV: {settings.env!r}")
```

### 3. 呼び出し元の使用パターン

```python
# Paper Trading 起動スクリプト（例）
settings = Settings()
broker = BrokerClientFactory.create(settings)

sqlite_conn = sqlite3.connect(settings.paper_sqlite_path)
# init_monitoring_db(sqlite_conn) でスキーマ初期化

engine = ExecutionEngine(
    broker=broker,
    repo=OrderRepository(sqlite_conn),
    risk_manager=RiskManager(...),
    order_manager=OrderManager(...),
    duckdb_conn=duckdb.connect(settings.duckdb_path),
    config=EngineConfig(...),
)
```

### 4. データ永続化

Paper Trading の注文・ポジション・監視データは `settings.paper_sqlite_path`（デフォルト: `data/paper_trading.db`）に保存する。スキーマは既存の `init_monitoring_db()` と同じ初期化ロジックを使用。`data/monitoring.db`（本番）とは完全分離し、混在リスクを排除する。

---

## エラーハンドリング

| 状況 | 挙動 |
|---|---|
| `PAPER_FILL_MODE` に無効値 | `ValueError` を raise（起動時に失敗） |
| `KABUSYS_ENV=live` で `create()` 呼び出し | `NotImplementedError` |
| `KABUSYS_ENV` が未定義値 | `ValueError` |

---

## テスト

| テスト名 | 検証内容 |
|---|---|
| `test_creates_mock_client_in_paper_mode` | `KABUSYS_ENV=paper_trading` → `MockBrokerClient` インスタンスを返す |
| `test_creates_mock_client_in_dev_mode` | `KABUSYS_ENV=development` → `MockBrokerClient` インスタンスを返す |
| `test_fill_mode_from_env` | `PAPER_FILL_MODE=partial` → `result.fill_mode == "partial"` |
| `test_fill_mode_default_instant` | `PAPER_FILL_MODE` 未設定 → `result.fill_mode == "instant"` |
| `test_fill_mode_never_and_reject` | `PAPER_FILL_MODE=never/reject` → それぞれ正しい fill_mode |
| `test_invalid_fill_mode_raises` | `PAPER_FILL_MODE=bad` → `ValueError` |
| `test_live_mode_raises_not_implemented` | `KABUSYS_ENV=live` → `NotImplementedError` |
| `test_unknown_env_raises_value_error` | `KABUSYS_ENV=unknown` → `ValueError` |
| `test_paper_sqlite_path_default` | 環境変数未設定 → `data/paper_trading.db` |
| `test_paper_sqlite_path_override` | `PAPER_TRADING_SQLITE_PATH=/tmp/test.db` → そのパス |

---

## 非スコープ

- 本番ブローカークライアント（`KabuStationClient`）の実装
- `ExecutionEngine` の変更（`__init__` は既存のままで使用可能）
- Streamlit ダッシュボードの Paper Trading 専用表示
- Paper Trading 期間中の自動レポート生成
