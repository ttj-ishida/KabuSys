# Phase 5 ポートフォリオ構築エンジン 設計仕様

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this spec.

**Goal:** シグナル生成後のポートフォリオ構築層を実装する。銘柄選定・資金配分・リスク制御を担う純粋関数モジュール群を `src/kabusys/portfolio/` に新設し、バックテストエンジン（`run_backtest`）および将来の本番執行系から共通利用できる設計とする。

**Architecture:** `generate_signals()` が出力した `signals` テーブルの BUY シグナルを入力とし、`select_candidates` → `apply_sector_cap` → `calc_*_weights` → `calc_position_sizes` の順に処理して最終的な発注株数を決定する。各モジュールは純粋関数（DB 参照なし、メモリ内計算のみ）とし、バックテストと本番の両方から再利用できる。

**Tech Stack:** Python 3.10+, DuckDB, J-Quants API（`/listed/info` エンドポイント）

**Related Issues:** #24, #25, #26, #27

---

## ⚠️ 破壊的変更の明示

### `execute_orders` のシグネチャ変更（`alloc` → `shares`）

Phase 4 で実装した `PortfolioSimulator.execute_orders` の BUY シグナル形式を変更する。

```python
# Phase 4 まで（金額指定）
{"code": "1234", "side": "buy", "alloc": 1_000_000.0}

# Phase 5 以降（株数指定）
{"code": "1234", "side": "buy", "shares": 200}
```

`_execute_buy` 内の `math.floor(alloc / entry_price)` によるシェア数計算を廃止し、渡された `shares` をそのまま使用する。スリッページ・手数料の計算ロジックは維持する。

**既存テスト更新ガイド（主要ケース）:**

| テスト名 | 変更前 | 変更後 |
|---------|--------|--------|
| `test_simulator_buy_reduces_cash` | `alloc=200_000` → 内部で `floor(200000/1.001/entry)` 計算 | `shares=100`（事前計算した株数を渡す）、cash減少額を `100 * entry_price * (1 + slippage) * (1 + commission)` で検証 |
| `test_simulator_buy_slippage` | `alloc=100_000` → slippage 後価格で floor | `shares=50` を渡し、slippage 後価格での cash 減少を検証 |
| `test_simulator_insufficient_cash_skips_buy` | 現金不足時に `execute_orders` 内でスキップ | `calc_position_sizes` が `shares=0` を返すため、`execute_orders` には `shares > 0` の銘柄しか渡らない。テストは `calc_position_sizes` 側に移動 |

### `max_position_pct` デフォルト値の変更

Phase 4 の `run_backtest` は `max_position_pct=0.20` をデフォルトとしていた。Phase 5 で設計書（RiskManagement.md Section 4.2、StrategyModel.md Section 6.1）の規定値である **`0.10`（10%）に修正**する。

Phase 4 のテスト `test_run_backtest_max_position_pct` は `max_position_pct=0.10` を明示的に渡していたため影響なし。ただし `run_backtest` をデフォルト引数のまま呼んでいる箇所は挙動が変わるため注意。

---

## ファイル構成

### 新規作成

| ファイル | 責務 |
|---------|------|
| `src/kabusys/portfolio/__init__.py` | `select_candidates`, `calc_equal_weights`, `calc_score_weights`, `calc_position_sizes`, `apply_sector_cap`, `calc_regime_multiplier` をエクスポート |
| `src/kabusys/portfolio/portfolio_builder.py` | 銘柄選定・配分重み計算 |
| `src/kabusys/portfolio/position_sizing.py` | 株数決定・リスク制限・単元株丸め |
| `src/kabusys/portfolio/risk_adjustment.py` | セクター集中制限・レジーム乗数 |
| `tests/test_portfolio_construction.py` | Phase 5 全体テスト |

### 変更

| ファイル | 変更内容 |
|---------|---------|
| `src/kabusys/data/schema.py` | `stocks` テーブル追加 |
| `src/kabusys/data/jquants_client.py` | `fetch_listed_info()` 追加 |
| `src/kabusys/backtest/engine.py` | `run_backtest` をポートフォリオモジュール使用に更新。`_read_day_signals` に `score` 列を追加。`_fetch_regime` ヘルパー追加。`_fetch_sector_map` ヘルパー追加。 |
| `src/kabusys/backtest/simulator.py` | `execute_orders`・`_execute_buy` の `alloc` → `shares` 変更 |
| `tests/test_backtest_framework.py` | シグネチャ変更に伴う既存 22 テストの更新（上記ガイド参照） |

---

## データフロー

