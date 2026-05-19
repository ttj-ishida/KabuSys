# Backtest Framework

- 対象: KabuSys のバックテスト実行基盤
- 更新: 実装済み仕様ベース

---

## 1. 目的

KabuSys のバックテストは、実運用で使っている `generate_signals()` と同じロジックを再利用しながら、専用のインメモリ DB 上で安全に検証するための仕組みです。  
`paper_trading` や `live` と乖離しないことを優先し、シグナル生成・保有制御・地合い判定をできるだけ共通化しています。

---

## 2. 位置づけ

1. Research
   Notebook や分析コードで仮説を作る
2. Backtest
   共通ロジックで過去検証する
3. Paper Trading
   模擬約定で運用フローを確認する
4. Live
   実口座で日次運用する

---

## 3. 主な評価指標

- CAGR
- Sharpe Ratio
- Max Drawdown
- Win Rate
- Payoff Ratio
- Profit Factor
- Annual Volatility
- Calmar Ratio
- Avg Holding Days

集計は `src/kabusys/backtest/metrics.py` と `src/kabusys/backtest/report.py` で行う。

---

## 4. 実行モデル

1 営業日ごとに次を繰り返す。

1. 前営業日に作った注文を当日寄りで約定させる
2. 当日の `positions` をインメモリ DB に反映する
3. 当日終値で時価評価する
4. 当日データで `generate_signals()` を実行する
5. 翌営業日寄りで執行する注文キューを組む

これにより、シグナル生成は当日終値ベース、執行は翌営業日寄りという運用系と同じ前提で評価する。

---

## 5. モジュール構成

```text
src/kabusys/backtest/
├── __init__.py
├── clock.py
├── simulator.py
├── metrics.py
├── engine.py
├── report.py
└── run.py

tests/
├── test_backtest_framework.py
├── test_backtest_scope.py
├── test_backtest_report.py
└── test_min_holding_days.py
```

---

## 6. 公開 API

### `run_backtest()`

```python
run_backtest(
    conn,
    start_date,
    end_date,
    initial_cash=10_000_000,
    slippage_rate=0.001,
    commission_rate=0.00055,
    max_position_pct=0.10,
    allocation_method="risk_based",
    max_utilization=0.70,
    max_positions=10,
    risk_pct=0.005,
    stop_loss_pct=0.08,
    lot_size=100,
    backtest_scope=None,
    min_holding_days=5,
    max_holding_days=60,
    trailing_stop_atr=2.0,
    threshold=None,                          # BUY 閾値（None で yaml 読み込み）
    topix_size_multiplier_weak_bear=None,    # 弱ベア時 size_multiplier（None で yaml 読み込み）
    topix_size_multiplier_strong_bear=None,  # 強ベア時 size_multiplier（None で yaml 読み込み）
    use_ma200_filter=False,                  # MA200 フィルタ有効化
    volume_breakout_threshold=None,          # 出来高ブレイクアウト閾値
    portfolio_drawdown_stop_pct=None,        # ポートフォリオドローダウンストップ閾値（Issue #348）
    portfolio_drawdown_stop_timeout_days=None,  # ストップのタイムアウト日数（Issue #350）
)
```

### `BacktestScope`

```python
BacktestScope(
    mode="default_universe" | "manual_codes",
    codes=None,
    preserve_universe_filters=True,
)
```

### `BacktestResult`

`BacktestResult` には次のメタデータが入る。

- `history`
- `trades`
- `metrics`
- `scope_mode`
- `scope_codes`
- `effective_universe_size`
- `excluded_codes`
- `preserve_universe_filters`
- `params` — 実行パラメータのスナップショット（例: `{"portfolio_drawdown_stop_timeout_days": 30}`）

---

## 7. CLI

基本実行:

```bash
python -m kabusys.backtest.run \
    --start 2023-01-01 \
    --end 2024-12-31 \
    --cash 10000000 \
    --db data/kabusys.duckdb
```

主なオプション:

