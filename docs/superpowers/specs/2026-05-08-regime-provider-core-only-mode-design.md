# RegimeProvider と Core-only モード定義 実装設計

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `signal_generator.py` と `backtest/engine.py` が `market_regime` テーブルを直接前提にする結合を `RegimeProvider` プロトコルで抽象化し、`ENABLE_AI_SENTIMENT=false` かつ AI テーブルが空の状態で Core の売買フローとバックテストが明示的に正常動作するようにする（Issue #271）。

**Architecture:** `src/kabusys/core/interfaces/regime.py` に `RegimeProvider` Protocol・`NullRegimeProvider`・`DatabaseRegimeProvider` を定義する。`signal_generator.py` の `_is_bear_regime()` を廃止して `regime_provider.get_regime()` に置き換え、AI スコアクエリを `enable_ai_sentiment` フラグでガードする。`backtest/engine.py` の `_get_daily_regime()` も同様に置き換える。

**Tech Stack:** Python 3.10+, typing.Protocol, DuckDB, pytest

---

## ファイル構成

### 新規作成

| ファイル | 役割 |
|---|---|
| `src/kabusys/core/__init__.py` | `core` パッケージ初期化（空） |
| `src/kabusys/core/interfaces/__init__.py` | `interfaces` パッケージ初期化・`build_regime_provider` 公開 |
| `src/kabusys/core/interfaces/regime.py` | `RegimeProvider` Protocol・`NullRegimeProvider`・`DatabaseRegimeProvider` |
| `tests/test_regime_provider.py` | `RegimeProvider` 実装の単体テスト |

### 変更

| ファイル | 変更内容 |
|---|---|
| `src/kabusys/strategy/signal_generator.py` | `_is_bear_regime()` 廃止、`generate_signals()` に `regime_provider` 引数追加、AI スコアフラグガード追加 |
| `src/kabusys/backtest/engine.py` | `_get_daily_regime()` 廃止、`regime_provider` 注入、AI テーブルコピーを条件化 |

### 変更なし

- `src/kabusys/portfolio/risk_adjustment.py` — `calc_regime_multiplier(regime: str)` はすでに文字列受け取りで抽象化済み

---

## Task 1: `RegimeProvider` インターフェースを定義する

**Files:**
- Create: `src/kabusys/core/__init__.py`
- Create: `src/kabusys/core/interfaces/__init__.py`
- Create: `src/kabusys/core/interfaces/regime.py`
- Test: `tests/test_regime_provider.py`

- [ ] **Step 1: テストを書く（失敗確認用）**

```python
# tests/test_regime_provider.py
"""tests/test_regime_provider.py — RegimeProvider 実装の単体テスト"""
from datetime import date
import duckdb
import pytest

from kabusys.core.interfaces import build_regime_provider
from kabusys.core.interfaces.regime import (
    DatabaseRegimeProvider,
    NullRegimeProvider,
)


@pytest.fixture
def duck_conn():
    import duckdb
    from kabusys.data.schema import init_schema
    conn = init_schema(":memory:")
    yield conn
    conn.close()


# --- NullRegimeProvider ---

def test_null_regime_provider_always_bull():
    p = NullRegimeProvider()
    assert p.get_regime(date.today()) == "bull"


def test_null_regime_provider_any_date():
    p = NullRegimeProvider()
    assert p.get_regime(date(2020, 1, 1)) == "bull"


# --- DatabaseRegimeProvider ---

def test_db_regime_provider_empty_table_returns_bull(duck_conn):
    p = DatabaseRegimeProvider(duck_conn)
    assert p.get_regime(date.today()) == "bull"


def test_db_regime_provider_returns_stored_label(duck_conn):
    duck_conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label, ma200_ratio, macro_sentiment)"
        " VALUES ('2024-09-01', 0.8, 'neutral', 1.05, 0.1)"
    )
    p = DatabaseRegimeProvider(duck_conn)
    assert p.get_regime(date(2024, 9, 1)) == "neutral"


def test_db_regime_provider_bear(duck_conn):
    duck_conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label, ma200_ratio, macro_sentiment)"
        " VALUES ('2024-09-02', -0.5, 'bear', 0.88, -0.4)"
    )
    p = DatabaseRegimeProvider(duck_conn)
    assert p.get_regime(date(2024, 9, 2)) == "bear"


# --- build_regime_provider factory ---

def test_build_regime_provider_disabled_returns_null(duck_conn):
    p = build_regime_provider(duck_conn, enabled=False)
    assert isinstance(p, NullRegimeProvider)


def test_build_regime_provider_enabled_returns_db(duck_conn):
    p = build_regime_provider(duck_conn, enabled=True)
    assert isinstance(p, DatabaseRegimeProvider)
```

