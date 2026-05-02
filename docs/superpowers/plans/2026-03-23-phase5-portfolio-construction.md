# Phase 5 ポートフォリオ構築エンジン Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `src/kabusys/portfolio/` に銘柄選定・資金配分・リスク制御の純粋関数モジュール群を新設し、`run_backtest` をポートフォリオ構築モジュール経由に更新する。

**Architecture:** `generate_signals()` → `select_candidates` → `apply_sector_cap` → `calc_*_weights` → `calc_position_sizes` → `execute_orders(shares=N)` の順に処理する。各モジュールは DB 非依存の純粋関数とし、バックテストと本番の両方から再利用できる。`stocks` テーブルをスキーマに追加し、J-Quants `/listed/info` からセクター情報を取得する。

**Tech Stack:** Python 3.10+, DuckDB, pytest, 標準ライブラリのみ（新規外部依存なし）

**Related Issues:** #24, #25, #26, #27

**Spec:** `docs/superpowers/specs/2026-03-22-phase5-portfolio-construction-design.md`

---

## ⚠️ 破壊的変更サマリー

| 変更 | 影響 |
|------|------|
| `execute_orders` の BUY シグナル: `alloc` → `shares` | `test_backtest_framework.py` の simulator テスト 4 本 |
| `run_backtest` の `max_position_pct` デフォルト: 0.20 → 0.10 | デフォルトで呼ぶ統合テスト |
| `run_backtest` 新パラメータ追加 | 後方互換あり（デフォルト値あり） |

---

## ファイル構成

### 新規作成

| ファイル | 責務 |
|---------|------|
| `src/kabusys/portfolio/__init__.py` | 6関数をエクスポート |
| `src/kabusys/portfolio/portfolio_builder.py` | `select_candidates`, `calc_equal_weights`, `calc_score_weights` |
| `src/kabusys/portfolio/position_sizing.py` | `calc_position_sizes`（3 allocation_method 対応） |
| `src/kabusys/portfolio/risk_adjustment.py` | `apply_sector_cap`, `calc_regime_multiplier` |
| `tests/test_portfolio_construction.py` | Phase 5 全テスト |

### 変更

| ファイル | 変更内容 |
|---------|---------|
| `src/kabusys/data/schema.py` | `_STOCKS` DDL 追加、`_ALL_DDL` に追加 |
| `src/kabusys/data/jquants_client.py` | `fetch_listed_info()` 追加 |
| `src/kabusys/backtest/simulator.py` | `execute_orders`/`_execute_buy` の `alloc` → `shares` |
| `src/kabusys/backtest/engine.py` | `run_backtest` 新シグネチャ、`_read_day_signals` に `score` 追加、`_fetch_regime`/`_fetch_sector_map` ヘルパー追加、`_build_backtest_conn` に `stocks` コピー追加 |
| `tests/test_backtest_framework.py` | `alloc` → `shares` 変換、`run_backtest` 新パラメータ対応 |

---

## Task 1: stocks テーブル追加 + fetch_listed_info

**Files:**
- Modify: `src/kabusys/data/schema.py`
- Modify: `src/kabusys/data/jquants_client.py`
- Test: `tests/test_portfolio_construction.py`（新規作成、最初のテストのみ）

作業ディレクトリ: `C:\Users\tetsu\Projects\KabuSys\.worktrees\phase4-backtest`

- [ ] **Step 1: テストファイルを作成し、stocks テーブルの存在確認テストを書く**

```python
# tests/test_portfolio_construction.py
"""Phase 5 ポートフォリオ構築エンジン テスト"""
from __future__ import annotations

import pytest
from kabusys.data.schema import init_schema


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Task 1: schema.py — stocks テーブル
# ---------------------------------------------------------------------------

def test_stocks_table_exists(conn):
    """stocks テーブルが init_schema で作成される。"""
    row = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'stocks'"
    ).fetchone()
    assert row[0] == 1


def test_stocks_table_insert(conn):
    """stocks テーブルに INSERT できる。"""
    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["1234", "テスト株式会社", "Prime", "電気機器"],
    )
    row = conn.execute("SELECT code, sector FROM stocks WHERE code = '1234'").fetchone()
    assert row is not None
    assert row[0] == "1234"
    assert row[1] == "電気機器"


def test_stocks_table_upsert(conn):
    """stocks テーブルは PRIMARY KEY (code) で UPSERT できる（冪等）。"""
    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["1234", "旧名称", "Prime", "電気機器"],
    )
    conn.execute(
        """
        INSERT INTO stocks (code, name, market, sector)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (code) DO UPDATE SET
            name   = excluded.name,
            market = excluded.market,
            sector = excluded.sector
        """,
        ["1234", "新名称", "Standard", "機械"],
    )
    row = conn.execute("SELECT name, market, sector FROM stocks WHERE code = '1234'").fetchone()
    assert row[0] == "新名称"
    assert row[1] == "Standard"
    assert row[2] == "機械"
```

- [ ] **Step 2: テストを実行して FAIL を確認**

```
cd C:\Users\tetsu\Projects\KabuSys\.worktrees\phase4-backtest
python -m pytest tests/test_portfolio_construction.py::test_stocks_table_exists -v
```

Expected: `FAILED` — `stocks` テーブルが存在しないため

- [ ] **Step 3: schema.py に stocks テーブル DDL を追加**

`src/kabusys/data/schema.py` の `# ---- Feature Layer` の手前（`_FEATURES` の前）に追加：

```python
# ---- Master Data Layer -----------------------------------------------------

_STOCKS = """
CREATE TABLE IF NOT EXISTS stocks (
    code        VARCHAR     NOT NULL,
    name        VARCHAR,
    market      VARCHAR,
    sector      VARCHAR,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (code)
)
"""
```

`_ALL_DDL` リストの `_FEATURES` の前に `_STOCKS` を追加：

```python
_ALL_DDL: list[str] = [
    # Raw
    _RAW_PRICES,
    _RAW_FINANCIALS,
    _RAW_NEWS,
    _RAW_EXECUTIONS,
    # Processed
    _PRICES_DAILY,
    _MARKET_CALENDAR,
    _FUNDAMENTALS,
    _NEWS_ARTICLES,
    _NEWS_SYMBOLS,
    # Master
    _STOCKS,
    # Feature
    _FEATURES,
    _AI_SCORES,
    _MARKET_REGIME,
    # Execution
    _SIGNALS,
    _SIGNAL_QUEUE,
    _PORTFOLIO_TARGETS,
    _ORDERS,
    _TRADES,
    _POSITIONS,
    _PORTFOLIO_PERFORMANCE,
]
```

- [ ] **Step 4: テストを実行して PASS を確認**

```
python -m pytest tests/test_portfolio_construction.py -v
```

Expected: 3 passed

- [ ] **Step 5: fetch_listed_info のテストを追加**

`tests/test_portfolio_construction.py` に追記：

```python
# ---------------------------------------------------------------------------
# Task 1: jquants_client.py — fetch_listed_info のマッピングテスト
# ---------------------------------------------------------------------------

def test_fetch_listed_info_field_mapping():
    """fetch_listed_info が J-Quants API レスポンスを stocks スキーマにマッピングする。"""
    from unittest.mock import patch
    from kabusys.data.jquants_client import fetch_listed_info

    mock_response = {
        "info": [
            {
                "Code": "13010",
                "CompanyName": "テスト会社",
                "MarketCode": "0111",
                "Sector33CodeName": "電気機器",
            },
            {
                "Code": "20050",
                "CompanyName": "サンプル工業",
                "MarketCode": "0121",
                "Sector33CodeName": "機械",
            },
            {
                "Code": "30090",
                "CompanyName": "グロース社",
                "MarketCode": "0131",
                "Sector33CodeName": "情報通信業",
            },
            {
                "Code": "99999",
                "CompanyName": "その他",
                "MarketCode": "9999",
                "Sector33CodeName": "その他",
            },
        ]
    }

    with patch("kabusys.data.jquants_client._request", return_value=mock_response):
        result = fetch_listed_info()

    assert len(result) == 4
    # MarketCode → market 変換確認
    by_code = {r["code"]: r for r in result}
    assert by_code["13010"]["market"] == "Prime"
    assert by_code["20050"]["market"] == "Standard"
    assert by_code["30090"]["market"] == "Growth"
    assert by_code["99999"]["market"] == "Other"
    # name, sector
    assert by_code["13010"]["name"] == "テスト会社"
    assert by_code["13010"]["sector"] == "電気機器"


def test_fetch_listed_info_missing_fields_skipped():
    """Code が欠損するレコードはスキップされる。"""
    from unittest.mock import patch
    from kabusys.data.jquants_client import fetch_listed_info

    mock_response = {
        "info": [
            {"Code": "1234", "CompanyName": "正常", "MarketCode": "0111", "Sector33CodeName": "電気機器"},
            {"Code": "", "CompanyName": "コード欠損", "MarketCode": "0111", "Sector33CodeName": ""},
            {"CompanyName": "コードなし", "MarketCode": "0111", "Sector33CodeName": ""},
        ]
    }

    with patch("kabusys.data.jquants_client._request", return_value=mock_response):
        result = fetch_listed_info()

    assert len(result) == 1
    assert result[0]["code"] == "1234"
```

