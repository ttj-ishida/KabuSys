# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  
現在のバージョンはパッケージの __version__ に合わせて 0.1.0 です。

注意: 以下は提供されたソースコードから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システムの基礎モジュールを実装。

### Added
- パッケージ骨格
  - パッケージルート: kabusys（__version__ = 0.1.0）
  - サブパッケージ公開: data, strategy, execution, monitoring（空 __init__ を配置）

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）
  - .env/.env.local の読み込み順序と上書き制御（OS 環境変数保護）
  - 行パースで export 構文やクォート、インラインコメントを適切に処理するパーサを実装
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須設定を取得する _require()（未設定時は ValueError）
  - Settings クラス（プロパティ経由で以下の設定を取得）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev の補助プロパティ

- J-Quants API クライアント（kabusys.data.jquants_client）
  - daily quotes（OHLCV）、financial statements（四半期 BS/PL）、market calendar の取得機能を実装
  - レート制御: 固定間隔スロットリング（120 req/min）
  - 再試行ロジック: 指数バックオフ、最大3回（408, 429, 5xx をリトライ対象）
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの id_token キャッシュ
  - ページネーション対応（pagination_key の取り扱い）
  - DuckDB への冪等保存関数:
    - save_daily_quotes (raw_prices に INSERT ... ON CONFLICT DO UPDATE)
    - save_financial_statements (raw_financials に INSERT ... ON CONFLICT DO UPDATE)
    - save_market_calendar (market_calendar に INSERT ... ON CONFLICT DO UPDATE)
  - データ変換ユーティリティ (_to_float, _to_int)
  - get_id_token()（リフレッシュトークンから id_token を取得）
  - 詳細なログ出力（取得件数、警告等）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得と記事の正規化・保存処理を実装
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録
  - セキュリティ指向の設計:
    - defusedxml を利用した XML パース（XML Bomb 等への対策）
    - SSRF 対策: URL スキーム検証（http/https のみ）、プライベートIP/ループバック/リンクローカル/マルチキャストの判定と拒否、リダイレクト先の検査（カスタム RedirectHandler）
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）
    - User-Agent ヘッダー、Accept-Encoding による gzip 対応
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）
  - 記事IDは正規化 URL の SHA-256 の先頭32文字で生成（冪等性確保）
  - テキスト前処理（URL 除去、空白正規化）
  - RSS 解析: title, content:encoded の優先利用、pubDate のパースと UTC 変換（失敗時は代替）
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id（チャンク挿入、トランザクション内）
    - save_news_symbols: 記事と銘柄コードの紐付けを INSERT ... RETURNING で実施
    - _save_news_symbols_bulk: 複数記事分の紐付けをチャンク処理で一括保存
  - 銘柄コード抽出ロジック（4桁数値候補、known_codes によるフィルタ、重複排除）
  - run_news_collection: 複数ソースの統合収集ジョブ（各ソースの個別エラーハンドリング、既存記事はスキップ、記事→銘柄紐付けの一括処理）
  - テスト容易性: _urlopen をモック差し替え可能

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層に分けたテーブル群を定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な型チェック、PRIMARY KEY、FOREIGN KEY、CHECK 制約を付与
  - インデックス定義（頻出クエリを想定）
  - init_schema(db_path): 親ディレクトリ自動作成、全DDLとインデックスを作成して DuckDB 接続を返す（冪等）
  - get_connection(db_path): 既存 DB への接続（初期化は行わない）

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラス（ETL 実行結果と品質問題・エラーを保持）
  - 差分更新ユーティリティ: テーブル存在チェック、最大日付取得ヘルパー
  - 市場カレンダーの営業日調整 (_adjust_to_trading_day)
  - 差分更新のための最終日取得関数:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
  - run_prices_etl（差分 ETL の開始。差分算出、backfill の実装（デフォルト backfill_days=3）、J-Quants からの取得 → 保存の流れを実装）
  - 設計方針として品質チェックモジュール（quality）との連携を想定（品質異常があっても ETL 継続）

### Changed
- （初回リリースのため過去変更なし）

### Fixed
- （初回リリースのため過去修正なし）

### Security
- RSS パーサ/フェッチで複数の安全対策を導入:
  - defusedxml による XML パース
  - SSRF 防止（スキーム検証、プライベートホスト拒否、リダイレクト検査）
  - レスポンスのバイト数上限と gzip 解凍後のチェック

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings プロパティ経由で必須となる（未設定時は ValueError を投げる）
- 自動 .env 読み込み:
  - プロジェクトルートが .git または pyproject.toml のいずれかを含むディレクトリとして自動検出されます
  - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- DuckDB の初期化:
  - init_schema(db_path) を初回実行してデータベースを作成してください（":memory:" を指定するとインメモリ）
  - デフォルトの DuckDB ファイルパスは data/kabusys.duckdb
- テストのしやすさ:
  - news_collector._urlopen や jquants_client の id_token 注入など、モック差し替えポイントを用意

### Known limitations / TODO（コードから推測）
- pipeline.run_prices_etl の末尾が途中で切れているため、完全な ETL フロー（品質チェックの実行・ETLResult への格納・他ジョブの統合）は実装や補完が必要と思われる
- strategy / execution / monitoring パッケージは現状空の __init__ のみで、戦略実行部分および実際の発注実装は未実装
- quality モジュールの存在が参照されているが、本コード内に定義は含まれていない（別途実装が必要）

---

[0.1.0]: https://example.com/releases/0.1.0 (初回リリース - 仮リンク)