# TODO: 夜間バッチ結果確認レポートの運用フロー接続

- ステータス: **未接続**
- 関連モジュール: `src/kabusys/operations/night_batch_report.py`（実装済み）
- 関連仕様: `documents/10_Runtime/MVP_NightBatchOperationsReportSpec.md`

---

## 1. 現状

`src/kabusys/operations/night_batch_report.py` は以下の機能をすべて実装済みである。

- `build_report()` — `JobRunResult` リストから `NightBatchReport` を構築
- `format_cli_summary()` / `format_json()` / `format_markdown()` — 3 形式出力
- `save_report()` — `artifacts/night_batch/{run_date}/` に保存

しかし、**運用フロー（Task Scheduler + 各バッチスクリプト）に接続されていない**ため、実運用では使われていない。

---

## 2. 未実装の接続部分

### 2-1. ジョブ実行結果の記録機構

各夜間バッチスクリプト（`run_data_update.py` / `run_feature_gen.py` / `run_ai_analysis.py` /
`run_strategy_signal.py` / `run_portfolio_construction.py`）は現在、ジョブの開始時刻・終了時刻・
更新件数・エラーを `JobRunResult` 形式で保存していない。

レポートを生成するには、各ジョブが実行結果を永続化する仕組みが必要。

**想定方針**: 各ジョブ終了時に `artifacts/job_runs/{date}/{job_name}.json` へ書き出す。

```python
# 各バッチスクリプト末尾に追加するイメージ
from kabusys.operations.night_batch_report import JobRunResult
import json
result = JobRunResult(
    job_name="data_update_job",
    status="success",
    started_at=started,
    finished_at=datetime.now(),
    duration_sec=(datetime.now() - started).total_seconds(),
    updated_rows={"prices_daily": count},
    warnings=[],
    errors=[],
)
out_dir = Path("artifacts/job_runs") / str(date.today())
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / f"{result.job_name}.json").write_text(...)
```

### 2-2. ランナースクリプトの作成

`scripts/run_night_batch_report.py` が存在しない。

このスクリプトの責務:
1. `artifacts/job_runs/{today}/` から全ジョブの JSON を読み込み `JobRunResult` を復元
2. DuckDB を参照して `UpdateCounts` と `NextDaySummary` を集計
3. `build_report()` でレポートを構築
4. `format_cli_summary()` を標準出力へ表示
5. `save_report()` で `artifacts/night_batch/{today}/` に保存

### 2-3. Task Scheduler への登録

`scripts/setup_task_scheduler.ps1` に登録がない。

ポートフォリオ構築（21:00）完了後の 21:15 に実行するジョブとして登録する。

```powershell
Register-KabuSysTask -TaskName "KabuSys_NightBatchReport" `
    -Script "run_night_batch_report.py" `
    -TriggerTime "21:15"
```

---

## 3. やること

- [ ] **各夜間バッチスクリプトへの JobRunResult 書き出し追加**
  - 対象: `run_data_update.py`, `run_feature_gen.py`, `run_ai_analysis.py`,
    `run_strategy_signal.py`, `run_portfolio_construction.py`
  - 書き出し先: `artifacts/job_runs/{date}/{job_name}.json`
  - ジョブ失敗時も書き出すこと（`status="failed"`, `errors=[...]`）

- [ ] **`scripts/run_night_batch_report.py` の作成**
  - `artifacts/job_runs/{date}/*.json` を読み込んで `JobRunResult` を復元
  - DuckDB クエリで `UpdateCounts`（各テーブルの当日更新件数）を集計
  - DuckDB クエリで `NextDaySummary`（signal_queue の buy/sell 件数）を集計
  - `build_report()` → `format_cli_summary()` → `save_report()`
  - ジョブ結果 JSON が 0 件でも `BLOCKED` として生成すること

- [ ] **`setup_task_scheduler.ps1` への登録追加**
  - タスク名: `KabuSys_NightBatchReport`
  - 実行時刻: `21:15`（portfolio_construction の 15 分後）
  - ジョブ数カウントを更新（現在 "8 件" → "9 件"）

- [ ] **テスト追加**
  - `run_night_batch_report.py` のユニットテスト（ジョブ JSON なし → BLOCKED 確認等）

---

## 4. 完了条件

- `python scripts/run_night_batch_report.py` を実行すると CLI summary が表示され、
  `artifacts/night_batch/{today}/summary.json` と `report.md` が生成される
- 夜間バッチ完了後の 21:15 に Task Scheduler が自動実行する
- ジョブ失敗時も `BLOCKED` レポートが必ず生成される

---

## 5. 関連ファイル

| ファイル | 状態 |
|---|---|
| `src/kabusys/operations/night_batch_report.py` | 実装済み（接続待ち） |
| `scripts/run_night_batch_report.py` | **未作成** |
| `scripts/setup_task_scheduler.ps1` | 登録なし |
| `scripts/run_data_update.py` | JobRunResult 書き出し未実装 |
| `scripts/run_feature_gen.py` | JobRunResult 書き出し未実装 |
| `scripts/run_ai_analysis.py` | JobRunResult 書き出し未実装 |
| `scripts/run_strategy_signal.py` | JobRunResult 書き出し未実装 |
| `scripts/run_portfolio_construction.py` | JobRunResult 書き出し未実装 |