- [ ] **Step 6: テストを実行して FAIL を確認**

```
python -m pytest tests/test_portfolio_construction.py::test_fetch_listed_info_field_mapping -v
```

Expected: `FAILED` — `fetch_listed_info` 未実装

- [ ] **Step 7: jquants_client.py に fetch_listed_info を追加**

`src/kabusys/data/jquants_client.py` の `save_market_calendar` の後（`_to_float` の前）に追加：

```python
def fetch_listed_info(id_token: str | None = None) -> list[dict[str, Any]]:
    """全上場銘柄情報を GET /listed/info から取得する。

    J-Quants API フィールドと stocks テーブルのマッピング:
        "Code"             → code
        "CompanyName"      → name
        "MarketCode"       → market（"0111"→"Prime", "0121"→"Standard", "0131"→"Growth", その他→"Other"）
        "Sector33CodeName" → sector

    Args:
        id_token: 認証トークン。省略時はモジュールキャッシュを使用。

    Returns:
        [{"code": str, "name": str, "market": str, "sector": str}, ...]
        Code が欠損するレコードはスキップ。
    """
    _MARKET_CODE_MAP: dict[str, str] = {
        "0111": "Prime",
        "0121": "Standard",
        "0131": "Growth",
    }

    data = _request("/listed/info", id_token=id_token)
    records = data.get("info", [])

    result: list[dict[str, Any]] = []
    skipped = 0
    for r in records:
        code = str(r.get("Code") or "").strip()
        if not code:
            skipped += 1
            continue
        market_code = str(r.get("MarketCode") or "")
        result.append({
            "code": code,
            "name": str(r.get("CompanyName") or ""),
            "market": _MARKET_CODE_MAP.get(market_code, "Other"),
            "sector": str(r.get("Sector33CodeName") or ""),
        })

    if skipped:
        logger.warning("fetch_listed_info: %d 件を Code 欠損によりスキップ", skipped)
    logger.info("fetch_listed_info: %d 件取得", len(result))
    return result
```

- [ ] **Step 8: テストを実行して PASS を確認**

```
python -m pytest tests/test_portfolio_construction.py -v
```

Expected: 5 passed

- [ ] **Step 9: 既存テスト全体が壊れていないことを確認**

```
python -m pytest tests/test_backtest_framework.py -v --tb=short
```

Expected: 全テスト PASS（schema 変更の影響なし）

- [ ] **Step 10: コミット**

```
git add src/kabusys/data/schema.py src/kabusys/data/jquants_client.py tests/test_portfolio_construction.py
git commit -m "feat: add stocks master table to schema and fetch_listed_info to jquants_client"
```

---

## Task 2: portfolio_builder.py 実装

**Files:**
- Create: `src/kabusys/portfolio/__init__.py`
- Create: `src/kabusys/portfolio/portfolio_builder.py`
- Modify: `tests/test_portfolio_construction.py`

作業ディレクトリ: `C:\Users\tetsu\Projects\KabuSys\.worktrees\phase4-backtest`

- [ ] **Step 1: portfolio_builder.py のテストを追加**

`tests/test_portfolio_construction.py` に追記：

```python
# ---------------------------------------------------------------------------
# Task 2: portfolio_builder.py
# ---------------------------------------------------------------------------

def test_select_candidates_top_n():
    """select_candidates → スコア降順で上位 max_positions 件を返す。"""
    from kabusys.portfolio.portfolio_builder import select_candidates

    signals = [
        {"code": "A", "signal_rank": 3, "score": 0.5},
        {"code": "B", "signal_rank": 1, "score": 0.9},
        {"code": "C", "signal_rank": 2, "score": 0.7},
        {"code": "D", "signal_rank": 4, "score": 0.3},
    ]
    result = select_candidates(signals, max_positions=2)
    assert len(result) == 2
    assert result[0]["code"] == "B"
    assert result[1]["code"] == "C"


def test_select_candidates_fewer_than_max():
    """候補数 ≤ max_positions なら全件返す。"""
    from kabusys.portfolio.portfolio_builder import select_candidates

    signals = [
        {"code": "A", "signal_rank": 1, "score": 0.8},
        {"code": "B", "signal_rank": 2, "score": 0.6},
    ]
    result = select_candidates(signals, max_positions=10)
    assert len(result) == 2


def test_select_candidates_empty():
    """空リスト → 空リスト。"""
    from kabusys.portfolio.portfolio_builder import select_candidates

    assert select_candidates([], max_positions=10) == []


def test_calc_equal_weights_sums_to_one():
    """calc_equal_weights → 重みの合計が 1.0。"""
    from kabusys.portfolio.portfolio_builder import calc_equal_weights

    candidates = [
        {"code": "A", "score": 0.9, "signal_rank": 1},
        {"code": "B", "score": 0.7, "signal_rank": 2},
        {"code": "C", "score": 0.5, "signal_rank": 3},
    ]
    weights = calc_equal_weights(candidates)
    assert set(weights.keys()) == {"A", "B", "C"}
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    # 等分
    assert abs(weights["A"] - 1/3) < 1e-9


def test_calc_equal_weights_empty():
    """candidates が空なら {}。"""
    from kabusys.portfolio.portfolio_builder import calc_equal_weights

    assert calc_equal_weights([]) == {}


def test_calc_score_weights_proportional():
    """calc_score_weights → score に比例した重み。"""
    from kabusys.portfolio.portfolio_builder import calc_score_weights

    candidates = [
        {"code": "A", "score": 0.6, "signal_rank": 1},
        {"code": "B", "score": 0.4, "signal_rank": 2},
    ]
    weights = calc_score_weights(candidates)
    assert abs(weights["A"] - 0.6) < 1e-9
    assert abs(weights["B"] - 0.4) < 1e-9


def test_calc_score_weights_fallback_on_all_zero():
    """全スコアが 0.0 のとき等金額配分にフォールバックする。"""
    from kabusys.portfolio.portfolio_builder import calc_score_weights

    candidates = [
        {"code": "A", "score": 0.0, "signal_rank": 1},
        {"code": "B", "score": 0.0, "signal_rank": 2},
    ]
    weights = calc_score_weights(candidates)
    assert abs(weights["A"] - 0.5) < 1e-9
    assert abs(weights["B"] - 0.5) < 1e-9


def test_calc_score_weights_empty():
    """candidates が空なら {}。"""
    from kabusys.portfolio.portfolio_builder import calc_score_weights

    assert calc_score_weights([]) == {}
```

- [ ] **Step 2: テストを実行して FAIL を確認**

```
python -m pytest tests/test_portfolio_construction.py::test_select_candidates_top_n -v
```

Expected: `FAILED` — `kabusys.portfolio` モジュールが存在しないため

- [ ] **Step 3: portfolio_builder.py を実装**

まず `src/kabusys/portfolio/` ディレクトリを作成し、`__init__.py` と `portfolio_builder.py` を作成する。

`src/kabusys/portfolio/__init__.py`:

```python
"""Portfolio construction module.

Exports:
    select_candidates, calc_equal_weights, calc_score_weights — portfolio_builder
    calc_position_sizes — position_sizing
    apply_sector_cap, calc_regime_multiplier — risk_adjustment
"""
from kabusys.portfolio.portfolio_builder import (
    calc_equal_weights,
    calc_score_weights,
    select_candidates,
)
from kabusys.portfolio.position_sizing import calc_position_sizes
from kabusys.portfolio.risk_adjustment import apply_sector_cap, calc_regime_multiplier

__all__ = [
    "select_candidates",
    "calc_equal_weights",
    "calc_score_weights",
    "calc_position_sizes",
    "apply_sector_cap",
    "calc_regime_multiplier",
]
```

