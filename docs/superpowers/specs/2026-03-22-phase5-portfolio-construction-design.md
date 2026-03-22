# Phase 5 ポートフォリオ構築エンジン 設計仕様

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this spec.

**Goal:** シグナル生成後のポートフォリオ構築層を実装する。銘柄選定・資金配分・リスク制御を担う純粋関数モジュール群を `src/kabusys/portfolio/` に新設し、バックテストエンジン（`run_backtest`）および将来の本番執行系から共通利用できる設計とする。

**Architecture:** `generate_signals()` が出力した `signals` テーブルの BUY シグナルを入力とし、`portfolio_builder` → `position_sizing` → `risk_adjustment` の順に処理して最終的な発注株数を決定する。各モジュールは純粋関数（DB 参照なし、メモリ内計算のみ）とし、バックテストと本番の両方から再利用できる。

**Tech Stack:** Python 3.10+, DuckDB, J-Quants API（`/listed/info` エンドポイント）

**Related Issues:** #24, #25, #26, #27

---

## ファイル構成

### 新規作成

| ファイル | 責務 |
|---------|------|
| `src/kabusys/portfolio/__init__.py` | `build_portfolio` をエクスポート |
| `src/kabusys/portfolio/portfolio_builder.py` | 銘柄選定・配分重み計算 |
| `src/kabusys/portfolio/position_sizing.py` | 株数決定・リスク制限・単元株丸め |
| `src/kabusys/portfolio/risk_adjustment.py` | セクター集中制限・レジーム乗数 |
| `tests/test_portfolio_construction.py` | Phase 5 全体テスト |

### 変更

| ファイル | 変更内容 |
|---------|---------|
| `src/kabusys/data/schema.py` | `stocks` テーブル追加 |
| `src/kabusys/data/jquants_client.py` | `fetch_listed_info()` 追加 |
| `src/kabusys/backtest/engine.py` | `run_backtest` をポートフォリオモジュール使用に更新 |
| `src/kabusys/backtest/simulator.py` | `execute_orders` のシグネチャを `alloc` → `shares` に変更 |
| `tests/test_backtest_framework.py` | シグネチャ変更に伴う既存 22 テストの更新 |

---

## データフロー

```
generate_signals(conn, date)
  → signals テーブル（BUY ranked + SELL）
    → select_candidates()        # 上位N銘柄選定
      → apply_sector_cap()       # セクター30%上限チェック
        → calc_*_weights()       # 配分重み計算（equal / score / risk_based）
          → calc_position_sizes() # 株数決定 + リスク制限 + 単元株丸め
            → apply_regime_multiplier() # Bull/Neutral/Bear 調整
              → {code: shares}   # 最終発注株数
```

---

## モジュール詳細

### portfolio_builder.py

```python
def select_candidates(
    buy_signals: list[dict],   # {"code": str, "signal_rank": int, "score": float}
    max_positions: int = 10,
) -> list[dict]:
    """スコア順で上位 max_positions 銘柄を選定する（最大 15）。"""

def calc_equal_weights(candidates: list[dict]) -> dict[str, float]:
    """等金額配分。各銘柄に 1/N の重みを返す。"""

def calc_score_weights(candidates: list[dict]) -> dict[str, float]:
    """スコア加重配分。weight_i = score_i / sum(scores)。"""
```

### position_sizing.py

```python
def calc_position_sizes(
    weights: dict[str, float],          # {code: weight}（equal / score 方式）
    portfolio_value: float,
    cash: float,                         # レジーム乗数適用後の利用可能現金
    current_positions: dict[str, int],   # 既存保有 {code: shares}
    open_prices: dict[str, float],       # {code: price}
    allocation_method: str = "risk_based",  # "equal" | "score" | "risk_based"
    risk_pct: float = 0.005,            # 許容リスク率（risk_based 時）
    stop_loss_pct: float = 0.08,        # 損切り率（risk_based 時）
    max_position_pct: float = 0.10,     # 1銘柄上限
    max_utilization: float = 0.70,      # 投下資金上限
    lot_size: int = 100,
) -> dict[str, int]:                    # {code: shares_to_buy}
    """
    allocation_method 別の株数計算:

    "risk_based":
        shares = floor(portfolio_value * risk_pct / (price * stop_loss_pct))
        上限: floor(portfolio_value * max_position_pct / price)

    "equal" / "score":
        alloc = portfolio_value * weight[code] * max_utilization
        shares = floor(alloc / price)
        上限: floor(portfolio_value * max_position_pct / price)

    共通後処理:
        - lot_size (100株) 単位に切り捨て
        - 既存保有分を考慮（追加購入分のみ）
        - 総投下資金が cash を超えないよう最終調整
    """
```

### risk_adjustment.py

