# Signal Queue Confirmation View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 翌営業日の発注予定シグナルをDuckDBから読み取り、BUY/SELL件数・銘柄一覧をCLI/Markdown/JSONで出力する確認レポートを実装する。

**Architecture:** `signals LEFT JOIN portfolio_targets` をDuckDBで照会する `collect_signals()` と、その結果を受け取る純粋関数群（`build_report` / `format_*` / `save_report`）を `signal_queue_report.py` に集約する。エントリーポイント `run_signal_queue_report.py` がDB接続・引数解析・出力を担う。`pre_market_report.py` / `execution_startup_report.py` と同じ分離パターンに従う。

**Tech Stack:** Python 3.10+, DuckDB（`signals` + `portfolio_targets` テーブル）, pytest, ruff

---

## File Structure

| ファイル | 役割 |
|---------|------|
| `src/kabusys/operations/signal_queue_report.py` | 新規作成。`collect_signals()`（DuckDB照会）+ 純粋関数（`build_report` / `format_*` / `save_report`） |
| `src/kabusys/run_signal_queue_report.py` | 新規作成。CLIエントリーポイント。DB接続・引数解析・出力 |
| `tests/test_signal_queue_report.py` | 新規作成。21件のユニットテスト |

---

## 前提知識（実装者向け）

- `signals` テーブル（DuckDB）: `date DATE, code VARCHAR, side VARCHAR('buy'|'sell'), score DOUBLE, signal_rank INTEGER, size_multiplier DOUBLE`
- `portfolio_targets` テーブル（DuckDB）: `date DATE, code VARCHAR, target_weight DOUBLE, target_size BIGINT`
- `signal_queue_report.py` の中で DB に触れるのは `collect_signals()` のみ。他は全て純粋関数。
- `DuckDB` は `?` プレースホルダーをサポートする。
- 保存先: `artifacts/signal_queue/{report_date}/summary.json|report.md|warnings.json`
- ステータス: `READY`（シグナルあり） / `EMPTY`（シグナルなし）

---

## Task 1: テストファイルを作成する（21件・全件 FAIL）

**Files:**
- Create: `tests/test_signal_queue_report.py`

- [ ] **Step 1: テストファイルを作成する**

