# Position Reconciliation View 設計仕様

**Issue:** #204
**Date:** 2026-04-27
**Status:** Approved

---

## 1. 概要

DB上のローカル推定ポジション（注文履歴から集計）と証券口座（kabuステーション）のポジションを突き合わせ、一致・不一致を銘柄単位で表示する独立CLIコマンドを実装する。

任意のタイミングで実行でき（朝の事前確認・ザラ場中・手動確認等）、`--watch` オプションによる定期ポーリングもサポートする。

---

## 2. 設計方針

- **スタンドアロンコマンド**として実装する。Execution Startup Summary (#201) には組み込まない（起動時レポートは既に差分警告を表示しており重複になるため）
- `signal_queue_report.py` / `pre_market_report.py` / `execution_startup_report.py` と同じ分離パターンに従う：
  - DBアクセスは `collect_position_snapshot()` のみ
  - それ以外はすべて純粋関数
- **全保有銘柄を表示**する（差分がある銘柄に限らず、broker・local の union を一覧表示）
- `--watch` による定期ポーリングをエントリーポイントで実装する

---

## 3. ファイル構成

| ファイル | 役割 |
|---------|------|
| `src/kabusys/operations/position_reconciliation_report.py` | `collect_position_snapshot()` + 純粋関数群（`build_report` / `format_*` / `save_report`） |
| `src/kabusys/run_position_reconciliation_report.py` | CLIエントリーポイント。DB接続・引数解析・`--watch` ループ |
| `tests/test_position_reconciliation_report.py` | ユニットテスト |

---

## 4. データモデル

### 4.1 PositionEntry

```python
@dataclass
class PositionEntry:
    code: str
    broker_qty: int   # ブローカー側保有数量（未保有なら 0）
    local_qty: int    # ローカルDB推定数量（Filled/PartialFill の net qty）
    diff: int         # broker_qty - local_qty（0 なら一致）
    status: str       # "MATCH" / "MISMATCH"
```

### 4.2 PositionReconciliationReport

```python
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
```

**ステータス定義：**
- `CLEAN` — 全銘柄 diff == 0（保有ゼロ銘柄を含む）
- `DISCREPANCY` — 1件以上 diff ≠ 0

---

## 5. コアモジュール（`position_reconciliation_report.py`）

### 5.1 `collect_position_snapshot(broker, repo) -> list[PositionEntry]`

DB・ブローカーAPIに触れる唯一の関数。

**処理：**
1. `broker.get_positions()` → `broker_map: dict[str, int]`（同一コードは合算）
2. `repo.list_active()` → `Filled` / `PartialFill` の注文から `local_map: dict[str, int]`（buy加算・sell減算）
3. `union(broker_map, local_map)` の全コードに対して `PositionEntry` を生成
4. `code` 昇順でソートして返す

**ローカル推定の制約（既存 Reconciler と同仕様）：**
- `Filled` → net qty に加減算
- `PartialFill` → `filled_qty` を加減算
- `Closed` / `Cancelled` / `Rejected` は除外
- 将来 Closed 遷移が実装された場合は再検討が必要

### 5.2 `build_report(entries, *, report_date) -> PositionReconciliationReport`

純粋関数。`entries` リストから `PositionReconciliationReport` を構築する。

### 5.3 `_generate_warnings(entries) -> list[str]`

純粋関数。MISMATCH 銘柄ごとに警告文字列を生成する。

```
code=7203: broker=100株 / local=80株 (diff=+20)
```

brokerのみ存在（local=0）や localのみ存在（broker=0）も MISMATCH として警告に含める。

### 5.4 フォーマッター

**`format_cli_summary(report)`：** ステータス・件数サマリー + 全銘柄テーブル（MISMATCH行はわかるよう `[!]` マーク）

**`format_json(report)`：** `asdict(report)` の JSON

**`format_markdown(report)`：** Overview テーブル + 全銘柄テーブル + Warnings セクション（差分がある場合）+ Final Decision

### 5.5 `save_report(report, output_dir=None) -> Path`

保存先：`artifacts/position_reconciliation/{report_date}/`

保存ファイル：
- `summary.json`
- `report.md`
- `warnings.json`

`report_date` の形式バリデーション：正規表現 + `date.fromisoformat()` （既存モジュールと同仕様）

---

## 6. エントリーポイント（`run_position_reconciliation_report.py`）

### 6.1 CLIオプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--date YYYY-MM-DD` | `date.today()` | 対象日（`save_report` の保存先ディレクトリ名に使用） |
| `--save` | False | `artifacts/position_reconciliation/` に保存する |
| `--json` | False | JSON形式で出力する |
| `--watch` | False | 定期ポーリングモードで実行する |
| `--interval N` | 600 | `--watch` 時のポーリング間隔（秒） |

### 6.2 通常実行フロー

1. `Settings()` から `sqlite_path` / `duckdb_path` を取得
2. `sqlite_conn = sqlite3.connect(str(sqlite_path))`
3. `broker = BrokerClientFactory.create(settings)`
4. `repo = OrderRepository(sqlite_conn)`
5. `entries = collect_position_snapshot(broker, repo)`
6. `report = build_report(entries, report_date=args.date)`
7. `format_cli_summary` または `format_json` で print
8. `--save` なら `save_report(report)`
9. `sqlite_conn.close()`
10. 終了コード：`CLEAN=0`, `DISCREPANCY=1`

### 6.3 `--watch` モード

```python
while True:
    try:
        # 接続 → collect → build → print → (save)
        ...
    except KeyboardInterrupt:
        break
    except Exception as e:
        logger.error("ポーリング中にエラー: %s", e)
    time.sleep(args.interval)
```

- 各ループで SQLite 接続を開閉する（長時間接続によるロック回避）
- `--save` と組み合わせると各ループで `artifacts/` に上書き保存
- Ctrl+C で正常終了（終了コード 0）
- エラーが発生しても次のループへ継続（ログ出力のみ）

---

## 7. テスト方針

`tests/test_position_reconciliation_report.py` に以下を実装する。

**`collect_position_snapshot` のテスト（MockBroker + in-memory SQLite）：**
- 空の場合（broker・local ともゼロ）
- broker のみ保有（local に注文なし）
- local のみ推定（broker に未反映）
- 一致するケース
- 差分があるケース
- 複数銘柄の混在

**`build_report` のテスト（純粋関数）：**
- CLEAN ステータス
- DISCREPANCY ステータス
- カウント集計の正確性
- `generated_at` がUTC

**フォーマッターのテスト：**
- `format_cli_summary`：CLEAN / DISCREPANCY 各ケース、`[!]` マーク
- `format_json`：必須キーの存在
- `format_markdown`：必須セクション、Full Decisionセクション

**`save_report` のテスト（`tmp_path`）：**
- 3ファイル生成
- 不正日付で ValueError
- 存在しないカレンダー日付で ValueError
- 冪等（2回実行しても例外なし）

---

## 8. 依存関係

- `kabusys.execution.broker_factory.BrokerClientFactory`
- `kabusys.execution.broker_api.BrokerAPIProtocol`, `Position`
- `kabusys.execution.order_repository.OrderRepository`
- `kabusys.execution.order_record.OrderState`
- `kabusys.config.Settings`

---

## 9. 完了条件

- `python -m kabusys.run_position_reconciliation_report` が1コマンドで実行できる
- 全銘柄の broker / local 数量が一覧表示される
- MISMATCH 銘柄が明示される（CLI では `[!]` マーク、Markdown では Warnings セクション）
- `--watch --interval 300` で10分ごとの定期確認が動作する
- `pytest tests/test_position_reconciliation_report.py` が全件 PASS
- `ruff check` が通る
