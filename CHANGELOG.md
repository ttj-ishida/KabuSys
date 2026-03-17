CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。
リリース日はファイル作成時点の暫定日付です。

[Unreleased]
-------------

- 初期リリースに向けた開発中の変更履歴はここに記載します。

0.1.0 - 2026-03-17
------------------

Added
- 基本パッケージ
  - パッケージ初期化: kabusys.__version__ = "0.1.0"、公開APIとして data/strategy/execution/monitoring を設定。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml を基準に探索するため、カレントワーキングディレクトリに依存しない自動読み込みをサポート。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサーの強化:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、行中および行末コメント処理に対応。
  - Settings クラスを提供し、J-Quants, kabuステーション, Slack, DBパス等の設定プロパティを安全に取得可能。
    - 必須変数未設定時は ValueError を送出。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）。
    - デフォルト DB パス（duckdb/sqlite）を提供。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装:
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
    - リトライ処理（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンで id_token を自動再取得して1回リトライ。
    - ページネーション対応（pagination_key を使用）で全件取得。
    - JSON デコード失敗時の明示的なエラー。
    - モジュールレベルで id_token をキャッシュしてページネーション間で共有。
  - データ取得関数:
    - fetch_daily_quotes（株価日足: OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB 保存関数（冪等性を担保）:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存。
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE で保存。
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE で保存。
  - ユーティリティ: _to_float / _to_int（堅牢な型変換。例: "1.0" → int などの合理的判定）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS 収集と前処理の実装:
    - RSS 取得 (fetch_rss): HTTP(S) のみ許可、User-Agent と gzip 受け入れ、Content-Length/サイズ上限チェック（10MB）、gzip 解凍後のサイズ検証。
    - XML パースに defusedxml を使用して XML ボム等への対策。
    - リダイレクト時の SSRF 防止ハンドラ (_SSRFBlockRedirectHandler) を導入し、リダイレクト先のスキームとプライベートIP判定を実施。
    - URL 正規化 (_normalize_url): トラッキングパラメータ除去、キーソート、フラグメント削除、スキーム/ホスト小文字化。
    - 記事ID 生成 (_make_article_id): 正規化 URL の SHA-256 先頭32文字を使用し冪等性を確保。
    - テキスト前処理 (preprocess_text): URL 除去と空白正規化。
    - 銘柄コード抽出 (extract_stock_codes): 4桁数字パターンと known_codes に基づくフィルタリング。
  - DB 保存:
    - save_raw_news: raw_news へチャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id、1トランザクションでコミット。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への一括挿入（重複除去、トランザクション、RETURNING を使用して実際に挿入された件数を返す）。
  - 統合ジョブ run_news_collection を実装:
    - 複数 RSS ソースを順次処理。各ソースは独立してエラーハンドリング（1ソース失敗でも他ソースは継続）。
    - 新規挿入記事に対して銘柄紐付けを一括で作成。

- DuckDB スキーマ (kabusys.data.schema)
  - DataPlatform 設計に基づいた多層スキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 生データテーブル: raw_prices, raw_financials, raw_news, raw_executions。
  - 整形済みテーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - 特徴量/AI層: features, ai_scores。
  - 発注/実行層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - インデックス群: 頻出クエリに基づくインデックスを作成。
  - init_schema(db_path): DB ファイルの親ディレクトリ自動作成、全DDLとインデックスを適用する初期化関数。
  - get_connection(db_path): 既存 DB への接続を返すヘルパー。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー等を格納）。
  - テーブル存在チェック・最大日付取得のユーティリティ。
  - 市場カレンダーに基づく営業日補正ヘルパー (_adjust_to_trading_day)。
  - 差分更新ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - run_prices_etl: 差分更新のロジックを実装（最終取得日に基づく date_from の自動算出、backfill オプション、J-Quants からの取得と保存呼び出し）。

Security
- 複数のセキュリティ対策を導入:
  - defusedxml による XML 安全パース。
  - SSRF 対策: URL スキーム検証、リダイレクト先のプライベートIP検査、DNS 解決時の IP チェック。
  - HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策。
  - クエリパラメータのトラッキング除去による記事IDの安定化。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Notes / Known limitations
- run_prices_etl 等パイプラインは基本的な差分取得ロジックを実装済みだが、本番運用での追加検証（例: 品質チェックモジュールの統合、スケジューリングや並列取得の最適化）は必要。
- strategy や execution パッケージは初期スケルトンで、各戦略や注文処理ロジックは今後の実装対象。

License
- 明示的な記載がソース内にはありません。公開時は適切なライセンスファイルを追加してください。

---- 

（この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のコミット履歴やリリース計画に合わせて調整してください。）