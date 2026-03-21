# Backtest Framework 実装設計

## 概要

KabuSys の戦略・AI スコアリング層を過去データで検証するバックテストフレームワークを実装する。
既存の `generate_signals(conn, target_date)` をそのまま呼び出し、エンジン側は「日付ループ＋擬似約定＋集計」に専念する薄いラッパー設計（アプローチ A）を採用する。

**対象 Issue**: #19, #20, #21, #22, #23

---

## モジュール構成

```
src/kabusys/backtest/
├── __init__.py
├── clock.py       # SimulatedClock（将来の拡張用薄いデータクラス）
├── simulator.py   # PortfolioSimulator — 擬似約定・ポートフォリオ状態管理
├── metrics.py     # calc_metrics() — CAGR / Sharpe / MaxDD / WinRate
├── engine.py      # run_backtest() — 全体を統合するエントリポイント
└── run.py         # CLI エントリポイント

tests/
└── test_backtest_framework.py
```

---

## 公開 API

### `engine.py`

```python
def run_backtest(
    conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
    initial_cash: float = 10_000_000,
    slippage_rate: float = 0.001,      # 0.1%
    commission_rate: float = 0.00055,  # 0.055%（国内証券標準）
    max_position_pct: float = 0.20,    # 1銘柄あたりの最大ポートフォリオ比率（RiskManagement.md準拠）
) -> BacktestResult:
    ...

@dataclass
class BacktestResult:
    history: list[DailySnapshot]   # 日次ポートフォリオ履歴
    trades: list[TradeRecord]      # 全約定履歴
    metrics: BacktestMetrics       # 計算済みメトリクス
```

### CLI

```bash
python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 \
    --db path/to/kabusys.duckdb   # 本番DBから歴史データをコピーして使用
```

**CLI の前提条件**: 指定 DB ファイルに `prices_daily`, `features`, `ai_scores`,
`market_regime`, `market_calendar` が入力済みであること。

---

## インメモリ DB 分離（本番 DB 汚染防止）

`generate_signals()` は `signals` テーブルに書き込み、`_generate_sell_signals()` は
`positions` テーブルを読み取る。これらを本番 DB に書くと本番データを汚染する。

**方針**: バックテストは専用のインメモリ DuckDB を使用する。

```python
def _build_backtest_conn(
    source_conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
) -> duckdb.DuckDBPyConnection:
    """
    1. ":memory:" で新規 DuckDB を作成しスキーマを初期化
    2. source_conn から必要なテーブルのデータをコピー:
       - prices_daily (start_date - 300日 〜 end_date)
       - features     (同範囲)
       - ai_scores    (同範囲)
       - market_regime (同範囲)
       - market_calendar (全件)
    3. インメモリ conn を返す
    """
```

`run_backtest(conn, ...)` の `conn` は本番 DB 接続。内部で `_build_backtest_conn()` を
呼び出してインメモリ DB を構築し、シミュレーション全体をそこで実行する。
CLI でも同様に本番 DB からコピーする。

---

## 実行フロー（1日のループ）

```
# 初期化
bt_conn = _build_backtest_conn(conn, start_date, end_date)
simulator = PortfolioSimulator(cash=initial_cash, ...)
signals_prev = []

for trading_day in get_trading_days(bt_conn, start_date, end_date):

    1. 前日シグナルを当日 open 価格で約定
       → open_prices = _fetch_open_prices(bt_conn, trading_day)
       → simulator.execute_orders(signals_prev, open_prices,
                                  slippage_rate, commission_rate)

    2. シミュレータの positions を bt_conn の positions テーブルに書き戻す
       → _write_positions(bt_conn, trading_day, simulator.positions,
                          simulator.cost_basis)
       ※ DELETE WHERE date = trading_day → INSERT（冪等）
       ※ market_value は NULL で挿入（nullable カラム。_generate_sell_signals は参照しない）

    3. 当日終値で時価評価・スナップショット記録
       → close_prices = _fetch_close_prices(bt_conn, trading_day)
       → simulator.mark_to_market(trading_day, close_prices)

    4. 翌日用シグナルを生成
       → generate_signals(bt_conn, target_date=trading_day)
       ※ bt_conn の positions テーブルを読んで SELL 判定を行う
       → signals_prev = _read_signals(bt_conn, trading_day)
```

---

## Look-ahead Bias 防止

| 処理 | 使うデータ | 根拠 |
|------|-----------|------|
| シグナル生成（day T） | `date < T` の価格・特徴量（features/ai_scores） | `generate_signals()` の SQL が `WHERE date = T` でバインド |
| SELL 判定（day T） | `date <= T` の prices_daily（最新終値） | `_generate_sell_signals()` の SQL が `WHERE date <= T` でバインド |
| 約定（day T+1） | day T+1 の始値 | シグナルは常に翌営業日の始値で執行 |

