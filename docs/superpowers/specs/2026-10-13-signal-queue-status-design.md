# signal_queue ステータス追跡の修正 設計

- Issue: #413
- ブランチ: `fix/issue-413-signal-queue-status`
- 関連: #410（最終レビューで判明）、#398（Paper Trading 検証）

ユーザーから「自動で進められる部分は自動で進める」と指示されている。以下の判断はユーザー確認を経ずに決めたもので、PR で確認してもらう。現在は手動注文がメインの運用で、Execution Engine は起動していない。そのため、ここでの変更は自動発注・Paper Trading に戻すときの安全性を確保するためのものである。

## 1. 問題（Issue 記載分＋調査で判明した既存不具合）

1. PUSH 経由の約定通知（`_handle_push`）で `signal_queue` のステータスが更新されない。
2. 発注直後の `sync_order` の結果が Rejected・Cancelled でも、ステータスが `processing` になる。
3. 重複の扱いが統一されていない。Gate 1 の `DUPLICATE_ORDER` では `failed`、`DuplicateOrderError` では `processing` になる。
4. Gate 2 のレート制限で `failed` になると、同日中に再起動しても再試行されない。
5. failed・重複・ステータス更新失敗の各経路にテストがない。
6. `run_execution.py` が DuckDB を read-write で開き、セッション中ずっとロックを保持する。そのため、ダッシュボードや他ジョブの DuckDB 接続と競合する。
7. **（調査で判明）キューの日付がずれている。** `run_portfolio_construction.py` は夜（D 日）に `signal_queue.date = D` で行を書き込む。一方、翌朝の `run_execution.py` は `target_date = 今日（D+1）` を指定して `WHERE q.date = target_date` で読むため、夜間バッチの行を拾えない。`pre_market_collector.check_signal_queue` と `run_execution._count_pending_signals` も `date = 今日` で数えている。
8. **（調査で判明）** `market_close_collector.check_signal_pending` と `check_signal_filled` が、SQLite に存在しない `signal_queue` テーブルを参照している。
9. `position_entries` の `fill_date = next_trading_day(target_date)` は、`target_date = 今日` だと翌日になる。発注した当日（今日）の寄付で約定する想定とずれている。

## 2. 決定事項

### 2.1 ステータスの記録先を SQLite に移す（問題 6）

- Execution Engine は、`signal_queue` のステータスを DuckDB には書かない。代わりに、SQLite の新しいテーブル `signal_queue_status` に記録する。
  ```sql
  CREATE TABLE IF NOT EXISTS signal_queue_status (
      queue_signal_id TEXT PRIMARY KEY,   -- signal_queue.signal_id
      business_key    TEXT NOT NULL,      -- {signal_date}_{code}_{side}
      signal_date     TEXT NOT NULL,
      code            TEXT NOT NULL,
      side            TEXT NOT NULL,
      status          TEXT NOT NULL CHECK (status IN ('pending','processing','filled','cancelled','failed')),
      reason          TEXT,
      client_order_id TEXT,
      updated_at      TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_sqs_business_key ON signal_queue_status(business_key);
  ```
- 新規モジュール `src/kabusys/execution/signal_queue_status.py` に、次の関数を置く。
  - `ensure_schema(sqlite_conn)`
  - `record(sqlite_conn, ...)`：UPSERT
  - `get_statuses(sqlite_conn, signal_date) -> dict[queue_signal_id, status]`
  - `update_by_client_order_id(sqlite_conn, client_order_id, status, reason=None)`
  - `sync_to_duckdb(duckdb_conn, sqlite_conn) -> int`
- `run_execution.py` は DuckDB を再び `read_only=True` で開く。これで #410 の前の挙動に戻り、他プロセスの読み取りと共存できる。
- 夜間の `run_portfolio_construction.py` は、DuckDB の排他利用を前提とする時間帯に動く。その冒頭で `sync_to_duckdb` を呼び、SQLite のステータスを DuckDB の `signal_queue.status` と `processed_at` に反映する。対象は `status != 'pending'` の行に限る。同期に失敗しても警告ログだけ出して処理を続ける。
- DuckDB スキーマの `orders.signal_id → signal_queue(signal_id)` の外部キーについて：DuckDB の `orders` は Execution Engine では使っていない（注文は SQLite）。このためスキーマは変更せず、コメントで「Execution Engine の注文は SQLite に保存しており、`orders.signal_id` には業務キーが入る」と明記する。