`src/kabusys/portfolio/portfolio_builder.py`:

```python
"""銘柄選定・配分重み計算。

PortfolioConstruction.md Section 5〜7 に基づく純粋関数群。
DB 参照なし — メモリ内計算のみ。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def select_candidates(
    buy_signals: list[dict],
    max_positions: int = 10,
) -> list[dict]:
    """BUY シグナルをスコア降順に並べ、上位 max_positions 件を返す。

    Args:
        buy_signals: [{"code": str, "signal_rank": int, "score": float}, ...]
        max_positions: 最大保有銘柄数（PortfolioConstruction.md 推奨: 5〜15）

    Returns:
        スコア降順の候補リスト（重みなし）。
    """
    if not buy_signals:
        return []
    sorted_signals = sorted(buy_signals, key=lambda s: s.get("score", 0.0), reverse=True)
    return sorted_signals[:max_positions]


def calc_equal_weights(candidates: list[dict]) -> dict[str, float]:
    """等金額配分の重みを返す。

    Args:
        candidates: [{code, score, signal_rank}, ...]

    Returns:
        {code: weight}。candidates が空なら {}。各重みは 1/N。
    """
    if not candidates:
        return {}
    n = len(candidates)
    return {c["code"]: 1.0 / n for c in candidates}


def calc_score_weights(candidates: list[dict]) -> dict[str, float]:
    """スコア加重配分の重みを返す。

    weight_i = score_i / sum(scores)。
    全銘柄のスコアが 0.0 の場合は等金額配分にフォールバックし WARNING を出す。

    Args:
        candidates: [{code, score, signal_rank}, ...]

    Returns:
        {code: weight}。candidates が空なら {}。
    """
    if not candidates:
        return {}

    total = sum(c.get("score", 0.0) for c in candidates)
    if total <= 0.0:
        logger.warning(
            "calc_score_weights: 全銘柄のスコアが 0.0。等金額配分にフォールバック。"
        )
        return calc_equal_weights(candidates)

    return {c["code"]: c.get("score", 0.0) / total for c in candidates}
```

- [ ] **Step 4: テストを実行して PASS を確認**

```
python -m pytest tests/test_portfolio_construction.py -k "select_candidates or equal_weights or score_weights" -v
```

Expected: 7 passed

- [ ] **Step 5: コミット**

```
git add src/kabusys/portfolio/ tests/test_portfolio_construction.py
git commit -m "feat: add portfolio_builder with select_candidates, calc_equal_weights, calc_score_weights"
```

---

## Task 3: position_sizing.py 実装

**Files:**
- Create: `src/kabusys/portfolio/position_sizing.py`
- Modify: `tests/test_portfolio_construction.py`

作業ディレクトリ: `C:\Users\tetsu\Projects\KabuSys\.worktrees\phase4-backtest`

- [ ] **Step 1: position_sizing.py のテストを追加**

`tests/test_portfolio_construction.py` に追記：

```python
# ---------------------------------------------------------------------------
# Task 3: position_sizing.py
# ---------------------------------------------------------------------------

def _make_candidates(*codes: str) -> list[dict]:
    return [{"code": c, "score": 0.8, "signal_rank": i + 1} for i, c in enumerate(codes)]


def test_calc_position_sizes_risk_based_basic():
    """risk_based: 0.5% リスク・8% 損切りで株数が計算される。

    portfolio_value=10_000_000, price=1000
    → raw = floor(10M*0.005 / (1000*0.08)) = floor(50000/80) = floor(625) = 625 株
    → 100株単位切り捨て: (625 // 100) * 100 = 600 株
    """
    from kabusys.portfolio.position_sizing import calc_position_sizes

    result = calc_position_sizes(
        weights={},
        candidates=[{"code": "1234", "score": 0.8, "signal_rank": 1}],
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={},
        open_prices={"1234": 1000.0},
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    assert "1234" in result
    shares = result["1234"]
    # floor(10M * 0.005 / (1000 * 0.08)) = floor(625) = 625 → 100株切り捨て → 600
    assert shares == 600


def test_calc_position_sizes_max_position_pct_cap():
    """max_position_pct=0.10 が守られる（1銘柄上限 = 総資産の10%）。

    portfolio_value=1_000_000, price=100, risk_based → 理論株数 625 だが上限は 10000 株
    price=1000, portfolio_value=1_000_000 → 上限 = 1M * 0.10 / 1000 = 100 株
    """
    from kabusys.portfolio.position_sizing import calc_position_sizes

    result = calc_position_sizes(
        weights={},
        candidates=[{"code": "1234", "score": 0.8, "signal_rank": 1}],
        portfolio_value=1_000_000,
        available_cash=1_000_000,
        current_positions={},
        open_prices={"1234": 1000.0},
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    # 上限 = floor(1M * 0.10 / 1000) = 100 株
    assert result.get("1234", 0) <= 100


def test_calc_position_sizes_lot_size_truncation():
    """100株単位に切り捨てられる。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    # risk_based で端数が出るよう設定: 10M * 0.005 / (1100 * 0.08) = 568.18... → 500 株
    result = calc_position_sizes(
        weights={},
        candidates=[{"code": "1234", "score": 0.8, "signal_rank": 1}],
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={},
        open_prices={"1234": 1100.0},
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    shares = result.get("1234", 0)
    assert shares % 100 == 0


def test_calc_position_sizes_max_utilization_aggregate_cap():
    """max_utilization=0.70 が守られる（全ポジション合計の上限）。

    portfolio_value=1_000_000, available_cash=1_000_000（レジーム係数 1.0 後）
    3銘柄 × risk_based → 投資合計が available_cash * max_utilization = 700_000 以内
    """
    from kabusys.portfolio.position_sizing import calc_position_sizes

    candidates = [
        {"code": "A", "score": 0.9, "signal_rank": 1},
        {"code": "B", "score": 0.8, "signal_rank": 2},
        {"code": "C", "score": 0.7, "signal_rank": 3},
    ]
    open_prices = {"A": 500.0, "B": 500.0, "C": 500.0}
    result = calc_position_sizes(
        weights={},
        candidates=candidates,
        portfolio_value=1_000_000,
        available_cash=1_000_000,
        current_positions={},
        open_prices=open_prices,
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    total_invested = sum(result.get(c["code"], 0) * open_prices[c["code"]] for c in candidates)
    # 投資合計が available_cash を超えない
    assert total_invested <= 1_000_000 * 1.001  # 0.1% の誤差許容


def test_calc_position_sizes_equal_method():
    """allocation_method="equal" → 等金額配分で株数を計算。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    candidates = [
        {"code": "A", "score": 0.9, "signal_rank": 1},
        {"code": "B", "score": 0.5, "signal_rank": 2},
    ]
    weights = {"A": 0.5, "B": 0.5}

    result = calc_position_sizes(
        weights=weights,
        candidates=candidates,
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={},
        open_prices={"A": 1000.0, "B": 1000.0},
        allocation_method="equal",
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    # alloc_A = 10M * 0.5 * 0.70 = 3_500_000 → floor(3500000 / 1000) = 3500 → 但し max_position は 1000 株
    # 1銘柄上限: floor(10M * 0.10 / 1000) = 1000 株
    assert result.get("A", 0) == 1000
    assert result.get("B", 0) == 1000


def test_calc_position_sizes_score_method():
    """allocation_method="score" → スコア比例配分。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    candidates = [
        {"code": "A", "score": 0.6, "signal_rank": 1},
        {"code": "B", "score": 0.4, "signal_rank": 2},
    ]
    weights = {"A": 0.6, "B": 0.4}

    result = calc_position_sizes(
        weights=weights,
        candidates=candidates,
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={},
        open_prices={"A": 1000.0, "B": 1000.0},
        allocation_method="score",
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    # A: 10M * 0.6 * 0.70 = 4_200_000 → floor(4200000/1000) = 4200 → 上限 1000
    # B: 10M * 0.4 * 0.70 = 2_800_000 → floor(2800000/1000) = 2800 → 上限 1000
    assert result.get("A", 0) == 1000
    assert result.get("B", 0) == 1000


def test_calc_position_sizes_no_price_skipped():
    """open_prices に価格がない銘柄はスキップ（0株）。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    result = calc_position_sizes(
        weights={},
        candidates=[{"code": "9999", "score": 0.9, "signal_rank": 1}],
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={},
        open_prices={},  # 価格なし
        allocation_method="risk_based",
    )
    assert result.get("9999", 0) == 0


def test_calc_position_sizes_existing_position_excluded():
    """既存保有分は追加購入しない（追加分 = max(0, target - current)）。"""
    from kabusys.portfolio.position_sizing import calc_position_sizes

    result = calc_position_sizes(
        weights={},
        candidates=[{"code": "1234", "score": 0.9, "signal_rank": 1}],
        portfolio_value=10_000_000,
        available_cash=10_000_000,
        current_positions={"1234": 600},  # 既に 600 株保有
        open_prices={"1234": 1000.0},
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        max_position_pct=0.10,
        max_utilization=0.70,
        lot_size=100,
    )
    # target=600, current=600 → 追加分=0
    assert result.get("1234", 0) == 0
```

