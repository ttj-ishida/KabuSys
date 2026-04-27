# Execution Startup Summary 設計書

- Issue: #201
- Date: 2026-04-27
- Status: Approved

---

## 1. 目的

08:30 の Execution モジュール起動直後に、運転継続可否をユーザーが判断できる構造化サマリを自動出力する。ログだけに依存した確認から脱却し、`READY / READY_WITH_WARNINGS / BLOCKED` の明示的な判定を提供する。

---

## 2. アーキテクチャ

`night_batch_report.py` / `pre_market_report.py` と同じ純粋関数パターンを採用する。

```
run_execution.py
  └─ reconciler.run()  → ReconcileResult
  └─ build_report(reconcile_result, startup_date)  → ExecutionStartupReport
  └─ save_report(report)  → artifacts/execution_startup/{date}/
  └─ format_cli_summary(report)  → stdout（ログと同タイミングで確認可能）
```

IO 依存（DB クエリ・ファイル操作）は `run_execution.py` が担い、`execution_startup_report.py` は受け取ったデータのみで判定・フォーマットを行う純粋関数モジュールとする。

---

## 3. ファイル構成

| ファイル | 区分 | 役割 |
|---------|------|------|
| `src/kabusys/operations/execution_startup_report.py` | 新規 | データクラス・ステータス判定・フォーマッター・保存 |
| `src/kabusys/run_execution.py` | 既存修正 | Reconciler 実行後に `build_report()` + `save_report()` を呼ぶ |
| `tests/test_execution_startup_report.py` | 新規 | 純粋関数のユニットテスト |

---

## 4. データモデル

### 4.1 入力: ReconcileResult（既存）

```python
# src/kabusys/execution/reconciler.py（既存）
@dataclass
class PositionDiscrepancy:
    code: str
    broker_qty: int
    local_qty: int
    diff: int

@dataclass
class ReconcileResult:
    orders_synced: int = 0
    orders_no_status: int = 0
    position_discrepancies: list[PositionDiscrepancy] = field(default_factory=list)
```

### 4.2 出力: ExecutionStartupReport（新規）

```python
@dataclass
class ExecutionStartupReport:
    startup_date: str          # ISO date（起動日）
    generated_at: str          # ISO 8601 UTC
    status: str                # READY / READY_WITH_WARNINGS / BLOCKED
    orders_synced: int
    orders_no_status: int
    position_discrepancies: list[dict]  # PositionDiscrepancy の dict 表現
    warnings: list[str]
```

---

## 5. ステータス判定ロジック

```
BLOCKED 条件（いずれかが真）:
  - orders_no_status > 0
    → 注文ステータス不明は二重発注・未約定放置のリスクがあり執行継続不可

READY_WITH_WARNINGS 条件（BLOCKED でなく、いずれかが真）:
  - len(position_discrepancies) > 0
    → DB とブローカー間で数量差分あり。執行は継続できるが要確認

READY:
  - orders_no_status == 0 かつ position_discrepancies が空
```

---

## 6. 出力フォーマット

### 6.1 CLI サマリ（stdout）

```
====================================================
  Execution Startup Summary  2026-04-27
  Status : ✅ READY
====================================================
  Reconciliation:
    orders_synced      :      3
    orders_no_status   :      0
    position_discrepancies: 0 件
====================================================
```

### 6.2 保存先

`artifacts/execution_startup/{startup_date}/` に以下を保存:

| ファイル | 内容 |
|---------|------|
| `summary.json` | 全指標 JSON |
| `report.md` | Markdown レポート（人間向け） |
| `warnings.json` | 警告リスト JSON |

既存の `night_batch_report.py` / `pre_market_report.py` と同じディレクトリ構造・ファイル名規約に準拠する。

---

## 7. run_execution.py への統合

Reconciler 実行直後（発注ループ開始前）に以下を追加する:

```python
from kabusys.operations.execution_startup_report import build_report, format_cli_summary, save_report

reconcile_result = reconciler.run()

report = build_report(
    reconcile_result=reconcile_result,
    startup_date=date.today(),
)
print(format_cli_summary(report))
save_report(report)
```

`run_execution.py` の変更は最小限に留め、レポート生成の失敗が Execution の起動を妨げないよう `try/except` で保護する。

---

## 8. テスト方針

`tests/test_execution_startup_report.py` で純粋関数のみをテストする:

- `_determine_status()`: BLOCKED / READY_WITH_WARNINGS / READY の各境界条件
- `_generate_warnings()`: 各警告メッセージの生成
- `build_report()`: ReconcileResult からレポートが正しく構築されること
- `format_cli_summary()`: ステータス文字列が含まれること
- `format_json()`: JSON パースが成功し必要キーが存在すること
- `format_markdown()`: 必要なセクションが含まれること
- `save_report()`: 3 ファイルが生成されること / 不正な startup_date でエラーになること

`run_execution.py` への統合は既存の integration テストが通ることで確認する（新規テストなし）。

---

## 9. スコープ外

- ログファイルの ERROR/CRITICAL 解析（run_execution.py が正常起動しサマリ生成できた時点で「起動ログに重大エラーなし」を意味するため）
- Execution 以外のプロセス（monitoring 等）の状態確認
- リアルタイム更新や Streamlit UI
- LINE / Slack 通知
