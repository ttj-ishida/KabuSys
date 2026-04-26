# RiskConfig設定ファイル統合 & KabuStationClient配線 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `RiskConfig` パラメータを `config/risk_config.yaml` から読み込む設計に統一し、`is_live` 環境で `KabuStationClient` を使って実際に発注できる状態にする。

**Architecture:** `run_execution.py` に `_load_risk_config(path, initial_portfolio_value)` を追加して YAML から `RiskConfig` を構築する。`initial_portfolio_value` は起動時に `get_available_cash() + 保有評価額` で総資産を算出して渡す。`BrokerClientFactory` の `is_live` ブランチを `KabuStationClient` で実装し、`Settings` に `kabu_trade_password` を追加する。

**Tech Stack:** Python 3.10+, PyYAML (pyyaml>=6.0), pytest, monkeypatch, unittest.mock

---

## ファイル変更マップ

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `config/risk_config.yaml` | Modify | フィールド名を `RiskConfig` に合わせて書き直し |
| `src/kabusys/run_execution.py` | Modify | `_load_risk_config()` 追加、`RiskConfig` 直書き削除、`total_assets` 計算追加 |
| `src/kabusys/config.py` | Modify | `kabu_trade_password` プロパティ追加 |
| `src/kabusys/execution/broker_factory.py` | Modify | `is_live` ブランチを `KabuStationClient` 実装に置換 |
| `src/kabusys/config_setup.py` | Modify | `KABU_TRADE_PASSWORD` 項目追加 |
| `tests/test_run_execution.py` | Modify | `_load_risk_config` パッチ追加・`total_assets` テスト追加 |
| `tests/test_broker_factory.py` | Modify | `is_live` テストを `KabuStationClient` 返却検証に変更 |

---

## Task 1: config/risk_config.yaml の書き直し

**Files:**
- Modify: `config/risk_config.yaml`

- [ ] **Step 1: risk_config.yaml を RiskConfig フィールド名に揃えて書き直す**

`config/risk_config.yaml` を以下の内容で完全に置き換える:

```yaml
# risk_config.yaml — リスク管理設定
# キー名は RiskConfig データクラスのフィールド名に対応する
risk:
  max_position_pct: 0.20           # 1銘柄最大投資比率（総資産比）
  max_utilization: 0.80            # 全ポジション投下上限（現金最低20%維持）
  rate_limit_per_sec: 5            # API レート制限（毎秒）
  circuit_breaker_errors: 10       # サーキットブレーカー発動エラー数上限
  circuit_breaker_window_sec: 60   # サーキットブレーカーカウントウィンドウ（秒）
  max_drawdown: 0.20               # キルスイッチ発動ドローダウン閾値
```

- [ ] **Step 2: コミット**

```bash
git add config/risk_config.yaml
git commit -m "config: risk_config.yaml のキー名を RiskConfig フィールド名に統一"
```

---

## Task 2: _load_risk_config() の TDD 実装

**Files:**
- Modify: `src/kabusys/run_execution.py`
- Test: `tests/test_run_execution.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_run_execution.py` の末尾に以下を追加する:

```python
import tempfile
import yaml as yaml_mod
from kabusys.execution.risk_manager import RiskConfig
import kabusys.run_execution as re_mod


class TestLoadRiskConfig:
    def _write_yaml(self, tmp_path, data: dict) -> Path:
        p = tmp_path / "risk_config.yaml"
        p.write_text(yaml_mod.dump(data), encoding="utf-8")
        return p

    def test_loads_all_fields(self, tmp_path):
        p = self._write_yaml(tmp_path, {
            "risk": {
                "max_position_pct": 0.15,
                "max_utilization": 0.70,
                "rate_limit_per_sec": 3,
                "circuit_breaker_errors": 5,
                "circuit_breaker_window_sec": 30,
                "max_drawdown": 0.10,
            }
        })
        config = re_mod._load_risk_config(p, initial_portfolio_value=5_000_000.0)
        assert isinstance(config, RiskConfig)
        assert config.max_position_pct == 0.15
        assert config.max_utilization == 0.70
        assert config.rate_limit_per_sec == 3
        assert config.circuit_breaker_errors == 5
        assert config.circuit_breaker_window_sec == 30
        assert config.max_drawdown == 0.10
        assert config.initial_portfolio_value == 5_000_000.0

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            re_mod._load_risk_config(tmp_path / "nonexistent.yaml", 0.0)

    def test_missing_key_raises(self, tmp_path):
        p = self._write_yaml(tmp_path, {"risk": {"max_position_pct": 0.20}})
        with pytest.raises(KeyError):
            re_mod._load_risk_config(p, 0.0)
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_run_execution.py::TestLoadRiskConfig -v
```

