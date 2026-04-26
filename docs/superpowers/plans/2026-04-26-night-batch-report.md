# Night Batch Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 夜間バッチ完了後に READY/READY_WITH_WARNINGS/BLOCKED 判定を含むレポートを CLI/JSON/Markdown の3形式で生成・保存するモジュールを実装する。

**Architecture:** `src/kabusys/operations/night_batch_report.py` に `JobRunResult`・`UpdateCounts`・`NextDaySummary`・`NightBatchReport` の4つのデータクラスと、`build_report()`・`_determine_status()`・`_generate_warnings()`・フォーマッター3関数・`save_report()` を実装する。既存の `src/kabusys/backtest/report.py` と同じ「dataclass → formatter → save」パターンに従う。DB への参照は行わず、呼び出し元からデータを受け取る純粋関数設計とする。

**Tech Stack:** Python 3.10+、標準ライブラリのみ（`dataclasses`、`json`、`datetime`、`pathlib`）

---

## File Structure

| ファイル | 役割 |
|---------|------|
| `src/kabusys/operations/__init__.py` | 新規作成（空ファイル） |
| `src/kabusys/operations/night_batch_report.py` | 新規作成：データクラス・ビルダー・フォーマッター・保存 |
| `tests/test_night_batch_report.py` | 新規作成：全機能のユニットテスト |

---

### Task 1: operations パッケージ作成 + データクラス定義

**Files:**
- Create: `src/kabusys/operations/__init__.py`
- Create: `src/kabusys/operations/night_batch_report.py`
- Create: `tests/test_night_batch_report.py`

- [ ] **Step 1: テストファイルを作成し、データクラスのインスタンス化テストを書く**

```python
# tests/test_night_batch_report.py
"""夜間バッチレポートモジュールのテスト"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from kabusys.operations.night_batch_report import (
    JobRunResult,
    NightBatchReport,
    NextDaySummary,
    UpdateCounts,
)


def _make_job(
    name: str = "data_update_job",
    status: str = "success",
    duration: float = 10.0,
    updated_rows: dict | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> JobRunResult:
    dt = datetime(2026, 4, 26, 15, 30, 0, tzinfo=timezone.utc)
    return JobRunResult(
        job_name=name,
        status=status,
        started_at=dt,
        finished_at=datetime(2026, 4, 26, 15, 30, int(duration), tzinfo=timezone.utc),
        duration_sec=duration,
        updated_rows=updated_rows or {},
        warnings=warnings or [],
        errors=errors or [],
    )


def _make_counts(**kwargs) -> UpdateCounts:
    defaults = dict(
        prices_daily=1850,
        news_articles=120,
        fundamentals=1850,
        features=1850,
        ai_scores=1850,
        signals=25,
        signal_queue=15,
    )
    defaults.update(kwargs)
    return UpdateCounts(**defaults)


def _make_next_day(**kwargs) -> NextDaySummary:
    defaults = dict(buy_count=8, sell_count=7, target_symbols=15, expected_orders=15)
    defaults.update(kwargs)
    return NextDaySummary(**defaults)


def test_job_run_result_instantiation():
    """JobRunResult が正しくインスタンス化できる。"""
    job = _make_job()
    assert job.job_name == "data_update_job"
    assert job.status == "success"
    assert job.duration_sec == 10.0


def test_update_counts_defaults():
    """UpdateCounts のデフォルト値がすべて 0。"""
    counts = UpdateCounts()
    assert counts.prices_daily == 0
    assert counts.signal_queue == 0


def test_next_day_summary_instantiation():
    """NextDaySummary が正しくインスタンス化できる。"""
    nd = _make_next_day()
    assert nd.buy_count == 8
    assert nd.expected_orders == 15
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_night_batch_report.py -v
```

Expected: `ImportError: No module named 'kabusys.operations'`

- [ ] **Step 3: `__init__.py` と `night_batch_report.py` にデータクラスを実装する**

```python
# src/kabusys/operations/__init__.py
# (空ファイル)
```