- [ ] **Step 2: テスト実行（失敗確認）**

```bash
pytest tests/test_regime_provider.py -v
```

期待: `ModuleNotFoundError: No module named 'kabusys.core'`

- [ ] **Step 3: `src/kabusys/core/__init__.py` を作成**

```python
```
（空ファイル）

- [ ] **Step 4: `src/kabusys/core/interfaces/regime.py` を作成**

```python
"""regime.py — RegimeProvider プロトコルと Core 実装。

Core-only モード（AI Addon 未導入時）は NullRegimeProvider を使う。
AI Addon 有効時は DatabaseRegimeProvider が market_regime テーブルを参照する。
"""
from __future__ import annotations

from datetime import date
from typing import Protocol

import duckdb


class RegimeProvider(Protocol):
    """市場レジームラベルを返すインターフェース。"""

    def get_regime(self, target_date: date) -> str:
        """レジームラベルを返す。データなし時は 'bull' を返す。"""
        ...


class NullRegimeProvider:
    """AI Addon 未導入時のフォールバック。常に 'bull' を返す。"""

    def get_regime(self, target_date: date) -> str:
        return "bull"


class DatabaseRegimeProvider:
    """market_regime テーブルからレジームを取得する Core 実装。"""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def get_regime(self, target_date: date) -> str:
        row = self._conn.execute(
            "SELECT regime_label FROM market_regime WHERE date = ?",
            [target_date],
        ).fetchone()
        return row[0] if row else "bull"
```

- [ ] **Step 5: `src/kabusys/core/interfaces/__init__.py` を作成**

```python
"""core/interfaces — Core が Addon に公開する接続点の定義。"""
from __future__ import annotations

import duckdb

from kabusys.core.interfaces.regime import (
    DatabaseRegimeProvider,
    NullRegimeProvider,
    RegimeProvider,
)

__all__ = [
    "RegimeProvider",
    "NullRegimeProvider",
    "DatabaseRegimeProvider",
    "build_regime_provider",
]


def build_regime_provider(
    conn: duckdb.DuckDBPyConnection,
    enabled: bool,
) -> RegimeProvider:
    """ENABLE_AI_SENTIMENT フラグに基づいて RegimeProvider を返す。"""
    if enabled:
        return DatabaseRegimeProvider(conn)
    return NullRegimeProvider()
```

- [ ] **Step 6: テスト実行（パス確認）**

```bash
pytest tests/test_regime_provider.py -v
```

期待: 8 件 PASSED

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/core/ tests/test_regime_provider.py
git commit -m "feat: RegimeProvider プロトコルと Core 実装を追加 (Issue #271)"
```

---

## Task 2: `signal_generator.py` を `RegimeProvider` に移行する

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py`
- Test: `tests/test_signal_generator.py` （既存テストがパスすることを確認）

- [ ] **Step 1: 既存テストを実行してベースラインを確認**

```bash
pytest tests/test_signal_generator.py -v --tb=short
```

期待: 全件 PASSED（件数を記録する）

- [ ] **Step 2: `signal_generator.py` のインポートを追加**

`signal_generator.py` の先頭 import 群に追加:

```python
from kabusys.core.interfaces import RegimeProvider, build_regime_provider
```