- [ ] **Step 2: テストを実行して FAIL を確認**

```
python -m pytest tests/test_portfolio_construction.py::test_calc_position_sizes_risk_based_basic -v
```

Expected: `FAILED` — `position_sizing` モジュールが存在しないため

- [ ] **Step 3: position_sizing.py を実装**

`src/kabusys/portfolio/position_sizing.py`:

```python
"""株数決定・リスク制限・単元株丸め。

PortfolioConstruction.md Section 7、StrategyModel.md Section 6 に基づく純粋関数。
DB 参照なし — メモリ内計算のみ。
"""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


def calc_position_sizes(
    weights: dict[str, float],
    candidates: list[dict],
    portfolio_value: float,
    available_cash: float,
    current_positions: dict[str, int],
    open_prices: dict[str, float],
    allocation_method: str = "risk_based",
    risk_pct: float = 0.005,
    stop_loss_pct: float = 0.08,
    max_position_pct: float = 0.10,
    max_utilization: float = 0.70,
    lot_size: int = 100,
) -> dict[str, int]:
    """allocation_method に応じて各銘柄の発注株数を計算する。

    Args:
        weights:           {code: weight}（equal / score 方式で使用）
        candidates:        [{code, score, signal_rank}, ...]（risk_based 方式で使用）
        portfolio_value:   総資産（円）
        available_cash:    レジーム乗数適用後の利用可能現金
        current_positions: 既存保有 {code: shares}
        open_prices:       {code: price}
        allocation_method: "equal" | "score" | "risk_based"
        risk_pct:          許容リスク率（risk_based 時）
        stop_loss_pct:     損切り率（risk_based 時）
        max_position_pct:  1銘柄上限（総資産比）
        max_utilization:   投下資金上限（総資産比）
        lot_size:          単元株数

    Returns:
        {code: shares_to_buy}（0株の銘柄は含まない）
    """
    if not candidates:
        return {}

    max_per_stock_shares_cap = lambda price: math.floor(
        portfolio_value * max_position_pct / price
    ) if price > 0 else 0

    raw_shares: dict[str, int] = {}

    if allocation_method == "risk_based":
        for c in candidates:
            code = c["code"]
            price = open_prices.get(code)
            if price is None or price <= 0:
                logger.debug("calc_position_sizes: %s の価格が取得できません。スキップ。", code)
                continue

            # リスクベース株数計算
            base_shares = math.floor(
                portfolio_value * risk_pct / (price * stop_loss_pct)
            )
            cap_shares = max_per_stock_shares_cap(price)
            target_shares = min(base_shares, cap_shares)
            target_shares = (target_shares // lot_size) * lot_size

            # 既存保有分を差し引く
            current = current_positions.get(code, 0)
            add_shares = max(0, target_shares - current)
            if add_shares > 0:
                raw_shares[code] = add_shares

    else:  # "equal" or "score"
        for c in candidates:
            code = c["code"]
            price = open_prices.get(code)
            if price is None or price <= 0:
                logger.debug("calc_position_sizes: %s の価格が取得できません。スキップ。", code)
                continue
            w = weights.get(code, 0.0)
            if w <= 0.0:
                continue

            alloc = portfolio_value * w * max_utilization
            base_shares = math.floor(alloc / price)
            cap_shares = max_per_stock_shares_cap(price)
            target_shares = min(base_shares, cap_shares)
            target_shares = (target_shares // lot_size) * lot_size

            current = current_positions.get(code, 0)
            add_shares = max(0, target_shares - current)
            if add_shares > 0:
                raw_shares[code] = add_shares

    # aggregate cap: 全銘柄の投資合計が available_cash を超える場合にスケールダウン
    if raw_shares:
        total_cost = sum(
            raw_shares[code] * open_prices[code]
            for code in raw_shares
            if code in open_prices
        )
        if total_cost > available_cash and total_cost > 0:
            scale = available_cash / total_cost
            scaled: dict[str, int] = {}
            for code, shares in raw_shares.items():
                price = open_prices.get(code, 0)
                new_shares = math.floor(shares * scale)
                new_shares = (new_shares // lot_size) * lot_size
                if new_shares > 0:
                    scaled[code] = new_shares
            return scaled

    return raw_shares
```

- [ ] **Step 4: テストを実行して PASS を確認**

```
python -m pytest tests/test_portfolio_construction.py -k "position_sizes" -v
```

Expected: 8 passed

- [ ] **Step 5: 全テストを実行して回帰なし確認**

```
python -m pytest tests/test_portfolio_construction.py -v
```

Expected: 全テスト PASS

- [ ] **Step 6: コミット**

```
git add src/kabusys/portfolio/position_sizing.py src/kabusys/portfolio/__init__.py tests/test_portfolio_construction.py
git commit -m "feat: add calc_position_sizes supporting risk_based, equal, score allocation methods"
```

---

## Task 4: risk_adjustment.py 実装

**Files:**
- Create: `src/kabusys/portfolio/risk_adjustment.py`
- Modify: `tests/test_portfolio_construction.py`

作業ディレクトリ: `C:\Users\tetsu\Projects\KabuSys\.worktrees\phase4-backtest`

- [ ] **Step 1: risk_adjustment.py のテストを追加**

`tests/test_portfolio_construction.py` に追記：

