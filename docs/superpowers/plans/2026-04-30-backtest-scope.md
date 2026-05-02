# 銘柄指定バックテスト機能（BacktestScope）実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `BacktestScope` データクラスを追加し、`generate_signals()` と `run_backtest()` を拡張して指定銘柄のみを対象にバックテストできるようにする。

**Architecture:** `BacktestScope` を `src/kabusys/backtest/engine.py` に定義し、`signal_generator.py` が `scope` 引数で受け取って features フィルタを適用する。`run_backtest()` は `backtest_scope` 引数を受け取り、除外銘柄・有効ユニバースサイズ等のメタデータを `BacktestResult` に記録して返す。`breadth_stop` と `regime` は引き続き全市場ベースで計算する（scope に関わらず変更しない）。

**Tech Stack:** Python 3.10+, DuckDB, `dataclasses.field`, `typing.TYPE_CHECKING`

---

## ファイル構成

| 操作 | パス | 役割 |
|---|---|---|
| Modify | `src/kabusys/backtest/engine.py` | `BacktestScope` データクラス追加、`BacktestResult` にメタデータフィールド追加、`run_backtest()` に `backtest_scope` 引数追加 |
| Modify | `src/kabusys/strategy/signal_generator.py` | `generate_signals()` に `scope` 引数追加、features フィルタ実装 |
| Modify | `src/kabusys/backtest/run.py` | CLI に `--scope-mode`, `--codes`, `--no-preserve-universe-filters` 引数追加 |
| Create | `tests/test_backtest_scope.py` | 全テスト（Task 1〜3 の計 12 件） |

---

### Task 1: `BacktestScope` データクラスと `BacktestResult` メタデータフィールドの追加

**Files:**
- Modify: `src/kabusys/backtest/engine.py:8-37`（import と dataclass 定義）
- Create: `tests/test_backtest_scope.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_backtest_scope.py` を新規作成する:

```python
"""tests/test_backtest_scope.py — BacktestScope / BacktestResult メタデータ テスト"""

from __future__ import annotations

import contextlib
import io
from datetime import date
from unittest.mock import patch

import pytest

from kabusys.backtest.engine import BacktestResult, BacktestScope
from kabusys.backtest.metrics import BacktestMetrics
from kabusys.data.schema import init_schema


def _make_metrics() -> BacktestMetrics:
    return BacktestMetrics(
        cagr=0.0,
        sharpe_ratio=0.0,
        max_drawdown=0.0,
        win_rate=0.0,
        payoff_ratio=0.0,
        total_trades=0,
    )


class TestBacktestScope:
    def test_default_universe_defaults(self):
        """mode='default_universe' のデフォルト値を検証する。"""
        scope = BacktestScope(mode="default_universe")
        assert scope.mode == "default_universe"
        assert scope.codes is None
        assert scope.preserve_universe_filters is True

    def test_manual_codes_mode(self):
        """`mode='manual_codes'` + コード指定が正しく保持される。"""
        scope = BacktestScope(mode="manual_codes", codes=["1234", "5678"])
        assert scope.mode == "manual_codes"
        assert scope.codes == ["1234", "5678"]

    def test_preserve_filters_false(self):
        """`preserve_universe_filters=False` が保持される。"""
        scope = BacktestScope(
            mode="manual_codes", codes=["1234"], preserve_universe_filters=False
        )
        assert scope.preserve_universe_filters is False


class TestBacktestResultMetadata:
    def test_result_default_scope_fields(self):
        """`BacktestResult` がスコープメタデータフィールドをデフォルト値で持つ。"""
        result = BacktestResult(history=[], trades=[], metrics=_make_metrics())
        assert result.scope_mode == "default_universe"
        assert result.scope_codes is None
        assert result.preserve_universe_filters is True
        assert result.effective_universe_size is None
        assert result.excluded_codes == []
        assert result.excluded_reasons == {}

    def test_result_scope_fields_can_be_set(self):
        """スコープメタデータがコンストラクタで設定できる。"""
        result = BacktestResult(
            history=[],
            trades=[],
            metrics=_make_metrics(),
            scope_mode="manual_codes",
            scope_codes=["1234", "5678"],
            preserve_universe_filters=False,
            effective_universe_size=2,
            excluded_codes=["9999"],
            excluded_reasons={"9999": "not in features (universe filter)"},
        )
        assert result.scope_mode == "manual_codes"
        assert result.scope_codes == ["1234", "5678"]
        assert result.preserve_universe_filters is False
        assert result.effective_universe_size == 2
        assert result.excluded_codes == ["9999"]
        assert result.excluded_reasons == {"9999": "not in features (universe filter)"}
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_backtest_scope.py::TestBacktestScope tests/test_backtest_scope.py::TestBacktestResultMetadata -v
```