```
generate_signals(conn, date)
  → signals テーブル（BUY ranked + SELL）

select_candidates(buy_signals, max_positions)
  → candidates: [{code, score, rank}, ...]      ← 重みなし

apply_sector_cap(candidates, sector_map, ...)
  → filtered_candidates: [{code, score, rank}, ...]   ← 重みなし・セクター上限適用済み

calc_equal_weights(filtered_candidates)          ← allocation_method に応じて選択
  OR calc_score_weights(filtered_candidates)
  → weights: {code: float}

multiplier = calc_regime_multiplier(regime)
available_cash = cash * multiplier

calc_position_sizes(weights, portfolio_value, available_cash, ...)
  → {code: shares_to_buy}   ← 最終発注株数
```

**注意:** `apply_sector_cap` は `select_candidates` の出力（重みなし）を受け取る。重み計算は セクターフィルタ後に行う。

---

## モジュール詳細

### portfolio_builder.py

```python
def select_candidates(
    buy_signals: list[dict],   # {"code": str, "signal_rank": int, "score": float}
    max_positions: int = 10,   # PortfolioConstruction.md 推奨: 5〜15
) -> list[dict]:
    """スコア降順で上位 max_positions 件を返す。
    max_positions に上限はなし（呼び出し側が PortfolioConstruction.md の推奨範囲 5〜15 を守ること）。
    """

def calc_equal_weights(candidates: list[dict]) -> dict[str, float]:
    """等金額配分。各銘柄に 1/N の重みを返す。candidates が空なら {}。"""

def calc_score_weights(candidates: list[dict]) -> dict[str, float]:
    """スコア加重配分。weight_i = score_i / sum(scores)。
    全銘柄の score が 0.0 の場合は等金額配分にフォールバックし WARNING を出す。
    """
```

### position_sizing.py

```python
def calc_position_sizes(
    weights: dict[str, float],          # {code: weight}（equal / score 方式で使用）
    candidates: list[dict],             # [{code, score}, ...]（risk_based 方式で使用）
    portfolio_value: float,             # 総資産（円）
    available_cash: float,              # レジーム乗数適用後の利用可能現金
    current_positions: dict[str, int],  # 既存保有 {code: shares}
    open_prices: dict[str, float],      # {code: price}
    allocation_method: str = "risk_based",  # "equal" | "score" | "risk_based"
    risk_pct: float = 0.005,           # 許容リスク率（risk_based 時）
    stop_loss_pct: float = 0.08,       # 損切り率（risk_based 時）
    max_position_pct: float = 0.10,    # 1銘柄上限（総資産比）
    max_utilization: float = 0.70,     # 投下資金上限（総資産比）
    lot_size: int = 100,
) -> dict[str, int]:                   # {code: shares_to_buy}
    """
    allocation_method 別の株数計算:

    "risk_based":
        per_stock_shares = floor(portfolio_value * risk_pct / (price * stop_loss_pct))
        上限: floor(portfolio_value * max_position_pct / price)

    "equal" / "score":
        alloc_i = portfolio_value * weights[code] * max_utilization
        per_stock_shares = floor(alloc_i / price)
        上限: floor(portfolio_value * max_position_pct / price)

    共通後処理（全 allocation_method 共通）:
        1. lot_size (100株) 単位に切り捨て
        2. 既存保有分を考慮（追加購入分のみ: new_shares = max(0, target - current_positions[code])）
        3. 総投下資金の上限チェック（max_utilization 適用）:
           - 全銘柄の (shares * price) 合計が available_cash を超える場合、
             各銘柄の shares を available_cash / total_cost の比率でスケールダウン
             してから再度 lot_size 単位に切り捨て
    """
```

### risk_adjustment.py

```python
def apply_sector_cap(
    candidates: list[dict],             # [{code, score, rank}, ...] ← 重みなし
    sector_map: dict[str, str],         # {code: sector}
    portfolio_value: float,
    current_positions: dict[str, int],  # 既存保有 {code: shares}
    open_prices: dict[str, float],
    max_sector_pct: float = 0.30,
) -> list[dict]:
    """
    同一セクターの既存保有時価が portfolio_value × max_sector_pct を超える場合、
    そのセクターの新規 BUY 候補を除外する。
    sector_map にコードが存在しない（セクター不明）場合は "unknown" 扱いとし、
    "unknown" セクターには max_sector_pct を適用しない（制限なし・除外しない）。
    戻り値は入力と同じ [{code, score, rank}] 形式。
    """

def calc_regime_multiplier(regime: str) -> float:
    """
    市場レジームに応じた投下資金乗数を返す。
    market_regime.regime_label は小文字で格納される（regime_detector.py 実装準拠）。
    "bull" → 1.0 / "neutral" → 0.7 / "bear" → 0.3 / その他（未知）→ 1.0（フォールバック）

    【重要】Bear レジームで BUY シグナルが生成されない理由:
    generate_signals() はレジームが Bear の場合、BUY シグナルを一切生成しない
    （StrategyModel.md Section 5.1 の「Bear 時は新規買いエントリー不可」ルールを
    signal_generator.py が実装済み）。
    したがって multiplier=0.3 は signal_generator が BUY を出す Neutral 等の
    「緩やかな縮小局面」向けの追加セーフガードであり、Bear での BUY を許容するものではない。
    """
```