```python
# ---------------------------------------------------------------------------
# Task 4: risk_adjustment.py
# ---------------------------------------------------------------------------

def test_apply_sector_cap_removes_overweight_sector():
    """同一セクターが 30% 超なら新規候補を除外。

    既存保有: 電気機器 A = 1000株 × 1000円 = 1,000,000円
    portfolio_value = 3,000,000 → セクター比 = 33.3% > 30%
    → 電気機器の新規候補 B を除外
    """
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    candidates = [
        {"code": "B", "score": 0.9, "signal_rank": 1},  # 電気機器
        {"code": "C", "score": 0.8, "signal_rank": 2},  # 機械
    ]
    sector_map = {"A": "電気機器", "B": "電気機器", "C": "機械"}
    current_positions = {"A": 1000}
    open_prices = {"A": 1000.0, "B": 900.0, "C": 800.0}

    result = apply_sector_cap(
        candidates=candidates,
        sector_map=sector_map,
        portfolio_value=3_000_000,
        current_positions=current_positions,
        open_prices=open_prices,
        max_sector_pct=0.30,
    )

    codes = {c["code"] for c in result}
    assert "B" not in codes   # 除外
    assert "C" in codes       # 通過


def test_apply_sector_cap_allows_under_limit():
    """セクター比が 30% 未満なら除外しない。"""
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    candidates = [
        {"code": "B", "score": 0.9, "signal_rank": 1},
    ]
    sector_map = {"A": "電気機器", "B": "電気機器"}
    current_positions = {"A": 100}
    open_prices = {"A": 1000.0, "B": 900.0}

    result = apply_sector_cap(
        candidates=candidates,
        sector_map=sector_map,
        portfolio_value=5_000_000,  # A = 100_000 / 5M = 2% < 30%
        current_positions=current_positions,
        open_prices=open_prices,
        max_sector_pct=0.30,
    )

    assert len(result) == 1
    assert result[0]["code"] == "B"


def test_apply_sector_cap_unknown_sector_passes():
    """sector_map にないコード（セクター不明）は制限なく通過する。"""
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    candidates = [
        {"code": "X", "score": 0.9, "signal_rank": 1},  # セクター不明
    ]
    sector_map = {}  # X のセクターなし
    # 仮に既存保有でどのセクターも超えていても、Xは通過
    result = apply_sector_cap(
        candidates=candidates,
        sector_map=sector_map,
        portfolio_value=1_000_000,
        current_positions={},
        open_prices={"X": 1000.0},
        max_sector_pct=0.30,
    )
    assert len(result) == 1
    assert result[0]["code"] == "X"


def test_apply_sector_cap_preserves_order_and_fields():
    """apply_sector_cap は {code, score, rank} 形式を保持して返す。"""
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    candidates = [
        {"code": "A", "score": 0.9, "signal_rank": 1},
        {"code": "B", "score": 0.7, "signal_rank": 2},
    ]
    sector_map = {"A": "電気機器", "B": "機械"}
    result = apply_sector_cap(
        candidates=candidates,
        sector_map=sector_map,
        portfolio_value=10_000_000,
        current_positions={},
        open_prices={"A": 1000.0, "B": 1000.0},
        max_sector_pct=0.30,
    )
    assert len(result) == 2
    assert result[0]["code"] == "A"
    assert "score" in result[0]
    assert "signal_rank" in result[0]


def test_calc_regime_multiplier_values():
    """calc_regime_multiplier: bull=1.0, neutral=0.7, bear=0.3, 未知=1.0。"""
    from kabusys.portfolio.risk_adjustment import calc_regime_multiplier

    assert calc_regime_multiplier("bull") == 1.0
    assert calc_regime_multiplier("neutral") == 0.7
    assert calc_regime_multiplier("bear") == 0.3
    assert calc_regime_multiplier("unknown_regime") == 1.0


def test_calc_regime_multiplier_case_sensitive():
    """大文字の "Bull" は未知とみなし 1.0 にフォールバックする（DB は小文字で格納）。"""
    from kabusys.portfolio.risk_adjustment import calc_regime_multiplier

    # regime_label は DB で小文字（regime_detector.py に準拠）
    # 大文字の場合は未知扱い（フォールバック）
    assert calc_regime_multiplier("Bull") == 1.0
```

- [ ] **Step 2: テストを実行して FAIL を確認**

```
python -m pytest tests/test_portfolio_construction.py::test_calc_regime_multiplier_values -v
```

Expected: `FAILED` — `risk_adjustment` モジュールが存在しないため

- [ ] **Step 3: risk_adjustment.py を実装**

`src/kabusys/portfolio/risk_adjustment.py`:

```python
"""セクター集中制限・レジーム乗数。

PortfolioConstruction.md Section 8〜9 に基づく純粋関数。
DB 参照なし — メモリ内計算のみ。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def apply_sector_cap(
    candidates: list[dict],
    sector_map: dict[str, str],
    portfolio_value: float,
    current_positions: dict[str, int],
    open_prices: dict[str, float],
    max_sector_pct: float = 0.30,
) -> list[dict]:
    """同一セクターの既存保有比率が max_sector_pct を超える場合、そのセクターの新規候補を除外する。

    Args:
        candidates:        [{code, score, signal_rank}, ...]（重みなし）
        sector_map:        {code: sector}。コードが存在しないものは "unknown" 扱い。
        portfolio_value:   総資産（円）
        current_positions: 既存保有 {code: shares}
        open_prices:       {code: price}
        max_sector_pct:    1セクターの最大保有比率

    Returns:
        セクター上限チェック後の candidates（同じ {code, score, signal_rank} 形式）。
        "unknown" セクターは max_sector_pct を適用しない（除外しない）。
    """
    if not candidates or portfolio_value <= 0:
        return candidates

    # 既存保有のセクター別時価を計算
    sector_exposure: dict[str, float] = {}
    for code, shares in current_positions.items():
        sector = sector_map.get(code, "unknown")
        if sector == "unknown":
            continue
        price = open_prices.get(code, 0.0)
        sector_exposure[sector] = sector_exposure.get(sector, 0.0) + shares * price

    # 超過セクターの集合を作成
    blocked_sectors: set[str] = set()
    for sector, exposure in sector_exposure.items():
        if exposure / portfolio_value > max_sector_pct:
            blocked_sectors.add(sector)
            logger.debug(
                "apply_sector_cap: セクター '%s' が上限超過 (%.1f%% > %.1f%%)",
                sector, exposure / portfolio_value * 100, max_sector_pct * 100,
            )

    if not blocked_sectors:
        return candidates

    # 候補をフィルタ
    filtered = []
    for c in candidates:
        sector = sector_map.get(c["code"], "unknown")
        if sector == "unknown" or sector not in blocked_sectors:
            filtered.append(c)
        else:
            logger.debug(
                "apply_sector_cap: %s（%s）を除外（セクター上限）", c["code"], sector
            )

    return filtered


def calc_regime_multiplier(regime: str) -> float:
    """市場レジームに応じた投下資金乗数を返す。

    market_regime.regime_label は小文字で格納される（regime_detector.py 実装準拠）。
    "bull"    → 1.0（通常運用）
    "neutral" → 0.7（やや縮小）
    "bear"    → 0.3（大幅縮小）
    その他    → 1.0（未知レジームは Bull 相当でフォールバック）

    【重要】Bear レジームで BUY シグナルが生成されない理由:
    generate_signals() は regime が Bear の場合 BUY シグナルを一切生成しない
    (StrategyModel.md Section 5.1)。multiplier=0.3 は Neutral 等の中間局面向けの
    追加セーフガード。

    Args:
        regime: market_regime.regime_label の値（小文字）

    Returns:
        投下資金乗数（0.0〜1.0）
    """
    _MULTIPLIER_MAP: dict[str, float] = {
        "bull": 1.0,
        "neutral": 0.7,
        "bear": 0.3,
    }
    multiplier = _MULTIPLIER_MAP.get(regime)
    if multiplier is None:
        logger.warning(
            "calc_regime_multiplier: 未知のレジーム '%s'。1.0 でフォールバック。", regime
        )
        return 1.0
    return multiplier
```

- [ ] **Step 4: テストを実行して PASS を確認**

```
python -m pytest tests/test_portfolio_construction.py -k "sector_cap or regime_multiplier" -v
```

Expected: 6 passed

- [ ] **Step 5: 統合テストを追加して実行**

`tests/test_portfolio_construction.py` に追記：

```python
# ---------------------------------------------------------------------------
# Task 4: 統合テスト（portfolio_builder + position_sizing + risk_adjustment）
# ---------------------------------------------------------------------------

def test_integration_neutral_regime_reduces_available_cash():
    """`neutral` レジームで available_cash が 70% に抑制される。

    portfolio_value=10M, multiplier=0.7 → available_cash=7M
    risk_based: 10M * 0.005 / (1000 * 0.08) = 625 → 600 株 × 1000 = 600_000
    total_cost=600_000 < available_cash=7_000_000 → スケールダウンなし
    """
    from kabusys.portfolio.portfolio_builder import select_candidates
    from kabusys.portfolio.position_sizing import calc_position_sizes
    from kabusys.portfolio.risk_adjustment import calc_regime_multiplier

    portfolio_value = 10_000_000
    multiplier = calc_regime_multiplier("neutral")
    assert multiplier == 0.7
    available_cash = portfolio_value * multiplier  # 7_000_000

    candidates = select_candidates(
        [{"code": "1234", "signal_rank": 1, "score": 0.9}]
    )
    result = calc_position_sizes(
        weights={},
        candidates=candidates,
        portfolio_value=portfolio_value,
        available_cash=available_cash,
        current_positions={},
        open_prices={"1234": 1000.0},
        allocation_method="risk_based",
    )
    # 600_000 < 7_000_000 なのでスケールダウンなし
    assert result.get("1234", 0) == 600


def test_integration_sector_cap_then_size():
    """セクター上限フィルタ後に position_sizing が動作する。"""
    from kabusys.portfolio.portfolio_builder import select_candidates, calc_equal_weights
    from kabusys.portfolio.position_sizing import calc_position_sizes
    from kabusys.portfolio.risk_adjustment import apply_sector_cap

    signals = [
        {"code": "A", "signal_rank": 1, "score": 0.9},  # 電気機器（除外される）
        {"code": "B", "signal_rank": 2, "score": 0.7},  # 機械（通過）
    ]
    sector_map = {"existing_A": "電気機器", "A": "電気機器", "B": "機械"}
    current_positions = {"existing_A": 1000}  # 電気機器に 1000 株保有
    open_prices = {"existing_A": 1200.0, "A": 1000.0, "B": 900.0}
    portfolio_value = 3_500_000  # existing_A = 1.2M / 3.5M = 34.3% > 30%

    candidates = select_candidates(signals)
    filtered = apply_sector_cap(
        candidates, sector_map, portfolio_value, current_positions, open_prices
    )

    assert len(filtered) == 1
    assert filtered[0]["code"] == "B"

    weights = calc_equal_weights(filtered)
    result = calc_position_sizes(
        weights=weights,
        candidates=filtered,
        portfolio_value=portfolio_value,
        available_cash=portfolio_value,
        current_positions=current_positions,
        open_prices=open_prices,
        allocation_method="equal",
        max_position_pct=0.10,
        max_utilization=0.70,
    )
    assert result.get("A", 0) == 0  # セクター除外
    assert result.get("B", 0) > 0   # 購入あり
```

