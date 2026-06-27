# 夜LINE通知へのシグナル詳細追加 Design Spec

## Goal

夜間バッチ完了後のLINE通知（`format_evening_message`）に、翌日BUY/SELLシグナルの証券コード・証券名・購入株数を含める。

## Architecture

`run_portfolio_construction.py` が `signal_queue JOIN stocks` をクエリしてシグナル詳細リストを生成し、`format_evening_message()` に渡す。`format_evening_message()` はリストを受け取り整形する純粋関数として実装する。

変更は `line_reports.py`（フォーマット）・`run_portfolio_construction.py`（クエリ追加）・`test_line_reports.py`（テスト）の3ファイルのみ。

## Tech Stack

Python 3.10+, DuckDB (JOIN クエリ), pytest

---

## 変更ファイル

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/kabusys/operations/line_reports.py` | Modify | `format_evening_message()` にパラメータ追加 |
| `scripts/run_portfolio_construction.py` | Modify | シグナル詳細クエリと呼び出し更新 |
| `tests/test_line_reports.py` | Modify | 新パラメータのテスト追加 |

---

## 詳細設計

### 1. `format_evening_message()` シグネチャ変更

```python
def format_evening_message(
    *,
    inserted: int,
    report_date: str,
    daily_return: float | None = None,
    buy_signals: list[dict] | None = None,
    sell_signals: list[dict] | None = None,
    max_signals: int = 10,
) -> str:
```

- `buy_signals=None` / `sell_signals=None` のとき件数表示のみ（後方互換維持）
- `buy_signals` 各要素: `{"code": str, "name": str, "size": int}`
- `sell_signals` 各要素: `{"code": str, "name": str}`

### 2. LINE通知フォーマット

```
【KabuSys 夜】2026-06-27
翌日BUY: 3件 / SELL: 1件
当日リターン: +1.2%
───────────────
BUY銘柄:
  7203 トヨタ自動車  100株
  6758 ソニーグループ  200株
  9984 ソフトバンクG  50株
SELL銘柄:
  4661 オリエンタルランド
```

- BUY/SELLともに最大 `max_signals`（デフォルト10）件を表示し、超過分は「他N件」
- `buy_signals=None` のとき（シグナルなし or クエリ失敗）は従来通り件数行のみ

### 3. `run_portfolio_construction.py` クエリ

`signal_queue` 挿入後、LINE通知送信直前に以下をクエリ:

```sql
-- BUY シグナル
SELECT q.code, COALESCE(st.name, q.code) AS name, q.size
FROM signal_queue q
LEFT JOIN stocks st ON q.code = st.code
WHERE q.date = ? AND q.side = 'buy' AND q.status = 'pending'
ORDER BY q.code

-- SELL シグナル
SELECT q.code, COALESCE(st.name, q.code) AS name
FROM signal_queue q
LEFT JOIN stocks st ON q.code = st.code
WHERE q.date = ? AND q.side = 'sell' AND q.status = 'pending'
ORDER BY q.code
```

- クエリ失敗時は `buy_signals=None` / `sell_signals=None` にフォールバックし、LINE通知は件数のみ表示（ジョブ失敗にはしない）

### 4. テスト方針

`tests/test_line_reports.py` に以下を追加:

- `buy_signals=None` → 既存フォーマット（後方互換）
- `buy_signals=[]` → BUY銘柄セクションなし
- BUY 1件 → コード・名前・株数が含まれる
- BUY 12件 → 10件表示 + 「他2件」
- SELL 1件 → コード・名前のみ（株数なし）
- BUY + SELL 混在 → 両セクションが正しく出力される

---

## 制約

- LINE通知の送信失敗はジョブ失敗にしない（既存ポリシー踏襲）
- クエリ失敗時は `buy_signals=None` にフォールバック（LINE通知は件数のみ表示）
- `stocks.name` が NULL の場合は `code` を代用（`COALESCE` で対応）