Expected: `ImportError: cannot import name 'BacktestScope' from 'kabusys.backtest.engine'`

- [ ] **Step 3: `BacktestScope` を定義し `BacktestResult` にフィールドを追加**

`src/kabusys/backtest/engine.py` の import 行（8〜12行目）を次に変更する:

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

import duckdb
```

`BacktestResult` クラス定義（30〜36行目）を次で置き換える（`BacktestScope` を先に定義する）:

```python
@dataclass
class BacktestScope:
    """バックテスト対象スコープの指定。"""

    mode: Literal["default_universe", "manual_codes"]
    codes: list[str] | None = None
    preserve_universe_filters: bool = True


@dataclass
class BacktestResult:
    """run_backtest() の戻り値。"""

    history: list[DailySnapshot]
    trades: list[TradeRecord]
    metrics: BacktestMetrics
    scope_mode: str = "default_universe"
    scope_codes: list[str] | None = None
    preserve_universe_filters: bool = True
    effective_universe_size: int | None = None
    excluded_codes: list[str] = field(default_factory=list)
    excluded_reasons: dict[str, str] = field(default_factory=dict)
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_backtest_scope.py::TestBacktestScope tests/test_backtest_scope.py::TestBacktestResultMetadata -v
```

Expected: 5 passed

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/backtest/engine.py tests/test_backtest_scope.py
git commit -m "feat: BacktestScope データクラスと BacktestResult メタデータを追加 (Issue #190)"
```

---

### Task 2: `generate_signals()` にスコープフィルタを追加

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py:25-30`（import）と `524-598`（シグネチャ + features 読み込み）
- Modify: `tests/test_backtest_scope.py`（テスト追加）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_backtest_scope.py` の末尾に追加する（`import` は追加不要 — Task 1 のファイル先頭で既にインポート済み）:

