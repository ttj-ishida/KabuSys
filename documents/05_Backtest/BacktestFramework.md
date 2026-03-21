# Backtest Framework (バックテスト・検証基盤)

- 対象: AIスコア、クオンツ戦略のリサーチおよびバックテストパイプライン
- 版数: v2.0

---

## 1. 目的

システムに実装する「戦略（Strategy）」や「AIモデルのスコアリング」が、**「本当に利益を生む優位性があるか（Alpha）」**を過去のデータを用いて検証する枠組み。

「本番環境（Production）」と「テスト環境（Backtest）」のコードベース（ロジック）を完全に共通化し、バックテストで利益が出たのに本番で損をする「乖離（オーバーフィッティング等）」を最小限にとどめることを目的とする。

---

## 2. Research Environment ワークフロー

新しい戦略やAIスコアは、以下の厳格なステップを踏んで本番へ導入される。

1. **Research (探索・分析)**
   - Jupyter Notebook等でJ-Quantsのヒストリカルデータやニュース履歴を分析。
   - 特徴量の相関や、AIニューススコアの統計的優位性を仮説立て・探索。
2. **Backtest (ヒストリカル・シミュレーション)**
   - 過去数年分（Bull/Bearの両相場を含む期間）のデータに取引ロジックを流し込み、スリッページや売買手数料を考慮した詳細なパフォーマンス測定を実施。
3. **Forward Test (ペーパー取引 / シミュレーション実行)**
   - バックテストで合格したロジックを、本番と**全く同じExecution System**のまま「注文照会API等を用いた模擬環境」または「1株単位の超少額」でリアルタイム稼働させる。
   - ここで、APIの速度や、リアルタイムの気配値更新特有の遅延（レイテンシ）の影響を評価。
4. **Production (本番稼働)**
   - Forward Testで想定通りの乖離率に収まり、システム安定性が確認された場合のみ、通常のロット（資金）を投下して本番運用を開始。

---

## 3. レポート評価指標（Metrics）

バックテストの結果は、単なる「最終利益」だけでなく、いかに安定して資産を増やせるかというリスク調整後リターンで評価する。

| 指標 | 定義 | 合格ライン |
|------|------|-----------|
| **CAGR (年平均成長率)** | `(最終資産/初期資産)^(1/年数) - 1` | — |
| **Sharpe Ratio** | `年次化超過リターン / 年次化標準偏差`（無リスク金利=0） | ≥ 1.0（理想 1.5） |
| **Max Drawdown** | `max(1 - 評価額 / 過去ピーク)` | ≤ 20% |
| **Win Rate / Payoff Ratio** | 勝ちトレード数 / 全クローズトレード数、平均利益 / 平均損失 | — |

**税金は計算対象外**（確定申告ルール・NISA・損失繰越が複雑なため）。手数料のみ適用する。

---

## 4. ルックアヘッド・バイアス（未来情報漏洩）の完全防止策

バックテストにおける最大の罠は「その時点で知り得ない未来（翌日や来週）のデータを使って今日の売買判断をしてしまうこと」である。これをフレームワークレベルで厳粛に防ぐ。

### 4.1 財務情報・ニュースの反映タイミング

「決算発表日」や「大引け後（15:00以降）のニュース」のデータは、その日の取引が終わった後にしか市場に反映されない前提とする。これらがシグナル生成に使えるのは、厳密に「翌営業日の寄付き（または夜間バッチ）」からである。

### 4.2 本番用とバックテスト用クロック（時計）の共通化

`Strategy` 層などからはサーバーの現在時刻 (`datetime.now()`) を直接見ず、フレームワークから注入される `Current Simulated Time` インターフェースに依存するように設計する。
これにより、同じコードを時計の針だけ任意に進めてループ実行することで、未来のデータへの参照を物理的にブロックする。

実装上は `engine.py` のループ変数 `trading_day` がそのまま Simulated Time として機能する。
既存の `generate_signals(conn, target_date)` は引数で日付を受け取る設計のため、`datetime.now()` に依存しない。

| 処理 | 使うデータ | 根拠 |
|------|-----------|------|
| シグナル生成（day T） | `date < T` の価格・特徴量 | `generate_signals()` の SQL が `WHERE date = T` でバインド |
| SELL 判定（day T） | `date <= T` の prices_daily | `_generate_sell_signals()` の SQL が `WHERE date <= T` でバインド |
| 約定（day T+1） | day T+1 の始値 | シグナルは常に翌営業日の始値で執行 |