---

## stocks テーブル（schema.py 追加）

```sql
CREATE TABLE IF NOT EXISTS stocks (
    code        VARCHAR NOT NULL,
    name        VARCHAR,
    market      VARCHAR,   -- 'Prime' | 'Standard' | 'Growth'（MarketCode から変換）
    sector      VARCHAR,   -- TSE 33業種名（Sector33CodeName）
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (code)
);
```

---

## jquants_client.py 追加

```python
def fetch_listed_info(id_token: str | None = None) -> list[dict]:
    """
    GET /listed/info を呼び出し、全上場銘柄情報を返す。

    J-Quants API レスポンスフィールドと stocks テーブルのマッピング:
        API "Code"            → stocks.code
        API "CompanyName"     → stocks.name
        API "MarketCode"      → stocks.market（変換: "0111"→"Prime", "0121"→"Standard", "0131"→"Growth", その他→"Other"）
        API "Sector33CodeName"→ stocks.sector

    Returns:
        [{"code": str, "name": str, "market": str, "sector": str}, ...]
    """
```

ETL パイプラインから呼ばれ、`stocks` テーブルに INSERT OR REPLACE で UPSERT する。

---

## run_backtest 更新後シグネチャ

```python
def run_backtest(
    conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
    initial_cash: float = 10_000_000,
    slippage_rate: float = 0.001,
    commission_rate: float = 0.00055,
    max_position_pct: float = 0.10,      # Phase 4 の 0.20 から変更（設計書準拠）
    max_utilization: float = 0.70,
    max_positions: int = 10,
    allocation_method: str = "risk_based",   # "equal" | "score" | "risk_based"
    risk_pct: float = 0.005,
    stop_loss_pct: float = 0.08,
) -> BacktestResult:
```

**`_read_day_signals` の更新（`score` 列追加）:**

```python
# 変更前
buy_rows = conn.execute(
    "SELECT code, signal_rank FROM signals WHERE date = ? AND side = 'buy' ORDER BY signal_rank",
    [trading_day],
).fetchall()
buy_signals = [{"code": row[0], "signal_rank": row[1]} for row in buy_rows]

# 変更後（score を追加）
buy_rows = conn.execute(
    "SELECT code, signal_rank, score FROM signals WHERE date = ? AND side = 'buy' ORDER BY signal_rank",
    [trading_day],
).fetchall()
buy_signals = [{"code": row[0], "signal_rank": row[1], "score": row[2]} for row in buy_rows]
```

**ループ内の変更点（Step 5）:**

```python
# sector_map はバックテスト開始前に一度だけ取得（銘柄のセクターは日次変化しない）
sector_map = _fetch_sector_map(bt_conn)   # {code: sector}

for trading_day in trading_days:
    # ... Steps 1-4 は変更なし ...

    # Step 5: ポートフォリオ構築（Phase 5 モジュール使用）
    buy_signals, sell_signals = _read_day_signals(bt_conn, trading_day)
    regime = _fetch_regime(bt_conn, trading_day)   # market_regime テーブル参照
    multiplier = calc_regime_multiplier(regime)
    prior_pv = simulator.history[-1].portfolio_value if simulator.history else initial_cash

    candidates = select_candidates(buy_signals, max_positions)
    candidates = apply_sector_cap(
        candidates, sector_map, prior_pv, simulator.positions, open_prices
    )

    if allocation_method == "equal":
        weights = calc_equal_weights(candidates)
    elif allocation_method == "score":
        weights = calc_score_weights(candidates)
    else:
        weights = {}   # risk_based は weights 不使用

    sized = calc_position_sizes(
        weights=weights,
        candidates=candidates,
        portfolio_value=prior_pv,
        available_cash=simulator.cash * multiplier,
        current_positions=simulator.positions,
        open_prices=open_prices,
        allocation_method=allocation_method,
        risk_pct=risk_pct,
        stop_loss_pct=stop_loss_pct,
        max_position_pct=max_position_pct,
        max_utilization=max_utilization,
    )

    signals_prev = [
        {"code": code, "side": "buy", "shares": shares}
        for code, shares in sized.items() if shares > 0
    ] + [{"code": s["code"], "side": "sell"} for s in sell_signals]
```

