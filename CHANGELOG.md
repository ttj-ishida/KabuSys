CHANGELOG
=========

すべての変更は「Keep a Changelog」仕様に従って記載しています。
このプロジェクトの初期バージョンを記録しています。

v0.1.0 - 2026-03-17
-------------------

Added
- パッケージ初期リリース。
  - パッケージメタ情報:
    - kabusys.__version__ = "0.1.0"
    - 公開モジュール: data, strategy, execution, monitoring（strategy / execution はプレースホルダ）
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定（CWD 非依存）。
  - .env パーサを実装（export 形式、クォート内のエスケープ、インラインコメント処理などの対応）。
  - 環境変数取得のユーティリティ _require と Settings クラスを追加。
    - 代表的な設定キー:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV (development/paper_trading/live の検証)
      - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL の検証)
    - Settings による is_live / is_paper / is_dev プロパティを提供。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ _request を実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（最大3回、指数バックオフ、HTTP 408/429/5xx に対応）。
    - 429 の場合は Retry-After ヘッダ優先。
    - 401 発生時は自動で ID トークンを 1 回リフレッシュして再試行（再帰防止）。
    - ページネーション対応。
    - JSON デコード失敗時の明確なエラーメッセージ。
  - 認証ヘルパー get_id_token を実装（リフレッシュトークン→IDトークン）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX 取引カレンダー）
    - 取得ログ（取得件数）を出力。
  - DuckDB 保存関数（冪等/ON CONFLICT を使用）:
    - save_daily_quotes → raw_prices（date, code を PK に ON CONFLICT DO UPDATE）
    - save_financial_statements → raw_financials（code, report_date, period_type を PK に ON CONFLICT DO UPDATE）
    - save_market_calendar → market_calendar（date を PK に ON CONFLICT DO UPDATE）
    - 各保存関数は PK 欠損行をスキップし、スキップ数をログ出力。
  - 型変換ユーティリティ _to_float / _to_int を実装（堅牢な空値・フォーマット処理）。
  - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news / news_symbols に保存する一連処理を実装。
  - セキュリティ・堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リダイレクト先のスキーム検査およびプライベートIP/ループバック/リンクローカルの拒否（事前検証 + リダイレクトハンドラ）。
    - リクエスト受信サイズ上限 (MAX_RESPONSE_BYTES = 10MB) と Gzip 解凍後のサイズ検査（メモリDoS対策）。
    - URL のスキーム検査で http/https 以外を拒否。
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ（utm_* 等）を除去し、クエリキーでソート、フラグメント除去。
    - 正規化 URL の SHA-256（先頭32文字）を記事IDとして採用 → 冪等性確保。
  - テキスト前処理: URL 除去、連続空白の正規化、トリムを行う preprocess_text。
  - RSS パースは content:encoded を優先し、description を代替。
  - 銘柄コード抽出: 正規表現 \b(\d{4})\b を用い、known_codes との照合で有効コードのみ抽出（重複排除）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDのリストを返す。チャンク単位（デフォルト 1000 件）でトランザクション内挿入。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への一括挿入、ON CONFLICT DO NOTHING RETURNING を使って挿入数を返す。トランザクションで整合性保証。
  - run_news_collection: 複数ソースを順次処理し、各ソースは独立してエラーハンドリング（1ソース失敗でも他は継続）。新規保存件数をソース毎に集計して返す。
- DuckDB スキーマ定義 & 初期化 (kabusys.data.schema)
  - DataSchema に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・CHECK 制約・PRIMARY KEY・外部キーを設定。
  - 頻出クエリ用にインデックス群を作成。
  - init_schema(db_path) を実装:
    - 親ディレクトリが無ければ自動作成。
    - 全 DDL / インデックスを実行して初期化（冪等）。
  - get_connection(db_path) を提供（初期化は行わない）。
- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass を実装（取得件数、保存件数、品質問題一覧、エラー一覧などを保持）。
    - to_dict により品質問題を辞書化して出力可能。
    - has_errors / has_quality_errors プロパティを提供。
  - テーブル存在チェック、最大日付取得のユーティリティ (_table_exists, _get_max_date) を実装。
  - 市場カレンダーを利用した取引日の調整ヘルパー _adjust_to_trading_day を実装（非営業日の場合は直近営業日に調整）。
  - 差分更新用ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を追加。
  - run_prices_etl を実装（差分取得・バックフィルのロジック入り）:
    - date_from 未指定時に DB の最終取得日から backfill_days（デフォルト 3 日）前を開始日とする。初回ロード時は _MIN_DATA_DATE（2017-01-01）から取得。
    - fetch_daily_quotes → save_daily_quotes の流れで差分更新を行う。
  - 品質チェックモジュール（quality）との統合ポイントを用意（品質問題は収集して ETLResult に格納、Fail-Fast ではない設計）。

Security
- セキュリティ対策を重視して実装:
  - RSS の XML パースに defusedxml を使用。
  - SSRF 対策のためリダイレクト時および最終 URL のスキーム / ホスト検査を実施。
  - レスポンスサイズ制限、Gzip 解凍後の検査で Gzip-Bomb やメモリ DoS を軽減。
  - 環境変数の読み込みでは OS 環境変数を保護する protected 機能を提供（.env による意図しない上書きを防止）。

Notes / Known limitations
- strategy/execution パッケージは空の初期プレースホルダとなっており、実際の取引ロジックやオーダー送信実装は未提供。
- quality モジュールは pipeline から呼び出される想定（パイプライン内で品質チェックを行う設計）。品質チェックの具体実装はこのスナップショットでは含まれていない可能性あり。
- pipeline.run_prices_etl のファイル末尾が現在のコードスナップショットで途中（トランケート）になっているため、パイプラインの最終的な結果集約やエラー処理の全ての詳細は実装の続きが必要。

Compatibility / Breaking Changes
- 初期リリースのため互換性の過去バージョンとの互換性考慮は不要。

Acknowledgements
- 初期実装は API クライアント、ニュース収集、安全対策、DuckDB スキーマ、ETL 基盤を中心に構築しました。今後は戦略ロジック・実際の注文実行・監視周りを追加する予定です。