- `--cash 10000000` — 初期資金（円）。デフォルト 10,000,000。実口座に合わせて変更可能。
- `--allocation-method risk_based|equal|score` — 資金配分方式。デフォルト `risk_based`。
- `--max-positions 10` — 最大同時保有銘柄数。
- `--max-utilization 0.70` — 最大投下資金比率（全ポジション合計の上限）。
- `--risk-pct 0.005` — 1トレードあたり許容リスク率（`risk_based` 時）。
- `--stop-loss-pct 0.08` — 損切り率（株数計算用）。
- `--scope-mode default_universe|manual_codes`
- `--codes 7203 9984 ...`
- `--no-preserve-universe-filters`
- `--min-holding-days 5`
- `--max-holding-days 60`
- `--trailing-stop-atr 2.0`
- `--threshold 0.60` — BUY シグナル閾値（未指定時は strategy_config.yaml から読み込む）
- `--topix-size-multiplier-weak-bear 0.5` — 弱ベア時の size_multiplier（Issue #349）
- `--topix-size-multiplier-strong-bear 0.0` — 強ベア時の size_multiplier（Issue #349）
- `--ma200-filter` — MA200 フィルタ有効化
- `--volume-breakout-threshold 1.5` — 出来高ブレイクアウト閾値
- `--portfolio-drawdown-stop 0.15` — ドローダウンストップ閾値（ピーク比 N% 超下落で新規 BUY 停止、Issue #348）
- `--portfolio-drawdown-stop-timeout 30` — ストップのタイムアウト日数（N カレンダー日経過で自動解除、Issue #350）
- `--output-format summary|json|markdown|all`
- `--output-dir artifacts/backtests/...`

`manual_codes` を使うと対象銘柄を限定した targeted backtest を実行できる。

---

## 8. インメモリ DB 分離

バックテストは本番 DB 汚染を防ぐため、毎回 `:memory:` の DuckDB を作って必要データだけをコピーして実行する。

概念的には次の流れ。

```text
_build_backtest_conn(source_conn, start_date, end_date)
  1. :memory: DB を作成
  2. 必要テーブルを source_conn からコピー
  3. prices_daily から market_breadth を再計算
  4. positions / signals / position_entries をバックテスト用に使う
```

コピーまたは再構成する主なテーブル:

- `prices_daily`
- `features`
- `ai_scores`（`ENABLE_AI_SENTIMENT=true` のときのみコピー）
- `market_regime`（常にコピー — Core 側が将来書き込む可能性があるため）
- `market_calendar`
- `stocks`
- `earnings_calendar`
- `market_breadth`（コピーではなく再計算）

Bear レジーム判定は `RegimeProvider` プロトコルを経由する（Issue #271）。
`ENABLE_AI_SENTIMENT=false` のバックテストでは `NullRegimeProvider` が使用され、Bear フィルタは常に無効となる。

重要:

- `market_breadth` は未対応ではなく、現在はバックテスト用 DB で再計算される
- そのため `breadth_stop` フィルタはバックテストでも有効
- `manual_codes` 指定時でも `market_regime` / `market_breadth` は市場全体ベースで判定する

---

## 9. 実装済みの保有制御

バックテストで評価できる主な保有制御:

- `min_holding_days`
- `max_holding_days` による `time_exit`
- `trailing_stop_atr`
- Bear regime による BUY 抑制
- `breadth_stop` による BUY 抑制
- TOPIX MA クロスベアガード（`topix_size_multiplier_weak_bear` / `topix_size_multiplier_strong_bear`）による発注サイズ縮小（Issue #349）
- 決算回避
- ストップロス
- `portfolio_drawdown_stop_pct`: ポートフォリオがピーク比で閾値超下落した場合、新規 BUY を停止（Issue #348）
  - `portfolio_drawdown_stop_timeout_days`: N カレンダー日経過で自動解除（Issue #350）

`min_holding_days` は通常 SELL を抑制するが、ストップロス・決算回避・time exit・一部の優先 SELL 条件はバイパスされる。

---

## 10. レポート出力

`src/kabusys/backtest/report.py` でバックテスト結果をレポート化できる。

出力形式:

- CLI summary
- JSON
- Markdown
- 保存一式

`--output-format all` を指定すると、既定で `artifacts/backtests/{run_id}/` に次を保存する。

- `summary.json`
- `report.md`
- `trades.csv`
- `daily_equity.csv`
- `warnings.json`

targeted backtest の場合は `report_type = targeted_backtest` となり、スコープ情報と警告がレポートへ反映される。

---

## 11. 関連

- `documents/02_Strategy/StrategyModel.md`
- `documents/06_RiskManagement/RiskManagement.md`
- `documents/Archive/TODO_TargetedBacktest.md`
- `documents/Archive/TODO_BacktestReporting.md`
- `documents/Archive/TODO_MinHoldingDaysBacktestComparison.md`
