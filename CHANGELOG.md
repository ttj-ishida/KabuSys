CHANGELOG
=========

すべての変更は Keep a Changelog 規約に準拠して記載します。
このファイルは日本語でまとめられています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初版リリース (kabusys v0.1.0)
  - パッケージルート: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - export KEY=val 形式、クォート・エスケープ、行内コメント等に対応する堅牢な .env パーサ実装。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数チェック機能 (_require) と Settings クラスを提供。
  - 主要設定プロパティ:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
  - 環境判定ヘルパー: is_live, is_paper, is_dev。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日次株価（OHLCV）, 財務データ（四半期 BS/PL）, JPX 市場カレンダー取得 API 実装。
  - レート制限遵守のための固定間隔スロットリング実装（120 req/min、_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx を再試行対象に。
  - 401 (Unauthorized) 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ。
  - ページネーション対応（pagination_key を利用し重複検知）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - 冪等性を確保するため ON CONFLICT DO UPDATE を使用。
    - fetched_at に取得時刻（UTC）を付与。
    - PK 欠損行のスキップとログ出力。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し不正値に耐性。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集して raw_news / news_symbols に保存する一連の処理を実装。
  - 設計上の安全対策・堅牢化:
    - defusedxml を利用した XML パース（XML Bomb 等の防御）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - gzip 圧縮の解凍に対応し、解凍後サイズも再チェック（Gzip bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、DNS 解決してプライベートアドレスを検出、リダイレクト先も検証するカスタム RedirectHandler。
    - トラッキングパラメータ（utm_* / fbclid / gclid 等）の除去とクエリソートによる URL 正規化。
    - 記事 ID は正規化 URL の SHA-256 先頭32文字を使用して冪等性を保証。
    - コンテンツ前処理: URL 除去・空白正規化。
  - DB 保存:
    - raw_news へのチャンク INSERT（ON CONFLICT DO NOTHING）および INSERT ... RETURNING を使って実際に挿入された ID を返す。
    - news_symbols への紐付けはチャンク処理および INSERT ... RETURNING で実際に挿入された数を返す。
    - トランザクションでまとめ、失敗時はロールバックし例外を再送出。
  - 銘柄コード抽出 (extract_stock_codes): 4桁数字を正規表現で抽出し、known_codes セットでフィルタ（重複除去）。

- DuckDB スキーマ定義 & 初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層＋実行レイヤーのテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）および頻出クエリのためのインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成 → テーブル・インデックス作成（冪等）。
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新に基づく ETL ワークフローの下地を実装:
    - DB の最終取得日を基に差分(date_from / date_to)を自動算出（_MIN_DATA_DATE, backfill に対応）。
    - 市場カレンダーの先読み日数設定とバックフィルロジック（デフォルト backfill_days=3）。
    - 品質チェックモジュールとの連携用フック（quality モジュールを想定した QualityIssue 集約）。
  - ユーティリティ:
    - テーブル存在確認、最大日付取得、取引日への調整等のヘルパー関数。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - 個別ジョブ: run_prices_etl の雛形（fetch -> save の一連処理）を実装。

Changed
- （初版につき該当なし）

Fixed
- （初版につき該当なし）

Security
- RSS パーサで defusedxml を利用、SSRF 対策（スキーム検証・ホスト/IP チェック・リダイレクト検査）、レスポンスサイズ制限、gzip 解凍後のサイズチェックを導入。

Notes / Migration / 使用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。settings プロパティ経由で _require によりチェックされます。
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）から .env を自動読み込みします。
  - テストなどで自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB 初期化:
  - 初回は schema.init_schema(path) を呼び出して DuckDB ファイル・テーブルを作成してください（":memory:" も使用可）。
  - 既存 DB に接続する場合は schema.get_connection(path) を使用し、初期化は行わないでください。
- J-Quants API 注意点:
  - API レートやリトライ挙動は jquants_client にて制御されますが、外部のレート制限変更等に注意してください。
  - fetch 系関数はページネーションを内部で処理します。
- ニュース収集:
  - fetch_rss は不正なフィードや大容量レスポンスをスキップして空リストを返す設計のため、呼び出し元でログやリトライを検討してください。
  - extract_stock_codes の有効性は渡す known_codes セットに依存します。known_codes を与えない場合は紐付け処理をスキップします。

Breaking Changes
- 初版につき破壊的変更はありません。

Contributors
- 初回実装（リポジトリ内のコードベースに基づく自動作成ドキュメント）

----- 

注: 本 CHANGELOG は与えられたコード内容から推測して作成しています。実際のリリースノートに利用する際は、リポジトリのコミット履歴やリリース方針に合わせて適宜調整してください。