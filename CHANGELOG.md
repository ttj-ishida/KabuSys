CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
----------

（現在なし）

0.1.0 - 2026-03-17
------------------

初回リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能を実装しました。

Added
- パッケージ初期化
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を追加。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を自動読み込み。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない自動ロードを実現。
  - .env パーサー（export KEY=val 形式に対応、引用符内のバックスラッシュエスケープ、インラインコメント処理などを考慮）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスで主要設定をプロパティとして公開（J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベルなど）。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装（_request）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライ制御（指数バックオフ、最大試行回数 3、対象ステータス: 408, 429, 5xx）。
    - 429 に対しては Retry-After ヘッダを優先。
    - 401 受信時はトークン自動リフレッシュを 1 回だけ行い再試行。
  - id_token の取得（get_id_token）とモジュールレベルのトークンキャッシュ。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - 取得時に fetched_at を記録する設計思想（look-ahead bias 防止）を採用。
  - DuckDB への保存用関数（冪等性を考慮した ON CONFLICT 処理）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 不正なレコード（PK 欠損）をスキップし警告ログを出力。
  - 型変換ユーティリティ: _to_float / _to_int（厳密な変換ルールを定義）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と記事保存の ETL 実装。
  - セキュリティ・堅牢性機能:
    - defusedxml を使った XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト先のスキーム検証とプライベートアドレス検出（_SSRFBlockRedirectHandler, _is_private_host）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
  - URL 正規化と記事 ID 生成:
    - _normalize_url によりトラッキングパラメータ（utm_ 等）を除去、クエリキーソート、フラグメント削除。
    - _make_article_id は正規化 URL の SHA-256 ハッシュ先頭32文字を記事IDとして使用（冪等性確保）。
  - テキスト前処理（URL 除去、空白正規化）と pubDate パース処理（UTC 正規化、失敗時フォールバック）。
  - fetch_rss: RSS の取得と記事リスト生成（content:encoded 優先、guid の URL 代替等）。
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用い、実際に挿入された記事 ID を返す（チャンク分割&1トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括挿入（ON CONFLICT で重複スキップ、INSERT RETURNING を利用）。
  - 銘柄抽出ユーティリティ:
    - extract_stock_codes: 4桁数字パターンから known_codes に含まれる銘柄のみ抽出（重複除去）。

- DuckDB スキーマ定義 & 初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層をカバーするテーブル DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義。
  - よく使われるクエリに対するインデックスを用意（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) でディレクトリ作成、DDL実行、接続を返す。get_connection は既存 DB への接続を返す。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETL 実行結果を表す ETLResult dataclass（取得数、保存数、品質問題リスト、エラーリスト等）。
  - テーブル存在チェックや最大日付取得のユーティリティ（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーを使った営業日調整(_adjust_to_trading_day)。
  - 差分更新の方針（最終取得日から backfill_days を遡って再取得）に基づく run_prices_etl の導入。fetch -> save のワークフローを想定。

Security
- defusedxml による XML パース、SSRF 防止用のリダイレクト検査、プライベートIP検出、URL スキーム制限、レスポンス/解凍後サイズ制限など、外部入力に対する複数層の防御を導入。

Notes / Known limitations
- pipeline.run_prices_etl をはじめとする ETL 処理群は差分更新ロジックや品質チェックとの統合を意図して実装されていますが、品質チェック（quality モジュール）との連携や一部の高レベルな運用ロジックは別モジュール側で実装される想定です。
- strategy, execution サブパッケージの __init__.py はプレースホルダとして存在。戦略実装・発注実装は今後追加予定です。
- 現時点では J-Quants / kabu API の呼び出しは urllib を使った同期実装です。必要に応じて非同期化や外部 HTTP ライブラリの導入を検討してください。

導入・移行メモ
- 初期化: DuckDB スキーマを作成するには init_schema(settings.duckdb_path) を呼び出してください。
- 環境変数: .env/.env.local の自動読み込みはデフォルトで有効です。テスト等で自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants 認証: 環境変数 JQUANTS_REFRESH_TOKEN が必須です（Settings.jquants_refresh_token）。

お問い合わせ
- 不明点や追加の変更履歴希望があれば教えてください。必要に応じて各モジュールごとに詳細なリリースノートを作成します。