```python
# src/kabusys/operations/night_batch_report.py
"""
夜間バッチ結果確認レポート生成モジュール。

夜間バッチ（21:00頃）完了後に READY / READY_WITH_WARNINGS / BLOCKED
の最終判定を含むレポートを生成する。DB への参照は行わず、
呼び出し元から受け取ったデータのみを使用する。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

# 必須ジョブ一覧（いずれかが failed → BLOCKED）
MANDATORY_JOBS: list[str] = [
    "data_update_job",
    "feature_generation_job",
    "ai_analysis_job",
    "strategy_signal_job",
    "portfolio_construction_job",
]

STATUS_READY = "READY"
STATUS_READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
STATUS_BLOCKED = "BLOCKED"


@dataclass
class JobRunResult:
    """1ジョブの実行結果。"""

    job_name: str
    status: str  # success / warning / failed / skipped
    started_at: datetime
    finished_at: datetime
    duration_sec: float
    updated_rows: dict[str, int]
    warnings: list[str]
    errors: list[str]


@dataclass
class UpdateCounts:
    """各テーブルへの更新件数。"""

    prices_daily: int = 0
    news_articles: int = 0
    fundamentals: int = 0
    features: int = 0
    ai_scores: int = 0
    signals: int = 0
    signal_queue: int = 0


@dataclass
class NextDaySummary:
    """翌営業日の発注準備サマリ。"""

    buy_count: int = 0
    sell_count: int = 0
    target_symbols: int = 0
    expected_orders: int = 0


@dataclass
class NightBatchReport:
    """夜間バッチ結果確認レポート全体。"""

    run_date: str           # ISO date（バッチ実行日）
    target_date: str        # ISO date（対象取引日＝翌営業日）
    generated_at: str       # ISO 8601 UTC
    status: str             # READY / READY_WITH_WARNINGS / BLOCKED
    job_results: list[JobRunResult]
    update_counts: UpdateCounts
    next_day_summary: NextDaySummary
    warnings: list[str]
```

- [ ] **Step 4: テストを実行して通過することを確認する**

```
pytest tests/test_night_batch_report.py::test_job_run_result_instantiation tests/test_night_batch_report.py::test_update_counts_defaults tests/test_night_batch_report.py::test_next_day_summary_instantiation -v
```

Expected: 3 passed

- [ ] **Step 5: コミットする**

```bash
git add src/kabusys/operations/__init__.py src/kabusys/operations/night_batch_report.py tests/test_night_batch_report.py
git commit -m "feat: operations パッケージ + NightBatchReport データクラス定義 (Issue #193)"
```

---

### Task 2: `_determine_status()` と `_generate_warnings()` の実装

**Files:**
- Modify: `src/kabusys/operations/night_batch_report.py`
- Modify: `tests/test_night_batch_report.py`

- [ ] **Step 1: テストを追加する**

