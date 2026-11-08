# 日次成績の記録（portfolio_performance）設計

- Issue: #427
- ブランチ: `fix/issue-427-performance-record`

ユーザーから「Issue を進めてください」と指示されているため、以下の判断は確認を経ずに決めた。PR で確認してもらう。

## 1. 問題

成績レポート（`run_performance_report`）・夜 LINE の「当日リターン」・`market_close_report`・Streamlit の Performance ページは、すべて `portfolio_performance` を読む。しかし、このテーブルに書き込む処理がどこにもない（運用 DB は 0 行）。また、`run_performance_report --env` の既定値は `live` で、運用の `KABUSYS_ENV`（`paper_trading`）と一致しない。

## 2. 決定事項

### 2.1 記録ジョブ
- 新規 `src/kabusys/operations/performance_recorder.py` に `record_daily_performance(conn, *, as_of: date, env: str, equity: float, cash: float) -> PerformanceRow` を置く。
  - `(date, env)` 単位で UPSERT する（冪等）。
  - `daily_return` = equity ÷ 同じ env の直前の日付の equity − 1（直前がない場合は None）。
  - `drawdown` = equity ÷ 同じ env の as_of 以前の最大 equity（当日を含む）− 1。0 以下の値（例 −0.05）。
- 新規 `scripts/run_performance_record.py [--date YYYY-MM-DD]`（既定は今日）。既存スクリプトと同じく process_registry・logging・job_run_recorder を使う。job 名は `performance_record_job`。
  - 資産額の算出元:
    - `MANUAL_TRADING_ENABLED=true` → `calc_manual_portfolio_value(conn, settings.manual_trading_initial_cash, as_of=date)`（総資産＝equity、利用可能現金＝cash）。
    - それ以外で `KABUSYS_ENV=paper_trading` / `development` → 既存の Paper の資産算出（`scripts/run_portfolio_construction.py` の `_calc_paper_portfolio_value`）を `src/kabusys/operations/` に移して共用する（ロジックは変更しない）。
    - `live`（自動執行・証券口座）→ 今回は対象外。警告ログを出して何もしない（終了コード 0）。
  - env には `settings.env` を記録する（手動運用でも `paper_trading` など、`.env` の値をそのまま使う）。
  - 非営業日は記録しない（`is_trading_day` が False なら何もせずに終了）。
- スケジュール: `scripts/run_scheduler.py` に `JobSpec("performance_record", "run_performance_record.py", [], 18, 0, True)` を追加する（17:30 の data_update の後で、当日の終値が入ってから記録する。DuckDB に書き込むため排他）。`setup_task_scheduler.ps1` にも 18:00 で登録する（既存の書式に合わせる）。

### 2.2 レポート側
- `run_performance_report --env` の既定値を `settings.env` にする（choices に `development` も加える）。
- 夜 LINE の「当日リターン」は、記録があれば自然に表示されるようになる（コード変更不要）。

### 2.3 ドキュメント
- RuntimeJobSchedule.md の時刻表に 18:00 `performance_record` を追加する。
- TradingRunbook.md・D_LiveOperation.md の「成績レポートは現在空になる」という注意書きを、「18:00 に日次の成績を記録し、成績レポートで確認できる（手動運用は元手＋手動約定ベース）」に改める。

## 3. テスト
- `record_daily_performance`：初日（daily_return None、drawdown 0）、2 日目の騰落率、ピークからの下落率、同じ日を再実行しても 1 行（冪等）、env ごとに独立。
- スクリプト：手動運用モードで `calc_manual_portfolio_value` の値を記録する、live モードは何もしない、非営業日は何もしない（いずれも関数単位でテストできる構成にする）。
- `run_performance_report` の既定の env が `settings.env` になる。
- スケジューラーに 18:00 `performance_record` がある（`excl=True`）。
- 既存テストが通ること（paper の資産算出を移したため、`tests/test_scripts_batch.py` などのモック先の変更が必要なら最小限にする）。

## 4. 対象外
- live（証券口座）の成績記録
- 過去日付の成績の遡及作成（手動運用の約定から過去分を再計算することは可能だが、今回は `--date` を使った手動実行に留める）
