# CHANGELOG

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。  
安定版リリース毎にエントリを追加してください。

## [Unreleased]

## [0.1.0] - 2026-03-17

初回公開リリース — 日本株自動売買システム「KabuSys」ベース実装。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。サブパッケージとして data, strategy, execution, monitoring を公開。
  - バージョン: 0.1.0

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダー実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を探索、CWDに依存しない）。
  - .env と .env.local の読み込み優先順位を実装（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - export KEY=val 形式やシングル／ダブルクォートを含む行のパースに対応。行内コメント処理、クォート内のバックスラッシュエスケープを考慮。
  - Settings クラスを提供し、主要な環境変数アクセスをラッパー化：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: ローカル）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL の検証

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - データ取得機能を追加:
    - fetch_daily_quotes（株価日足 - OHLCV、ページネーション対応）
    - fetch_financial_statements（財務データ - 四半期 BS/PL、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - 認証補助:
    - get_id_token（リフレッシュトークンから idToken を取得）
    - モジュールレベルの id_token キャッシュを導入（ページネーション間で共有）
  - ネットワーク制御:
    - 固定間隔レートリミッタ（120 req/min）を実装
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
    - 401 受信時は自動で id_token を 1 回リフレッシュして再試行
  - DuckDB 保存用ユーティリティ（冪等性重視）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE により重複を排除して更新
  - 値変換ヘルパー: _to_float, _to_int（空値/不正値耐性）

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集・前処理・保存パイプラインを実装
    - fetch_rss: RSS 取得、XML パース（defusedxml 使用）、gzip 解凍、サイズ上限チェック（10 MB）
    - preprocess_text: URL 除去・空白正規化
    - URL 正規化と記事 ID 生成（_normalize_url / _make_article_id: SHA-256 の先頭32文字）
    - SSRF 対策: スキーム検証 (http/https 限定)、リダイレクト先ホストのプライベートアドレス検査、リダイレクトハンドラを使った事前検証
    - save_raw_news: DuckDB へチャンクINSERT（INSERT ... RETURNING id を使用）を行い、実際に挿入された記事IDを返却
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクで保存（INSERT ... RETURNING を使用）
    - extract_stock_codes: テキスト中の4桁数字を抽出し known_codes と照合（重複除去）
  - デフォルトソースに YahooFinance のビジネス RSS を追加（DEFAULT_RSS_SOURCES）

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataPlatform.md に基づく多層スキーマを導入（Raw / Processed / Feature / Execution）
  - 主なテーブルを定義（冪等 CREATE TABLE IF NOT EXISTS）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリ向けのインデックスを作成
  - init_schema(db_path) でディレクトリ作成→テーブル・インデックス作成を行い接続を返す
  - get_connection(db_path) で既存 DB 接続を返す（スキーマ初期化は行わない）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL の共通ロジック・ヘルパーを実装
    - ETLResult データクラス（品質チェック・エラー情報を含む）
    - テーブル存在チェック、最大日付取得ユーティリティ
    - _adjust_to_trading_day: 非営業日の調整（market_calendar に基づく）
    - 差分更新向けヘルパー（get_last_price_date 等）
    - run_prices_etl の枠組み（差分計算、backfill_days の取り扱い、jquants_client の fetch/save 呼び出し）
  - 設計方針をドキュメント内に明記（差分更新、backfill、品質チェックの扱い、テスト向け id_token 注入）

### Changed
- （初版のため過去からの変更は無し）

### Fixed
- （初版のため過去からの修正は無し）

### Security
- ニュース取得で defusedxml を採用し XML Bomb 等の脅威を軽減
- RSS フェッチで SSRF 対策を導入（スキーム制限、リダイレクト先のプライベートIP拒否、Content-Length/レスポンスサイズ制限）
- .env 読み込みで OS 環境変数を保護する protected 機構を導入

### Notes / Known issues / TODO
- run_prices_etl の実装終端に不完全な return が見受けられます（ソースの末尾が "return len(records)," のように途中で終了しているため、保存件数を返す箇所が未完成の可能性があります）。ETL 呼び出し元から期待される戻り値（fetched, saved）の整合性を確認のうえ修正してください。
- strategy/ execution / monitoring サブパッケージは公開された名前空間があるものの本リポジトリ内では空の初期化（プレースホルダ）に留まっています。戦略ロジック、発注実行ロジック、監視機能の実装は今後の作業。
- NewsCollector の URL 正規化やトラッキングパラメータ削除は既知のプレフィックスのみを除去します。特殊なケースは追加ルールの検討が必要です。
- DuckDB の SQL 文は一部 SQL インジェクション対策に注意（現在はプレースホルダを使っているが、DDL の動的組み立て箇所は注意が必要）。

### Migration / Upgrade notes
- 初回起動時は必ず schema.init_schema(db_path) を呼び出して DuckDB のテーブルを作成してください（get_connection() はスキーマ初期化を行いません）。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用リフレッシュトークン）
  - KABU_API_PASSWORD（kabuステーション API 用パスワード）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知用）
- 任意・デフォルト:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
- テスト実行や CI で自動 .env 読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### Developer notes
- ネットワーク I/O を含む関数はテストのために差し替え可能（例: news_collector._urlopen をモックする設計）。
- jquants_client のレートリミッタと id_token キャッシュはモジュールレベルで動作しているため、並列実行やプロセス分散時は挙動の確認が必要。
- 依存ライブラリ:
  - duckdb
  - defusedxml
  - （標準ライブラリ: urllib, gzip, hashlib, ipaddress, socket, logging 等）

---

今後のリリースでは戦略ロジック、発注実行（kabu API との連携）、監視アラート、品質チェックモジュールの追加、テストカバレッジ拡充を予定しています。