期待: `AttributeError: module 'kabusys.run_execution' has no attribute '_load_risk_config'`

- [ ] **Step 3: _load_risk_config() を run_execution.py に実装する**

`run_execution.py` の import ブロック直後（`logger = ...` の前）に以下を追加する:

```python
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STOP_FLAG = _PROJECT_ROOT / "data" / "stop_requested.flag"
_EXECUTION_PID = _PROJECT_ROOT / "data" / "execution.pid"
_RISK_CONFIG = _PROJECT_ROOT / "config" / "risk_config.yaml"
```

※ `_PROJECT_ROOT`・`_STOP_FLAG`・`_EXECUTION_PID` は既存のためそのまま。`_RISK_CONFIG` だけ追加。

続けて `logger = logging.getLogger(__name__)` の直後に以下を追加する:

```python
def _load_risk_config(path: Path, initial_portfolio_value: float) -> "RiskConfig":
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    r = data["risk"]
    return RiskConfig(
        max_position_pct=r["max_position_pct"],
        max_utilization=r["max_utilization"],
        rate_limit_per_sec=r["rate_limit_per_sec"],
        circuit_breaker_errors=r["circuit_breaker_errors"],
        circuit_breaker_window_sec=r["circuit_breaker_window_sec"],
        max_drawdown=r["max_drawdown"],
        initial_portfolio_value=initial_portfolio_value,
    )
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_run_execution.py::TestLoadRiskConfig -v
```

期待: 3テストすべて PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/run_execution.py tests/test_run_execution.py
git commit -m "feat: run_execution に _load_risk_config() を追加（#189）"
```

---

## Task 3: initial_portfolio_value 計算と RiskConfig 直書きの置換

**Files:**
- Modify: `src/kabusys/run_execution.py`
- Modify: `tests/test_run_execution.py`

- [ ] **Step 1: initial_portfolio_value のテストを書く**

`tests/test_run_execution.py` のファイル先頭の import ブロックに以下を追加する:

```python
from kabusys.execution.broker_api import Position
from kabusys.execution.risk_manager import RiskConfig
```

続けて `TestRunExecutionMain` クラスに以下2つのテストメソッドを追加する:

```python
def test_initial_portfolio_value_includes_positions(self):
    mock_broker = MagicMock()
    mock_broker.get_available_cash.return_value = 1_000_000.0
    mock_broker.get_positions.return_value = [
        Position(code="1234", qty=100, avg_price=2000.0, current_price=2500.0),
        # 100 * 2500 = 250_000
    ]
    mock_engine = MagicMock()

    with (
        patch("kabusys.run_execution.set_process_priority"),
        patch("kabusys.run_execution.Settings") as mock_settings_cls,
        patch("kabusys.run_execution.sqlite3.connect"),
        patch("kabusys.run_execution.init_monitoring_db"),
        patch("kabusys.run_execution.duckdb.connect"),
        patch("kabusys.run_execution.BrokerClientFactory.create", return_value=mock_broker),
        patch("kabusys.run_execution.OrderRepository"),
        patch("kabusys.run_execution.OrderManager"),
        patch("kabusys.run_execution.RiskManager"),
        patch("kabusys.run_execution.Reconciler"),
        patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine),
        patch("kabusys.run_execution._load_risk_config") as mock_load,
    ):
        mock_load.return_value = RiskConfig()
        settings = MagicMock()
        settings.is_paper = False
        settings.sqlite_path = Path("/prod.db")
        settings.duckdb_path = Path("/data.duckdb")
        mock_settings_cls.return_value = settings

        main()

    # _load_risk_config は total_assets = 1_000_000 + 250_000 = 1_250_000 で呼ばれる
    mock_load.assert_called_once()
    assert mock_load.call_args.kwargs["initial_portfolio_value"] == 1_250_000.0

