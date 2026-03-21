# Backtest Framework 実装設計

## 概要

KabuSys の戦略・AI スコアリング層を過去データで検証するバックテストフレームワークを実装する。
既存の `generate_signals(conn, target_date, holdings)` をそのまま呼び出し、エンジン側は「日付ループ＋擬似約定＋集計」に専念する薄いラッパー設計（アプローチ A）を採用する。

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
    --cash 10000000 --db path/to/kabusys.duckdb
```

---

## 実行フロー（1日のループ）

```
for each trading_day in calendar(start_date, end_date):

    1. 前日シグナルを当日 open 価格で約定
       → PortfolioSimulator.execute_orders(signals_prev, open_prices_today)
       → 約定価格 = open * (1 + slippage_rate)  for BUY
                    open * (1 - slippage_rate)  for SELL
       → 手数料を現金から差し引き（commission_rate × 約定金額）

    2. 当日終値で時価評価
       → PortfolioSimulator.mark_to_market(close_prices_today)
       → DailySnapshot を記録

    3. 翌日用シグナルを生成
       → generate_signals(conn, target_date=trading_day, holdings=positions)
       → signals テーブルへ書き込み（冪等）
```

---

## Look-ahead Bias 防止

| 処理 | 使うデータ | 根拠 |
|------|-----------|------|
| シグナル生成（day T） | `date < T` の価格・特徴量 | 既存の `generate_signals()` が SQL レベルで保証 |
| 約定（day T+1） | day T+1 の始値 | シグナルは常に翌営業日の始値で執行 |

`SimulatedClock` は `engine.py` のループ変数 `trading_day` がそのまま代替する。
既存コードが `target_date` 引数で設計されているため、clock オブジェクトの注入は不要。
`clock.py` は `SimulatedClock` を薄いデータクラスとして定義し、将来の拡張性のみ担保する。

---

## データ構造

```python
@dataclass
class DailySnapshot:
    date: date
    cash: float
    positions: dict[str, int]   # code → 株数
    portfolio_value: float      # cash + 時価評価額

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

**税金は対象外**（確定申告ルール・NISA・損失繰越が複雑なため）。手数料のみ適用し、README に明記する。

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

既存の `test_regime_detector.py` と同パターン（インメモリ DuckDB + フィクスチャでデータ挿入）を採用する。

| テスト | 検証内容 |
|--------|---------|
| 既知結果の検証 | 価格既知のシンプルな売買で損益が手計算と一致する |
| Look-ahead 不存在確認 | day T のシグナル生成が day T 以降のデータを参照しないことをアサート |
| スリッページ適用確認 | 約定価格 = open × (1 ± slippage_rate) を検証 |
| 手数料適用確認 | 現金残高が `約定金額 × commission_rate` 減少することを検証 |
| Max Drawdown 計算 | 既知の資産推移から期待 MDD を検証 |
| Sharpe Ratio 計算 | 既知のリターン列から期待 Sharpe を検証 |
| 冪等性 | 同一期間を2回実行しても結果が変わらない |

---

## 制約（CLAUDE.md 準拠）

- `datetime.today()` / `date.today()` をバックテストロジック内で参照しない
- シグナル生成は既存の `generate_signals()` を直接呼び出し、ロジックを重複実装しない
- AI・LLM は直接発注しない（Strategy 層経由のみ）
- `signal_queue` は本番専用。バックテストでは使用しない