```
python -m pytest tests/test_portfolio_construction.py -v
```

Expected: 全テスト PASS

- [ ] **Step 6: コミット**

```
git add src/kabusys/portfolio/risk_adjustment.py tests/test_portfolio_construction.py
git commit -m "feat: add risk_adjustment with apply_sector_cap and calc_regime_multiplier"
```

---

## Task 5: simulator.py 更新（alloc → shares）

**Files:**
- Modify: `src/kabusys/backtest/simulator.py`
- Modify: `tests/test_backtest_framework.py`

作業ディレクトリ: `C:\Users\tetsu\Projects\KabuSys\.worktrees\phase4-backtest`

- [ ] **Step 1: テストを先に更新（失敗する状態にする）**

`tests/test_backtest_framework.py` の以下のテストを更新する。

**`test_simulator_buy_reduces_cash` を更新:**

```python
def test_simulator_buy_reduces_cash():
    """BUY 約定 → 現金が (株数 × 約定価格 + 手数料) 分減る。"""
    sim = _make_simulator(1_000_000)
    signals = [{"code": "1234", "side": "buy", "shares": 100}]
    open_prices = {"1234": 1000.0}
    slippage = 0.001
    commission = 0.00055

    sim.execute_orders(signals, open_prices, slippage, commission)

    entry_price = 1000.0 * (1 + slippage)  # 1001.0
    shares = 100
    cost = shares * entry_price
    comm = cost * commission
    expected_cash = 1_000_000 - cost - comm
    assert abs(sim.cash - expected_cash) < 0.01
```

**`test_simulator_buy_slippage` を更新:**

```python
def test_simulator_buy_slippage():
    """BUY 約定価格 = open * (1 + slippage_rate)。"""
    sim = _make_simulator()
    signals = [{"code": "1234", "side": "buy", "shares": 100}]
    open_prices = {"1234": 2000.0}
    sim.execute_orders(signals, open_prices, slippage_rate=0.001, commission_rate=0.00055)

    assert len(sim.trades) == 1
    trade = sim.trades[0]
    assert abs(trade.price - 2000.0 * 1.001) < 1e-6
```

**`test_simulator_sell_realized_pnl` を更新（BUY 部分）:**

```python
def test_simulator_sell_realized_pnl():
    """SELL → realized_pnl = shares * (exit_price - cost_basis) - commission。"""
    sim = _make_simulator()
    # まず BUY して cost_basis を確立（shares 指定に変更）
    sim.execute_orders(
        [{"code": "1234", "side": "buy", "shares": 300}],
        {"1234": 1000.0},
        slippage_rate=0.0,
        commission_rate=0.0,
    )
    buy_trade = sim.trades[0]
    shares = buy_trade.shares

    # SELL
    sim.execute_orders(
        [{"code": "1234", "side": "sell"}],
        {"1234": 1200.0},
        slippage_rate=0.0,
        commission_rate=0.0,
    )
    sell_trade = sim.trades[1]
    expected_pnl = shares * (1200.0 - 1000.0)
    assert abs(sell_trade.realized_pnl - expected_pnl) < 0.01
```

**`test_simulator_no_price_skips_buy` を更新:**

```python
def test_simulator_no_price_skips_buy():
    """open_prices に code が存在しない BUY シグナルはスキップ（ログのみ）。"""
    sim = _make_simulator()
    sim.execute_orders(
        [{"code": "9999", "side": "buy", "shares": 100}],
        {},  # 価格なし
        slippage_rate=0.001,
        commission_rate=0.00055,
    )
    assert sim.cash == 1_000_000  # 変化なし
    assert len(sim.trades) == 0
```

**`test_simulator_insufficient_cash_skips_buy` を更新（役割変更）:**

```python
def test_simulator_insufficient_cash_skips_buy():
    """shares > 0 でも現金不足なら全体を再調整してスキップ。"""
    sim = _make_simulator(initial_cash=100)  # 現金が極端に少ない
    sim.execute_orders(
        [{"code": "1234", "side": "buy", "shares": 100}],
        {"1234": 10_000.0},  # 100株 × 10000円 = 1,000,000 円必要
        slippage_rate=0.0,
        commission_rate=0.0,
    )
    assert len(sim.trades) == 0  # 現金不足でスキップ
```

- [ ] **Step 2: テストを実行して FAIL を確認**

```
python -m pytest tests/test_backtest_framework.py::test_simulator_buy_reduces_cash -v
```

Expected: `FAILED` — `simulate.execute_orders` はまだ `alloc` を受け取るため

- [ ] **Step 3: simulator.py を更新（alloc → shares）**

`src/kabusys/backtest/simulator.py` を以下の通り変更：

**`execute_orders` docstring の `alloc` を `shares` に変更:**

```python
    def execute_orders(
        self,
        signals: list[dict],
        open_prices: dict[str, float],
        slippage_rate: float,
        commission_rate: float,
        trading_day: date | None = None,
    ) -> None:
        """シグナルリストを当日 open 価格で約定処理する。

        SELL を先に処理してから BUY を処理する（資金確保のため）。
        SELL は保有全量をクローズする（部分利確・部分損切り非対応）。

        Args:
            signals:       [{"code": str, "side": "buy"|"sell", "shares": int}]
                           sell の場合 shares キーは不要（保有全量をクローズ）。
            open_prices:   code → 当日始値 の辞書。
            slippage_rate: スリッページ率。BUY は +、SELL は -。
            commission_rate: 手数料率（約定金額 × commission_rate）。
            trading_day:   約定日（TradeRecord.date に使用）。None の場合は history[-1].date を使用。
        """
```

**BUY ループを `shares` 対応に変更:**

```python
        # BUY を後に処理
        for sig in [s for s in signals if s["side"] == "buy"]:
            self._execute_buy(
                sig["code"],
                sig.get("shares", 0),
                open_prices,
                slippage_rate,
                commission_rate,
                trading_day,
            )
```

**`_execute_buy` シグネチャと本体を変更（alloc → shares）:**

```python
    def _execute_buy(
        self,
        code: str,
        shares: int,
        open_prices: dict[str, float],
        slippage_rate: float,
        commission_rate: float,
        trading_day: date | None = None,
    ) -> None:
        if shares <= 0:
            logger.debug("execute_orders: BUY %s shares=%d。スキップ。", code, shares)
            return

        open_price = open_prices.get(code)
        if open_price is None:
            logger.warning("execute_orders: BUY %s の始値が取得できません。スキップ。", code)
            return

        entry_price = open_price * (1.0 + slippage_rate)
        cost = shares * entry_price
        commission = cost * commission_rate
        total_cost = cost + commission

        if total_cost > self.cash:
            logger.debug("execute_orders: BUY %s 現金不足（必要: %.0f, 保有: %.0f）。スキップ。",
                         code, total_cost, self.cash)
            return

        self.cash -= total_cost

        # 平均取得単価の更新
        existing_shares = self.positions.get(code, 0)
        existing_cost = self.cost_basis.get(code, 0.0) * existing_shares
        new_total_shares = existing_shares + shares
        self.cost_basis[code] = (existing_cost + cost) / new_total_shares
        self.positions[code] = new_total_shares

        trade_date = trading_day if trading_day is not None else (
            self.history[-1].date if self.history else date(1970, 1, 1)
        )
        self.trades.append(TradeRecord(
            date=trade_date,
            code=code,
            side="buy",
            shares=shares,
            price=entry_price,
            commission=commission,
            realized_pnl=None,
        ))
```