```python
SCOPE_DATE = date(2026, 4, 1)


@pytest.fixture
def bt_conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def _insert_feature(conn, code: str, d: date) -> None:
    """高スコアの features 行を挿入する。"""
    conn.execute(
        "INSERT INTO features "
        "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
        "VALUES (?, ?, 3.0, 3.0, -3.0, 3.0, 5.0, 3.0)",
        [d, code],
    )


def _insert_regime(conn, d: date, label: str = "bull") -> None:
    score = 0.5 if label == "bull" else -0.5
    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
        [d, score, label],
    )


def _insert_breadth(conn, d: date, stop: bool = False) -> None:
    conn.execute(
        "INSERT INTO market_breadth (date, adv_decline_ratio, ma25_above_pct, breadth_stop) "
        "VALUES (?, ?, ?, ?)",
        [d, 100.0, 0.5, stop],
    )


class TestGenerateSignalsScope:
    def test_scope_none_generates_all_codes(self, bt_conn):
        """scope=None → 既存動作と変わらず全銘柄でシグナル生成。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(bt_conn, SCOPE_DATE)
        _insert_breadth(bt_conn, SCOPE_DATE)
        for code in ["1234", "5678", "9999"]:
            _insert_feature(bt_conn, code, SCOPE_DATE)

        generate_signals(bt_conn, SCOPE_DATE, scope=None)

        rows = bt_conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [SCOPE_DATE]
        ).fetchall()
        codes = {r[0] for r in rows}
        assert {"1234", "5678", "9999"}.issubset(codes)

    def test_scope_manual_codes_excludes_out_of_scope(self, bt_conn):
        """`mode='manual_codes'` → scope.codes 外の銘柄はシグナルに含まれない。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(bt_conn, SCOPE_DATE)
        _insert_breadth(bt_conn, SCOPE_DATE)
        for code in ["1234", "5678", "9999"]:
            _insert_feature(bt_conn, code, SCOPE_DATE)

        scope = BacktestScope(mode="manual_codes", codes=["1234", "5678"])
        generate_signals(bt_conn, SCOPE_DATE, scope=scope)

        rows = bt_conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [SCOPE_DATE]
        ).fetchall()
        codes = {r[0] for r in rows}
        assert "9999" not in codes, "scope 外の銘柄がシグナルに含まれている"
        assert codes.intersection({"1234", "5678"}), "scope 内銘柄のシグナルがない"

    def test_scope_default_universe_same_as_none(self, bt_conn):
        """`mode='default_universe'` → scope=None と同じく全銘柄が対象。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(bt_conn, SCOPE_DATE)
        _insert_breadth(bt_conn, SCOPE_DATE)
        for code in ["1234", "5678"]:
            _insert_feature(bt_conn, code, SCOPE_DATE)

        scope = BacktestScope(mode="default_universe")
        generate_signals(bt_conn, SCOPE_DATE, scope=scope)

        rows = bt_conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [SCOPE_DATE]
        ).fetchall()
        codes = {r[0] for r in rows}
        assert "1234" in codes
        assert "5678" in codes

    def test_scope_empty_codes_generates_no_buy(self, bt_conn):
        """`codes=[]` → features フィルタが空集合 → BUY シグナルなし。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(bt_conn, SCOPE_DATE)
        _insert_breadth(bt_conn, SCOPE_DATE)
        for code in ["1234", "5678"]:
            _insert_feature(bt_conn, code, SCOPE_DATE)

        scope = BacktestScope(mode="manual_codes", codes=[])
        generate_signals(bt_conn, SCOPE_DATE, scope=scope)

        rows = bt_conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [SCOPE_DATE]
        ).fetchall()
        assert len(rows) == 0
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_backtest_scope.py::TestGenerateSignalsScope -v
```

Expected: `TypeError: generate_signals() got an unexpected keyword argument 'scope'`

- [ ] **Step 3: `generate_signals()` に `scope` 引数を追加して実装**

`src/kabusys/strategy/signal_generator.py` の import セクション（25〜30行目）に `TYPE_CHECKING` を追加する:

```python
from __future__ import annotations

import logging
import math
from datetime import date
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kabusys.backtest.engine import BacktestScope
```

`generate_signals()` のシグネチャ（524〜530行目）を変更する:

```python
def generate_signals(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    threshold: float = _DEFAULT_THRESHOLD,
    weights: dict[str, float] | None = None,
    event_dates: dict[date, str] | None = None,
    scope: BacktestScope | None = None,
) -> int:
```

features 読み込みブロック（581〜598行目）を次で置き換える:

```python
    # 1. features 読み込み（scope.mode="manual_codes" の場合は対象銘柄に限定）
    _scope_codes: frozenset[str] | None = None
    if scope is not None and scope.mode == "manual_codes" and scope.codes:
        _scope_codes = frozenset(scope.codes)

    if _scope_codes is not None:
        placeholders = ", ".join(["?" for _ in _scope_codes])
        feat_rows = conn.execute(
            f"""
            SELECT code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev
            FROM features
            WHERE date = ? AND code IN ({placeholders})
            """,
            [target_date, *_scope_codes],
        ).fetchall()
    else:
        feat_rows = conn.execute(
            """
            SELECT code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev
            FROM features
            WHERE date = ?
            """,
            [target_date],
        ).fetchall()
    feat_cols = [
        "code",
        "momentum_20",
        "momentum_60",
        "volatility_20",
        "volume_ratio",
        "per",
        "ma200_dev",
    ]
    features = [dict(zip(feat_cols, r)) for r in feat_rows]
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_backtest_scope.py::TestGenerateSignalsScope -v
```