- [ ] **Step 3: `_is_bear_regime()` 関数を削除する**

以下の関数ブロックを丸ごと削除:

```python
def _is_bear_regime(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> bool:
    """market_regime テーブルの regime_label を参照し、Bear 相場か否かを判定する。

    データが存在しない場合は False（安全側：BUY を許可）を返す。
    """
    row = conn.execute(
        "SELECT regime_label FROM market_regime WHERE date = ?",
        [target_date],
    ).fetchone()
    if row is None:
        return False
    return row[0] == "bear"
```

- [ ] **Step 4: `generate_signals()` シグネチャに `regime_provider` を追加**

変更前:
```python
def generate_signals(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> list[dict[str, Any]]:
```

変更後:
```python
def generate_signals(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    *,
    regime_provider: RegimeProvider | None = None,
) -> list[dict[str, Any]]:
```

- [ ] **Step 5: `generate_signals()` 内の AI スコアと regime 参照を書き換える**

`generate_signals()` 関数の先頭付近（weights 取得の直後、features クエリの前）に追加:

```python
    ai_enabled = Settings().enable_ai_sentiment
    if regime_provider is None:
        regime_provider = build_regime_provider(conn, ai_enabled)
```

AI スコアのクエリ部分（`# 2. AI スコア読み込み` セクション）を書き換え:

```python
    # 2. AI スコア読み込み（ENABLE_AI_SENTIMENT=false 時はスキップ）
    if ai_enabled:
        ai_rows = conn.execute(
            "SELECT code, ai_score FROM ai_scores WHERE date = ?",
            [target_date],
        ).fetchall()
        ai_map: dict[str, dict] = {code: {"ai_score": ai} for code, ai in ai_rows}
    else:
        ai_map = {}
```

Bear レジーム判定部分（`# 3. Bear レジーム判定` セクション）を書き換え:

```python
    # 3. Bear レジーム判定
    regime_is_bear = regime_provider.get_regime(target_date) == "bear"
    if regime_is_bear:
        logger.info(
            "generate_signals: Bear レジーム検知 — BUY シグナル抑制 date=%s",
            target_date,
        )
```

ループ前に既存の `ai_enabled = Settings().enable_ai_sentiment` が 1 行あるので削除する（Step 4 で上方に移動済みのため重複となる）。

- [ ] **Step 6: テスト実行**

```bash
pytest tests/test_signal_generator.py -v --tb=short
```

期待: Step 1 と同件数 PASSED

- [ ] **Step 7: ruff チェック**

```bash
python -m ruff check src/kabusys/strategy/signal_generator.py
python -m ruff format --check src/kabusys/strategy/signal_generator.py
```

期待: エラーなし

- [ ] **Step 8: コミット**

```bash
git add src/kabusys/strategy/signal_generator.py
git commit -m "refactor: signal_generator を RegimeProvider に移行し AI スコアをフラグガード化 (Issue #271)"
```

---

## Task 3: `backtest/engine.py` を `RegimeProvider` に移行する

**Files:**
- Modify: `src/kabusys/backtest/engine.py`
- Test: `tests/test_backtest_engine.py` （既存テストがパスすることを確認）

- [ ] **Step 1: 既存テストを実行してベースラインを確認**

```bash
pytest tests/test_backtest_engine.py -v --tb=short
```

期待: 全件 PASSED（件数を記録する）

- [ ] **Step 2: `engine.py` のインポートを追加**

`engine.py` の先頭 import 群に追加:

```python
from kabusys.core.interfaces import RegimeProvider, build_regime_provider
```

- [ ] **Step 3: `_get_daily_regime()` 関数を削除する**

以下の関数ブロックを丸ごと削除:

```python
def _get_daily_regime(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> str:
    """market_regime テーブルから当日レジームを返す。データなしなら 'bull' でフォールバック。

    schema.py の market_regime テーブルのレジーム列名は `regime_label`。
    """
    row = conn.execute(
        "SELECT regime_label FROM market_regime WHERE date = ?", [trading_day]
    ).fetchone()
    return row[0] if row else "bull"
```