```python
# tests/test_night_batch_report.py に追記

from kabusys.operations.night_batch_report import (
    _determine_status,
    _generate_warnings,
)


# ---------------------------------------------------------------------------
# _determine_status
# ---------------------------------------------------------------------------

def test_status_ready_all_success():
    """全ジョブ成功 + signal_queue > 0 → READY。"""
    jobs = [_make_job(name=n) for n in [
        "data_update_job", "feature_generation_job", "ai_analysis_job",
        "strategy_signal_job", "portfolio_construction_job",
    ]]
    counts = _make_counts()
    assert _determine_status(jobs, counts) == "READY"


def test_status_blocked_mandatory_failed():
    """必須ジョブが failed → BLOCKED。"""
    jobs = [_make_job(name="data_update_job", status="failed")]
    counts = _make_counts()
    assert _determine_status(jobs, counts) == "BLOCKED"


def test_status_blocked_signal_queue_zero():
    """signal_queue == 0 → BLOCKED。"""
    jobs = [_make_job(name=n) for n in [
        "data_update_job", "feature_generation_job", "ai_analysis_job",
        "strategy_signal_job", "portfolio_construction_job",
    ]]
    counts = _make_counts(signal_queue=0)
    assert _determine_status(jobs, counts) == "BLOCKED"


def test_status_ready_with_warnings_job_warning():
    """ジョブが warning → READY_WITH_WARNINGS。"""
    jobs = [_make_job(name="ai_analysis_job", status="warning")]
    counts = _make_counts()
    assert _determine_status(jobs, counts) == "READY_WITH_WARNINGS"


def test_status_ready_with_warnings_signals_zero():
    """signals == 0（signal_queue > 0）→ READY_WITH_WARNINGS。"""
    jobs = [_make_job()]
    counts = _make_counts(signals=0, signal_queue=5)
    assert _determine_status(jobs, counts) == "READY_WITH_WARNINGS"


def test_status_ready_with_warnings_job_has_warning_message():
    """ジョブの warnings リストが空でない → READY_WITH_WARNINGS。"""
    jobs = [_make_job(warnings=["データ件数が少ない"])]
    counts = _make_counts()
    assert _determine_status(jobs, counts) == "READY_WITH_WARNINGS"


# ---------------------------------------------------------------------------
# _generate_warnings
# ---------------------------------------------------------------------------

def test_warnings_failed_mandatory_job():
    """必須ジョブが failed → 警告にジョブ名が含まれる。"""
    jobs = [_make_job(name="data_update_job", status="failed")]
    warnings = _generate_warnings(jobs, _make_counts())
    assert any("data_update_job" in w for w in warnings)


def test_warnings_signal_queue_zero():
    """signal_queue == 0 → 警告に signal_queue が含まれる。"""
    warnings = _generate_warnings([_make_job()], _make_counts(signal_queue=0))
    assert any("signal_queue" in w for w in warnings)


def test_warnings_signals_zero():
    """signals == 0 → 警告に signals が含まれる。"""
    warnings = _generate_warnings([_make_job()], _make_counts(signals=0))
    assert any("signals" in w for w in warnings)


def test_warnings_prices_daily_zero():
    """prices_daily == 0 → 警告が生成される。"""
    warnings = _generate_warnings([_make_job()], _make_counts(prices_daily=0))
    assert any("prices_daily" in w for w in warnings)


def test_warnings_empty_on_healthy():
    """全ジョブ成功・全カウント正常 → 警告なし。"""
    jobs = [_make_job(name=n) for n in MANDATORY_JOBS]
    warnings = _generate_warnings(jobs, _make_counts())
    assert warnings == []


def test_warnings_includes_job_warnings():
    """ジョブの warnings フィールドが全体の warnings に含まれる。"""
    jobs = [_make_job(warnings=["シグナル件数が少ない"])]
    warnings = _generate_warnings(jobs, _make_counts())
    assert "シグナル件数が少ない" in warnings
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_night_batch_report.py -k "status or warnings" -v
```

Expected: ImportError（関数未定義）

- [ ] **Step 3: `_determine_status()` と `_generate_warnings()` を実装する**

`src/kabusys/operations/night_batch_report.py` の `NightBatchReport` クラス定義の直後に追記:

```python
def _determine_status(
    job_results: list[JobRunResult],
    update_counts: UpdateCounts,
) -> str:
    """READY / READY_WITH_WARNINGS / BLOCKED を判定する。

    BLOCKED 条件（いずれかが真）:
      - 必須ジョブのいずれかが failed
      - signal_queue == 0

    READY_WITH_WARNINGS 条件（BLOCKED でなく、いずれかが真）:
      - いずれかのジョブが status == "warning"
      - いずれかのジョブの warnings リストが空でない
      - signals == 0

    それ以外: READY
    """
    failed_mandatory = [
        j for j in job_results
        if j.job_name in MANDATORY_JOBS and j.status == "failed"
    ]
    if failed_mandatory or update_counts.signal_queue == 0:
        return STATUS_BLOCKED

    has_warning_status = any(j.status == "warning" for j in job_results)
    has_job_warnings = any(j.warnings for j in job_results)
    if has_warning_status or has_job_warnings or update_counts.signals == 0:
        return STATUS_READY_WITH_WARNINGS

    return STATUS_READY


def _generate_warnings(
    job_results: list[JobRunResult],
    update_counts: UpdateCounts,
) -> list[str]:
    """警告メッセージのリストを生成する。"""
    warnings: list[str] = []

    for j in job_results:
        if j.status == "failed" and j.job_name in MANDATORY_JOBS:
            warnings.append(f"必須ジョブが失敗しました: {j.job_name}")
        if j.status == "warning":
            warnings.append(f"ジョブが警告で完了: {j.job_name}")
        warnings.extend(j.warnings)

    if update_counts.signals == 0:
        warnings.append("signals が生成されていません")
    if update_counts.signal_queue == 0:
        warnings.append("signal_queue が空です（翌営業日の自動執行は不可）")
    if update_counts.prices_daily == 0:
        warnings.append("prices_daily の更新件数が 0 件です")
    if update_counts.features == 0:
        warnings.append("features の更新件数が 0 件です")

    return warnings
```