Expected: 4 passed

- [ ] **Step 5: 既存テストで回帰なし確認**

```bash
python -m pytest tests/test_signal_generator.py tests/test_backtest_scope.py -v
```

Expected: 全テスト pass

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_backtest_scope.py
git commit -m "feat: generate_signals() に scope フィルタを追加 (Issue #190)"
```

---

### Task 3: `run_backtest()` スコープ統合と CLI 拡張

**Files:**
- Modify: `src/kabusys/backtest/engine.py:351-551`（`run_backtest()` シグネチャ・スコープメタデータ計算・戻り値）
- Modify: `src/kabusys/backtest/run.py:30-175`（CLI 引数追加・`run_backtest()` 呼び出し変更）
- Modify: `tests/test_backtest_scope.py`（テスト追加）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_backtest_scope.py` の末尾に追加する（`import` は追加不要 — Task 1 のファイル先頭で既にインポート済み）:

```python
class TestRunBacktestScope:
    def test_run_backtest_has_backtest_scope_param(self):
        """`run_backtest()` が `backtest_scope` 引数を持つ。"""
        import inspect
        from kabusys.backtest.engine import run_backtest

        sig = inspect.signature(run_backtest)
        assert "backtest_scope" in sig.parameters

    def test_run_backtest_returns_default_scope_mode(self):
        """`backtest_scope=None` → BacktestResult.scope_mode == 'default_universe'。"""
        from kabusys.backtest.engine import run_backtest
        from kabusys.data.schema import init_schema

        conn = init_schema(":memory:")
        try:
            result = run_backtest(
                conn,
                start_date=date(2025, 1, 6),
                end_date=date(2025, 1, 7),
                backtest_scope=None,
            )
        finally:
            conn.close()
        assert result.scope_mode == "default_universe"
        assert result.scope_codes is None
        assert result.excluded_codes == []

    def test_run_backtest_manual_scope_sets_metadata(self):
        """`backtest_scope.mode='manual_codes'` → BacktestResult にスコープ情報が入る。"""
        from kabusys.backtest.engine import run_backtest, BacktestScope
        from kabusys.data.schema import init_schema

        conn = init_schema(":memory:")
        scope = BacktestScope(mode="manual_codes", codes=["1234", "5678"])
        try:
            result = run_backtest(
                conn,
                start_date=date(2025, 1, 6),
                end_date=date(2025, 1, 7),
                backtest_scope=scope,
            )
        finally:
            conn.close()
        assert result.scope_mode == "manual_codes"
        assert result.scope_codes == ["1234", "5678"]
        # DB が空なので全コードが除外される
        assert set(result.excluded_codes) == {"1234", "5678"}
        assert result.effective_universe_size == 0


class TestCLIScope:
    def _get_help_text(self) -> str:
        """kabusys.backtest.run の --help 出力を取得する。"""
        from kabusys.backtest import run as run_module

        out = io.StringIO()
        with contextlib.suppress(SystemExit):
            with contextlib.redirect_stdout(out):
                with patch("sys.argv", ["prog", "--help"]):
                    run_module.main()
        return out.getvalue()

    def test_cli_has_scope_mode_arg(self):
        """`--scope-mode` 引数が CLI に登録されている。"""
        assert "--scope-mode" in self._get_help_text()

    def test_cli_has_codes_arg(self):
        """`--codes` 引数が CLI に登録されている。"""
        assert "--codes" in self._get_help_text()

    def test_cli_has_no_preserve_universe_filters_arg(self):
        """`--no-preserve-universe-filters` 引数が CLI に登録されている。"""
        assert "--no-preserve-universe-filters" in self._get_help_text()
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_backtest_scope.py::TestRunBacktestScope tests/test_backtest_scope.py::TestCLIScope -v
```

