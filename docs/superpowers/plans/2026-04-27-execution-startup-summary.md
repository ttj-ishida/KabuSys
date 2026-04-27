# Execution Startup Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `run_execution.py` が Reconciler 完了直後に `READY / READY_WITH_WARNINGS / BLOCKED` を含む起動サマリを stdout 出力 + `artifacts/execution_startup/{date}/` に3ファイル保存する。

**Architecture:** `execution_startup_report.py`（純粋関数モジュール）を新規作成し、`night_batch_report.py` と同パターンで実装する。`run_execution.py` では Reconciler を engine に渡す前に `reconciler.run()` を呼び出し、その戻り値でレポートを生成する。engine には `reconciler=None` を渡してレポートと二重実行を避ける。

**Tech Stack:** Python 3.10+, dataclasses, pathlib, json, re（外部依存なし）

---

## File Map

| ファイル | 区分 | 変更内容 |
|---------|------|---------|
| `tests/test_execution_startup_report.py` | 新規 | 純粋関数ユニットテスト |
| `src/kabusys/operations/execution_startup_report.py` | 新規 | データクラス・判定・フォーマッター・保存 |
| `src/kabusys/run_execution.py` | 既存修正 | reconciler.run() 呼び出し位置変更 + レポート生成追加 |

---

### Task 1: テストファイルを作成する

**Files:**
- Create: `tests/test_execution_startup_report.py`

- [ ] **Step 1: テストファイルを書く**

`tests/test_execution_startup_report.py` を以下の内容で作成する:

```python
"""execution_startup_report のユニットテスト"""

from __future__ import annotations

import json as json_mod
from datetime import date

import pytest

from kabusys.execution.reconciler import PositionDiscrepancy, ReconcileResult
from kabusys.operations.execution_startup_report import (
    ExecutionStartupReport,
    _determine_status,
    _generate_warnings,
    build_report,
    format_cli_summary,
    format_json,
    format_markdown,
    save_report,
)


# ---------------------------------------------------------------------------
# _determine_status
# ---------------------------------------------------------------------------


def test_determine_status_blocked_by_no_status():
    assert _determine_status(orders_no_status=1, position_discrepancies_count=0) == "BLOCKED"


def test_determine_status_blocked_even_with_discrepancies():
    """orders_no_status > 0 は discrepancies があっても BLOCKED。"""
    assert _determine_status(orders_no_status=2, position_discrepancies_count=3) == "BLOCKED"


def test_determine_status_ready_with_warnings():
    assert (
        _determine_status(orders_no_status=0, position_discrepancies_count=1)
        == "READY_WITH_WARNINGS"
    )


def test_determine_status_ready():
    assert _determine_status(orders_no_status=0, position_discrepancies_count=0) == "READY"


# ---------------------------------------------------------------------------
# _generate_warnings
# ---------------------------------------------------------------------------


def test_generate_warnings_no_issues():
    assert _generate_warnings(orders_no_status=0, position_discrepancies=[]) == []


def test_generate_warnings_orders_no_status():
    w = _generate_warnings(orders_no_status=2, position_discrepancies=[])
    assert len(w) == 1
    assert "2" in w[0]


def test_generate_warnings_position_discrepancy():
    disc = [{"code": "1234", "broker_qty": 100, "local_qty": 80, "diff": 20}]
    w = _generate_warnings(orders_no_status=0, position_discrepancies=disc)
    assert len(w) == 1
    assert "1234" in w[0]


def test_generate_warnings_both():
    disc = [{"code": "1234", "broker_qty": 100, "local_qty": 80, "diff": 20}]
    w = _generate_warnings(orders_no_status=1, position_discrepancies=disc)
    assert len(w) == 2


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def test_build_report_ready():
    result = ReconcileResult(orders_synced=3, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    assert report.status == "READY"
    assert report.orders_synced == 3
    assert report.orders_no_status == 0
    assert report.position_discrepancies == []
    assert report.warnings == []
    assert report.startup_date == "2026-04-27"


def test_build_report_blocked():
    result = ReconcileResult(orders_synced=0, orders_no_status=1, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    assert report.status == "BLOCKED"
    assert len(report.warnings) > 0


def test_build_report_ready_with_warnings():
    discrepancy = PositionDiscrepancy(code="1234", broker_qty=100, local_qty=80, diff=20)
    result = ReconcileResult(
        orders_synced=2, orders_no_status=0, position_discrepancies=[discrepancy]
    )
    report = build_report(result, startup_date=date(2026, 4, 27))
    assert report.status == "READY_WITH_WARNINGS"
    assert len(report.position_discrepancies) == 1
    assert report.position_discrepancies[0]["code"] == "1234"
    assert report.position_discrepancies[0]["diff"] == 20


def test_build_report_generated_at_is_utc():
    result = ReconcileResult()
    report = build_report(result, startup_date=date(2026, 4, 27))
    assert "+00:00" in report.generated_at


# ---------------------------------------------------------------------------
# format_cli_summary
# ---------------------------------------------------------------------------


def test_format_cli_summary_ready():
    result = ReconcileResult(orders_synced=3, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    s = format_cli_summary(report)
    assert "READY" in s
    assert "2026-04-27" in s
    assert "orders_synced" in s


def test_format_cli_summary_blocked_shows_warnings():
    result = ReconcileResult(orders_synced=0, orders_no_status=1, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    s = format_cli_summary(report)
    assert "BLOCKED" in s
    assert "Warnings" in s


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------


def test_format_json_parseable_with_required_keys():
    result = ReconcileResult(orders_synced=1, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    data = json_mod.loads(format_json(report))
    assert data["status"] == "READY"
    assert data["orders_synced"] == 1
    assert "startup_date" in data
    assert "generated_at" in data
    assert "warnings" in data
    assert "position_discrepancies" in data


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------


def test_format_markdown_contains_required_sections():
    result = ReconcileResult(orders_synced=1, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    md = format_markdown(report)
    assert "Execution Startup Summary" in md
    assert "Reconciliation" in md
    assert "Final Decision" in md


def test_format_markdown_blocked_includes_warnings_section():
    result = ReconcileResult(orders_synced=0, orders_no_status=2, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    md = format_markdown(report)
    assert "Warnings" in md
    assert "BLOCKED" in md


def test_format_markdown_discrepancy_table():
    discrepancy = PositionDiscrepancy(code="5678", broker_qty=50, local_qty=30, diff=20)
    result = ReconcileResult(orders_synced=0, orders_no_status=0, position_discrepancies=[discrepancy])
    report = build_report(result, startup_date=date(2026, 4, 27))
    md = format_markdown(report)
    assert "5678" in md
    assert "Position Discrepancies" in md


# ---------------------------------------------------------------------------
# save_report
# ---------------------------------------------------------------------------


def test_save_report_creates_three_files(tmp_path):
    result = ReconcileResult(orders_synced=2, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    dest = save_report(report, output_dir=tmp_path)
    assert (dest / "summary.json").exists()
    assert (dest / "report.md").exists()
    assert (dest / "warnings.json").exists()


def test_save_report_invalid_startup_date_raises(tmp_path):
    report = ExecutionStartupReport(
        startup_date="invalid-date",
        generated_at="2026-04-27T00:00:00+00:00",
        status="READY",
        orders_synced=0,
        orders_no_status=0,
        position_discrepancies=[],
        warnings=[],
    )
    with pytest.raises(ValueError, match="Invalid startup_date"):
        save_report(report, output_dir=tmp_path)


def test_save_report_overwrite_is_idempotent(tmp_path):
    """同一 startup_date で 2 回保存しても例外にならない。"""
    result = ReconcileResult(orders_synced=1, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    save_report(report, output_dir=tmp_path)
    save_report(report, output_dir=tmp_path)  # 2回目も例外なし
    assert (tmp_path / "2026-04-27" / "summary.json").exists()
```

- [ ] **Step 2: テストを実行して全件 FAIL を確認する**

```
pytest tests/test_execution_startup_report.py -v
```

