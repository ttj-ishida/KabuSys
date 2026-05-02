# Position Reconciliation View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DB上のローカル推定ポジション（注文履歴から集計）とブローカー保有ポジションを銘柄単位で比較し、CLEAN/DISCREPANCY を報告する独立CLIコマンドを実装する。

**Architecture:** `collect_position_snapshot(broker, repo)` がブローカーAPIとOrderRepositoryを呼び出し `PositionEntry` リストを返す。`build_report` / `format_*` / `save_report` はすべて純粋関数。エントリーポイント `run_position_reconciliation_report.py` が `--watch` ループを含むI/Oを担当する。`signal_queue_report.py` / `execution_startup_report.py` と同じ分離パターン。

**Tech Stack:** Python 3.10+, SQLite（OrderRepository）, MockBrokerClient（テスト用）, pytest, ruff

---

## File Structure

| ファイル | 役割 |
|---------|------|
| `src/kabusys/operations/position_reconciliation_report.py` | 新規作成。`collect_position_snapshot()` + 純粋関数群 |
| `src/kabusys/run_position_reconciliation_report.py` | 新規作成。CLIエントリーポイント（`--watch` ループ含む） |
| `tests/test_position_reconciliation_report.py` | 新規作成。29件のユニットテスト |

---

## 前提知識（実装者向け）

- `MockBrokerClient(initial_positions=[Position(code="...", qty=..., avg_price=...)])` でブローカーポジションを設定できる
- `OrderRepository(conn)` + `init_orders_db(conn)` でインメモリSQLiteにOrderテーブルを作成できる
- `repo.save(record)` でOrderRecordをDBに挿入できる
- `OrderState.Filled` / `OrderState.PartialFill` の注文のみがローカル推定数量に計上される（`Closed` / `Cancelled` / `Rejected` は `list_active()` に含まれない）
- `collect_position_snapshot()` はブローカー・ローカル双方の union を返す（一致銘柄も含む）
- ステータス定数: `ENTRY_MATCH="MATCH"` / `ENTRY_MISMATCH="MISMATCH"` / `STATUS_CLEAN="CLEAN"` / `STATUS_DISCREPANCY="DISCREPANCY"`

---

## Task 1: テストファイルを作成する（29件・全件 FAIL）

**Files:**
- Create: `tests/test_position_reconciliation_report.py`

- [ ] **Step 1: テストファイルを作成する**