Expected: `TypeError: run_backtest() got an unexpected keyword argument 'backtest_scope'` と `AssertionError`

- [ ] **Step 3: `run_backtest()` に `backtest_scope` 引数を追加して実装**

`src/kabusys/backtest/engine.py` の `run_backtest()` シグネチャ（351〜366行目）を変更する:

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
    lot_size: int = 100,
    event_dates: dict[date, str] | None = None,
    backtest_scope: BacktestScope | None = None,
) -> BacktestResult:
```

バリデーション後の `bt_conn = _build_backtest_conn(...)` の直後（`try:` ブロック内の `trading_days = get_trading_days(...)` の直後）にスコープメタデータ計算を追加する（現在の 423〜431行目付近）:

```python
        trading_days = get_trading_days(bt_conn, start_date, end_date)
        logger.info(
            "run_backtest: 開始 start=%s end=%s 営業日数=%d 初期資金=%.0f allocation=%s",
            start_date,
            end_date,
            len(trading_days),
            initial_cash,
            allocation_method,
        )

        # スコープメタデータを計算（manual_codes モード時）
        _scope_mode = backtest_scope.mode if backtest_scope else "default_universe"
        _scope_codes = backtest_scope.codes if backtest_scope and backtest_scope.codes else None
        _preserve_filters = backtest_scope.preserve_universe_filters if backtest_scope else True
        _effective_universe_size: int | None = None
        _excluded_codes: list[str] = []
        _excluded_reasons: dict[str, str] = {}

        if _scope_mode == "manual_codes" and _scope_codes:
            placeholders = ", ".join(["?" for _ in _scope_codes])
            available_rows = bt_conn.execute(
                f"SELECT DISTINCT code FROM features WHERE date >= ? AND date <= ? AND code IN ({placeholders})",
                [start_date, end_date, *_scope_codes],
            ).fetchall()
            available: set[str] = {r[0] for r in available_rows}
            _effective_universe_size = len(available)
            for code in _scope_codes:
                if code not in available:
                    _excluded_codes.append(code)
                    _excluded_reasons[code] = (
                        "not in features (universe filter)"
                        if _preserve_filters
                        else "not in features (data not available)"
                    )
            if _excluded_codes:
                logger.warning(
                    "run_backtest: scope で指定された %d 件が features に存在しません: %s",
                    len(_excluded_codes),
                    _excluded_codes,
                )
```

`generate_signals()` の呼び出し（461〜463行目付近）を変更して `scope` を渡す:

```python
            generate_signals(
                bt_conn,
                target_date=trading_day,
                event_dates=event_dates or {},
                scope=backtest_scope,
            )
```

`BacktestResult` の返却（547〜551行目）を変更する:

```python
    return BacktestResult(
        history=simulator.history,
        trades=simulator.trades,
        metrics=metrics,
        scope_mode=_scope_mode,
        scope_codes=_scope_codes,
        preserve_universe_filters=_preserve_filters,
        effective_universe_size=_effective_universe_size,
        excluded_codes=_excluded_codes,
        excluded_reasons=_excluded_reasons,
    )
```

**注意:** `_scope_mode` 等の変数は `try` ブロック内で定義される。`finally: bt_conn.close()` の後にある `metrics = calc_metrics(...)` と `return BacktestResult(...)` は `try` ブロック外にある。`_scope_mode` 等を `try` ブロック外でも参照できるよう、`try` ブロックに入る前にデフォルト値を初期化する:

`bt_conn = _build_backtest_conn(conn, start_date, end_date)` の直後（`try:` より前）に追加する:

```python
    # try ブロック外でも参照できるようデフォルト初期化
    _scope_mode = backtest_scope.mode if backtest_scope else "default_universe"
    _scope_codes = backtest_scope.codes if backtest_scope and backtest_scope.codes else None
    _preserve_filters = backtest_scope.preserve_universe_filters if backtest_scope else True
    _effective_universe_size: int | None = None
    _excluded_codes: list[str] = []
    _excluded_reasons: dict[str, str] = {}