- [ ] **Step 4: `_build_backtest_conn()` の AI テーブルコピーを条件化**

変更前:
```python
    date_filtered_tables = ("prices_daily", "features", "ai_scores", "market_regime")
```

変更後:
```python
    from kabusys.config import Settings
    ai_enabled = Settings().enable_ai_sentiment
    core_tables: tuple[str, ...] = ("prices_daily", "features", "market_regime")
    ai_tables: tuple[str, ...] = ("ai_scores",) if ai_enabled else ()
    date_filtered_tables = core_tables + ai_tables
```

- [ ] **Step 5: `_run_backtest_loop()` に `regime_provider` を注入する**

`_run_backtest_loop()` のシグネチャに `regime_provider` を追加し、`_get_daily_regime()` の呼び出しを置き換える。

変更前のシグネチャ:
```python
def _run_backtest_loop(
    conn: duckdb.DuckDBPyConnection,
    ...
) -> BacktestResult:
```

変更後のシグネチャ:
```python
def _run_backtest_loop(
    conn: duckdb.DuckDBPyConnection,
    ...,
    regime_provider: RegimeProvider,
) -> BacktestResult:
```

`_get_daily_regime(conn, trading_day)` の呼び出し箇所を:
```python
    regime = regime_provider.get_regime(trading_day)
```
に置き換える。

- [ ] **Step 6: `run_backtest()` から `regime_provider` を構築して渡す**

`run_backtest()` 内の `_run_backtest_loop()` 呼び出し前に追加:

```python
    from kabusys.config import Settings
    regime_provider = build_regime_provider(bt_conn, Settings().enable_ai_sentiment)
```

`_run_backtest_loop()` の呼び出しに `regime_provider=regime_provider` を追加する。

- [ ] **Step 7: テスト実行**

```bash
pytest tests/test_backtest_engine.py -v --tb=short
```

期待: Step 1 と同件数 PASSED

- [ ] **Step 8: ruff チェック**

```bash
python -m ruff check src/kabusys/backtest/engine.py
python -m ruff format --check src/kabusys/backtest/engine.py
```

期待: エラーなし

- [ ] **Step 9: コミット**

```bash
git add src/kabusys/backtest/engine.py
git commit -m "refactor: backtest/engine を RegimeProvider に移行し AI テーブルコピーをフラグ条件化 (Issue #271)"
```

---

## Task 4: 全体テストとドキュメント更新

**Files:**
- Test: 全テストスイート
- Modify: `documents/00_Architecture/TODO_CoreAddonImportBoundaryAudit.md`

- [ ] **Step 1: 全テストを実行**

```bash
pytest --tb=short -q
```

期待: 全件 PASSED（リグレッションなし）

- [ ] **Step 2: `ENABLE_AI_SENTIMENT=false` での動作確認**

```bash
pytest tests/test_regime_provider.py tests/test_signal_generator.py tests/test_backtest_engine.py -v
```

期待: 全件 PASSED

- [ ] **Step 3: `TODO_CoreAddonImportBoundaryAudit.md` の Section 2.1 と Section 5 を更新**

Section 2.1（AI — 判定）の「データ境界: `未分離`」を「データ境界: `✅ 分離済み（Issue #271）`」に変更する。

Section 5（Issue 3 の次アクション）の item 1・2 に ✅ を追加:
```markdown
1. ~~`signal_generator.py` の `ai_scores` / `market_regime` 参照を抽象化する~~ ✅ 完了（Issue #271 / PR #???）
2. ~~`backtest` の `Core-only` 入力要件を定義する~~ ✅ 完了（Issue #271 / PR #???）
```

- [ ] **Step 4: コミット**

```bash
git add documents/00_Architecture/TODO_CoreAddonImportBoundaryAudit.md
git commit -m "docs: Core-only モード定義の完了を設計書に反映 (Issue #271)"
```