- [ ] **Step 4: テストを実行して通過することを確認する**

```
pytest tests/test_night_batch_report.py -k "status or warnings" -v
```

Expected: 11 passed

- [ ] **Step 5: コミットする**

```bash
git add src/kabusys/operations/night_batch_report.py tests/test_night_batch_report.py
git commit -m "feat: _determine_status / _generate_warnings 実装 (Issue #193)"
```

---

### Task 3: `build_report()` の実装

**Files:**
- Modify: `src/kabusys/operations/night_batch_report.py`
- Modify: `tests/test_night_batch_report.py`

- [ ] **Step 1: テストを追加する**

```python
# tests/test_night_batch_report.py に追記

from kabusys.operations.night_batch_report import (
    MANDATORY_JOBS,
    build_report,
)


def _all_success_jobs() -> list[JobRunResult]:
    return [_make_job(name=n) for n in MANDATORY_JOBS]


def test_build_report_returns_night_batch_report():
    """build_report() が NightBatchReport を返す。"""
    report = build_report(
        _all_success_jobs(),
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert isinstance(report, NightBatchReport)


def test_build_report_status_ready():
    """全成功 → status == READY。"""
    report = build_report(
        _all_success_jobs(),
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert report.status == "READY"


def test_build_report_status_blocked():
    """必須ジョブ失敗 → status == BLOCKED。"""
    jobs = [_make_job(name="data_update_job", status="failed")]
    report = build_report(
        jobs,
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert report.status == "BLOCKED"


def test_build_report_dates_as_iso_string():
    """run_date / target_date が ISO 形式文字列。"""
    report = build_report(
        _all_success_jobs(),
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert report.run_date == "2026-04-26"
    assert report.target_date == "2026-04-27"


def test_build_report_generated_at_is_utc_iso():
    """generated_at が UTC ISO 8601 形式（末尾が +00:00）。"""
    report = build_report(
        _all_success_jobs(),
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert report.generated_at.endswith("+00:00")


def test_build_report_no_warnings_on_healthy():
    """全成功・全カウント正常 → warnings が空。"""
    report = build_report(
        _all_success_jobs(),
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert report.warnings == []
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_night_batch_report.py -k "build_report" -v
```

Expected: ImportError（build_report 未定義）

- [ ] **Step 3: `build_report()` を実装する**

`src/kabusys/operations/night_batch_report.py` の `_generate_warnings()` の直後に追記:

```python
def build_report(
    job_results: list[JobRunResult],
    update_counts: UpdateCounts,
    next_day_summary: NextDaySummary,
    *,
    run_date: date,
    target_date: date,
) -> NightBatchReport:
    """NightBatchReport を構築する。

    Args:
        job_results:      各ジョブの実行結果リスト。
        update_counts:    各テーブルへの更新件数。
        next_day_summary: 翌営業日の発注準備サマリ。
        run_date:         バッチ実行日（キーワード引数）。
        target_date:      対象取引日（キーワード引数）。

    Returns:
        NightBatchReport インスタンス。
    """
    warnings = _generate_warnings(job_results, update_counts)
    status = _determine_status(job_results, update_counts)
    return NightBatchReport(
        run_date=run_date.isoformat(),
        target_date=target_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=status,
        job_results=job_results,
        update_counts=update_counts,
        next_day_summary=next_day_summary,
        warnings=warnings,
    )
```

- [ ] **Step 4: テストを実行して通過することを確認する**

```
pytest tests/test_night_batch_report.py -k "build_report" -v
```

Expected: 6 passed

- [ ] **Step 5: コミットする**

```bash
git add src/kabusys/operations/night_batch_report.py tests/test_night_batch_report.py
git commit -m "feat: build_report() 実装 (Issue #193)"
```

