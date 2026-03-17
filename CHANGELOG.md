# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期バージョンの内容をコードベースから推測してまとめています。

全般的なバージョン表記は semver 準拠です。  

## [Unreleased]

### Added
- 開発中の機能・設計ドキュメント準拠の実装（詳細は 0.1.0 に含まれる機能参照）。

### Notes
- 今後のリリースではテスト・ドキュメンテーション・エラーハンドリングの強化、CLI/サービス化の追加を予定。

---

## [0.1.0] - 2026-03-17

初回リリース — 「KabuSys」日本株自動売買システムの基礎機能を実装。

### Added
- パッケージ初期化
  - パッケージのバージョン管理用 __version__ を "0.1.0" に設定。
  - 公開モジュール: data, strategy, execution, monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートの検出: .git または pyproject.toml）。
  - .env のパースロジックを実装（export プレフィックス対応、シングル/ダブルクォート中のエスケープ、コメント処理）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得関数（_require）と Settings クラスを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須項目として扱う。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを提供。
    - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の値検証を実装。
    - is_live / is_paper / is_dev プロパティを追加。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - ベースURL と HTTP リクエストユーティリティを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を導入。
  - 冪等性・堅牢性を考慮したリトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）を実装。
  - 401 Unauthorized を検知した際のリフレッシュトークンによる自動トークン更新（1回のみ）をサポート。
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar() を実装（ページネーション対応）。
  - DuckDB への保存関数 save_daily_quotes(), save_financial_statements(), save_market_calendar() を実装し、ON CONFLICT を用いた冪等保存を実現。
  - レスポンス取得時の JSON デコードエラーやタイムアウトなどのエラーに対する適切な例外メッセージを実装。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を取得して raw_news テーブルへ保存する処理を実装。
  - セキュリティ/堅牢性のための対策を多数実装:
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト時の検査用ハンドラ (_SSRFBlockRedirectHandler)、ホストのプライベートアドレス判定（_is_private_host）。
    - レスポンスの最大読み取りバイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック。
    - トラッキングパラメータ (utm_*, fbclid 等) を削除する URL 正規化と記事 ID の SHA-256（先頭32文字）生成。
  - テキスト前処理（URL 除去・空白正規化）や RSS pubDate の UTC 正規化実装。
  - save_raw_news(), save_news_symbols(), _save_news_symbols_bulk() によるトランザクション単位でのチャンク挿入（INSERT ... RETURNING を利用）を実装。
  - extract_stock_codes() による本文からの銘柄コード抽出（4桁数字、known_codes フィルタ）。
  - run_news_collection() により複数ソースの収集を安全に実行（個々のソースは独立してエラーハンドリング）。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions をはじめとする生データテーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の整形済みテーブル。
  - features, ai_scores 等の特徴量テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の実行系テーブル。
  - 各種チェック制約・外部キー・インデックスを設定。
  - init_schema(db_path) による DB ファイル親ディレクトリ自動作成・DDL 実行機能を提供。get_connection() で既存 DB への接続を返す。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計原則（差分更新、backfill、品質チェック連携）に基づく基礎機能を実装。
  - ETLResult データクラスを実装し、実行結果（取得数、保存数、品質問題、エラー）を集約可能に。
  - DB 内の最終取得日を取得するヘルパー (get_last_price_date(), get_last_financial_date(), get_last_calendar_date()) を実装。
  - 営業日調整ヘルパー (_adjust_to_trading_day) を実装（market_calendar 参照、最大 30 日遡る）。
  - run_prices_etl() により差分取得ロジック（最終取得日からの backfill）と保存を実装（jquants_client 経由）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- XML パースに defusedxml を使用して外部攻撃（XML Bomb 等）への耐性を確保。
- RSS フェッチ時に SSRF を防止するためのスキームチェック、プライベートアドレス判定、リダイレクト検査を導入。
- HTTP レスポンスの読み取り上限を設けてメモリ DoS を回避。
- .env ロードは既存の OS 環境変数を保護する（上書き制御と protected set）。

### Performance / Reliability
- J-Quants API 用の固定間隔レートリミッタと指数バックオフ付きリトライ実装により、API レート制限遵守とリトライ安定化を実現。
- DuckDB へのバルク挿入はチャンク分割と 1 トランザクションまとめによるオーバーヘッド削減を実施。
- INSERT ... ON CONFLICT / DO UPDATE / DO NOTHING を積極的に利用し冪等性を担保。
- 頻出クエリ向けインデックスを作成。

### Documentation / Usage notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
  - KABU_API_PASSWORD（kabuステーション API パスワード）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知用）
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われる。テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Python の型ヒントに | を使用しているため Python 3.10 以降が想定依存関係。
- 依存ライブラリ（主なもの）:
  - duckdb
  - defusedxml

---

今後の課題（予定）
- strategy, execution, monitoring モジュールの実実装（現状はパッケージプレースホルダ）。
- 品質チェックモジュール（kabusys.data.quality）の実装と ETL パイプラインとの統合テスト。
- 単体テスト・統合テストの追加（HTTP クライアント / DB アクセスのモック化を含む）。
- 運用用 CLI またはデーモン化、監視・アラート機能の整備。