期待結果: `ImportError` か `ModuleNotFoundError`（モジュール未作成のため）

- [ ] **Step 3: コミットする**

```bash
git add tests/test_execution_startup_report.py
git commit -m "test: Execution Startup Summary のユニットテストを追加 (Issue #201)"
```

---

### Task 2: `execution_startup_report.py` を実装する

**Files:**
- Create: `src/kabusys/operations/execution_startup_report.py`

- [ ] **Step 1: モジュールを作成する**

`src/kabusys/operations/execution_startup_report.py` を以下の内容で作成する:

```python
"""Execution Startup Summary レポート生成モジュール。

Execution 起動直後に READY / READY_WITH_WARNINGS / BLOCKED の判定を含む
サマリを生成する。DB への参照は行わず、呼び出し元から受け取ったデータのみを使用する。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from kabusys.execution.reconciler import ReconcileResult

STATUS_READY = "READY"
STATUS_READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
STATUS_BLOCKED = "BLOCKED"


@dataclass
class ExecutionStartupReport:
    startup_date: str           # ISO date（起動日）
    generated_at: str           # ISO 8601 UTC
    status: str                 # READY / READY_WITH_WARNINGS / BLOCKED
    orders_synced: int
    orders_no_status: int
    position_discrepancies: list[dict]  # PositionDiscrepancy の dict 表現
    warnings: list[str]


def _determine_status(
    *,
    orders_no_status: int,
    position_discrepancies_count: int,
) -> str:
    """READY / READY_WITH_WARNINGS / BLOCKED を判定する。

    BLOCKED: orders_no_status > 0
      → 注文ステータス不明は二重発注・未約定放置のリスクがあり執行継続不可
    READY_WITH_WARNINGS: position_discrepancies_count > 0
      → DB とブローカー間で数量差分あり。要確認だが執行は継続可能
    READY: それ以外
    """
    if orders_no_status > 0:
        return STATUS_BLOCKED
    if position_discrepancies_count > 0:
        return STATUS_READY_WITH_WARNINGS
    return STATUS_READY


def _generate_warnings(
    *,
    orders_no_status: int,
    position_discrepancies: list[dict],
) -> list[str]:
    """警告メッセージのリストを生成する。"""
    warnings: list[str] = []
    if orders_no_status > 0:
        warnings.append(
            f"ステータス不明の注文が {orders_no_status} 件あります"
            "（二重発注・未約定放置のリスク。手動確認が必要）"
        )
    for d in position_discrepancies:
        warnings.append(
            f"ポジション差分: {d['code']}"
            f" broker={d['broker_qty']} local={d['local_qty']} diff={d['diff']:+d}"
        )
    return warnings


def build_report(
    reconcile_result: ReconcileResult,
    *,
    startup_date: date,
) -> ExecutionStartupReport:
    """ReconcileResult から ExecutionStartupReport を構築する。

    Args:
        reconcile_result: reconciler.run() の戻り値。
        startup_date:     起動日（キーワード引数）。

    Returns:
        ExecutionStartupReport インスタンス。
    """
    discrepancies = [
        {
            "code": d.code,
            "broker_qty": d.broker_qty,
            "local_qty": d.local_qty,
            "diff": d.diff,
        }
        for d in reconcile_result.position_discrepancies
    ]
    warnings = _generate_warnings(
        orders_no_status=reconcile_result.orders_no_status,
        position_discrepancies=discrepancies,
    )
    status = _determine_status(
        orders_no_status=reconcile_result.orders_no_status,
        position_discrepancies_count=len(discrepancies),
    )
    return ExecutionStartupReport(
        startup_date=startup_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=status,
        orders_synced=reconcile_result.orders_synced,
        orders_no_status=reconcile_result.orders_no_status,
        position_discrepancies=discrepancies,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------


def format_cli_summary(report: ExecutionStartupReport) -> str:
    """CLI 表示用サマリ文字列を返す。"""
    sep = "=" * 52
    thin = "-" * 52
    lines = [
        f"\n{sep}",
        f"  Execution Startup Summary  {report.startup_date}",
        f"  Status : {report.status}",
        f"{sep}",
        "  Reconciliation:",
        f"    orders_synced      : {report.orders_synced:>6}",
        f"    orders_no_status   : {report.orders_no_status:>6}",
        f"    position_discrepancies: {len(report.position_discrepancies)} 件",
    ]
    if report.warnings:
        lines.append(thin)
        lines.append("  Warnings:")
        for w in report.warnings:
            lines.append(f"    [!] {w}")
    lines.append(f"{sep}\n")
    return "\n".join(lines)


def format_json(report: ExecutionStartupReport) -> str:
    """全指標を含む JSON 文字列を返す。"""
    return json.dumps(asdict(report), ensure_ascii=False, indent=2)


def format_markdown(report: ExecutionStartupReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    lines: list[str] = [
        "# Execution Startup Summary",
        "",
        "## 1. Overview",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| 起動日 | {report.startup_date} |",
        f"| 生成時刻 | {report.generated_at} |",
        f"| **最終判定** | **{report.status}** |",
        "",
        "## 2. Reconciliation",
        "",
        "| 項目 | 件数 |",
        "|-----|-----|",
        f"| orders_synced | {report.orders_synced} |",
        f"| orders_no_status | {report.orders_no_status} |",
        f"| position_discrepancies | {len(report.position_discrepancies)} |",
        "",
    ]

    if report.position_discrepancies:
        lines += [
            "### Position Discrepancies",
            "",
            "| 銘柄コード | broker_qty | local_qty | diff |",
            "|-----------|-----------|----------|------|",
        ]
        for d in report.position_discrepancies:
            lines.append(
                f"| {d['code']} | {d['broker_qty']} | {d['local_qty']} | {d['diff']:+d} |"
            )
        lines.append("")

    sec = 3
    if report.warnings:
        lines += [
            f"## {sec}. Warnings",
            "",
        ]
        for w in report.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")
        sec += 1

    lines += [f"## {sec}. Final Decision", ""]
    if report.status == STATUS_READY:
        lines += [
            f"**{STATUS_READY}** — 発注ループを継続できます。",
            "",
            "- リコンシリエーション正常完了。",
            "- 特段の対応は不要です。",
        ]
    elif report.status == STATUS_READY_WITH_WARNINGS:
        lines += [
            f"**{STATUS_READY_WITH_WARNINGS}** — ポジション差分を確認した上で、執行を継続してください。",
            "",
            "- 執行は継続可能ですが、上記 Warnings に記載の差分銘柄を確認してください。",
        ]
    else:
        lines += [
            f"**{STATUS_BLOCKED}** — 注文ステータス不明のため執行継続 **不可**。",
            "",
            "- 上記 Warnings に記載の注文を手動確認し、問題を解消してから再起動してください。",
        ]
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: ExecutionStartupReport,
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/execution_startup/{startup_date}/ に保存する。

    保存ファイル:
        summary.json    全指標 JSON
        report.md       Markdown レポート
        warnings.json   警告リスト JSON

    同一 startup_date で再実行した場合は既存ファイルを上書きする（exist_ok=True）。

    Returns:
        保存先ディレクトリのパス。
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report.startup_date):
        raise ValueError(f"Invalid startup_date: {report.startup_date!r}")
    base = (
        Path(output_dir) if output_dir else Path("artifacts") / "execution_startup"
    )
    run_dir = base / report.startup_date
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

```
pytest tests/test_execution_startup_report.py -v
```

期待結果: 全テスト PASS

- [ ] **Step 3: ruff でコードを確認する**

```
ruff check src/kabusys/operations/execution_startup_report.py
```

期待結果: エラーなし。もし出た場合は `ruff check --fix` で修正する。

- [ ] **Step 4: コミットする**

```bash
git add src/kabusys/operations/execution_startup_report.py
git commit -m "feat: Execution Startup Summary モジュールを実装 (Issue #201)"
```

---

### Task 3: `run_execution.py` に統合する

**Files:**
- Modify: `src/kabusys/run_execution.py`

**背景:** 現在 `reconciler.run()` は `ExecutionEngine.run_session()` 内で呼ばれている（`execution_engine.py:329-341`）。`run_execution.py` で先に呼び出してレポートを生成し、engine には `reconciler=None` を渡すことで二重実行を避ける。`reconciler.run()` は内部で例外をキャッチして `ReconcileResult` を返すため、外部に例外は伝播しない。

- [ ] **Step 1: import を追加する**

`src/kabusys/run_execution.py` の先頭 import 群（既存の `from kabusys.execution.reconciler import Reconciler` の直後）に以下を追加する:

```python
from kabusys.operations.execution_startup_report import (  # noqa: E402
    build_report,
    format_cli_summary,
    save_report,
)
```

既存の import はすべて `# noqa: E402` が付いているので同様に付ける。