---

### Task 4: `format_cli_summary()` と `format_json()` の実装

**Files:**
- Modify: `src/kabusys/operations/night_batch_report.py`
- Modify: `tests/test_night_batch_report.py`

- [ ] **Step 1: テストを追加する**

```python
# tests/test_night_batch_report.py に追記

import json as json_mod

from kabusys.operations.night_batch_report import (
    format_cli_summary,
    format_json,
)


def _make_report(status: str = "READY") -> NightBatchReport:
    if status == "BLOCKED":
        jobs = [_make_job(name="data_update_job", status="failed")]
    elif status == "READY_WITH_WARNINGS":
        jobs = [_make_job(name="ai_analysis_job", status="warning")]
    else:
        jobs = _all_success_jobs()
    return build_report(
        jobs,
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )


def test_format_cli_summary_contains_status():
    """CLI サマリに最終判定ステータスが含まれる。"""
    report = _make_report("READY")
    summary = format_cli_summary(report)
    assert "READY" in summary


def test_format_cli_summary_contains_run_date():
    """CLI サマリに実行日が含まれる。"""
    report = _make_report()
    summary = format_cli_summary(report)
    assert "2026-04-26" in summary


def test_format_cli_summary_contains_signal_queue():
    """CLI サマリに signal_queue 件数が含まれる。"""
    report = _make_report()
    summary = format_cli_summary(report)
    assert "15" in summary  # signal_queue=15


def test_format_cli_summary_blocked_shows_blocked():
    """BLOCKED のとき CLI サマリに BLOCKED が含まれる。"""
    report = _make_report("BLOCKED")
    summary = format_cli_summary(report)
    assert "BLOCKED" in summary


def test_format_json_is_valid_json():
    """format_json() が有効な JSON 文字列を返す。"""
    report = _make_report()
    raw = format_json(report)
    data = json_mod.loads(raw)
    assert isinstance(data, dict)


def test_format_json_contains_expected_keys():
    """JSON に必須キーが含まれる。"""
    report = _make_report()
    data = json_mod.loads(format_json(report))
    for key in ["run_date", "target_date", "generated_at", "status",
                "job_results", "update_counts", "next_day_summary", "warnings"]:
        assert key in data, f"Missing key: {key}"


def test_format_json_status_roundtrip():
    """JSON から status が正しく復元できる。"""
    report = _make_report("BLOCKED")
    data = json_mod.loads(format_json(report))
    assert data["status"] == "BLOCKED"


def test_format_json_datetime_serialized_as_string():
    """JobRunResult の started_at が JSON で文字列にシリアライズされる。"""
    report = _make_report()
    data = json_mod.loads(format_json(report))
    assert isinstance(data["job_results"][0]["started_at"], str)
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_night_batch_report.py -k "format_cli or format_json" -v
```

Expected: ImportError（フォーマッター未定義）

- [ ] **Step 3: `format_cli_summary()` と `format_json()` を実装する**

`src/kabusys/operations/night_batch_report.py` の `build_report()` の直後に追記:

```python
# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------

_STATUS_LABEL: dict[str, str] = {
    "READY": "READY",
    "READY_WITH_WARNINGS": "READY_WITH_WARNINGS",
    "BLOCKED": "BLOCKED",
}

_JOB_STATUS_LABEL: dict[str, str] = {
    "success": "SUCCESS",
    "warning": "WARNING",
    "failed": "FAILED",
    "skipped": "SKIPPED",
}


def format_cli_summary(report: NightBatchReport) -> str:
    """CLI 表示用サマリ文字列を返す。"""
    sep = "=" * 52
    thin = "-" * 52
    lines = [
        f"\n{sep}",
        f"  Night Batch Report  {report.run_date}",
        f"  Status : {_STATUS_LABEL.get(report.status, report.status)}",
        f"  Target : {report.target_date}（翌営業日）",
        f"{sep}",
        "  Job Status:",
    ]
    for j in report.job_results:
        label = _JOB_STATUS_LABEL.get(j.status, j.status.upper())
        lines.append(f"    {j.job_name:<32} {label}  ({j.duration_sec:.1f}s)")
    lines.append(thin)
    uc = report.update_counts
    lines += [
        "  Update Counts:",
        f"    prices_daily : {uc.prices_daily:>6}    features     : {uc.features:>6}",
        f"    news_articles: {uc.news_articles:>6}    ai_scores    : {uc.ai_scores:>6}",
        f"    fundamentals : {uc.fundamentals:>6}    signals      : {uc.signals:>6}",
        f"                              signal_queue : {uc.signal_queue:>6}",
    ]
    lines.append(thin)
    nd = report.next_day_summary
    lines += [
        f"  Next Trading Day ({report.target_date}):",
        f"    BUY: {nd.buy_count}  SELL: {nd.sell_count}  "
        f"Symbols: {nd.target_symbols}  Orders: {nd.expected_orders}",
    ]
    if report.warnings:
        lines.append(thin)
        lines.append("  Warnings:")
        for w in report.warnings:
            lines.append(f"    [!] {w}")
    lines.append(f"{sep}\n")
    return "\n".join(lines)


def _to_serializable(obj: object) -> object:
    """dataclass → dict 変換後の datetime を ISO 文字列に変換する。"""
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(i) for i in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def format_json(report: NightBatchReport) -> str:
    """全指標を含む JSON 文字列を返す。"""
    data = _to_serializable(asdict(report))
    return json.dumps(data, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: テストを実行して通過することを確認する**

```
pytest tests/test_night_batch_report.py -k "format_cli or format_json" -v
```

Expected: 8 passed

- [ ] **Step 5: コミットする**

```bash
git add src/kabusys/operations/night_batch_report.py tests/test_night_batch_report.py
git commit -m "feat: format_cli_summary / format_json 実装 (Issue #193)"
```

---

### Task 5: `format_markdown()` の実装

**Files:**
- Modify: `src/kabusys/operations/night_batch_report.py`
- Modify: `tests/test_night_batch_report.py`

- [ ] **Step 1: テストを追加する**

```python
# tests/test_night_batch_report.py に追記

from kabusys.operations.night_batch_report import format_markdown


def test_format_markdown_contains_sections():
    """Markdown に必須セクション見出しが含まれる。"""
    report = _make_report()
    md = format_markdown(report)
    for section in ["Overview", "Job Status", "Update Counts",
                    "Next Trading Day", "Final Decision"]:
        assert section in md, f"Missing section: {section}"


def test_format_markdown_contains_status():
    """Markdown にステータスが含まれる。"""
    report = _make_report("READY")
    md = format_markdown(report)
    assert "READY" in md


def test_format_markdown_contains_signal_queue():
    """Markdown に signal_queue 件数が含まれる。"""
    report = _make_report()
    md = format_markdown(report)
    assert "15" in md  # signal_queue=15


def test_format_markdown_warnings_section():
    """警告がある場合は Warnings セクションが含まれる。"""
    report = _make_report("READY_WITH_WARNINGS")
    md = format_markdown(report)
    assert "Warnings" in md


def test_format_markdown_no_warnings_section_when_empty():
    """警告なしのとき Warnings セクションは含まれない。"""
    report = _make_report("READY")
    md = format_markdown(report)
    assert "## 5. Warnings" not in md