### 2.2 キューの日付をそろえる（問題 7・9）

- `ExecutionConfig`（`EngineConfig`）の `target_date` は「執行日（今日）」のまま変えない。新たに `signal_date` を追加し、既定値は `prev_trading_day(target_date)` とする。`calendar_management` の既存ヘルパーを使い、カレンダーがない場合は土日だけを除外する。
- `_read_signal_queue_rows` は、`WHERE q.date = signal_date` で読む。`signals` との JOIN も同じ日付で行う。
- 発注の業務キーは `{signal_date}_{code}_{side}` とする（夜間バッチの単位で 1 回だけ発注するため）。
- `position_entries` の `fill_date` は `target_date`（執行日。当日の寄付で約定する想定）とする。バックテストの「シグナル翌日の寄付でエントリー」と一致する。
- `run_execution._count_pending_signals`、`pre_market_collector.check_signal_queue`、`market_close_collector` の件数集計も `signal_date`（前営業日）を基準にする。
- テスト環境でシグナルを直接投入する経路（`inject_dummy_signal` やテストのヘルパー）は、`signal_date` を明示して従来どおり動くようにする。

### 2.3 ステータスの遷移

| 事象 | status | reason |
|---|---|---|
| Gate 1 不合格（DUPLICATE_ORDER 以外） | failed | Gate 1 の理由 |
| Gate 1 DUPLICATE_ORDER／`DuplicateOrderError`（同じ業務キーの注文が既にある） | cancelled | duplicate |
| Gate 2 レート制限（3 回リトライ後） | 記録しない（pending のまま） | — |
| Gate 2 サーキットブレーカー | 記録しない（pending のまま。ループ停止） | — |
| 発注直前 | processing | — |
| 発注 API の失敗 | failed | 例外メッセージ |
| `OrderSentPendingError` | processing | sent_pending |
| `sync_order` の結果が Filled | filled | — |
| `sync_order` の結果が Rejected | failed | rejected |
| `sync_order` の結果が Cancelled | cancelled | cancelled |
| それ以外（Accepted・PartialFill・Sent） | processing | — |

- PUSH（`_handle_push`）：`sync_order` の後、注文の状態を上の表で変換し、`update_by_client_order_id` でその注文の行を更新する（問題 1）。
- 起動時のリコンシリエーションの後も、アクティブだった注文について同じように同期する（再起動で状態が取り残されないようにするため）。
- 再起動時の読み込み：`_read_signals` は、SQLite の `signal_queue_status` に `pending` 以外で記録済みの `queue_signal_id` を除外する。業務キーによる重複判定と合わせて、二重発注を二重に防ぐ。
- ステータス記録の失敗は警告ログに留め、発注フローは止めない（現状維持）。

### 2.4 market_close_collector（問題 8）

- pending と filled の件数は、SQLite の `signal_queue_status`（`signal_date` 基準）から数える。テーブルがない場合は 0 とする。

## 3. テスト

- §2.3 の表の各行（Gate 1 の失敗・重複・Gate 2 のレート制限で pending のまま・API の失敗・Filled・Rejected・Cancelled・PUSH での Filled 反映）。
- 同じ業務キーの 2 行（uuid が異なる）があっても注文は 1 件になる（既存テストを維持）。再起動時は、処理済みの行を再読込しない。
- キュー日付：前営業日（金曜 → 月曜を含む）の行を読み、当日の行は読まない。`fill_date` が執行日になる。
- `run_execution` が DuckDB を read_only で開く（読み取り専用接続でエンジンが動く）。
- `sync_to_duckdb` が DuckDB の `signal_queue` を更新し、pending の行には触れない。portfolio_construction から呼ばれる。
- `pre_market_collector`、`market_close_collector`、`_count_pending_signals` の日付基準。
- 既存の統合テスト（`tests/integration/test_integration.py`、`test_paper_trading.py`）を新しい日付の考え方に合わせる。テストの期待値を変える場合は理由をテスト名か docstring に書く。

## 4. 対象外

- DuckDB `orders` テーブルのスキーマ変更
- 発注ロジック・リスクゲートの閾値の変更