def test_initial_portfolio_value_fallback_to_avg_price_when_no_current_price(self):
    mock_broker = MagicMock()
    mock_broker.get_available_cash.return_value = 500_000.0
    mock_broker.get_positions.return_value = [
        Position(code="9999", qty=200, avg_price=1500.0, current_price=None),
        # current_price=None → avg_price で代替: 200 * 1500 = 300_000
    ]
    mock_engine = MagicMock()

    with (
        patch("kabusys.run_execution.set_process_priority"),
        patch("kabusys.run_execution.Settings") as mock_settings_cls,
        patch("kabusys.run_execution.sqlite3.connect"),
        patch("kabusys.run_execution.init_monitoring_db"),
        patch("kabusys.run_execution.duckdb.connect"),
        patch("kabusys.run_execution.BrokerClientFactory.create", return_value=mock_broker),
        patch("kabusys.run_execution.OrderRepository"),
        patch("kabusys.run_execution.OrderManager"),
        patch("kabusys.run_execution.RiskManager"),
        patch("kabusys.run_execution.Reconciler"),
        patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine),
        patch("kabusys.run_execution._load_risk_config") as mock_load,
    ):
        mock_load.return_value = RiskConfig()
        settings = MagicMock()
        settings.is_paper = False
        settings.sqlite_path = Path("/prod.db")
        settings.duckdb_path = Path("/data.duckdb")
        mock_settings_cls.return_value = settings

        main()

    # total_assets = 500_000 + 300_000 = 800_000
    assert mock_load.call_args.kwargs["initial_portfolio_value"] == 800_000.0
```

- [ ] **Step 2: 既存の _run_main ヘルパーを更新する**

`test_run_execution.py` の `_run_main()` 関数を以下の通り更新する（`get_positions` の追加と `_load_risk_config` のパッチ追加）:

```python
def _run_main(is_paper: bool = False):
    """全依存をモックして main() を実行するヘルパー。"""
    mock_broker = MagicMock()
    mock_broker.get_available_cash.return_value = 10_000_000.0
    mock_broker.get_positions.return_value = []  # ← 追加（positions なし）
    mock_engine = MagicMock()

    with (
        patch("kabusys.run_execution.set_process_priority") as mock_priority,
        patch("kabusys.run_execution.Settings") as mock_settings_cls,
        patch("kabusys.run_execution.sqlite3.connect") as mock_sqlite,
        patch("kabusys.run_execution.init_monitoring_db"),
        patch("kabusys.run_execution.duckdb.connect"),
        patch(
            "kabusys.run_execution.BrokerClientFactory.create", return_value=mock_broker
        ),
        patch("kabusys.run_execution.OrderRepository"),
        patch("kabusys.run_execution.OrderManager"),
        patch("kabusys.run_execution.RiskManager"),
        patch("kabusys.run_execution.Reconciler"),
        patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine),
        patch("kabusys.run_execution._load_risk_config", return_value=MagicMock()),  # ← 追加
    ):
        settings = MagicMock()
        settings.is_paper = is_paper
        settings.paper_sqlite_path = Path("/paper.db")
        settings.sqlite_path = Path("/prod.db")
        settings.duckdb_path = Path("/data.duckdb")
        settings.pid_file_path = Path("/data/execution.pid")
        mock_settings_cls.return_value = settings

        main()

    return mock_priority, mock_sqlite, mock_engine, settings