```python
# tests/test_signal_queue_report.py
"""signal_queue_report のユニットテスト"""
from __future__ import annotations

import json as json_mod
from datetime import date

import duckdb
import pytest

from kabusys.operations.signal_queue_report import (
    SignalQueueReport,
    _generate_warnings,
    build_report,
    collect_signals,
    format_cli_summary,
    format_json,
    format_markdown,
    save_report,
)

TARGET_DATE = date(2026, 4, 28)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    """signals + portfolio_targets テーブルを持つインメモリ DuckDB 接続。"""
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE signals (
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            score DOUBLE,
            signal_rank INTEGER,
            size_multiplier DOUBLE NOT NULL DEFAULT 1.0,
            PRIMARY KEY (date, code, side)
        )
    """)
    conn.execute("""
        CREATE TABLE portfolio_targets (
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            target_weight DOUBLE,
            target_size BIGINT,
            PRIMARY KEY (date, code)
        )
    """)
    yield conn
    conn.close()


def _sig(conn, d, code, side, rank=None, score=None):
    conn.execute(
        "INSERT INTO signals (date, code, side, signal_rank, score) VALUES (?, ?, ?, ?, ?)",
        [d, code, side, rank, score],
    )


def _tgt(conn, d, code, size=None, weight=None):
    conn.execute(
        "INSERT INTO portfolio_targets (date, code, target_size, target_weight) VALUES (?, ?, ?, ?)",
        [d, code, size, weight],
    )


# ---------------------------------------------------------------------------
# collect_signals
# ---------------------------------------------------------------------------


def test_collect_signals_empty(db):
    assert collect_signals(db, TARGET_DATE) == []


def test_collect_signals_buy_and_sell(db):
    _sig(db, TARGET_DATE, "7203", "buy", rank=1)
    _sig(db, TARGET_DATE, "9984", "sell", rank=2)
    _tgt(db, TARGET_DATE, "7203", size=100, weight=0.05)
    _tgt(db, TARGET_DATE, "9984", size=50, weight=0.03)

    result = collect_signals(db, TARGET_DATE)
    assert len(result) == 2
    assert result[0]["code"] == "7203"
    assert result[0]["side"] == "buy"
    assert result[0]["target_size"] == 100
    assert result[0]["target_weight"] == pytest.approx(0.05)
    assert result[0]["signal_rank"] == 1


def test_collect_signals_left_join_missing_target(db):
    """portfolio_targets にない銘柄でも取得できる（LEFT JOIN）。"""
    _sig(db, TARGET_DATE, "1234", "buy", rank=1)
    result = collect_signals(db, TARGET_DATE)
    assert len(result) == 1
    assert result[0]["target_size"] is None
    assert result[0]["target_weight"] is None


def test_collect_signals_filters_by_date(db):
    """対象日以外のシグナルは取得されない。"""
    _sig(db, date(2026, 4, 27), "7203", "buy")
    assert collect_signals(db, TARGET_DATE) == []


def test_collect_signals_sorted_by_rank(db):
    """signal_rank 昇順で返される。"""
    _sig(db, TARGET_DATE, "9999", "buy", rank=3)
    _sig(db, TARGET_DATE, "1111", "buy", rank=1)
    _sig(db, TARGET_DATE, "5555", "buy", rank=2)
    result = collect_signals(db, TARGET_DATE)
    assert [r["signal_rank"] for r in result] == [1, 2, 3]


# ---------------------------------------------------------------------------
# _generate_warnings
# ---------------------------------------------------------------------------


def test_generate_warnings_empty():
    w = _generate_warnings(signals=[], total_count=0)
    assert len(w) == 1
    assert "シグナルがありません" in w[0]


def test_generate_warnings_ready_no_warnings():
    sigs = [{"code": "7203", "side": "buy", "target_size": 100,
             "target_weight": 0.05, "signal_rank": 1}]
    assert _generate_warnings(signals=sigs, total_count=1) == []


def test_generate_warnings_buy_no_size():
    sigs = [{"code": "7203", "side": "buy", "target_size": None,
             "target_weight": 0.05, "signal_rank": 1}]
    w = _generate_warnings(signals=sigs, total_count=1)
    assert any("7203" in warning for warning in w)


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def test_build_report_ready():
    sigs = [
        {"code": "7203", "side": "buy", "target_size": 100,
         "target_weight": 0.05, "signal_rank": 1},
        {"code": "9984", "side": "sell", "target_size": 50,
         "target_weight": 0.03, "signal_rank": 2},
    ]
    report = build_report(sigs, report_date=TARGET_DATE)
    assert report.status == "READY"
    assert report.total_count == 2
    assert report.buy_count == 1
    assert report.sell_count == 1
    assert report.report_date == "2026-04-28"


def test_build_report_empty():
    report = build_report([], report_date=TARGET_DATE)
    assert report.status == "EMPTY"
    assert report.total_count == 0
    assert report.buy_count == 0
    assert report.sell_count == 0
    assert len(report.warnings) > 0


def test_build_report_generated_at_utc():
    report = build_report([], report_date=TARGET_DATE)
    assert "+00:00" in report.generated_at


def test_build_report_counts_correctly():
    sigs = [
        {"code": "1111", "side": "buy", "target_size": 100,
         "target_weight": 0.05, "signal_rank": 1},
        {"code": "2222", "side": "buy", "target_size": 200,
         "target_weight": 0.10, "signal_rank": 2},
        {"code": "3333", "side": "sell", "target_size": 50,
         "target_weight": 0.03, "signal_rank": 3},
    ]
    report = build_report(sigs, report_date=TARGET_DATE)
    assert report.buy_count == 2
    assert report.sell_count == 1
    assert report.total_count == 3


# ---------------------------------------------------------------------------
# format_cli_summary
# ---------------------------------------------------------------------------


def test_format_cli_summary_ready():
    sigs = [{"code": "7203", "side": "buy", "target_size": 100,
             "target_weight": 0.05, "signal_rank": 1}]
    report = build_report(sigs, report_date=TARGET_DATE)
    s = format_cli_summary(report)
    assert "READY" in s
    assert "2026-04-28" in s
    assert "7203" in s


def test_format_cli_summary_empty_shows_warning():
    report = build_report([], report_date=TARGET_DATE)
    s = format_cli_summary(report)
    assert "EMPTY" in s
    assert "Warnings" in s


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------


def test_format_json_parseable():
    report = build_report([], report_date=TARGET_DATE)
    data = json_mod.loads(format_json(report))
    for key in ("status", "report_date", "generated_at",
                "total_count", "buy_count", "sell_count", "signals", "warnings"):
        assert key in data


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------


def test_format_markdown_ready_has_signal_table():
    sigs = [{"code": "7203", "side": "buy", "target_size": 100,
             "target_weight": 0.05, "signal_rank": 1}]
    report = build_report(sigs, report_date=TARGET_DATE)
    md = format_markdown(report)
    assert "Signal Queue Confirmation" in md
    assert "Signal 一覧" in md
    assert "7203" in md
    assert "5.0%" in md


def test_format_markdown_empty_no_signal_table():
    report = build_report([], report_date=TARGET_DATE)
    md = format_markdown(report)
    assert "EMPTY" in md
    assert "Signal 一覧" not in md


def test_format_markdown_final_decision_section():
    report = build_report([], report_date=TARGET_DATE)
    md = format_markdown(report)
    assert "Final Decision" in md


# ---------------------------------------------------------------------------
# save_report
# ---------------------------------------------------------------------------


def test_save_report_creates_three_files(tmp_path):
    report = build_report([], report_date=TARGET_DATE)
    dest = save_report(report, output_dir=tmp_path)
    assert (dest / "summary.json").exists()
    assert (dest / "report.md").exists()
    assert (dest / "warnings.json").exists()


def test_save_report_invalid_format_raises(tmp_path):
    report = SignalQueueReport(
        report_date="invalid-date",
        generated_at="2026-04-27T00:00:00+00:00",
        status="EMPTY",
        total_count=0, buy_count=0, sell_count=0,
        signals=[], warnings=[],
    )
    with pytest.raises(ValueError, match="Invalid report_date"):
        save_report(report, output_dir=tmp_path)


def test_save_report_impossible_calendar_date_raises(tmp_path):
    report = SignalQueueReport(
        report_date="2026-02-30",
        generated_at="2026-04-27T00:00:00+00:00",
        status="EMPTY",
        total_count=0, buy_count=0, sell_count=0,
        signals=[], warnings=[],
    )
    with pytest.raises(ValueError, match="Invalid report_date"):
        save_report(report, output_dir=tmp_path)


def test_save_report_idempotent(tmp_path):
    report = build_report([], report_date=TARGET_DATE)
    save_report(report, output_dir=tmp_path)
    save_report(report, output_dir=tmp_path)
    assert (tmp_path / "2026-04-28" / "summary.json").exists()
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
python -m pytest tests/test_signal_queue_report.py -v
```