- [ ] **Step 2: `main()` の reconciler 生成部分を修正する**

現在の `run_execution.py` には以下のブロックがある（`reconciler = Reconciler(...)` の行から `engine = ExecutionEngine(...)` の行まで）:

```python
        reconciler = Reconciler(broker=broker, repo=repo, order_manager=order_manager)

        # 5. ExecutionEngine 起動
        engine = ExecutionEngine(
            broker=broker,
            repo=repo,
            risk_manager=risk_manager,
            order_manager=order_manager,
            duckdb_conn=duckdb_conn,
            config=EngineConfig(target_date=date.today()),
            reconciler=reconciler,
            pid_file=_EXECUTION_PID,
        )
```

これを以下に置き換える:

```python
        reconciler = Reconciler(broker=broker, repo=repo, order_manager=order_manager)

        # 起動時リコンシリエーション + Execution Startup Summary 生成
        reconcile_result = reconciler.run()
        try:
            _report = build_report(reconcile_result=reconcile_result, startup_date=date.today())
            print(format_cli_summary(_report))
            save_report(_report)
        except Exception:
            logger.warning(
                "Execution Startup Summary の生成に失敗しました（起動を続行します）",
                exc_info=True,
            )

        # 5. ExecutionEngine 起動（reconciliation は上で完了済みのため reconciler=None）
        engine = ExecutionEngine(
            broker=broker,
            repo=repo,
            risk_manager=risk_manager,
            order_manager=order_manager,
            duckdb_conn=duckdb_conn,
            config=EngineConfig(target_date=date.today()),
            reconciler=None,
            pid_file=_EXECUTION_PID,
        )
```