```python
# tests/test_position_reconciliation_report.py
"""position_reconciliation_report のユニットテスト"""
from __future__ import annotations

import json as json_mod
import sqlite3
from datetime import date, datetime, timezone

import pytest

from kabusys.execution.broker_api import Position
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_record import OrderRecord, OrderState
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.operations.position_reconciliation_report import (
    ENTRY_MATCH,
    ENTRY_MISMATCH,
    STATUS_CLEAN,
    STATUS_DISCREPANCY,
    PositionEntry,
    PositionReconciliationReport,
    _generate_warnings,
    build_report,
    collect_position_snapshot,
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
def conn():
    c = sqlite3.connect(":memory:")
    init_orders_db(c)
    yield c
    c.close()


@pytest.fixture()
def repo(conn):
    return OrderRepository(conn)


def _insert_order(
    repo: OrderRepository,
    code: str,
    side: str,
    qty: int,
    cid: str,
    state: OrderState = OrderState.Filled,
    filled_qty: int | None = None,
) -> None:
    """指定状態の注文を DB に挿入するヘルパー。"""
    record = OrderRecord(
        client_order_id=cid,
        signal_id=f"sig_{cid}",
        code=code,
        side=side,
        qty=qty,
        order_type="limit",
        price=1500.0,
        state=state,
        filled_qty=filled_qty if filled_qty is not None else qty,
        broker_order_id=f"BRK_{cid}",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    repo.save(record)


# ---------------------------------------------------------------------------
# collect_position_snapshot
# ---------------------------------------------------------------------------


def test_collect_empty_returns_empty_list(repo):
    broker = MockBrokerClient()
    assert collect_position_snapshot(broker, repo) == []


def test_collect_broker_only_is_mismatch(repo):
    """broker のみ保有（local 注文なし）→ MISMATCH, diff=broker_qty"""
    broker = MockBrokerClient(
        initial_positions=[Position(code="7203", qty=100, avg_price=1500.0)]
    )
    result = collect_position_snapshot(broker, repo)
    assert len(result) == 1
    assert result[0].code == "7203"
    assert result[0].broker_qty == 100
    assert result[0].local_qty == 0
    assert result[0].diff == 100
    assert result[0].status == ENTRY_MISMATCH


def test_collect_local_only_is_mismatch(repo):
    """local に Filled 注文あり、broker に未反映 → MISMATCH, diff 負"""
    broker = MockBrokerClient()
    _insert_order(repo, "9984", "buy", 50, "ord-001")
    result = collect_position_snapshot(broker, repo)
    assert len(result) == 1
    assert result[0].code == "9984"
    assert result[0].broker_qty == 0
    assert result[0].local_qty == 50
    assert result[0].diff == -50
    assert result[0].status == ENTRY_MISMATCH


def test_collect_matching_position_is_match(repo):
    """broker と local が一致 → MATCH, diff=0"""
    broker = MockBrokerClient(
        initial_positions=[Position(code="7203", qty=100, avg_price=1500.0)]
    )
    _insert_order(repo, "7203", "buy", 100, "ord-001")
    result = collect_position_snapshot(broker, repo)
    assert len(result) == 1
    assert result[0].status == ENTRY_MATCH
    assert result[0].diff == 0


def test_collect_qty_mismatch(repo):
    """broker=100, local Filled=80 → MISMATCH, diff=+20"""
    broker = MockBrokerClient(
        initial_positions=[Position(code="7203", qty=100, avg_price=1500.0)]
    )
    _insert_order(repo, "7203", "buy", 80, "ord-001")
    result = collect_position_snapshot(broker, repo)
    assert result[0].broker_qty == 100
    assert result[0].local_qty == 80
    assert result[0].diff == 20
    assert result[0].status == ENTRY_MISMATCH


def test_collect_multiple_codes(repo):
    """複数銘柄: 一致・不一致の混在"""
    broker = MockBrokerClient(
        initial_positions=[
            Position(code="1111", qty=100, avg_price=1000.0),
            Position(code="2222", qty=50, avg_price=2000.0),
        ]
    )
    _insert_order(repo, "1111", "buy", 100, "ord-001")  # MATCH
    _insert_order(repo, "2222", "buy", 30, "ord-002")   # MISMATCH
    result = collect_position_snapshot(broker, repo)
    codes = [e.code for e in result]
    assert "1111" in codes
    assert "2222" in codes
    assert next(e for e in result if e.code == "1111").status == ENTRY_MATCH
    assert next(e for e in result if e.code == "2222").status == ENTRY_MISMATCH


def test_collect_sorted_by_code(repo):
    """結果は code 昇順でソートされる"""
    broker = MockBrokerClient(
        initial_positions=[
            Position(code="9999", qty=10, avg_price=100.0),
            Position(code="1111", qty=10, avg_price=100.0),
            Position(code="5555", qty=10, avg_price=100.0),
        ]
    )
    result = collect_position_snapshot(broker, repo)
    assert [e.code for e in result] == ["1111", "5555", "9999"]


def test_collect_partial_fill_counts(repo):
    """PartialFill の filled_qty がローカル数量に反映される"""
    broker = MockBrokerClient()
    _insert_order(
        repo, "7203", "buy", 100, "ord-001",
        state=OrderState.PartialFill, filled_qty=50,
    )
    result = collect_position_snapshot(broker, repo)
    assert len(result) == 1
    assert result[0].local_qty == 50


def test_collect_sell_reduces_local_qty(repo):
    """buy Filled 100 - sell Filled 30 → local_qty=70"""
    broker = MockBrokerClient()
    _insert_order(repo, "7203", "buy", 100, "ord-001")
    _insert_order(repo, "7203", "sell", 30, "ord-002")
    result = collect_position_snapshot(broker, repo)
    assert len(result) == 1
    assert result[0].local_qty == 70


def test_collect_skips_non_filled_states(repo):
    """OrderCreated は local 集計に含まない"""
    broker = MockBrokerClient()
    _insert_order(
        repo, "7203", "buy", 100, "ord-001",
        state=OrderState.OrderCreated, filled_qty=0,
    )
    result = collect_position_snapshot(broker, repo)
    assert result == []


# ---------------------------------------------------------------------------
# _generate_warnings
# ---------------------------------------------------------------------------


def test_generate_warnings_clean():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=100, diff=0,
                      status=ENTRY_MATCH)
    ]
    assert _generate_warnings(entries) == []


def test_generate_warnings_mismatch_contains_code():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=80, diff=20,
                      status=ENTRY_MISMATCH)
    ]
    warnings = _generate_warnings(entries)
    assert len(warnings) == 1
    assert "7203" in warnings[0]
    assert "100" in warnings[0]
    assert "80" in warnings[0]


def test_generate_warnings_multiple_mismatch():
    entries = [
        PositionEntry(code="1111", broker_qty=100, local_qty=80, diff=20,
                      status=ENTRY_MISMATCH),
        PositionEntry(code="2222", broker_qty=0, local_qty=50, diff=-50,
                      status=ENTRY_MISMATCH),
    ]
    assert len(_generate_warnings(entries)) == 2


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def test_build_report_clean_status():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=100, diff=0,
                      status=ENTRY_MATCH)
    ]
    assert build_report(entries, report_date=TARGET_DATE).status == STATUS_CLEAN


def test_build_report_discrepancy_status():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=80, diff=20,
                      status=ENTRY_MISMATCH)
    ]
    assert build_report(entries, report_date=TARGET_DATE).status == STATUS_DISCREPANCY


def test_build_report_counts():
    entries = [
        PositionEntry(code="1111", broker_qty=100, local_qty=100, diff=0,
                      status=ENTRY_MATCH),
        PositionEntry(code="2222", broker_qty=50, local_qty=30, diff=20,
                      status=ENTRY_MISMATCH),
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    assert report.total_count == 2
    assert report.match_count == 1
    assert report.mismatch_count == 1


def test_build_report_generated_at_utc():
    report = build_report([], report_date=TARGET_DATE)
    assert "+00:00" in report.generated_at


def test_build_report_empty_entries_is_clean():
    report = build_report([], report_date=TARGET_DATE)
    assert report.status == STATUS_CLEAN
    assert report.total_count == 0
    assert report.warnings == []


# ---------------------------------------------------------------------------
# format_cli_summary
# ---------------------------------------------------------------------------


def test_format_cli_clean_no_mark():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=100, diff=0,
                      status=ENTRY_MATCH)
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    s = format_cli_summary(report)
    assert STATUS_CLEAN in s
    assert "2026-04-28" in s
    assert "[!]" not in s


def test_format_cli_discrepancy_shows_mark():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=80, diff=20,
                      status=ENTRY_MISMATCH)
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    s = format_cli_summary(report)
    assert STATUS_DISCREPANCY in s
    assert "[!]" in s


def test_format_cli_shows_all_positions():
    """MATCH 銘柄も出力に含まれる"""
    entries = [
        PositionEntry(code="1111", broker_qty=100, local_qty=100, diff=0,
                      status=ENTRY_MATCH),
        PositionEntry(code="2222", broker_qty=50, local_qty=30, diff=20,
                      status=ENTRY_MISMATCH),
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    s = format_cli_summary(report)
    assert "1111" in s
    assert "2222" in s


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------


def test_format_json_parseable():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=100, diff=0,
                      status=ENTRY_MATCH)
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    data = json_mod.loads(format_json(report))
    for key in ("status", "report_date", "generated_at", "total_count",
                "match_count", "mismatch_count", "positions", "warnings"):
        assert key in data


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------


def test_format_markdown_required_sections():
    report = build_report([], report_date=TARGET_DATE)
    md = format_markdown(report)
    assert "Position Reconciliation" in md
    assert "Overview" in md
    assert "Final Decision" in md


def test_format_markdown_warnings_only_when_discrepancy():
    clean_entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=100, diff=0,
                      status=ENTRY_MATCH)
    ]
    assert "Warnings" not in format_markdown(
        build_report(clean_entries, report_date=TARGET_DATE)
    )
    disc_entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=80, diff=20,
                      status=ENTRY_MISMATCH)
    ]
    assert "Warnings" in format_markdown(
        build_report(disc_entries, report_date=TARGET_DATE)
    )


def test_format_markdown_position_table():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=80, diff=20,
                      status=ENTRY_MISMATCH)
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    md = format_markdown(report)
    assert "7203" in md
    assert "ポジション一覧" in md


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
    report = PositionReconciliationReport(
        report_date="invalid-date",
        generated_at="2026-04-27T00:00:00+00:00",
        status=STATUS_CLEAN,
        total_count=0, match_count=0, mismatch_count=0,
        positions=[], warnings=[],
    )
    with pytest.raises(ValueError, match="Invalid report_date"):
        save_report(report, output_dir=tmp_path)


def test_save_report_impossible_calendar_date_raises(tmp_path):
    report = PositionReconciliationReport(
        report_date="2026-02-30",
        generated_at="2026-04-27T00:00:00+00:00",
        status=STATUS_CLEAN,
        total_count=0, match_count=0, mismatch_count=0,
        positions=[], warnings=[],
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
python -m pytest tests/test_position_reconciliation_report.py -v 2>&1 | head -20
```