期待: `ImportError: cannot import name 'SignalQueueReport' from 'kabusys.operations.signal_queue_report'` 相当のエラーで全件 FAIL

- [ ] **Step 3: コミット**

```bash
git add tests/test_signal_queue_report.py
git commit -m "test: signal_queue_report の失敗テスト 21 件を追加 (Issue #202)"
```

---

## Task 2: `signal_queue_report.py` を実装する

**Files:**
- Create: `src/kabusys/operations/signal_queue_report.py`

- [ ] **Step 1: ファイルを作成する**

```python
# src/kabusys/operations/signal_queue_report.py
"""Signal Queue Confirmation View レポート生成モジュール。

翌営業日の発注予定シグナルを DuckDB の signals / portfolio_targets テーブルから読み取り、
READY / EMPTY ステータスと銘柄一覧を出力する。
DB 参照は collect_signals() のみ。それ以外の関数はすべて純粋関数。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

STATUS_READY = "READY"
STATUS_EMPTY = "EMPTY"


@dataclass
class SignalQueueReport:
    report_date: str       # ISO date（対象日）
    generated_at: str      # ISO 8601 UTC
    status: str            # READY / EMPTY
    total_count: int       # シグナル総数
    buy_count: int         # BUY シグナル数
    sell_count: int        # SELL シグナル数
    signals: list[dict]    # [{code, side, target_size, target_weight, signal_rank}]
    warnings: list[str]


def collect_signals(conn, target_date: date) -> list[dict]:
    """DuckDB から対象日のシグナルを取得する。

    signals LEFT JOIN portfolio_targets で target_size / target_weight を付与し、
    signal_rank 昇順・side 昇順でソートして返す。
    """
    rows = conn.execute(
        """
        SELECT s.code, s.side, pt.target_size, pt.target_weight, s.signal_rank
        FROM signals s
        LEFT JOIN portfolio_targets pt
               ON s.date = pt.date AND s.code = pt.code
        WHERE s.date = ?
        ORDER BY s.signal_rank ASC NULLS LAST, s.side
        """,
        [target_date],
    ).fetchall()
    return [
        {
            "code": row[0],
            "side": row[1],
            "target_size": row[2],
            "target_weight": row[3],
            "signal_rank": row[4],
        }
        for row in rows
    ]


def _generate_warnings(*, signals: list[dict], total_count: int) -> list[str]:
    warnings: list[str] = []
    if total_count == 0:
        warnings.append("翌営業日のシグナルがありません（自動執行は行われません）")
    buy_no_size = [s["code"] for s in signals if s["side"] == "buy" and s["target_size"] is None]
    if buy_no_size:
        warnings.append(f"target_size 未設定の BUY シグナル: {', '.join(buy_no_size)}")
    return warnings


def build_report(
    signals: list[dict],
    *,
    report_date: date,
) -> SignalQueueReport:
    """signals リストから SignalQueueReport を構築する（純粋関数）。"""
    buy_count = sum(1 for s in signals if s["side"] == "buy")
    sell_count = sum(1 for s in signals if s["side"] == "sell")
    total_count = len(signals)
    warnings = _generate_warnings(signals=signals, total_count=total_count)
    status = STATUS_READY if total_count > 0 else STATUS_EMPTY
    return SignalQueueReport(
        report_date=report_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=status,
        total_count=total_count,
        buy_count=buy_count,
        sell_count=sell_count,
        signals=signals,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------


def format_cli_summary(report: SignalQueueReport) -> str:
    """CLI 表示用サマリ文字列を返す。"""
    sep = "=" * 52
    thin = "-" * 52
    lines = [
        f"\n{sep}",
        f"  Signal Queue Confirmation  {report.report_date}",
        f"  Status : {report.status}",
        f"{sep}",
        f"    total  : {report.total_count:>6}",
        f"    buy    : {report.buy_count:>6}",
        f"    sell   : {report.sell_count:>6}",
    ]
    if report.signals:
        lines.append(thin)
        lines.append(f"  {'Code':<8}  {'Side':<5}  {'Shares':>8}  {'Weight':>8}  {'Rank':>5}")
        lines.append(f"  {'-'*8}  {'-'*5}  {'-'*8}  {'-'*8}  {'-'*5}")
        for s in report.signals:
            weight_str = (
                f"{s['target_weight'] * 100:.1f}%"
                if s["target_weight"] is not None
                else "N/A"
            )
            size_str = str(s["target_size"]) if s["target_size"] is not None else "N/A"
            rank_str = str(s["signal_rank"]) if s["signal_rank"] is not None else "-"
            lines.append(
                f"  {s['code']:<8}  {s['side']:<5}  {size_str:>8}  {weight_str:>8}  {rank_str:>5}"
            )
    if report.warnings:
        lines.append(thin)
        lines.append("  Warnings:")
        for w in report.warnings:
            lines.append(f"    [!] {w}")
    lines.append(f"{sep}\n")
    return "\n".join(lines)


def format_json(report: SignalQueueReport) -> str:
    """全フィールドを含む JSON 文字列を返す。"""
    return json.dumps(asdict(report), ensure_ascii=False, indent=2)


def format_markdown(report: SignalQueueReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    lines: list[str] = [
        "# Signal Queue Confirmation",
        "",
        "## 1. Overview",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| 対象日 | {report.report_date} |",
        f"| 生成時刻 | {report.generated_at} |",
        f"| **ステータス** | **{report.status}** |",
        f"| total | {report.total_count} |",
        f"| BUY | {report.buy_count} |",
        f"| SELL | {report.sell_count} |",
        "",
    ]

    sec = 2
    if report.signals:
        lines += [
            f"## {sec}. Signal 一覧",
            "",
            "| 銘柄コード | 方向 | 株数 | 目標ウェイト | ランク |",
            "|-----------|------|------|------------|-------|",
        ]
        for s in report.signals:
            weight_str = (
                f"{s['target_weight'] * 100:.1f}%"
                if s["target_weight"] is not None
                else "N/A"
            )
            size_str = str(s["target_size"]) if s["target_size"] is not None else "N/A"
            rank_str = str(s["signal_rank"]) if s["signal_rank"] is not None else "-"
            lines.append(
                f"| {s['code']} | {s['side']} | {size_str} | {weight_str} | {rank_str} |"
            )
        lines.append("")
        sec += 1

    if report.warnings:
        lines += [f"## {sec}. Warnings", ""]
        for w in report.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")
        sec += 1

    lines += [f"## {sec}. Final Decision", ""]
    if report.status == STATUS_READY:
        lines += [
            f"**{STATUS_READY}** — 発注シグナルが存在します。Execution 起動後に自動執行されます。",
            "",
            "- 上記一覧を確認し、意図しない銘柄・方向がある場合は"
            " `data/stop_requested.flag` を作成して自動執行を停止してください。",
        ]
    else:
        lines += [
            f"**{STATUS_EMPTY}** — 翌営業日のシグナルがありません。",
            "",
            "- 夜間バッチが正常に完了しているか確認してください。",
        ]
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: SignalQueueReport,
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/signal_queue/{report_date}/ に保存する。

    保存ファイル:
        summary.json    全指標 JSON
        report.md       Markdown レポート
        warnings.json   警告リスト JSON

    同一 report_date で再実行した場合は上書き（exist_ok=True）。
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report.report_date):
        raise ValueError(f"Invalid report_date: {report.report_date!r}")
    try:
        date.fromisoformat(report.report_date)
    except ValueError:
        raise ValueError(
            f"Invalid report_date (not a valid calendar date): {report.report_date!r}"
        )
    base = Path(output_dir) if output_dir else Path("artifacts") / "signal_queue"
    run_dir = base / report.report_date
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "summary.json").write_text(format_json(report), encoding="utf-8")
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")
    (run_dir / "warnings.json").write_text(
        json.dumps(report.warnings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return run_dir
```