- [ ] **Step 4: テストを実行して PASS を確認**

```
python -m pytest tests/test_backtest_framework.py -v --tb=short
```

Expected: 全テスト PASS

- [ ] **Step 5: コミット**

```
git add src/kabusys/backtest/simulator.py tests/test_backtest_framework.py
git commit -m "feat: change execute_orders BUY signal from alloc to shares (breaking change)"
```

---

## Task 6: engine.py 更新（run_backtest + helpers）

**Files:**
- Modify: `src/kabusys/backtest/engine.py`
- Modify: `src/kabusys/backtest/run.py`
- Modify: `tests/test_backtest_framework.py`

作業ディレクトリ: `C:\Users\tetsu\Projects\KabuSys\.worktrees\phase4-backtest`

- [ ] **Step 1: engine.py 更新用テストを追加**

`tests/test_backtest_framework.py` に追記（`_setup_minimal_backtest` は Task 5 の統合テスト用ヘルパーとして既に同ファイルに定義済み）：

```python
# ---------------------------------------------------------------------------
# Task 6: engine.py — Phase 5 ヘルパーと run_backtest 更新
# ---------------------------------------------------------------------------

def test_fetch_regime_returns_bull_on_no_data(conn):
    """_fetch_regime: market_regime にデータなし → 'bull' を返す。"""
    from kabusys.backtest.engine import _fetch_regime
    from datetime import date

    result = _fetch_regime(conn, date(2024, 1, 5))
    assert result == "bull"


def test_fetch_regime_returns_correct_label(conn):
    """_fetch_regime: market_regime にデータあり → regime_label を返す。"""
    from kabusys.backtest.engine import _fetch_regime
    from datetime import date

    d = date(2024, 1, 5)
    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
        [d, -0.5, "bear"],
    )
    result = _fetch_regime(conn, d)
    assert result == "bear"


def test_fetch_sector_map_empty_table(conn):
    """_fetch_sector_map: stocks テーブルが空なら {}。"""
    from kabusys.backtest.engine import _fetch_sector_map

    result = _fetch_sector_map(conn)
    assert result == {}


def test_fetch_sector_map_returns_data(conn):
    """_fetch_sector_map: stocks テーブルからセクターマップを返す。"""
    from kabusys.backtest.engine import _fetch_sector_map

    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["1234", "テスト", "Prime", "電気機器"],
    )
    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["5678", "サンプル", "Standard", "機械"],
    )
    result = _fetch_sector_map(conn)
    assert result == {"1234": "電気機器", "5678": "機械"}


def test_build_backtest_conn_copies_stocks(conn):
    """_build_backtest_conn → stocks テーブルが bt_conn にコピーされる。"""
    from kabusys.backtest.engine import _build_backtest_conn
    from datetime import date

    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["1234", "テスト", "Prime", "電気機器"],
    )
    bt_conn = _build_backtest_conn(conn, date(2024, 1, 5), date(2024, 1, 5))
    row = bt_conn.execute("SELECT sector FROM stocks WHERE code = '1234'").fetchone()
    assert row is not None
    assert row[0] == "電気機器"
    bt_conn.close()


def test_read_day_signals_includes_score(conn):
    """_read_day_signals → buy_signals に score フィールドが含まれる。"""
    from kabusys.backtest.engine import _read_day_signals
    from datetime import date

    d = date(2024, 1, 5)
    conn.execute(
        "INSERT INTO signals (date, code, side, score, signal_rank) VALUES (?, ?, ?, ?, ?)",
        [d, "1234", "buy", 0.85, 1],
    )
    buy_signals, sell_signals = _read_day_signals(conn, d)
    assert len(buy_signals) == 1
    assert "score" in buy_signals[0]
    assert abs(buy_signals[0]["score"] - 0.85) < 1e-9


def test_run_backtest_new_params_accepted(conn):
    """run_backtest が新パラメータ（allocation_method, max_positions 等）を受け付ける。"""
    from kabusys.backtest.engine import run_backtest, BacktestResult
    from datetime import date

    _setup_minimal_backtest(conn)

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
        allocation_method="equal",
        max_positions=5,
        max_utilization=0.70,
    )

    assert isinstance(result, BacktestResult)


def test_run_backtest_risk_based_method(conn):
    """run_backtest の allocation_method="risk_based" が動作する。"""
    from kabusys.backtest.engine import run_backtest, BacktestResult
    from datetime import date

    _setup_minimal_backtest(conn)

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
    )

    assert isinstance(result, BacktestResult)


def test_run_backtest_default_max_position_pct_is_010(conn):
    """run_backtest のデフォルト max_position_pct は 0.10（Phase 5 設計書準拠）。"""
    import inspect
    from kabusys.backtest.engine import run_backtest

    sig = inspect.signature(run_backtest)
    default = sig.parameters["max_position_pct"].default
    assert default == 0.10, f"max_position_pct のデフォルトが {default}（0.10 であること）"
```

- [ ] **Step 2: テストを実行して FAIL を確認**

```
python -m pytest tests/test_backtest_framework.py::test_fetch_regime_returns_bull_on_no_data tests/test_backtest_framework.py::test_fetch_sector_map_empty_table tests/test_backtest_framework.py::test_run_backtest_default_max_position_pct_is_010 -v
```

Expected: `FAILED`

- [ ] **Step 3: engine.py を更新**

`src/kabusys/backtest/engine.py` を以下の通り変更する。

**import 追加（ファイル先頭部分、既存の `from kabusys.backtest.simulator import ...` 行の直後に挿入）:**

```python
from kabusys.backtest.metrics import BacktestMetrics, calc_metrics
from kabusys.backtest.simulator import DailySnapshot, PortfolioSimulator, TradeRecord
from kabusys.portfolio import (
    apply_sector_cap,
    calc_equal_weights,
    calc_position_sizes,
    calc_regime_multiplier,
    calc_score_weights,
    select_candidates,
)
```

**`_read_day_signals` に score を追加（既存関数を置き換え）:**

```python
def _read_day_signals(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> tuple[list[dict], list[dict]]:
    """指定日の signals テーブルから BUY / SELL シグナルを読み取る。

    Returns:
        (buy_signals, sell_signals)
        buy_signals:  [{"code": str, "signal_rank": int, "score": float}, ...]
        sell_signals: [{"code": str}, ...]
    """
    buy_rows = conn.execute(
        "SELECT code, signal_rank, score FROM signals "
        "WHERE date = ? AND side = 'buy' ORDER BY signal_rank",
        [trading_day],
    ).fetchall()
    sell_rows = conn.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
        [trading_day],
    ).fetchall()
    buy_signals = [{"code": row[0], "signal_rank": row[1], "score": row[2] or 0.0} for row in buy_rows]
    sell_signals = [{"code": row[0]} for row in sell_rows]
    return buy_signals, sell_signals
```

**`_fetch_regime` ヘルパーを追加（`_read_day_signals` の直後）:**

```python
def _fetch_regime(conn: duckdb.DuckDBPyConnection, trading_day: date) -> str:
    """market_regime テーブルから当日レジームを返す。データなしなら 'bull' でフォールバック。

    schema.py の market_regime テーブルのレジーム列名は `regime_label`。
    """
    row = conn.execute(
        "SELECT regime_label FROM market_regime WHERE date = ?", [trading_day]
    ).fetchone()
    if row is None:
        logger.warning(
            "_fetch_regime: %s のレジームが取得できません。'bull' でフォールバック。", trading_day
        )
        return "bull"
    return row[0]


def _fetch_sector_map(conn: duckdb.DuckDBPyConnection) -> dict[str, str]:
    """stocks テーブルから {code: sector} を返す。テーブルが空なら {}。"""
    rows = conn.execute(
        "SELECT code, sector FROM stocks WHERE sector IS NOT NULL"
    ).fetchall()
    return {code: sector for code, sector in rows}
```

**`_build_backtest_conn` に stocks コピーを追加（`market_calendar` コピーの直後）:**