```python
def apply_sector_cap(
    candidates: list[dict],             # [{code, weight}, ...]
    sector_map: dict[str, str],         # {code: sector}
    portfolio_value: float,
    current_positions: dict[str, int],
    open_prices: dict[str, float],
    max_sector_pct: float = 0.30,
) -> list[dict]:
    """
    同一セクターの既存保有 + 新規 BUY の合計時価が
    portfolio_value × max_sector_pct を超える銘柄を除外する。
    sector_map にコードが存在しない場合は "unknown" 扱いでスキップ（制限なし）。
    """

def calc_regime_multiplier(regime: str) -> float:
    """Bull → 1.0 / Neutral → 0.7 / Bear → 0.3。未知レジームは 1.0。"""
```

---

## stocks テーブル（schema.py 追加）

```sql
CREATE TABLE IF NOT EXISTS stocks (
    code        VARCHAR NOT NULL,
    name        VARCHAR,
    market      VARCHAR,   -- Prime / Standard / Growth
    sector      VARCHAR,   -- TSE 33業種名
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (code)
);
```

J-Quants `/listed/info` から毎日 UPSERT する。バックテスト用 `_build_backtest_conn` にも全件コピーを追加（日付フィルタ不要）。

---

## jquants_client.py 追加

```python
def fetch_listed_info(self) -> list[dict]:
    """
    GET /listed/info を呼び出し、全上場銘柄の
    {Code, CompanyName, Market, Sector33CodeName} を返す。
    """
```

ETL パイプラインから呼ばれ、`stocks` テーブルに UPSERT する。

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
    max_position_pct: float = 0.10,
    max_utilization: float = 0.70,
    max_positions: int = 10,
    allocation_method: str = "risk_based",   # "equal" | "score" | "risk_based"
    risk_pct: float = 0.005,
    stop_loss_pct: float = 0.08,
) -> BacktestResult:
```

ループ内の Step 5（発注リスト組み立て）を portfolio モジュール呼び出しに置き換える。

---

## execute_orders シグネチャ変更

```python
# 変更前（alloc: 金額）
{"code": "1234", "side": "buy", "alloc": 1_000_000.0}

# 変更後（shares: 株数）
{"code": "1234", "side": "buy", "shares": 200}
```

`PortfolioSimulator._execute_buy` は `alloc` と `floor` 計算を廃止し、渡された `shares` をそのまま使用する。スリッページ・手数料の計算ロジックは維持する。

---

## エラーハンドリング

| 状況 | 挙動 |
|------|------|
| `stocks` テーブルが空 / セクター不明銘柄 | セクター制限スキップ（`"unknown"` 扱い） |
| `market_regime` にデータなし | `multiplier = 1.0`（Bull 相当）でフォールバック、WARNING ログ |
| 全候補がセクター上限で除外 | BUY シグナルなし（安全側） |
| `lot_size=100` で `shares < 100` | 0株 → スキップ |
| `open_prices` に価格なし | 該当銘柄スキップ |

---

## テスト仕様

### test_portfolio_construction.py（新規）

**portfolio_builder:**
- `select_candidates`: スコア順上位 N 銘柄が選ばれる
- `select_candidates`: 候補数 < max_positions なら全件返す
- `calc_equal_weights`: 重みの合計が 1.0
- `calc_score_weights`: スコア比例で重みが割り当てられる

**position_sizing:**
- `risk_based`: 0.5% リスク・8% 損切りで株数が計算される
- `max_position_pct=0.10` が守られる
- `max_utilization=0.70` が守られる
- 100株単位に切り捨てられる
- cash 不足時は購入可能範囲に収まる

**risk_adjustment:**
- セクター 30% 超の銘柄が除外される
- セクター不明銘柄は制限なく通過する
- `calc_regime_multiplier`: Bull=1.0 / Neutral=0.7 / Bear=0.3

**統合:**
- Bear レジームで投下資金が 30% に抑制される
- 同一セクター集中時に上限が機能する
- `allocation_method="equal"` で等金額配分になる
- `allocation_method="score"` でスコア比例配分になる
- `allocation_method="risk_based"` でリスクベース配分になる

### test_backtest_framework.py（既存 22 本更新）
- `execute_orders` の `alloc` → `shares` シグネチャ変更に対応
- `run_backtest` の新パラメータに対応

---

## 実装順序

1. `stocks` テーブル追加（schema.py）+ `fetch_listed_info`（jquants_client.py）
2. `portfolio_builder.py` 実装 + テスト
3. `position_sizing.py` 実装 + テスト
4. `risk_adjustment.py` 実装 + テスト
5. `engine.py` + `simulator.py` 更新（alloc→shares、run_backtest 新パラメータ）
6. `test_backtest_framework.py` 既存テスト更新