- [ ] **Step 2: テストを実行して全件 PASS を確認する**

```bash
python -m pytest tests/test_signal_queue_report.py -v
```

期待: `21 passed`

- [ ] **Step 3: Lint・フォーマットを確認する**

```bash
python -m ruff check src/kabusys/operations/signal_queue_report.py
python -m ruff format --check src/kabusys/operations/signal_queue_report.py
```

期待: `All checks passed!` / `1 file already formatted`（差分があれば `ruff format` を実行）

- [ ] **Step 4: コミット**

```bash
git add src/kabusys/operations/signal_queue_report.py tests/test_signal_queue_report.py
git commit -m "feat: signal_queue_report モジュールを実装 (Issue #202)"
```

---

## Task 3: `run_signal_queue_report.py` エントリーポイントを実装する

**Files:**
- Create: `src/kabusys/run_signal_queue_report.py`

- [ ] **Step 1: ファイルを作成する**

```python
# src/kabusys/run_signal_queue_report.py
"""Signal Queue Confirmation View エントリーポイント。

使用方法:
    python -m kabusys.run_signal_queue_report
    python -m kabusys.run_signal_queue_report --date 2026-04-28
    python -m kabusys.run_signal_queue_report --save
    python -m kabusys.run_signal_queue_report --json
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

import duckdb

from kabusys.config import Settings
from kabusys.operations.signal_queue_report import (
    build_report,
    collect_signals,
    format_cli_summary,
    format_json,
    save_report,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Signal Queue Confirmation View を生成する")
    parser.add_argument(
        "--date",
        type=lambda s: date.fromisoformat(s),
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="対象日（省略時は今日）",
    )
    parser.add_argument("--save", action="store_true", help="artifacts/signal_queue/ に保存する")
    parser.add_argument("--json", action="store_true", help="JSON 形式で出力する")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        signals = collect_signals(conn, args.date)
    finally:
        conn.close()

    report = build_report(signals, report_date=args.date)

    if args.json:
        print(format_json(report))
    else:
        print(format_cli_summary(report))

    if args.save:
        run_dir = save_report(report)
        dest_msg = f"保存先: {run_dir}"
        if args.json:
            sys.stderr.write(dest_msg + "\n")
        else:
            print(dest_msg)

    return 0 if report.status == "READY" else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Lint・フォーマットを確認する**

```bash
python -m ruff check src/kabusys/run_signal_queue_report.py
python -m ruff format --check src/kabusys/run_signal_queue_report.py
```

期待: `All checks passed!` / `1 file already formatted`

- [ ] **Step 3: 全テストを実行してリグレッションなしを確認する**

```bash
python -m pytest tests/ -q
```

期待: `21 passed` 以上（既存テスト数 + 新規 21 件）、FAIL なし

- [ ] **Step 4: コミット**

```bash
git add src/kabusys/run_signal_queue_report.py
git commit -m "feat: run_signal_queue_report エントリーポイントを追加 (Issue #202)"
```

---

## Task 4: PR を作成して Issue をクローズする

**Files:** なし（git 操作のみ）

- [ ] **Step 1: リモートにプッシュする**

```bash
git push
```

- [ ] **Step 2: PR を作成する**

```bash
gh pr create \
  --title "feat: Signal Queue Confirmation View の実装 (Issue #202)" \
  --body "$(cat <<'EOF'