```python
    # stocks は全件コピー（銘柄のセクターは日付フィルタなし）
    try:
        rows = source_conn.execute("SELECT * FROM stocks").fetchall()
        if rows:
            result = source_conn.execute("SELECT * FROM stocks LIMIT 0")
            cols = [desc[0] for desc in result.description]
            col_list = ", ".join(cols)
            placeholders = ", ".join(["?" for _ in cols])
            bt_conn.executemany(
                f"INSERT INTO stocks ({col_list}) VALUES ({placeholders})", rows
            )
    except Exception as exc:
        logger.warning("_build_backtest_conn: stocks のコピーをスキップ: %s", exc)
```

**`run_backtest` シグネチャを更新し、ループ内の Step 5 を Phase 5 モジュール使用に置き換え:**

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
    allocation_method: str = "risk_based",
    risk_pct: float = 0.005,
    stop_loss_pct: float = 0.08,
) -> BacktestResult:
    """バックテストを実行し結果を返す。

    Args:
        conn:              本番 DuckDB 接続（読み取り専用で使用）。
        start_date:        バックテスト開始日（含む）。
        end_date:          バックテスト終了日（含む）。
        initial_cash:      初期資金（円）。
        slippage_rate:     スリッページ率（デフォルト 0.1%）。
        commission_rate:   手数料率（デフォルト 0.055%）。
        max_position_pct:  1銘柄あたりの最大ポートフォリオ比率（デフォルト 10%）。
        max_utilization:   全ポジション投下上限（デフォルト 70%）。
        max_positions:     最大保有銘柄数（デフォルト 10）。
        allocation_method: 資金配分方式: "equal" | "score" | "risk_based"（デフォルト）。
        risk_pct:          1トレード許容リスク率（risk_based 時、デフォルト 0.5%）。
        stop_loss_pct:     損切り率（株数計算用、risk_based 時、デフォルト 8%）。

    Returns:
        BacktestResult（history, trades, metrics）。
    """
    from kabusys.data.calendar_management import get_trading_days
    from kabusys.strategy.signal_generator import generate_signals

    bt_conn = _build_backtest_conn(conn, start_date, end_date)
    simulator = PortfolioSimulator(initial_cash=initial_cash)
    signals_prev: list[dict] = []

    try:
        trading_days = get_trading_days(bt_conn, start_date, end_date)
        logger.info(
            "run_backtest: 開始 start=%s end=%s 営業日数=%d 初期資金=%.0f allocation=%s",
            start_date, end_date, len(trading_days), initial_cash, allocation_method,
        )

        # sector_map はバックテスト開始前に一度だけ取得（銘柄のセクターは日次変化しない）
        sector_map = _fetch_sector_map(bt_conn)

        for trading_day in trading_days:
            # Step 1: 前日シグナルを当日 open で約定
            open_prices = _fetch_open_prices(bt_conn, trading_day)
            simulator.execute_orders(signals_prev, open_prices, slippage_rate, commission_rate, trading_day)

            # Step 2: positions テーブルに書き戻し（generate_signals の SELL 判定に必要）
            _write_positions(bt_conn, trading_day, simulator.positions, simulator.cost_basis)

            # Step 3: 終値で時価評価・スナップショット記録
            close_prices = _fetch_close_prices(bt_conn, trading_day)
            simulator.mark_to_market(trading_day, close_prices)

            # Step 4: 翌日用シグナル生成（bt_conn の positions を読んで SELL 判定）
            generate_signals(bt_conn, target_date=trading_day)

            # Step 5: ポートフォリオ構築（Phase 5 モジュール使用）
            buy_signals, sell_signals = _read_day_signals(bt_conn, trading_day)
            regime = _fetch_regime(bt_conn, trading_day)
            multiplier = calc_regime_multiplier(regime)
            prior_pv = simulator.history[-1].portfolio_value if simulator.history else initial_cash
            available_cash = simulator.cash * multiplier

            candidates = select_candidates(buy_signals, max_positions)
            candidates = apply_sector_cap(
                candidates, sector_map, prior_pv, simulator.positions, open_prices
            )

            if allocation_method == "equal":
                weights = calc_equal_weights(candidates)
            elif allocation_method == "score":
                weights = calc_score_weights(candidates)
            else:
                weights = {}  # risk_based は weights 不使用

            sized = calc_position_sizes(
                weights=weights,
                candidates=candidates,
                portfolio_value=prior_pv,
                available_cash=available_cash,
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
                for code, shares in sized.items()
                if shares > 0
            ] + [{"code": s["code"], "side": "sell"} for s in sell_signals]

    finally:
        bt_conn.close()

    metrics = calc_metrics(simulator.history, simulator.trades)
    logger.info(
        "run_backtest: 完了 CAGR=%.2f%% Sharpe=%.3f MaxDD=%.2f%% Trades=%d",
        metrics.cagr * 100, metrics.sharpe_ratio,
        metrics.max_drawdown * 100, metrics.total_trades,
    )
    return BacktestResult(
        history=simulator.history,
        trades=simulator.trades,
        metrics=metrics,
    )
```

- [ ] **Step 4: run.py の max_position_pct デフォルト値を更新**

`src/kabusys/backtest/run.py` の以下の行を変更：

```python
# 変更前
parser.add_argument("--max-position-pct", type=float, default=0.20, ...)
# 変更後
parser.add_argument("--max-position-pct", type=float, default=0.10,
                    help="Max position size as %% of portfolio per security [default: 0.10]")
```

- [ ] **Step 5: テストを実行して PASS を確認**

```
python -m pytest tests/test_backtest_framework.py -v --tb=short
```

Expected: 全テスト PASS

- [ ] **Step 6: コミット**

```
git add src/kabusys/backtest/engine.py src/kabusys/backtest/run.py tests/test_backtest_framework.py
git commit -m "feat: integrate Phase 5 portfolio modules into run_backtest; add _fetch_regime, _fetch_sector_map"
```

---

## Task 7: 全テスト実行・回帰確認

**Files:** なし（実行のみ）

作業ディレクトリ: `C:\Users\tetsu\Projects\KabuSys\.worktrees\phase4-backtest`

- [ ] **Step 1: 全テストを実行**

```
python -m pytest tests/ -v --tb=short 2>&1 | head -100
```

Expected: 全テスト PASS（エラーなし）

- [ ] **Step 2: テストカバレッジ確認（任意）**

```
python -m pytest tests/test_portfolio_construction.py tests/test_backtest_framework.py -v
```

新規・更新テストが全て PASS していることを確認。

- [ ] **Step 3: __init__.py のエクスポート確認**

```python
# 手動確認コマンド
python -c "from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: バックテストの簡易動作確認（インメモリ DB）**

```python
# 手動確認コマンド
python -c "
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
print('import OK')
print('run_backtest signature OK')
import inspect
sig = inspect.signature(run_backtest)
print('params:', list(sig.parameters.keys()))
"
```

Expected: `allocation_method`, `max_positions`, `max_utilization` などが含まれる

- [ ] **Step 5: 最終コミット（タグなし）**

```
git add -p  # 変更漏れがないか確認
git status
```

未コミットファイルがあれば追加してコミット。全てコミット済みなら次のステップへ。

---

## チェックリスト（実装完了条件）

- [ ] `init_schema(":memory:")` で `stocks` テーブルが作成される
- [ ] `fetch_listed_info()` が J-Quants フィールドを正しくマッピングする
- [ ] `select_candidates` がスコア降順で上位 N 件を返す
- [ ] `calc_equal_weights` / `calc_score_weights` が正しい重みを返す
- [ ] `calc_position_sizes` が 3 方式すべてで動作する
- [ ] `apply_sector_cap` がセクター上限を正しく適用する
- [ ] `calc_regime_multiplier` が小文字 "bull"/"neutral"/"bear" を正しく処理する
- [ ] `execute_orders` が `shares` キーで受け取る（`alloc` は廃止）
- [ ] `run_backtest` の `max_position_pct` デフォルトが 0.10
- [ ] `run_backtest` が `allocation_method`, `max_positions`, `max_utilization`, `risk_pct`, `stop_loss_pct` を受け付ける
- [ ] `_read_day_signals` が `score` フィールドを含む
- [ ] `_fetch_regime` が `regime_label` 列を参照し、データなしで `"bull"` を返す
- [ ] `_fetch_sector_map` が `stocks` テーブルから `{code: sector}` を返す
- [ ] `_build_backtest_conn` が `stocks` テーブルをコピーする
- [ ] 全テストが PASS（`tests/test_portfolio_construction.py` + `tests/test_backtest_framework.py`）