```

- [ ] **Step 3: テストが失敗することを確認**

```bash
pytest tests/test_run_execution.py::TestRunExecutionMain::test_initial_portfolio_value_includes_positions -v
```

期待: `AssertionError`（`_load_risk_config` が呼ばれていない or `initial_portfolio_value` が 0.0）

- [ ] **Step 4: run_execution.py の main() を書き換える**

`main()` 内の broker 初期化ブロック（`broker = BrokerClientFactory.create(settings)` の直後）を以下に置き換える:

```python
# 3. ブローカークライアント
broker = BrokerClientFactory.create(settings)

# 4. 起動時総資産を計算（現金 + 保有評価額）
cash = broker.get_available_cash()
positions = broker.get_positions()
total_assets = cash + sum(
    p.qty * (p.current_price if p.current_price is not None else p.avg_price)
    for p in positions
)

# 5. 依存コンポーネント組み立て
repo = OrderRepository(sqlite_conn)
order_manager = OrderManager(broker, repo)
risk_manager = RiskManager(
    broker=broker,
    repo=repo,
    config=_load_risk_config(_RISK_CONFIG, initial_portfolio_value=total_assets),
)
reconciler = Reconciler(broker=broker, repo=repo, order_manager=order_manager)
```

※ 元の `RiskConfig(max_position_pct=0.20, ...)` の直書きブロックを丸ごと削除し、上記に置き換える。

- [ ] **Step 5: テストが通ることを確認**

```bash
pytest tests/test_run_execution.py -v
```

期待: 全テスト PASS

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/run_execution.py tests/test_run_execution.py
git commit -m "feat: RiskConfig を risk_config.yaml から読み込み、initial_portfolio_value を総資産で計算 (#189)"
```

---

## Task 4: Settings に kabu_trade_password を追加

**Files:**
- Modify: `src/kabusys/config.py`
- Test: `tests/test_broker_factory.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_broker_factory.py` の末尾に以下クラスを追加する:

```python
class TestKabuTradePassword:
    def test_returns_none_when_not_set(self, monkeypatch):
        monkeypatch.delenv("KABU_TRADE_PASSWORD", raising=False)
        assert Settings().kabu_trade_password is None

    def test_returns_value_when_set(self, monkeypatch):
        monkeypatch.setenv("KABU_TRADE_PASSWORD", "secret123")
        assert Settings().kabu_trade_password == "secret123"

    def test_returns_none_for_empty_string(self, monkeypatch):
        monkeypatch.setenv("KABU_TRADE_PASSWORD", "")
        assert Settings().kabu_trade_password is None
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_broker_factory.py::TestKabuTradePassword -v
```

期待: `AttributeError: 'Settings' object has no attribute 'kabu_trade_password'`

- [ ] **Step 3: config.py に kabu_trade_password プロパティを追加する**

`config.py` の `kabu_api_base_url` プロパティの直後に以下を追加する:

```python
@property
def kabu_trade_password(self) -> str | None:
    return os.environ.get("KABU_TRADE_PASSWORD") or None
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_broker_factory.py::TestKabuTradePassword -v
```

期待: 3テストすべて PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/config.py tests/test_broker_factory.py
git commit -m "feat: Settings に kabu_trade_password プロパティを追加 (#186)"
```

---

## Task 5: BrokerClientFactory の is_live ブランチを KabuStationClient で実装

**Files:**
- Modify: `src/kabusys/execution/broker_factory.py`
- Modify: `tests/test_broker_factory.py`

- [ ] **Step 1: is_live テストを KabuStationClient 返却検証に更新する**

`tests/test_broker_factory.py` の `TestBrokerClientFactory` クラスの `test_live_mode_raises_not_implemented` を以下に置き換える:

```python
def test_live_mode_returns_kabu_station_client(self, monkeypatch):
    from kabusys.execution.kabu_client import KabuStationClient
    monkeypatch.setenv("KABUSYS_ENV", "live")
    monkeypatch.setenv("KABU_API_PASSWORD", "test_password")
    monkeypatch.delenv("KABU_TRADE_PASSWORD", raising=False)
    broker = BrokerClientFactory.create(Settings())
    assert isinstance(broker, KabuStationClient)
    broker.close()  # httpx.Client を閉じる