## Summary

- `src/kabusys/operations/signal_queue_report.py` を新規作成
  - `collect_signals()`: DuckDB `signals LEFT JOIN portfolio_targets` から翌営業日シグナルを取得
  - `build_report()` / `format_cli_summary()` / `format_json()` / `format_markdown()` / `save_report()`: 純粋関数群
  - ステータス: `READY`（シグナルあり）/ `EMPTY`（シグナルなし）
- `src/kabusys/run_signal_queue_report.py` を新規作成
  - `--date YYYY-MM-DD`（省略時は今日）/ `--save` / `--json` オプション
  - 終了コード: READY=0, EMPTY=1
- `tests/test_signal_queue_report.py` に 21 件のユニットテストを追加
- 保存先: `artifacts/signal_queue/{date}/summary.json|report.md|warnings.json`

Closes #202

## Test Plan

- [ ] `python -m pytest tests/test_signal_queue_report.py -v` → 21 passed
- [ ] `python -m ruff check src/kabusys/operations/signal_queue_report.py src/kabusys/run_signal_queue_report.py` → All checks passed
- [ ] CI (Lint + Tests) PASS
EOF
)"
```

- [ ] **Step 3: Issue #202 をクローズする**

```bash
gh issue close 202 --comment "PR にて実装完了。"
```