- [ ] **Step 3: ruff で確認する**

```
ruff check src/kabusys/run_execution.py
```

期待結果: エラーなし。もし出た場合は `ruff check --fix` で修正する。

- [ ] **Step 4: 全テストスイートを実行する**

```
pytest tests/ -v --tb=short
```

期待結果: 全テスト PASS（既存テストに回帰なし）

- [ ] **Step 5: コミットする**

```bash
git add src/kabusys/run_execution.py
git commit -m "feat: run_execution.py に Execution Startup Summary を統合 (Issue #201)"
```

---

### Task 4: PR を作成する

- [ ] **Step 1: push する**

```bash
git push origin main
```

（または feature ブランチを使う場合は `git push origin feature/issue-201-execution-startup-summary`）

- [ ] **Step 2: PR を作成する**

```bash
gh pr create \
  --title "feat: Execution Startup Summary を実装 (Issue #201)" \
  --body "$(cat <<'EOF'
## Summary

- `src/kabusys/operations/execution_startup_report.py` を新規作成（純粋関数モジュール）
- `run_execution.py` を最小変更で統合: `reconciler.run()` をエンジン起動前に実行し、 `READY / READY_WITH_WARNINGS / BLOCKED` サマリを stdout + `artifacts/execution_startup/{date}/` に出力
- ユニットテスト 17 件を追加

## Test plan

- [ ] `pytest tests/test_execution_startup_report.py -v` → 全件 PASS
- [ ] `pytest tests/ -v` → 既存テストに回帰なし
- [ ] `ruff check src/kabusys/operations/execution_startup_report.py` → エラーなし

Closes #201
EOF
)"
```