**`_fetch_sector_map` ヘルパー（engine.py に追加）:**

```python
def _fetch_sector_map(conn: duckdb.DuckDBPyConnection) -> dict[str, str]:
    """stocks テーブルから {code: sector} を返す。テーブルが空なら {}。"""
    rows = conn.execute("SELECT code, sector FROM stocks WHERE sector IS NOT NULL").fetchall()
    return {code: sector for code, sector in rows}
```

**`_fetch_regime` ヘルパー（engine.py に追加）:**

```python
def _fetch_regime(conn: duckdb.DuckDBPyConnection, trading_day: date) -> str:
    """market_regime テーブルから当日レジームを返す。データなしなら 'Bull'（フォールバック）。
    schema.py の market_regime テーブルのレジーム列名は `regime_label`。
    """
    row = conn.execute(
        "SELECT regime_label FROM market_regime WHERE date = ?", [trading_day]
    ).fetchone()
    if row is None:
        logger.warning("_fetch_regime: %s のレジームが取得できません。'Bull' でフォールバック。", trading_day)
        return "Bull"
    return row[0]
```

---

## _build_backtest_conn への stocks テーブル追加

```python
# 既存の date_filtered_tables に加え、stocks は全件コピー（日付フィルタなし）
try:
    rows = source_conn.execute("SELECT * FROM stocks").fetchall()
    if rows:
        # ... 既存の market_calendar コピーと同じパターンで INSERT ...
except Exception as exc:
    logger.warning("_build_backtest_conn: stocks のコピーをスキップ: %s", exc)
```

---

## エラーハンドリング

| 状況 | 挙動 |
|------|------|
| `stocks` テーブルが空 / セクター不明銘柄 | セクター制限スキップ（`"unknown"` 扱い、制限なし） |
| `market_regime` にデータなし | `multiplier = 1.0`（Bull 相当）でフォールバック、WARNING ログ |
| 全候補がセクター上限で除外 | BUY シグナルなし（安全側） |
| `lot_size=100` で `shares < 100` | 0株 → signals_prev に含めない |
| `open_prices` に価格なし | 該当銘柄スキップ |
| `calc_score_weights` で全スコアが 0.0 | 等金額配分にフォールバック + WARNING ログ |
| `risk_based` で総投下資金 > available_cash | 比率スケールダウン後、lot_size 単位に再切り捨て |

---

## テスト仕様

### test_portfolio_construction.py（新規）

**portfolio_builder:**
- `select_candidates`: スコア順上位 N 銘柄が選ばれる
- `select_candidates`: 候補数 ≤ max_positions なら全件返す
- `calc_equal_weights`: 重みの合計が 1.0
- `calc_score_weights`: スコア比例で重みが割り当てられる
- `calc_score_weights`: 全スコア 0.0 のとき等金額配分にフォールバックする

**position_sizing:**
- `risk_based`: 0.5% リスク・8% 損切りで株数が計算される
- `max_position_pct=0.10` が守られる
- `max_utilization=0.70` が守られる（risk_based でも aggregate cap が効く）
- 100株単位に切り捨てられる
- available_cash 不足時はスケールダウンされる

**risk_adjustment:**
- セクター 30% 超の銘柄が除外される
- セクター不明銘柄は制限なく通過する
- `calc_regime_multiplier`: "bull"=1.0 / "neutral"=0.7 / "bear"=0.3 / 未知=1.0

**統合:**
- "neutral" レジームで available_cash が 70% に抑制される
- 同一セクター集中時に上限が機能する
- `allocation_method="equal"` で等金額配分になる
- `allocation_method="score"` でスコア比例配分になる
- `allocation_method="risk_based"` でリスクベース配分になる

### test_backtest_framework.py（既存 22 本更新）
- `execute_orders` の `alloc` → `shares` シグネチャ変更に対応（上記ガイド参照）
- `run_backtest` の新パラメータ（`allocation_method`, `max_positions` 等）に対応
- `max_position_pct` デフォルト変更（0.20→0.10）の影響確認

---

## 実装順序

1. `stocks` テーブル追加（schema.py）+ `fetch_listed_info`（jquants_client.py）
2. `portfolio_builder.py` 実装 + テスト
3. `position_sizing.py` 実装 + テスト
4. `risk_adjustment.py` 実装 + テスト
   - ※ Steps 2-4 は Step 1 と並行して進めても可（portfolio モジュールは DB 非依存）
5. `simulator.py` 更新（`alloc` → `shares`）+ 既存テスト更新
6. `engine.py` 更新（`run_backtest` 新シグネチャ・portfolio モジュール統合）
7. 全テスト実行・回帰確認
