# Changelog

すべての変更は Keep a Changelog の形式に従いドキュメント化しています。  
このファイルには主にパッケージ初期実装（v0.1.0）の追加機能と設計上の重要点を記載しています。

全般的な注意
- 型アノテーション、ロギング、明示的なエラーハンドリングを多用した実装です。
- DuckDB をデータストアに利用する設計になっています（init_schema / get_connection を提供）。
- セキュリティ面（SSRF、XML Bomb、レスポンスサイズ制限等）に配慮した実装を行っています。

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期実装を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境変数/設定管理モジュール（src/kabusys/config.py）
  - .env ファイル（.env, .env.local）と OS 環境変数の自動読み込み機能を実装。
    - 読み込み順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - .env の読み込み時、既存の OS 環境変数は protected として上書きから保護。
  - .env パーサーの実装: コメント、export プレフィックス、クォート内のエスケープ、インラインコメントなどに対応。
  - Settings クラスを公開:
    - 必須環境変数アクセス: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）
    - デフォルト値: KABUSYS_API_BASE_URL（ローカルデフォルト）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）など
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のヘルパープロパティ

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API のベース実装（_BASE_URL 固定）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ、最大リトライ回数 3、408/429/5xx を再試行対象に設定。429 の場合は Retry-After を優先。
  - 401 ハンドリング: 受信時にリフレッシュトークンで id_token を自動更新し 1 回リトライ（無限再帰回避）。
  - ページネーション対応のフェッチ関数:
    - fetch_daily_quotes（株価日足 / OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes → raw_prices テーブル
    - save_financial_statements → raw_financials テーブル
    - save_market_calendar → market_calendar テーブル
  - データ整形ユーティリティ: _to_float / _to_int（不正値・空値は None）
  - トークンキャッシュをモジュールレベルで保持し、ページネーションで共有

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得と記事保存ワークフローを実装:
    - fetch_rss: RSS 取得、XML の安全パース、記事抽出、前処理（URL 除去・空白正規化）、記事ID生成
    - save_raw_news: raw_news テーブルに対するチャンク化された INSERT … RETURNING、トランザクション制御
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け（news_symbols）をチャンクで安全に保存
    - extract_stock_codes: テキスト中の 4 桁銘柄コード抽出（known_codes によるフィルタ、重複除去）
  - セキュリティ/堅牢性設計:
    - defusedxml を利用した XML パース（XML Bomb 対策）
    - SSRF 対策: URL スキーム検査、ホストがプライベート IP かどうか検査、リダイレクト時にも事前検証するカスタムハンドラを実装
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の上限検査（Gzip bomb 対策）
    - 受信サイズ上限を超える場合はスキップしログ出力
    - 記事 ID: URL 正規化（トラッキングパラメータ除去など）→ SHA-256 の先頭 32 文字を使用して冪等性を担保
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加（DEFAULT_RSS_SOURCES）

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataSchema.md に基づく 3 層構造（Raw / Processed / Feature / Execution）のテーブルを定義
  - 主要テーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY, CHECK など）を付与
  - インデックスを定義（頻出クエリパターンを想定）
  - init_schema(db_path) によりディレクトリ作成 → テーブル作成（冪等） → DuckDB 接続を返す
  - get_connection(db_path) を提供（既存 DB へ接続、スキーマ初期化は行わない）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラス（ETL 実行結果の集約、品質検査結果を含む）
  - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists / _get_max_date）
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）
  - 差分更新ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl 実装（差分取得、バックフィルの日数指定、jquants_client 経由で取得 → 保存）、初回取得日向け _MIN_DATA_DATE 等の定数を定義
  - 設計方針:
    - デフォルトで後出し修正吸収のため backfill_days=3
    - 品質チェックは収集は続行し、呼び出し元で対応する方式（Fail-Fast ではない）
    - テストしやすさのため id_token を注入可能

### Security
- ニュース収集に関する複数のセキュリティ対策を実装:
  - defusedxml による安全な XML パース（XXE/XML Bomb 対策）
  - SSRF 対策: スキーム検証、プライベートアドレス検出、リダイレクト時の事前検証ハンドラ
  - レスポンスサイズ制限（10 MB）と gzip 展開後の検査（Gzip Bomb 対策）
- jquants_client のリトライ/429 の Retry-After 考慮により外部 API レート制限・攻撃耐性を向上

### Notable defaults / required envs
- 必須環境変数（Settings が参照、未設定時 ValueError）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトファイルパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- KABUSYS_ENV: development / paper_trading / live（これ以外はエラー）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（これ以外はエラー）

### Changed
- （初版なので変更点はありません）

### Fixed
- （初版なので修正点はありません）

### Removed
- （初版なので除去点はありません）

### Deprecated
- （初版なので非推奨事項はありません）

補足
- run_prices_etl 以下の ETL ジョブや品質チェックモジュール（quality）の詳細実装はこのリリースで想定された API を提供していますが、別ファイル（quality 等）の実装状況に依存します。
- 初期リリースでは主にデータ取得・保存・スキーマ整備・ニュース収集の基盤を整備しています。運用や拡張（戦略実装、実行モジュール、監視連携など）は今後のリリースで追加予定です。