さらに、インメモリ DB には `end_date` 以降のデータを含まないため、物理的に未来参照が不可能。

### 4.3 スリッページと手数料の厳密なモデリング

シグナルが出た翌日の「始値（Open）」で約定すると仮定する。さらに、売買手数料を必ず差し引く設定をデフォルトとする。

| パラメータ | デフォルト値 | 説明 |
|-----------|------------|------|
| `slippage_rate` | 0.001 (0.1%) | BUY: `open × (1 + slippage_rate)` / SELL: `open × (1 - slippage_rate)` |
| `commission_rate` | 0.00055 (0.055%) | 国内証券の標準的な手数料率 |
| `max_position_pct` | 0.20 (20%) | 1銘柄あたりの最大ポートフォリオ比率（RiskManagement.md 準拠） |

---

## 5. モジュール構成

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

## 6. 公開 API

### `engine.py`

```python
def run_backtest(
    conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
    initial_cash: float = 10_000_000,
    slippage_rate: float = 0.001,
    commission_rate: float = 0.00055,
    max_position_pct: float = 0.20,
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
    --db path/to/kabusys.duckdb
```

**前提条件**: 指定 DB ファイルに `prices_daily`, `features`, `ai_scores`, `market_regime`, `market_calendar` が入力済みであること。

---

## 7. インメモリ DB 分離（本番 DB 汚染防止）

`generate_signals()` は `signals` テーブルに書き込み、`_generate_sell_signals()` は `positions` テーブルを読み取る。これらを本番 DB に直接書くと本番データを汚染する。

**方針**: バックテストは専用のインメモリ DuckDB を使用する。

```
_build_backtest_conn(source_conn, start_date, end_date):
  1. ":memory:" で新規 DuckDB を作成しスキーマを初期化
  2. source_conn から以下のデータをコピー:
     - prices_daily  (start_date - 300日 〜 end_date)
     - features      (同範囲)
     - ai_scores     (同範囲)
     - market_regime (同範囲)
     - market_calendar (全件)
  3. インメモリ conn を返す
```

---

## 8. 実行フロー（1日のループ）

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
          ※ shares = floor(alloc / (open * (1 + slippage_rate)))  for BUY
          ※ 約定価格 = open * (1 - slippage_rate)               for SELL

    2. positions テーブルに書き戻し（generate_signals の SELL 判定に必要）
       → _write_positions(bt_conn, trading_day,
                          simulator.positions, simulator.cost_basis)
          ※ DELETE WHERE date = trading_day → INSERT（冪等）
          ※ market_value は NULL（nullable カラム、SELL 判定では参照されない）

    3. 当日終値で時価評価・スナップショット記録
       → close_prices = _fetch_close_prices(bt_conn, trading_day)
       → simulator.mark_to_market(trading_day, close_prices)

    4. 翌日用シグナルを生成
       → generate_signals(bt_conn, target_date=trading_day)
          ※ 戻り値は int（書き込み件数）。シグナル内容は signals テーブルをクエリ

    5. 翌日の発注リストを組み立て（ポジションサイジング）
       → buy_signals  = SELECT code, signal_rank FROM signals
                         WHERE date = trading_day AND side = 'buy'
                         ORDER BY signal_rank
       → sell_signals = SELECT code FROM signals
                         WHERE date = trading_day AND side = 'sell'
       → prior_pv = simulator.history[-1].portfolio_value
                    if simulator.history else initial_cash
       → alloc = min(prior_pv * max_position_pct,
                     simulator.cash / len(buy_signals))   # buy なし時はスキップ
       → signals_prev = [{"code": s.code, "side": "buy", "alloc": alloc}
                          for s in buy_signals] +
                         [{"code": s.code, "side": "sell"}
                          for s in sell_signals]
```

---

## 9. データ構造

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
    cost_basis: dict[str, float]  # code → 平均取得単価
    history: list[DailySnapshot]
    trades: list[TradeRecord]

@dataclass
class BacktestMetrics:
    cagr: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    payoff_ratio: float
    total_trades: int
```
