# 設計書: RiskConfig設定ファイル統合 & KabuStationClient配線

- Issue: #189 (RiskConfig設定ファイル統合), #186 (KabuStationClient配線)
- 日付: 2026-04-25
- ステータス: 承認済み

---

## 背景

### #189: RiskConfig設定ファイル統合

`run_execution.py` 内で `RiskConfig(...)` のパラメータが直書きされており、設定変更のたびにコード修正が必要な状態。`config/risk_config.yaml` は存在するが、フィールド名が `RiskConfig` と不一致のため実行経路では使用されていない。

また `initial_portfolio_value` に `broker.get_available_cash()`（現金のみ）を渡しているため、既存保有ポジションがある場合にドローダウン計算の基準値が実際の総資産より小さくなるリスクがある。

### #186: KabuStationClient配線

`KabuStationClient` は `kabu_client.py` に完全実装済みだが、`broker_factory.py` の `is_live` ブランチが `NotImplementedError` を throw するだけで本番執行が不可能な状態。

---

## 設計

### #189: RiskConfig設定ファイル統合

#### 変更 1: `config/risk_config.yaml` の書き直し

`RiskConfig` データクラスのフィールド名に揃えて全キーを再定義する。

```yaml
risk:
  max_position_pct: 0.20           # 1銘柄最大投資比率
  max_utilization: 0.80            # 全ポジション投下上限（現金最低20%維持）
  rate_limit_per_sec: 5            # API レート制限（毎秒）
  circuit_breaker_errors: 10       # サーキットブレーカー発動エラー数上限
  circuit_breaker_window_sec: 60   # サーキットブレーカーカウントウィンドウ（秒）
  max_drawdown: 0.20               # キルスイッチ発動ドローダウン閾値
```

`initial_portfolio_value` は実行時に動的計算するため YAML には含めない。

#### 変更 2: `run_execution.py` へのローダー追加

プライベート関数 `_load_risk_config(path, initial_portfolio_value) -> RiskConfig` を追加し、YAML を読み込んで `RiskConfig` を返す。

`initial_portfolio_value` の計算:

```python
cash = broker.get_available_cash()
positions = broker.get_positions()
total_assets = cash + sum(
    p.qty * (p.current_price if p.current_price is not None else p.avg_price)
    for p in positions
)
```

`broker.get_positions()` の呼び出しは1回のみ（起動時）。

#### 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `config/risk_config.yaml` | フィールド名を `RiskConfig` に合わせて全キー書き直し |
| `src/kabusys/run_execution.py` | `_load_risk_config()` 追加、`RiskConfig(...)` 直書きを置換、`total_assets` 計算追加 |

---

### #186: KabuStationClient配線

#### 変更 1: `config.py` に `kabu_trade_password` を追加

```python
@property
def kabu_trade_password(self) -> str | None:
    return os.environ.get("KABU_TRADE_PASSWORD") or None
```

未設定時は `None` を返し、`KabuStationClient` 側で `api_password` にフォールバックする。

#### 変更 2: `broker_factory.py` の `is_live` ブランチを実装

```python
if settings.is_live:
    return create_broker_api(
        mock=False,
        api_password=settings.kabu_api_password,
        trade_password=settings.kabu_trade_password,
        base_url=settings.kabu_api_base_url,
    )
```

#### 変更 3: `config_setup.py` に `KABU_TRADE_PASSWORD` 項目を追加

オプション項目として `_ITEMS` リストへ追加。`_write_env()` にも対応行を追加。

#### 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `src/kabusys/config.py` | `kabu_trade_password` プロパティ追加 |
| `src/kabusys/execution/broker_factory.py` | `is_live` ブランチを `KabuStationClient` 実装に置換 |
| `src/kabusys/config_setup.py` | `KABU_TRADE_PASSWORD` 項目追加（オプション） |

---

## テスト方針

- `broker_factory.py` の `is_live` ブランチ: `Settings.is_live=True` のモック環境でファクトリが `KabuStationClient` インスタンスを返すことを確認
- `_load_risk_config()`: 正常 YAML・不正キー・ファイル不存在の各ケースをテスト
- `initial_portfolio_value` 計算: ポジションあり/なし両方のケースをテスト

---

## 制約

- `initial_portfolio_value` の計算で `get_positions()` を追加呼び出しするが、起動時1回のみであり性能影響は無視できる
- `KABUSYS_ENV=live` 時に `KABU_API_PASSWORD` が未設定の場合は既存の `ValueError` が発生する（変更なし）
