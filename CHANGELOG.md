# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを採用します。

全般:
- このリポジトリは Python パッケージ `kabusys` の初期公開リリースです（バージョン 0.1.0）。
- 主に日本株自動売買システム向けのデータ取得・保存・ETL・ニュース収集基盤を実装しています。
- DuckDB を中心としたローカルデータレイク設計と、J-Quants / RSS など外部データソースからの安全な取り込み機能を備えます。

Unreleased
---------
- なし

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージ基盤
  - パッケージエントリポイントを追加: kabusys.__init__ にて __version__ = "0.1.0"、モジュール公開 (data, strategy, execution, monitoring) を定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索（CWD非依存）。
  - .env 行のパースを細かく実装（export プレフィックス対応、クォート/エスケープ処理、インラインコメントの取り扱いなど）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスをサポート）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
  - OS 環境変数を保護するための override/protected 機構を備える。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本機能: 日足（OHLCV）、財務（四半期 BS/PL）、市場カレンダーの取得関数を実装。
  - レート制限制御: 固定間隔スロットリングによるリクエスト間隔維持（120 req/min を想定）。
  - 再試行ロジック: 指数バックオフ、最大 3 回のリトライ（408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
  - 認証トークン管理: リフレッシュトークンから id_token を取得する get_id_token、モジュールレベルでトークンキャッシュを保持しページネーション間で共有。
  - 401 時の自動トークンリフレッシュを 1 回試行して再試行する仕組み（無限再帰を防止）。
  - ページネーション対応（pagination_key）を実装。
  - DuckDB へ保存する save_* 関数群（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - ON CONFLICT DO UPDATE により冪等に保存。
    - レコード変換ユーティリティ（_to_float/_to_int）を提供し、不正値を安全にハンドリング。
    - PK 欠損行のスキップとログ出力。
  - ログ出力を整備（info/warning）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集（デフォルトソース: Yahoo Finance カテゴリニュース）と前処理を実装。
  - セキュリティ/堅牢性:
    - defusedxml を利用して XML Bomb 等に対処。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベート/IP 判定（DNS解決した全 A/AAAA を検査）、リダイレクト時にも検査を行うカスタムリダイレクトハンドラを実装。
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）。
  - URL 正規化: トラッキングパラメータ（utm_ 等）を除去、クエリをソート、フラグメント削除。
  - 記事ID: 正規化 URL の SHA-256 の先頭 32 文字で生成し冪等性を担保。
  - テキスト前処理: URL 除去・空白正規化を実装。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用、1 トランザクションで処理、新規挿入された記事 ID を返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを INSERT ... RETURNING により正確にカウント、チャンク・トランザクション処理。
  - 銘柄コード抽出: 4桁数字パターン（例: "7203"）を検出し、known_codes に含まれるもののみ返すユーティリティを提供。
  - run_news_collection: 複数 RSS ソースからの収集と DB 保存、銘柄紐付けの統合ジョブを実装（1ソース失敗しても他を継続）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataPlatform の三層（Raw / Processed / Feature）と実行関連テーブルを定義する DDL を実装:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの CHECK 制約や外部キーを定義しデータ整合性を担保。
  - 代表的なインデックスを作成（頻出クエリを想定）。
  - init_schema(db_path) によりディレクトリ自動作成 → テーブル/インデックスの作成を行い DuckDB 接続を返す（冪等）。
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない旨を明記）。

- ETL パイプライン基礎 (kabusys.data.pipeline)
  - ETLResult dataclass による実行結果集約（取得数、保存数、品質問題、エラーリスト等）。
  - テーブル存在チェック、最大日付取得ユーティリティ(_table_exists/_get_max_date) を実装。
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）。
  - 差分更新のための get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - run_prices_etl の差分取得ロジックを実装（最終取得日から backfill_days を考慮して date_from を決定、J-Quants から取得し保存）。（設計上、後続の品質チェックや追加ジョブを想定）

Security
- XML パースに defusedxml を使用して XML 関連の脆弱性を緩和。
- RSS フェッチにおける SSRF 対策を複数層で実施（スキーム検証、プライベートIP検査、リダイレクト時の再検証）。
- レスポンスサイズ制限や gzip 解凍後の検査でメモリ DoS を防止。

Documentation / Developer notes
- 各モジュールに詳細な docstring と設計原則を記載（レート制限、リトライ方針、冪等性設計など）。
- .env の雛形は .env.example を参照する想定。必須環境変数が未設定の場合は ValueError が発生する（Settings._require）。
- DuckDB 初期化は init_schema() を推奨。初回ロード時のデータ開始日はデフォルトで 2017-01-01 に設定（_MIN_DATA_DATE）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Migration / Usage notes
- リポジトリを導入したらまず init_schema(settings.duckdb_path) を呼び出して DuckDB スキーマを作成してください（":memory:" を指定してテスト可能）。
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を .env に設定してください。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- J-Quants API の利用にはレート制限と認証トークン管理の方式を遵守してください（本クライアントは 120 req/min を想定）。

今後の予定（例）
- pipeline の完全実装（品質チェックモジュール integration、calendar/backfill の自動スケジューリング）
- strategy / execution / monitoring モジュールの実装・統合テスト追加
- 単体テスト・CI の整備、型チェック（mypy）や静的解析ルールの導入

もし CHANGELOG に特記したい追加情報（著者・コントリビュータ、リリースノートの詳細化、日付の変更等）があれば教えてください。