インメモリ DB には `end_date` 以降のデータを含まないため、物理的に未来参照が不可能。

---

## ポジションサイジングルール

`generate_signals()` は BUY シグナルを `signal_rank`（1始まり）付きで返す。
1銘柄あたりの購入金額は以下で決定する:

```
# portfolio_value は前日スナップショットを使用（当日 open 約定時点では mark-to-market 未実施のため）
prior_portfolio_value = simulator.history[-1].portfolio_value if simulator.history else initial_cash

alloc_per_signal = min(
    prior_portfolio_value * max_position_pct,
    available_cash / num_buy_signals,
)
shares = floor(alloc_per_signal / entry_price)  # entry_price = open * (1 + slippage_rate)
```

- `max_position_pct = 0.20`（RiskManagement.md 準拠、1銘柄≤20%）
- `shares = 0` の場合（資金不足）は発注をスキップしログを出す
- 初日（`simulator.history` が空）は `initial_cash` を `prior_portfolio_value` として使用

---

## データ構造

```python
@dataclass
class DailySnapshot:
    date: date
    cash: float
    positions: dict[str, int]   # code → 株数
    portfolio_value: float      # cash + 時価評価額（Sharpe計算はこの日次系列から導出）

@dataclass
class TradeRecord:
    date: date
    code: str
    side: str                   # "buy" | "sell"
    shares: int
    price: float                # 約定価格（スリッページ適用後）
    commission: float
    realized_pnl: float | None  # SELL 時のみ（取得原価との差分）

@dataclass
class PortfolioSimulator:
    cash: float
    positions: dict[str, int]
    cost_basis: dict[str, float]   # code → 平均取得単価
    history: list[DailySnapshot]
    trades: list[TradeRecord]
```

---

## メトリクス

| 指標 | 定義 | 合格ライン |
|------|------|-----------|
| CAGR | `(最終資産/初期資産)^(1/年数) - 1` | — |
| Sharpe Ratio | `年次化超過リターン / 年次化標準偏差`（無リスク金利=0） | ≥ 1.0 |
| Max Drawdown | `max(1 - 評価額 / 過去ピーク)` | ≤ 20% |
| Win Rate | `勝ちトレード数 / 全クローズトレード数` | — |
| Payoff Ratio | `平均利益 / 平均損失（絶対値）` | — |

**税金は対象外**（確定申告ルール・NISA・損失繰越が複雑なため）。手数料のみ適用。

```python
@dataclass
class BacktestMetrics:
    cagr: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    payoff_ratio: float
    total_trades: int

def calc_metrics(
    history: list[DailySnapshot],
    trades: list[TradeRecord],
) -> BacktestMetrics:
    ...
```

---

## テスト方針（`tests/test_backtest_framework.py`）

既存の `test_regime_detector.py` と同パターン（インメモリ DuckDB + フィクスチャでデータ挿入）を採用。

| テスト | 検証内容 |
|--------|---------|
| 既知結果の検証 | 価格既知のシンプルな売買で損益・現金残高が手計算と一致する |
| Look-ahead 不存在確認 | `end_date + 1` 以降の価格行を DB に挿入し、`run_backtest` 完了後もシグナルに反映されていないことをアサート |
| スリッページ適用確認 | 約定価格 = open × (1 ± slippage_rate) を `TradeRecord.price` で検証 |
| 手数料適用確認 | 売買前後の `cash` 差分が `約定金額 × commission_rate` と一致することを検証 |
| Max Drawdown 計算 | 既知の下落シナリオ（資産が 100→80→90）で MDD = 0.20 を検証 |
| Sharpe Ratio 計算 | 等差のリターン列（標準偏差が既知）から期待 Sharpe を検証 |
| 冪等性 | 同一期間を2回実行しても `BacktestMetrics` が同一値になることを検証 |
| ポジションサイジング | `max_position_pct=0.10` で初期資本の10%以上を1銘柄に投じないことを検証 |

---

## 制約（CLAUDE.md 準拠）

- `datetime.today()` / `date.today()` をバックテストロジック内で参照しない
- シグナル生成は既存の `generate_signals()` を直接呼び出し、ロジックを重複実装しない
- AI・LLM は直接発注しない（Strategy 層経由のみ）
- `signal_queue` は本番専用。バックテストでは使用しない
- 本番 DB の `signals` / `positions` テーブルをバックテストで上書きしない（インメモリ DB 分離）
