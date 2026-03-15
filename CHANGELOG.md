# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

<!-- 参考: 変更履歴はコードベースから推測して作成しています。 -->

## [0.1.0] - 2026-03-15

### Added
- パッケージ初期リリース。トップレベルパッケージ `kabusys` を追加。
  - バージョン: 0.1.0
  - エクスポート: `data`, `strategy`, `execution`, `monitoring`

- 環境変数・設定管理モジュール (`kabusys.config`)
  - .env ファイルの自動読み込み機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
    - プロジェクトルート判定は `.git` または `pyproject.toml` を基準に行う（CWD に依存しない実装）。
  - .env のパースロジックを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 環境変数保護機構（OS 環境変数を protected として上書きを防ぐ）サポート。
  - 必須設定取得関数 `_require` を実装し、未設定時に分かりやすいエラーメッセージを返す。
  - Settings クラスを提供（プロパティ経由で設定値を取得）。
    - J-Quants、kabuステーション、Slack、DB パス、ログレベル、実行環境（development/paper_trading/live）等のプロパティを定義。
    - `KABUSYS_ENV` の値検証、`LOG_LEVEL` の値検証を実装。
    - ヘルパー: `is_live`, `is_paper`, `is_dev` プロパティを追加。
    - デフォルト DB パス: DuckDB `data/kabusys.duckdb`、SQLite `data/monitoring.db`（いずれも expanduser 対応）。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 基本設計方針に沿ったクライアント実装:
    - レート制限（120 req/min）に対応する固定間隔スロットリング（_RateLimiter）。
    - 再試行（指数バックオフ、最大 3 回。対象: 408, 429, 5xx およびネットワークエラー）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）と再試行ロジック。無限再帰を防ぐ仕組み（allow_refresh フラグ）。
    - ページネーション対応（pagination_key を用いた取得、モジュールレベルの ID トークンキャッシュ共有）。
    - 取得時刻（fetched_at）を UTC ISO8601 形式で記録する方針（Look-ahead Bias 防止）。
    - JSON デコード失敗時の明確なエラー報告。
  - API 呼び出しユーティリティ `_request` を実装（GET/POST、ヘッダ、タイムアウト、Retry-After 処理など）。
  - 認証ヘルパー `get_id_token` を実装（リフレッシュトークン → idToken を取得）。
  - データ取得関数を実装:
    - `fetch_daily_quotes`（株価日足、ページネーション対応）
    - `fetch_financial_statements`（四半期財務、ページネーション対応）
    - `fetch_market_calendar`（JPX マーケットカレンダー）
  - DuckDB への保存関数を追加（冪等性を考慮）:
    - `save_daily_quotes` → `raw_prices` テーブルへ INSERT ... ON CONFLICT DO UPDATE（重複更新）
    - `save_financial_statements` → `raw_financials`
    - `save_market_calendar` → `market_calendar`
    - PK 欠損行のスキップとログ警告処理
  - データ型変換ユーティリティ:
    - `_to_float`（安全な float 変換、失敗時は None）
    - `_to_int`（整合性チェック付きの int 変換、"1.0" 等は許容、非整数小数は None）

- DuckDB スキーマ定義・初期化モジュール (`kabusys.data.schema`)
  - DataLayer を想定したスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - Raw テーブル: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
  - Processed テーブル: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
  - Feature/AI テーブル: `features`, `ai_scores`
  - Execution テーブル群: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに適切な型、CHECK 制約、PRIMARY KEY、外部キー制約を付与。
  - 検索パフォーマンス向上のための索引（インデックス）を多数定義（銘柄×日付パターン、ステータス検索、外部キー参照用など）。
  - テーブル作成順序を外部キー依存に合わせて制御。
  - 公開 API:
    - `init_schema(db_path)`：DuckDB ファイルの親ディレクトリ自動作成、全 DDL 実行（冪等）、接続返却。
    - `get_connection(db_path)`：既存 DB への接続取得（スキーマ初期化は行わない）

- 監査ログ・トレーサビリティモジュール (`kabusys.data.audit`)
  - シグナルから約定までのトレーサビリティを意図した監査テーブル群を実装。
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を想定。
  - テーブル:
    - `signal_events`（戦略が生成したシグナルの全記録。棄却・エラーも記録）
    - `order_requests`（冪等キー order_request_id を持つ発注要求ログ。価格チェック（limit/stop）などのチェック制約を実装）
    - `executions`（証券会社からの約定ログ、broker_execution_id をユニーク冪等キーに設定）
  - 監査用索引を定義（戦略別・日付別検索、status スキャン、broker_order_id 結び付け等）。
  - 公開 API:
    - `init_audit_schema(conn)`：既存 DuckDB 接続に監査テーブルを追加（SET TimeZone='UTC' を実行）。
    - `init_audit_db(db_path)`：監査専用 DB を初期化して接続を返却。

### Security
- 認証トークンの扱い:
  - id_token の自動リフレッシュを組み込み、401 発生時は 1 回だけ再取得して再試行する実装により、長時間稼働でも認証切れから自動復旧可能。
  - get_id_token 呼び出し時は allow_refresh=False を使って無限再帰を防止。

### Notes / 推測
- Slack 連携のための必須環境変数（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を Settings で定義しているため、初期リリースでは Slack 通知機能（monitoring 等）を想定している。
- kabu ステーション API 用に `KABU_API_PASSWORD` と `KABU_API_BASE_URL` が設定可能。実取引（live）/ペーパートレード（paper_trading）の環境切替を想定。
- データ保存は DuckDB を主要なストレージとして設計。監査ログは削除しない方針（ON DELETE RESTRICT）でトレーサビリティを重視。
- Look-ahead Bias に対する注意（fetched_at を UTC で保存）や冪等性（ON CONFLICT DO UPDATE）など、運用を意識した設計が施されている。

### Breaking Changes
- 初期リリースのため該当なし。

--- 

今後のリリース案内や個別の変更点をより詳しく記載するために、実際のコミットメッセージやリリースノート（機能追加・バグ修正・互換性の変化）を提供いただければ、CHANGELOG を拡張して反映します。