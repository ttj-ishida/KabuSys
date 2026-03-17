# Changelog

すべての注目すべき変更は本ファイルに記録します。本ファイルは「Keep a Changelog」のフォーマットに準拠しています。  
フォーマットの慣例に従い、各リリースに対して「Added / Changed / Fixed / Security / ...」などのカテゴリ別に記載しています。

※この CHANGELOG はリポジトリ内のコードから推測して作成した初回リリース注記です。

## [Unreleased]
- 当面の開発予定・既知の未実装点や改善点をここに記載します（例：ETL の追加検証、テストカバレッジの強化など）。
- run_prices_etl の戻り値処理など、若干の未完（コード断片の切断）と思われる箇所は修正対象。

---

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。以下はコードベースから推測される主要な追加点と設計上の注意点です。

### Added
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__、バージョン 0.1.0）。
  - モジュール構成（data, strategy, execution, monitoring のエントリポイント）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - 自動ロードの探索ロジックは __file__ を起点にプロジェクトルート（.git または pyproject.toml）を検出。
  - .env と .env.local の優先度制御（OS環境変数を保護する protected ロジックを実装）。
  - 行パースは export 形式、クォート、インラインコメントなどに丁寧に対応。
  - 必須変数チェック（_require）と Settings クラスを公開（settings インスタンス）。
  - 主要設定プロパティ（例: jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live/is_paper/is_dev）。
  - 自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV: fetch_daily_quotes）、財務データ（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）を取得するクライアント実装（ページネーション対応）。
  - リクエスト共通処理での:
    - 固定間隔レート制御（120 req/min を満たす _RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx に対するリトライ）。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）と id_token キャッシュ共有機構。
    - JSON デコード失敗時の明示的エラー。
  - DuckDB への冪等保存用ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar（いずれも ON CONFLICT / DO UPDATE による重複排除）。
  - 型安全な変換ユーティリティ（_to_float, _to_int）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を取得し、前処理・正規化・DuckDB 保存を行う実装。
  - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭32文字を採用（utm_* 等トラッキング除去後に正規化）。
  - XML パーサは defusedxml を利用し XML Bomb 対策。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストであればブロック（_is_private_host）。
    - リダイレクト時にもスキーム・ホスト検証を行うカスタム RedirectHandler を使用。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使い、実際に挿入された記事IDを返す（チャンク & トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンクで挿入し、実際に挿入された件数を返す。
  - 銘柄抽出ロジック: 4桁数字パターンを検出し、known_codes に含まれるコードのみ採用（重複除去）。

- スキーマ定義（kabusys.data.schema）
  - DuckDB のスキーマを DataPlatform.md に準拠して定義（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, FOREIGN KEY, CHECK）および実務で想定されるデータ制約を設定。
  - インデックス定義（頻出クエリに対する補助インデックス）。
  - init_schema(db_path) によりファイルパスの親ディレクトリ自動作成とテーブル／インデックス作成を行う（冪等）。
  - get_connection(db_path) で既存 DB へ接続可能（スキーマ初期化は行わない旨を明記）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計方針と差分更新処理を実装（差分取得、backfill、品質チェックのフック）。
  - ETLResult dataclass を導入し ETL 実行結果（取得件数、保存件数、品質問題、エラー等）を構造化。
  - DB 上の最終取得日取得ユーティリティ（get_last_price_date など）。
  - 市場カレンダーを用いた営業日調整ロジック（_adjust_to_trading_day）。
  - run_prices_etl 実装（差分算出、backfill_days: デフォルト 3 日、jquants_client の fetch/save を呼び出し）。※ファイル切断により戻り値の完全な実装箇所が切れている可能性あり（下記 Known issues 参照）。

### Security
- RSS/XML 処理における複数の安全対策を実装:
  - defusedxml による XML の安全パース。
  - SSRF 対策（スキームチェック、プライベートIPチェック、リダイレクトハンドリング）。
  - レスポンスサイズ上限と gzip 解凍後の再チェック（DoS 対策）。
- jquants_client の HTTP 重試時に 401 を検出して自動トークン更新を行うが、allow_refresh=False の場面では無限再帰を防止。

### Performance / Reliability
- API レート制御（_RateLimiter）で J-Quants のレート制限を厳守。
- 再試行（指数バックオフ）と Retry-After ヘッダの尊重（429 の場合）。
- DuckDB へはバルク挿入・チャンク処理・トランザクションで書き込みのオーバーヘッドを抑制。
- raw_news / news_symbols の挿入において INSERT ... RETURNING を利用して実挿入数を正確に把握。

### Documentation
- 各モジュールに docstring と設計方針・仕様が詳細に記載されているため、実装意図が追いやすくなっている。
- 設定キーと既定値（duckdb path, sqlite path, KABUSYS_ENV の有効値等）が Settings クラスに明示されている。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Known issues / Notes
- run_prices_etl 関数の末尾がソース断片で切れているように見えるため、戻り値の最終処理（prices_saved の返却等）や例外ハンドリングの最終整備が必要に見えます。実運用前に該当箇所の完全な実装と単体テストを推奨します。
- news_collector は外部ネットワークに依存するため、テスト時は _urlopen などをモックする想定（コード内にその旨の注記あり）。
- 環境変数の自動ロードはプロジェクトルートの検出に依存するため、配布形態やインストール後の実行環境で .env 自動読み込みが期待通り動作するか確認が必要。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

### Upgrade / Migration notes
- 初回リリースのためアップグレード無し。初回導入時は以下を確認してください:
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DB 初期化: kabusys.data.schema.init_schema(settings.duckdb_path) を呼び出してスキーマを作成。
  - ログレベル・環境: KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか。LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれか。

---

（以降のリリースやバグ修正は本ファイルに順次追記してください）