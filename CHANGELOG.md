# CHANGELOG

すべての非互換変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog のフォーマットに準拠します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

初回リリース。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは `0.1.0`。（src/kabusys/__init__.py）
  - package-level のエクスポート: data, strategy, execution, monitoring。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込むユーティリティを追加。
  - プロジェクトルート自動検出機能（.git または pyproject.toml を起点）を実装。CWD に依存しない自動ロードをサポート。
  - .env 自動ロードの順序: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途）。
  - .env パーサーで export 構文、クォートやエスケープ、インラインコメント、キー保護（override/protected）に対応。
  - Settings オブジェクトを提供し、アプリ設定にアクセスするプロパティを実装:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`
    - kabuステーション: `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト http://localhost:18080/kabusapi）
    - Slack: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DB パス: `DUCKDB_PATH`（デフォルト data/kabusys.duckdb）、`SQLITE_PATH`
    - 環境判定: `KABUSYS_ENV`（development/paper_trading/live）および `LOG_LEVEL` の検証
    - ヘルパー: `is_live`, `is_paper`, `is_dev`

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリングを実装（内部 RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。対象ステータスコードのリトライ（408、429、および 5xx）。
  - 401 Unauthorized 受信時はリフレッシュトークンでのトークン更新を 1 回試行して再リクエスト。
  - ページネーション対応のフェッチ関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止する設計。
  - 型変換ユーティリティ `_to_float`, `_to_int` を実装（不正値は None）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからのニュース収集機能を実装。
  - セキュリティ対策と堅牢性:
    - defusedxml による XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証、ホストのプライベート/ループバック判定、リダイレクト時の事前検証ハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査。
    - 許可スキームは http/https のみ。
  - URL 正規化（トラッキングパラメータ除去、フラグメント除去、クエリソート）と SHA-256 による記事ID生成（先頭32文字）。
  - テキスト前処理（URL除去、空白正規化）。
  - DB への保存はチャンク/トランザクションで実施し、INSERT ... RETURNING を使用して実挿入数を取得:
    - save_raw_news（raw_news テーブル）
    - save_news_symbols（news_symbols テーブル）
    - 内部一括保存 `_save_news_symbols_bulk`
  - 銘柄コード抽出ユーティリティ `extract_stock_codes`（4桁数字に基づき known_codes と照合）。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を設定。

- DuckDB スキーマ定義および初期化 (kabusys.data.schema)
  - DataPlatform 設計に沿ったスキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 多数のテーブルと制約（型チェック、PRIMARY KEY、FOREIGN KEY、CHECK 制約）を定義:
    - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など
  - 頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) により親ディレクトリ作成・DDL 実行・接続返却（冪等）。
  - get_connection(db_path) で既存 DB 接続を返す（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新を行う ETL パイプライン用モジュールを追加（差分取得、保存、品質チェックの呼び出しに基づく設計）。
  - ETL の実行結果を表す dataclass `ETLResult` を導入（品質問題・エラーの集約、辞書化）。
  - テーブル存在確認、最大日付取得ユーティリティ（_table_exists, _get_max_date）を提供。
  - market_calendar を用いた営業日調整ユーティリティ `_adjust_to_trading_day` を実装。
  - 差分取得ヘルパー get_last_price_date, get_last_financial_date, get_last_calendar_date を追加。
  - run_prices_etl を実装（差分計算、backfill_days デフォルト 3、jquants_client 呼び出し、保存）。取得→保存→ログの流れを実装。

### Changed
- なし（初回リリースのため）

### Fixed
- なし（初回リリースのため）

### Security
- RSS フィード収集における SSRF 緩和、defusedxml の利用、受信サイズ制限、スキーム検証を実装。
- .env ロード時に OS 環境変数を保護する `protected` 機構を導入し、意図しない上書きを防止。

### Notes / Known limitations
- run_prices_etl の実装は現状、取得件数と保存件数の処理を行う設計ですが、リリース時点のコードはファイル末尾が途中で切れている箇所があり（戻り値のタプルの構築など）、追加の実装／検証が必要な可能性があります。ETL の完全なジョブ（品質チェックの呼び出し、calendar の先読み、financials の ETL 等）は今後の実装対象です。
- jquants_client は urllib を利用しており、HTTP セッションの再利用や接続プールは未実装。大量リクエストや高スループット運用時は追加の検討が必要です。
- news_collector の既定の RSS ソースは最小構成。追加のソース管理・更新スケジュールやフェイルオーバー戦略は今後の作業予定。
- テストのためにいくつかの内部関数（例: news_collector._urlopen）をモック可能に設計しています。ユニットテストの拡充を推奨します。

### Migration / Upgrade notes
- 初回リリースのためマイグレーションは不要です。既存のデータがある環境で schema 初期化（init_schema）を実行する際は、DDL が冪等であることを確認してから実行してください。

---

参考: 主要な環境変数
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD, KABU_API_BASE_URL
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DUCKDB_PATH, SQLITE_PATH
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 に設定すると .env 自動ロードを無効化)