期待: `ImportError: cannot import name 'collect_position_snapshot'` 相当のエラーで全件 FAIL

- [ ] **Step 3: コミット**

```bash
git add tests/test_position_reconciliation_report.py
git commit -m "test: position_reconciliation_report の失敗テスト 29 件を追加 (Issue #204)"
```

---

## Task 2: `position_reconciliation_report.py` を実装する

**Files:**
- Create: `src/kabusys/operations/position_reconciliation_report.py`

- [ ] **Step 1: ファイルを作成する**

```python
# src/kabusys/operations/position_reconciliation_report.py
"""Position Reconciliation View レポート生成モジュール。

DB上のローカル推定ポジション（注文履歴から集計）と証券口座（kabuステーション）のポジションを
銘柄単位で突き合わせ、CLEAN / DISCREPANCY ステータスと全銘柄一覧を出力する。
DB 参照は collect_position_snapshot() のみ。それ以外の関数はすべて純粋関数。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

STATUS_CLEAN = "CLEAN"
STATUS_DISCREPANCY = "DISCREPANCY"
ENTRY_MATCH = "MATCH"
ENTRY_MISMATCH = "MISMATCH"


@dataclass
class PositionEntry:
    code: str
    broker_qty: int   # ブローカー側保有数量（未保有なら 0）
    local_qty: int    # ローカルDB推定数量（Filled/PartialFill の net qty）
    diff: int         # broker_qty - local_qty（0 なら一致）
    status: str       # "MATCH" / "MISMATCH"


@dataclass
class PositionReconciliationReport:
    report_date: str       # ISO date（対象日 YYYY-MM-DD）
    generated_at: str      # ISO 8601 UTC タイムスタンプ
    status: str            # "CLEAN" / "DISCREPANCY"
    total_count: int       # union(broker, local) の銘柄数
    match_count: int       # diff == 0 の銘柄数
    mismatch_count: int    # diff != 0 の銘柄数
    positions: list[dict]  # PositionEntry の dict 化リスト
    warnings: list[str]


def collect_position_snapshot(broker, repo) -> list[PositionEntry]:
    """ブローカーAPIとOrderRepositoryからポジションを比較して返す。

    ブローカー側は get_positions()、ローカル側は list_active() の
    Filled / PartialFill 注文から net qty を集計する。
    結果は code 昇順でソートして返す。
    """
    from kabusys.execution.order_record import OrderState

    broker_map: dict[str, int] = {}
    for p in broker.get_positions():
        broker_map[p.code] = broker_map.get(p.code, 0) + p.qty

    local_map: dict[str, int] = {}
    for record in repo.list_active():
        if record.state not in {OrderState.Filled, OrderState.PartialFill}:
            continue
        side = record.side.lower()
        if side == "buy":
            local_map[record.code] = local_map.get(record.code, 0) + record.filled_qty
        elif side == "sell":
            local_map[record.code] = local_map.get(record.code, 0) - record.filled_qty

    entries: list[PositionEntry] = []
    for code in sorted(set(broker_map) | set(local_map)):
        broker_qty = broker_map.get(code, 0)
        local_qty = local_map.get(code, 0)
        diff = broker_qty - local_qty
        entries.append(
            PositionEntry(
                code=code,
                broker_qty=broker_qty,
                local_qty=local_qty,
                diff=diff,
                status=ENTRY_MATCH if diff == 0 else ENTRY_MISMATCH,
            )
        )
    return entries


def _generate_warnings(entries: list[PositionEntry]) -> list[str]:
    warnings: list[str] = []
    for e in entries:
        if e.status == ENTRY_MISMATCH:
            sign = "+" if e.diff > 0 else ""
            warnings.append(
                f"code={e.code}: broker={e.broker_qty}株 / local={e.local_qty}株"
                f" (diff={sign}{e.diff})"
            )
    return warnings


def build_report(
    entries: list[PositionEntry],
    *,
    report_date: date,
) -> PositionReconciliationReport:
    """entries リストから PositionReconciliationReport を構築する（純粋関数）。"""
    match_count = sum(1 for e in entries if e.status == ENTRY_MATCH)
    mismatch_count = sum(1 for e in entries if e.status == ENTRY_MISMATCH)
    total_count = len(entries)
    warnings = _generate_warnings(entries)
    status = STATUS_CLEAN if mismatch_count == 0 else STATUS_DISCREPANCY
    return PositionReconciliationReport(
        report_date=report_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=status,
        total_count=total_count,
        match_count=match_count,
        mismatch_count=mismatch_count,
        positions=[asdict(e) for e in entries],
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------


def format_cli_summary(report: PositionReconciliationReport) -> str:
    """CLI 表示用サマリ文字列を返す。"""
    sep = "=" * 56
    thin = "-" * 56
    lines = [
        f"\n{sep}",
        f"  Position Reconciliation  {report.report_date}",
        f"  Status : {report.status}",
        f"{sep}",
        f"    total     : {report.total_count:>6}",
        f"    match     : {report.match_count:>6}",
        f"    mismatch  : {report.mismatch_count:>6}",
    ]
    if report.positions:
        lines.append(thin)
        lines.append(
            f"  {'':3}{'Code':<8}  {'Broker':>8}  {'Local':>8}  {'Diff':>6}  Status"
        )
        lines.append(
            f"  {'':3}{'-'*8}  {'-'*8}  {'-'*8}  {'-'*6}  {'-'*10}"
        )
        for p in report.positions:
            mark = "[!]" if p["status"] == ENTRY_MISMATCH else "   "
            sign = "+" if p["diff"] > 0 else ""
            diff_str = f"{sign}{p['diff']}" if p["diff"] != 0 else "0"
            lines.append(
                f"  {mark} {p['code']:<8}  {p['broker_qty']:>8}"
                f"  {p['local_qty']:>8}  {diff_str:>6}  {p['status']}"
            )
    if report.warnings:
        lines.append(thin)
        lines.append("  Warnings:")
        for w in report.warnings:
            lines.append(f"    [!] {w}")
    lines.append(f"{sep}\n")
    return "\n".join(lines)


def format_json(report: PositionReconciliationReport) -> str:
    """全フィールドを含む JSON 文字列を返す。"""
    return json.dumps(asdict(report), ensure_ascii=False, indent=2)


def format_markdown(report: PositionReconciliationReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    lines: list[str] = [
        "# Position Reconciliation",
        "",
        "## 1. Overview",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| 対象日 | {report.report_date} |",
        f"| 生成時刻 | {report.generated_at} |",
        f"| **ステータス** | **{report.status}** |",
        f"| 総銘柄数 | {report.total_count} |",
        f"| 一致 | {report.match_count} |",
        f"| 不一致 | {report.mismatch_count} |",
        "",
    ]

    sec = 2
    if report.positions:
        lines += [
            f"## {sec}. ポジション一覧",
            "",
            "| 銘柄コード | Broker | Local | Diff | 状態 |",
            "|-----------|--------|-------|------|------|",
        ]
        for p in report.positions:
            sign = "+" if p["diff"] > 0 else ""
            diff_str = f"{sign}{p['diff']}" if p["diff"] != 0 else "0"
            mark = "⚠️ " if p["status"] == ENTRY_MISMATCH else ""
            lines.append(
                f"| {mark}{p['code']} | {p['broker_qty']}"
                f" | {p['local_qty']} | {diff_str} | {p['status']} |"
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
    if report.status == STATUS_CLEAN:
        lines += [
            f"**{STATUS_CLEAN}** — 全銘柄のポジションが一致しています。",
            "",
            "- 執行エンジンを安全に起動できます。",
        ]
    else:
        lines += [
            f"**{STATUS_DISCREPANCY}** — ポジションに差分が検出されました。",
            "",
            "- 上記 Warnings を確認し、手動調整を行ってください。",
            "- 差分が解消されるまで執行エンジンの起動を控えることを推奨します。",
        ]
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: PositionReconciliationReport,
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/position_reconciliation/{report_date}/ に保存する。

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
    base = (
        Path(output_dir) if output_dir else Path("artifacts") / "position_reconciliation"
    )
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
python -m pytest tests/test_position_reconciliation_report.py -v
```