def test_live_mode_passes_trade_password_when_set(self, monkeypatch):
    from kabusys.execution.kabu_client import KabuStationClient
    monkeypatch.setenv("KABUSYS_ENV", "live")
    monkeypatch.setenv("KABU_API_PASSWORD", "api_pass")
    monkeypatch.setenv("KABU_TRADE_PASSWORD", "trade_pass")
    broker = BrokerClientFactory.create(Settings())
    assert isinstance(broker, KabuStationClient)
    # trade_password が設定されていれば api_password と異なる値が使われる
    assert broker._trade_password == "trade_pass"
    broker.close()

def test_live_mode_falls_back_to_api_password_when_trade_password_not_set(self, monkeypatch):
    from kabusys.execution.kabu_client import KabuStationClient
    monkeypatch.setenv("KABUSYS_ENV", "live")
    monkeypatch.setenv("KABU_API_PASSWORD", "api_pass")
    monkeypatch.delenv("KABU_TRADE_PASSWORD", raising=False)
    broker = BrokerClientFactory.create(Settings())
    assert isinstance(broker, KabuStationClient)
    # trade_password 未設定時は kabu_client 内部で api_password にフォールバック
    assert broker._trade_password == "api_pass"
    broker.close()
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_broker_factory.py::TestBrokerClientFactory::test_live_mode_returns_kabu_station_client -v
```

期待: `FAIL` — `NotImplementedError` が発生

- [ ] **Step 3: broker_factory.py の is_live ブランチを実装する**

`broker_factory.py` の `is_live` の `raise NotImplementedError(...)` を以下に置き換える:

```python
if settings.is_live:
    return create_broker_api(
        mock=False,
        api_password=settings.kabu_api_password,
        trade_password=settings.kabu_trade_password,
        base_url=settings.kabu_api_base_url,
    )
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_broker_factory.py -v
```

期待: 全テスト PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/execution/broker_factory.py tests/test_broker_factory.py
git commit -m "feat: BrokerClientFactory の is_live ブランチで KabuStationClient を返すよう実装 (#186)"
```

---

## Task 6: config_setup.py に KABU_TRADE_PASSWORD を追加

**Files:**
- Modify: `src/kabusys/config_setup.py`

- [ ] **Step 1: _ITEMS リストに KABU_TRADE_PASSWORD 項目を追加する**

`config_setup.py` の `_ITEMS` リスト内の `KABU_API_BASE_URL` 項目の直後に以下を追加する:

```python
{
    "key": "KABU_TRADE_PASSWORD",
    "label": "kabuステーション 取引パスワード（任意）",
    "secret": True,
    "optional": True,
    "description": (
        "  kabuステーション 取引パスワード（空欄時は API パスワードを流用）\n"
        "  APIパスワードと同一の場合は空欄でよい"
    ),
},
```

- [ ] **Step 2: _write_env() に KABU_TRADE_PASSWORD の書き込み行を追加する**

`_write_env()` 内の `KABU_API_BASE_URL` 行の直後に以下を追加する:

```python
f"KABU_TRADE_PASSWORD={values.get('KABU_TRADE_PASSWORD', '')}",
```

- [ ] **Step 3: 動作確認**

```bash
pytest tests/test_config_setup.py -v
```

期待: 既存テスト全 PASS（_ITEMS の変更は既存テストに影響しない）

- [ ] **Step 4: コミット**

```bash
git add src/kabusys/config_setup.py
git commit -m "feat: config_setup に KABU_TRADE_PASSWORD 項目を追加 (#186)"
```

---

## Task 7: 全テストの最終確認

- [ ] **Step 1: 全テストを実行する**

```bash
pytest tests/ -v --tb=short
```

期待: 全テスト PASS（新規追加分含む）

- [ ] **Step 2: Issue をクローズする**

```bash
gh issue close 189 --comment "実装完了: risk_config.yaml 読み込み・initial_portfolio_value 総資産計算を実装"
gh issue close 186 --comment "実装完了: BrokerClientFactory.create() の is_live ブランチで KabuStationClient を返すよう実装"
```
