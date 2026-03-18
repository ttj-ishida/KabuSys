# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回公開リリース。

### Added
- パッケージ基本構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py の __version__ を設定)
  - 公開サブパッケージ: data, strategy, execution, monitoring（strategy/execution/monitoring は現時点では初期プレースホルダ）

- 設定・環境変数管理モジュール（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いを考慮）
  - 環境変数保護（OS 環境変数を保護して .env.local で上書きされないようにする）
  - Settings クラス（プロパティ経由で必須値の取得とバリデーション）
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB デフォルトパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境モード検証: KABUSYS_ENV (development|paper_trading|live) の検証
    - ログレベル検証: LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出し共通処理: _request 実装（JSON デコード、timeout、エラーハンドリング）
  - レートリミッタ実装：固定間隔スロットリングで 120 req/min を遵守 (_RateLimiter)
  - リトライ実装：指数バックオフ、最大 3 回、対象ステータス（408, 429, 5xx）
  - 401 発生時の自動トークンリフレッシュ（1 回のみリトライ）とトークンキャッシュ共有
  - get_id_token(): リフレッシュトークンから idToken を取得する POST 実装
  - ページネーション対応のデータ取得関数
    - fetch_daily_quotes (株価日足 OHLCV)
    - fetch_financial_statements (四半期 BS/PL)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換と不正値扱い）

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集の統合ジョブ（run_news_collection）
  - defusedxml による XML パース（XML Bomb 対策）
  - SSRF 対策:
    - URL スキーム検証（http/https のみ）
    - リダイレクト時のスキーム・ホスト検証用ハンドラ (_SSRFBlockRedirectHandler)
    - ホストがプライベート/ループバック等かを DNS 解決＋IP 判定で検査（_is_private_host）
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズチェック（Gzip-bomb 対策）
  - URL 正規化とトラッキングパラメータ除去（utm_ 等を削除）および記事ID生成（正規化URL の SHA-256 先頭32文字）
  - テキスト前処理（URL 除去、空白正規化）
  - RSS → NewsArticle 型へのパース（pubDate の RFC 2822 パースと UTC 正規化）
  - DuckDB への保存（冪等）
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id、チャンク挿入、トランザクション管理
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け保存（重複除去、チャンク・トランザクション、RETURNING を用いて実際に挿入された件数を返す）
  - 銘柄コード抽出（テキスト中の 4 桁数字を known_codes と照合して抽出）

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層をカバーするテーブル定義群
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックス定義を含む
  - init_schema(db_path) によりディレクトリ自動生成と一括DDL実行（冪等）
  - get_connection(db_path)（スキーマ初期化は行わない接続取得）

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult dataclass による実行結果集約（品質問題・エラー一覧を保持）
  - データ差分更新サポート（最終取得日を確認して新規分のみ取得）
  - バックフィル設定（デフォルト backfill_days=3 により最終取得日の数日前から再取得）
  - 市場カレンダー先読み設定 (_CALENDAR_LOOKAHEAD_DAYS = 90)
  - get_last_* ヘルパー（raw_prices/raw_financials/market_calendar の最終日取得）
  - 非営業日の調整ロジック（_adjust_to_trading_day）
  - run_prices_etl(): 差分取得→保存のワークフロー（fetch_daily_quotes / save_daily_quotes を使用）、バックフィル機能をサポート

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- ニュース収集での複数の防御策を実装
  - defusedxml による安全な XML パース
  - SSRF 防止（スキーム検証、プライベートIP検出、リダイレクト時の検査）
  - レスポンスサイズおよび gzip 解凍後のサイズ検査（DoS／Bomb 対策）
  - URL 正規化とトラッキングパラメータ除去により一意性と冪等性を強化

### Performance
- J-Quants API 呼び出しでグローバルなレートリミットを導入（固定間隔スロットリング）
- DuckDB へのバルク挿入でチャンク処理を採用（news_collector の _INSERT_CHUNK_SIZE）
- INSERT ... RETURNING を活用して実際に新規挿入された件数を正確に取得

### Known issues / Notes
- strategy/, execution/, monitoring/ サブパッケージは初期プレースホルダとして空の __init__.py が配置されており、各レイヤの具象実装は今後追加予定です。
- pipeline.run_prices_etl の戻り値の扱いや pipeline モジュールの一部処理は将来的に継続実装・拡張される想定です（品質チェックモジュール quality との統合が参照されています）。
- DuckDB に依存する機能はローカルファイルパスや権限の違いで環境差が出る可能性があるため、運用環境では DUCKDB_PATH などの設定を確認してください。

---

その他、細かな設計方針（冪等性の重視、Look-ahead Bias の回避、テスト容易性のための id_token 注入等）も初版から反映しています。今後は戦略実装、実行エンジン、監視・アラート機能の追加・安定化、さらに品質チェックやユニット/統合テストの拡充を予定しています。