期待: `29 passed`（全件 PASS）

テストが FAIL する場合は実装を修正すること。

- [ ] **Step 3: Lint・フォーマットを確認する**

```bash
python -m ruff check src/kabusys/operations/position_reconciliation_report.py
python -m ruff format --check src/kabusys/operations/position_reconciliation_report.py
```

差分があれば `python -m ruff format src/kabusys/operations/position_reconciliation_report.py` を実行。

テストファイルも確認:
```bash
python -m ruff format --check tests/test_position_reconciliation_report.py
```

差分があれば `python -m ruff format tests/test_position_reconciliation_report.py` を実行。

- [ ] **Step 4: コミット**

```bash
git add src/kabusys/operations/position_reconciliation_report.py tests/test_position_reconciliation_report.py
git commit -m "feat: position_reconciliation_report モジュールを実装 (Issue #204)"
```

---

## Task 3: `run_position_reconciliation_report.py` エントリーポイントを実装する

**Files:**
- Create: `src/kabusys/run_position_reconciliation_report.py`

- [ ] **Step 1: ファイルを作成する**

```python
# src/kabusys/run_position_reconciliation_report.py
"""Position Reconciliation View エントリーポイント。

使用方法:
    python -m kabusys.run_position_reconciliation_report
    python -m kabusys.run_position_reconciliation_report --date 2026-04-28
    python -m kabusys.run_position_reconciliation_report --save
    python -m kabusys.run_position_reconciliation_report --json
    python -m kabusys.run_position_reconciliation_report --watch
    python -m kabusys.run_position_reconciliation_report --watch --interval 300
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time
from datetime import date

from kabusys.config import Settings
from kabusys.execution.broker_factory import BrokerClientFactory
from kabusys.execution.order_repository import OrderRepository
from kabusys.operations.position_reconciliation_report import (
    STATUS_DISCREPANCY,
    build_report,
    collect_position_snapshot,
    format_cli_summary,
    format_json,
    save_report,
)

logger = logging.getLogger(__name__)


def _run_once(settings: Settings, target_date: date, args: argparse.Namespace) -> str:
    """1回のポーリングを実行してステータス文字列を返す。"""
    sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
    try:
        broker = BrokerClientFactory.create(settings)
        repo = OrderRepository(sqlite_conn)
        entries = collect_position_snapshot(broker, repo)
    finally:
        sqlite_conn.close()

    report = build_report(entries, report_date=target_date)

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

    return report.status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Position Reconciliation View を生成する"
    )
    parser.add_argument(
        "--date",
        type=lambda s: date.fromisoformat(s),
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="対象日（省略時は今日）",
    )
    parser.add_argument(
        "--save", action="store_true", help="artifacts/position_reconciliation/ に保存する"
    )
    parser.add_argument("--json", action="store_true", help="JSON 形式で出力する")
    parser.add_argument(
        "--watch", action="store_true", help="定期ポーリングモードで実行する"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=600,
        metavar="N",
        help="--watch 時のポーリング間隔（秒）（デフォルト: 600）",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    settings = Settings()

    if args.watch:
        while True:
            try:
                _run_once(settings, args.date, args)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("ポーリング中にエラー: %s", e, exc_info=True)
            try:
                time.sleep(args.interval)
            except KeyboardInterrupt:
                break
        return 0

    status = _run_once(settings, args.date, args)
    return 1 if status == STATUS_DISCREPANCY else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Lint・フォーマットを確認する**

```bash
python -m ruff check src/kabusys/run_position_reconciliation_report.py
python -m ruff format --check src/kabusys/run_position_reconciliation_report.py
```

差分があれば `python -m ruff format src/kabusys/run_position_reconciliation_report.py` を実行。

- [ ] **Step 3: 全テストを実行してリグレッションなしを確認する**

```bash
python -m pytest tests/ -q
```

期待: 既存テスト数 + 29 件がすべて PASS、FAIL なし

- [ ] **Step 4: コミット**

```bash
git add src/kabusys/run_position_reconciliation_report.py
git commit -m "feat: run_position_reconciliation_report エントリーポイントを追加 (Issue #204)"
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
  --title "feat: Position Reconciliation View の実装 (Issue #204)" \
  --body "$(cat <<'EOF'