```

そして `try` ブロック内の `trading_days = get_trading_days(...)` の直後のスコープメタデータ計算では、上記変数を再代入する（`_effective_universe_size`, `_excluded_codes`, `_excluded_reasons` のみ更新する）。

- [ ] **Step 4: CLI に引数を追加する**

`src/kabusys/backtest/run.py` のパーサ定義（`parser.add_argument("--db", ...)` の直前）に追加する:

```python
    parser.add_argument(
        "--scope-mode",
        default="default_universe",
        choices=["default_universe", "manual_codes"],
        help="Backtest scope mode [default: default_universe]",
    )
    parser.add_argument(
        "--codes",
        nargs="+",
        default=None,
        help="Stock codes for manual_codes scope (e.g. --codes 7203 9984)",
    )
    parser.add_argument(
        "--no-preserve-universe-filters",
        action="store_true",
        default=False,
        help="Disable universe quality filters for scope codes (diagnostic mode)",
    )
```

`main()` 内の `run_backtest()` 呼び出し（130〜144行目）を変更する:

```python
        from kabusys.data.schema import init_schema
        from kabusys.backtest.engine import run_backtest, BacktestScope
        from kabusys.backtest.report import (
            build_report,
            format_cli_summary,
            format_json,
            format_markdown,
            save_report,
        )

        conn = init_schema(args.db)
        try:
            scope: BacktestScope | None = None
            if args.scope_mode == "manual_codes":
                if not args.codes:
                    logger.error("--codes は --scope-mode=manual_codes のとき必須です")
                    sys.exit(1)
                scope = BacktestScope(
                    mode="manual_codes",
                    codes=args.codes,
                    preserve_universe_filters=not args.no_preserve_universe_filters,
                )

            result = run_backtest(
                conn=conn,
                start_date=start_date,
                end_date=end_date,
                initial_cash=args.cash,
                slippage_rate=args.slippage,
                commission_rate=args.commission,
                max_position_pct=args.max_position_pct,
                allocation_method=args.allocation_method,
                max_utilization=args.max_utilization,
                max_positions=args.max_positions,
                risk_pct=args.risk_pct,
                stop_loss_pct=args.stop_loss_pct,
                lot_size=args.lot_size,
                backtest_scope=scope,
            )
        finally:
            conn.close()
```

- [ ] **Step 5: テストが通ることを確認**

```bash
python -m pytest tests/test_backtest_scope.py -v
```

Expected: 12 passed

- [ ] **Step 6: ruff チェック**

```bash
python -m ruff check src/kabusys/backtest/engine.py src/kabusys/strategy/signal_generator.py src/kabusys/backtest/run.py tests/test_backtest_scope.py
python -m ruff format --check src/kabusys/backtest/engine.py src/kabusys/strategy/signal_generator.py src/kabusys/backtest/run.py tests/test_backtest_scope.py
```

Expected: `All checks passed!` / `N files already formatted`

ruff format が差分を出した場合は `python -m ruff format` を実行してから再チェックする。

- [ ] **Step 7: 全テストで回帰なし確認**

```bash
python -m pytest tests/test_signal_generator.py tests/test_backtest_framework.py tests/test_backtest_report.py tests/test_backtest_scope.py -v
```

Expected: 全テスト pass

- [ ] **Step 8: コミット**

```bash
git add src/kabusys/backtest/engine.py src/kabusys/strategy/signal_generator.py src/kabusys/backtest/run.py tests/test_backtest_scope.py
git commit -m "feat: run_backtest() に backtest_scope を追加し CLI を拡張 (Issue #190)"
```
