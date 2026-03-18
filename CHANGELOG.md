Keep a Changelog
=================

すべての注目に値する変更はこのファイルに記録します。  
このプロジェクトはセマンティック バージョニングに従います。詳細は <https://semver.org/> を参照してください。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージの初期リリースを追加。
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント処理に対応）。
  - 設定アクセスのラッパー Settings を導入。以下のプロパティを提供:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path（デフォルト data/kabusys.duckdb）, sqlite_path（デフォルト data/monitoring.db）
    - env（development/paper_trading/live の検証）, log_level（DEBUG..CRITICAL の検証）
    - is_live / is_paper / is_dev の利便性プロパティ
  - 必須環境変数未設定時は ValueError を送出して早期検出。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装:
    - レート制限 (120 req/min) を守る固定間隔スロットリング _RateLimiter を導入。
    - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
    - 401 発生時は自動でリフレッシュトークンから id_token を再取得して 1 回だけリトライ（無限再帰を防止）。
    - ページネーション対応（pagination_key）を利用して全データ取得。
    - JSON デコード失敗・HTTP エラー等の取り扱いを明確化。
  - データ取得関数を提供:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - データ永続化関数を提供（DuckDB 用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアス防止に配慮
    - INSERT ... ON CONFLICT DO UPDATE による冪等性確保
  - 型変換ユーティリティ _to_float / _to_int を実装（空値・不正値を安全に None に変換）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集と DuckDB への保存を実装。
  - セキュリティと堅牢性の考慮:
    - defusedxml を使った XML パース（XML-Bomb 等の攻撃対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキーム/ホスト検査、プライベートアドレス判定（IP と DNS 解決で判定）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding を明示。
  - 機能:
    - URL 正規化（ホスト/スキーム小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - テキスト前処理（URL 除去・空白正規化）。
    - fetch_rss: RSS 取得・パース・記事抽出ロジック。content:encoded を優先。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING を用いチャンク単位で一括挿入、新規挿入した記事IDのリストを返す。トランザクションでまとめて処理。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT で重複スキップ）、挿入数を正確に返す。
  - 銘柄コード抽出:
    - 4桁数字パターン (\b\d{4}\b) を検出し、known_codes に含まれるもののみを返す重複排除ロジック（extract_stock_codes）。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataSchema.md に基づく多層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラムの型・制約（CHECK, PRIMARY KEY, FOREIGN KEY）を明記してデータ整合性を強化。
  - 頻出クエリに対するインデックス定義を追加（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) でディレクトリ自動作成と全テーブル・インデックス生成を行い、DuckDB 接続を返す。get_connection() で既存 DB へ接続可能。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL 実行のための処理フロー実装の基礎を追加:
    - 差分更新（最終取得日からの差分取得）、backfill_days による過去再取得（デフォルト 3 日）で API の後出し修正を吸収。
    - 市場カレンダー先読み定数（_CALENDAR_LOOKAHEAD_DAYS = 90）。
    - ETLResult dataclass を導入して ETL 実行結果（取得数・保存数・品質問題・エラー）を一元管理。品質問題を辞書化してログ/監査に利用可能。
    - DB の最終取得日取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - run_prices_etl の雛形を実装（差分計算、fetch -> save の流れ）。（注: ファイル末尾に続きがある構成）

Changed
- 初版リリースのための内部設計注釈やドキュメント文字列を追加（DataPlatform.md / DataSchema.md 等に準拠した設計記述をコード内に含む）。

Fixed
- 初版リリース（該当なし／なし）。

Security
- news_collector で SSRF、XML パース攻撃、gzip/レスポンスサイズによる DoS 対策を盛り込む。
- .env 読み込みで OS 環境変数の上書きを保護する protected ロジックを導入。

Notes / Migration
- 初回は init_schema() でスキーマを初期化してください（既存テーブルはスキップされるため安全）。
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は Settings 経由で参照すると存在チェックされ、未設定時は ValueError が発生します。
- 自動 .env ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用に想定）。
- DuckDB ファイルのデフォルトパスは data/kabusys.duckdb。必要に応じて DUCKDB_PATH 環境変数で変更可能。

Acknowledgements
- 初期実装では外部ライブラリ（duckdb, defusedxml）を利用しています。運用環境での依存関係管理に注意してください。