## Summary

- `src/kabusys/operations/position_reconciliation_report.py` を新規作成
  - `collect_position_snapshot()`: ブローカーAPIとOrderRepositoryからポジションを比較取得
  - `build_report()` / `format_cli_summary()` / `format_json()` / `format_markdown()` / `save_report()`: 純粋関数群
  - ステータス: `CLEAN`（全銘柄一致）/ `DISCREPANCY`（1件以上差分あり）
  - 全保有銘柄を表示（一致銘柄も含む）。MISMATCH行に `[!]` マーク
- `src/kabusys/run_position_reconciliation_report.py` を新規作成
  - `--date YYYY-MM-DD` / `--save` / `--json` / `--watch` / `--interval N` オプション
  - `--watch` モード: SQLite接続を各ループで開閉し、エラー時も継続
  - 終了コード: CLEAN=0, DISCREPANCY=1（`--watch` は常に 0）
- `tests/test_position_reconciliation_report.py` に 29 件のユニットテストを追加
- 保存先: `artifacts/position_reconciliation/{date}/summary.json|report.md|warnings.json`

Closes #204

## Test Plan

- [ ] `python -m pytest tests/test_position_reconciliation_report.py -v` → 29 passed
- [ ] `python -m ruff check src/kabusys/operations/position_reconciliation_report.py src/kabusys/run_position_reconciliation_report.py` → All checks passed
- [ ] CI (Lint + Tests) PASS
EOF
)"
```

- [ ] **Step 3: Issue #204 をクローズする**

```bash
gh issue close 204 --comment "PR にて実装完了。"
```
