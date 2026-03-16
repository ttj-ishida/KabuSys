# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-16

初回公開リリース。

### Added
- パッケージのエントリポイントを追加
  - `kabusys.__init__` にてバージョン (0.1.0) と公開モジュール (`data`, `strategy`, `execution`, `monitoring`) を定義。

- 環境設定管理モジュール (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - ロード優先順位: OS 環境変数 > .env.local > .env。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用）。
  - .env パーサーは `export KEY=val`、クォート済み値のバックスラッシュエスケープ、インラインコメント等に対応。
  - OS 環境変数を保護するための上書きロジック（protected set）を実装。
  - 必須設定を取得する `_require()` と、各種プロパティでの型変換・検証を実装:
    - J-Quants、kabu API、Slack トークン・チャネル、DB パス (`duckdb_path`, `sqlite_path`) など。
  - `KABUSYS_ENV` の値検証（`development` / `paper_trading` / `live`）と `LOG_LEVEL` 検証を実装。
  - 使い方の例: `from kabusys.config import settings`。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を実装する `_RateLimiter`。
  - リトライロジック: 指数バックオフ、最大 3 回、対象ステータス 408/429 および 5xx。
  - 401 応答時はリフレッシュトークンで自動的に ID トークンを再取得して 1 回リトライする処理を実装（無限再帰回避）。
  - ページネーション対応のフェッチ関数:
    - `fetch_daily_quotes(...)`
    - `fetch_financial_statements(...)`
    - `fetch_market_calendar(...)`
  - DuckDB へ冪等に保存する `save_*` 関数を実装（INSERT ... ON CONFLICT DO UPDATE を使用）:
    - `save_daily_quotes(conn, records)`
    - `save_financial_statements(conn, records)`
    - `save_market_calendar(conn, records)`
  - データ変換ユーティリティ `_to_float` / `_to_int` を実装（空値や例外ケースを安全に扱う。`_to_int` は "1.0" などの float 文字列を許容し、小数部が存在する場合は None を返すという厳密な方針を採用）。
  - 取得日時を UTC の ISO8601（Z）で記録する `fetched_at` の付与により Look‑ahead Bias の可視化を支援。
  - モジュールレベルの ID トークンキャッシュでページネーション間のトークン共有を最適化。

- DuckDB スキーマ定義・初期化モジュール (`kabusys.data.schema`)
  - DataPlatform に基づく 3 層構造（Raw / Processed / Feature）と Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - インデックス定義（よく使うクエリパターンに対する複数の INDEX を作成）。
  - 外部キー依存順を考慮した DDL 実行順を整理。
  - `init_schema(db_path)` によりディレクトリ自動作成、テーブルの冪等作成を実施。
  - `get_connection(db_path)` により既存 DB への接続を取得（スキーマ初期化は行わない旨を明記）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分更新（差分取得 + バックフィル）を行う ETL 実装:
    - デフォルトのバックフィル日数は 3 日（`_DEFAULT_BACKFILL_DAYS`）。
    - 市場カレンダーは先読み（デフォルト 90 日）し営業日判定に利用。
  - 個別ジョブ:
    - `run_prices_etl(...)`
    - `run_financials_etl(...)`
    - `run_calendar_etl(...)`
  - メインエントリ `run_daily_etl(...)` を実装（処理順: カレンダー → 株価 → 財務 → 品質チェック）。
  - ETL の結果を表す `ETLResult` dataclass を提供（品質問題、エラーの集約・シリアライズ用 `to_dict()` を含む）。
  - ETL の設計方針:
    - API 後出し修正を吸収するための backfill。
    - 品質チェックは Fail‑Fast ではなく問題を収集し呼び出し元が判断する方式。
    - id_token の注入によりテスト容易性を確保。
  - ヘルパー: テーブル存在チェック、最大日付取得、営業日への調整（`_adjust_to_trading_day`）等を実装。

- データ品質チェックモジュール (`kabusys.data.quality`)
  - DataPlatform に基づく品質チェック一式を実装:
    - 欠損データ検出 (`check_missing_data`) — OHLC 欠損を検出（volume は除外）。
    - 異常値（スパイク）検出 (`check_spike`) — 前日比での急騰/急落を検出（デフォルト閾値 50%）。
    - 重複チェックや日付不整合チェックの骨子（SQL ベース）を設計。
  - 問題は `QualityIssue` dataclass として返却（check_name / table / severity / detail / rows）。
  - SQL はパラメータバインドを利用しインジェクション対策を施している。
  - スパイク検出は LAG ウィンドウを用いて効率的に実行。

- 監査ログ（トレーサビリティ）モジュール (`kabusys.data.audit`)
  - シグナルから約定までのトレーサビリティ用テーブルを実装:
    - `signal_events`, `order_requests`, `executions`
  - 発注の冪等性を担保する `order_request_id`、証券会社約定の冪等キー `broker_execution_id` を明確化。
  - 全ての TIMESTAMP を UTC で保存するため `SET TimeZone='UTC'` を実行。
  - ステータス遷移や制約（limit/stop/market のチェック、外部キーの ON DELETE 制約等）を明記。
  - 監査向けのインデックス群を作成し検索効率を考慮。
  - `init_audit_schema(conn)` / `init_audit_db(db_path)` を提供。

- その他
  - 空パッケージプレースホルダ:
    - `kabusys.execution.__init__`, `kabusys.strategy.__init__`, `kabusys.data.__init__` を配置（今後の拡張予定）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 環境変数読み取り時に OS 環境変数を保護する仕組みを導入（.env による上書きを制限）。
- J-Quants のトークンはモジュール内でキャッシュおよび安全に更新される（401 時の自動リフレッシュで明示的な再取得を行う。ただしトークンそのものの保護はユーザー側に依存）。

### Known limitations / Notes
- strategy / execution 層の具体的な取引ロジックおよび監視（monitoring）モジュールはまだ未実装の部分がある（パッケージプレースホルダのみ）。
- DuckDB スキーマのデータ型チェックや制約は定義済みだが、運用上のマイグレーション戦略（DDL 変更時の扱い）は別途検討が必要。
- ETL は外部 API に依存するため、ローカルでのテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用して環境を制御してください。
- `jquants_client._to_int` の仕様により、小数部を持つ数値文字列は意図的に None を返す（データの不整合を検出するための厳格な方針）。

---

今後の予定（例）
- strategy 層に戦略ライブラリを実装（シグナル生成、リスク管理）。
- execution 層にブローカー（kabu/他）への送受信実装、発注再試行・状態遷移処理の追加。
- monitoring / alerting（Slack 連携等）の実装拡張。