def test_format_markdown_final_decision_blocked():
    """BLOCKED のとき Final Decision に自動執行禁止の文言が含まれる。"""
    report = _make_report("BLOCKED")
    md = format_markdown(report)
    assert "BLOCKED" in md
    assert "自動執行" in md or "執行" in md
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_night_batch_report.py -k "format_markdown" -v
```

Expected: ImportError（format_markdown 未定義）

- [ ] **Step 3: `format_markdown()` を実装する**

`format_json()` の直後に追記:

```python
def format_markdown(report: NightBatchReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    lines: list[str] = []

    # 1. Overview
    lines += [
        "# Night Batch Report",
        "",
        "## 1. Overview",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| 実行日 | {report.run_date} |",
        f"| 対象取引日 | {report.target_date} |",
        f"| 生成時刻 | {report.generated_at} |",
        f"| **最終判定** | **{report.status}** |",
        "",
    ]

    # 2. Job Status
    lines += [
        "## 2. Job Status",
        "",
        "| ジョブ名 | ステータス | 開始時刻 | 終了時刻 | 実行時間(s) |",
        "|---------|-----------|---------|---------|------------|",
    ]
    for j in report.job_results:
        started = j.started_at.isoformat() if isinstance(j.started_at, datetime) else j.started_at
        finished = j.finished_at.isoformat() if isinstance(j.finished_at, datetime) else j.finished_at
        lines.append(
            f"| {j.job_name} | {j.status} | {started} | {finished} | {j.duration_sec:.1f} |"
        )
    lines.append("")

    # 3. Update Counts
    uc = report.update_counts
    lines += [
        "## 3. Update Counts",
        "",
        "| テーブル | 更新件数 |",
        "|---------|--------|",
        f"| prices_daily | {uc.prices_daily} |",
        f"| news_articles | {uc.news_articles} |",
        f"| fundamentals | {uc.fundamentals} |",
        f"| features | {uc.features} |",
        f"| ai_scores | {uc.ai_scores} |",
        f"| signals | {uc.signals} |",
        f"| signal_queue | {uc.signal_queue} |",
        "",
    ]

    # 4. Next Trading Day Preparation
    nd = report.next_day_summary
    lines += [
        "## 4. Next Trading Day Preparation",
        "",
        f"対象取引日: **{report.target_date}**",
        "",
        "| 項目 | 件数 |",
        "|-----|-----|",
        f"| BUY 件数 | {nd.buy_count} |",
        f"| SELL 件数 | {nd.sell_count} |",
        f"| 対象銘柄数 | {nd.target_symbols} |",
        f"| 想定発注件数 | {nd.expected_orders} |",
        "",
    ]

    # 5. Warnings（ある場合のみ）
    if report.warnings:
        lines += [
            "## 5. Warnings",
            "",
        ]
        for w in report.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    # 6. Final Decision
    lines += ["## 6. Final Decision", ""]
    if report.status == STATUS_READY:
        lines += [
            f"**{STATUS_READY}** — 翌営業日の自動執行を開始できます。",
            "",
            "- 全必須ジョブが正常完了しています。",
            "- signal_queue が正常に作成されています。",
            "- 特段の対応は不要です。",
        ]
    elif report.status == STATUS_READY_WITH_WARNINGS:
        lines += [
            f"**{STATUS_READY_WITH_WARNINGS}** — 警告を確認した上で、執行開始を判断してください。",
            "",
            "- 基本的な処理は完了していますが、警告があります。",
            "- 上記 Warnings を確認し、問題がなければ自動執行を開始できます。",
        ]
    else:  # BLOCKED
        lines += [
            f"**{STATUS_BLOCKED}** — 翌営業日の自動執行を **開始しないでください**。",
            "",
            "- 必須ジョブの失敗または signal_queue が空のため、自動執行は安全ではありません。",
            "- 上記 Warnings を確認し、手動で問題を解消してから再実行してください。",
        ]
    lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: テストを実行して通過することを確認する**

```
pytest tests/test_night_batch_report.py -k "format_markdown" -v
```

Expected: 6 passed

- [ ] **Step 5: コミットする**

```bash
git add src/kabusys/operations/night_batch_report.py tests/test_night_batch_report.py
git commit -m "feat: format_markdown 実装 (Issue #193)"
```

---

### Task 6: `save_report()` の実装

**Files:**
- Modify: `src/kabusys/operations/night_batch_report.py`
- Modify: `tests/test_night_batch_report.py`

- [ ] **Step 1: テストを追加する**

```python
# tests/test_night_batch_report.py に追記

import json as json_mod

from kabusys.operations.night_batch_report import save_report


def test_save_report_creates_files(tmp_path):
    """save_report() が summary.json / report.md / warnings.json を作成する。"""
    report = _make_report()
    run_dir = save_report(report, output_dir=tmp_path)
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "warnings.json").exists()


def test_save_report_run_dir_name(tmp_path):
    """保存先ディレクトリ名が run_date と一致する。"""
    report = _make_report()
    run_dir = save_report(report, output_dir=tmp_path)
    assert run_dir.name == "2026-04-26"


def test_save_report_summary_json_valid(tmp_path):
    """summary.json が有効な JSON で status キーを含む。"""
    report = _make_report()
    run_dir = save_report(report, output_dir=tmp_path)
    data = json_mod.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert data["status"] == "READY"


def test_save_report_warnings_json_is_list(tmp_path):
    """warnings.json がリスト形式。"""
    report = _make_report()
    run_dir = save_report(report, output_dir=tmp_path)
    data = json_mod.loads((run_dir / "warnings.json").read_text(encoding="utf-8"))
    assert isinstance(data, list)


def test_save_report_default_output_dir(tmp_path, monkeypatch):
    """output_dir 省略時は artifacts/operations/night_batch/ 以下に保存される。"""
    monkeypatch.chdir(tmp_path)
    report = _make_report()
    run_dir = save_report(report)
    assert run_dir.parts[-3] == "artifacts"
    assert run_dir.parts[-2] == "night_batch"


def test_save_report_overwrite_existing(tmp_path):
    """同一 run_date で再実行しても上書きできる（exist_ok=True）。"""
    report = _make_report()
    save_report(report, output_dir=tmp_path)
    save_report(report, output_dir=tmp_path)  # 2回目もエラーなし
    assert (tmp_path / "2026-04-26" / "summary.json").exists()
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_night_batch_report.py -k "save_report" -v
```

Expected: ImportError（save_report 未定義）

- [ ] **Step 3: `save_report()` を実装する**

`format_markdown()` の直後に追記:

```python
# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: NightBatchReport,
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/operations/night_batch/{run_date}/ に保存する。

    保存ファイル:
        summary.json    全指標 JSON
        report.md       Markdown レポート
        warnings.json   警告リスト JSON

    同一 run_date で再実行した場合は既存ファイルを上書きする（exist_ok=True）。

    Args:
        report:     build_report() の戻り値。
        output_dir: 保存先ルート（省略時は artifacts/operations/night_batch）。

    Returns:
        保存先ディレクトリのパス。
    """
    base = (
        Path(output_dir)
        if output_dir
        else Path("artifacts") / "operations" / "night_batch"
    )
    run_dir = base / report.run_date
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "summary.json").write_text(format_json(report), encoding="utf-8")
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")
    (run_dir / "warnings.json").write_text(
        json.dumps(report.warnings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return run_dir
```

- [ ] **Step 4: テストを実行して通過することを確認する**

```
pytest tests/test_night_batch_report.py -k "save_report" -v
```

Expected: 6 passed

- [ ] **Step 5: 全テストを実行して通過することを確認する**

```
pytest tests/test_night_batch_report.py -v
```

Expected: 全テスト passed

- [ ] **Step 6: ruff でリントとフォーマットを確認する**

```
python -m ruff check src/kabusys/operations/night_batch_report.py tests/test_night_batch_report.py
python -m ruff format --check src/kabusys/operations/night_batch_report.py tests/test_night_batch_report.py
```

Expected: All checks passed

- [ ] **Step 7: コミットする**

```bash
git add src/kabusys/operations/night_batch_report.py tests/test_night_batch_report.py
git commit -m "feat: save_report 実装・夜間バッチレポート完成 (Issue #193)"
```

---

### Task 7: PR 作成

**Files:** なし（git 操作のみ）

- [ ] **Step 1: 全テストスイートを実行する**

```
pytest --tb=short -q
```

Expected: 既存テストを含む全テスト passed（922件 + 新規分）

- [ ] **Step 2: PR を作成する**

```bash
git push -u origin feature/issue-193-night-batch-report
gh pr create \
  --title "feat: 夜間バッチ結果確認レポート実装 (Issue #193)" \
  --body "## Summary
- \`src/kabusys/operations/night_batch_report.py\` を新規実装
- READY / READY_WITH_WARNINGS / BLOCKED の3段階ステータス判定
- CLI summary / JSON / Markdown の3形式出力
- \`artifacts/operations/night_batch/{run_date}/\` への保存（summary.json / report.md / warnings.json）

## Test Plan
- [ ] pytest tests/test_night_batch_report.py 全テスト通過
- [ ] 全テストスイート（922件＋新規）通過
- [ ] ruff check / format クリーン
" \
  --assignee @me
```
