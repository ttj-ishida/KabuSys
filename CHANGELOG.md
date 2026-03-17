KEEP A CHANGELOG
すべての重要な変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

履歴:
- 変更は後方互換を壊す可能性がある場合に Breaking changes セクションで明示します。

Unreleased
- (なし)

0.1.0 - 2026-03-17
------------------
Added
- パッケージの初期リリース "KabuSys" を追加。
  - パッケージ宣言: kabusys.__version__ = 0.1.0、公開モジュール一覧 __all__ を定義。
- 環境変数 / 設定管理モジュールを追加 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数からの設定自動読み込み機能を実装。
  - プロジェクトルート検出 (_find_project_root): .git または pyproject.toml を基準に探索（CWD非依存）。
  - .env パーサーの強化: export 形式対応、シングル/ダブルクォートとエスケープ処理、インラインコメントの扱い、無効行スキップ等を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 実行環境などのプロパティを取得可能（必須項目未設定時は ValueError を送出）。
  - 有効な環境値チェック（KABUSYS_ENV, LOG_LEVEL）。
- J-Quants API クライアントを追加 (kabusys.data.jquants_client)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大3回、408/429/5xx に対する再試行。429 の Retry-After を考慮。
  - 401 受信時のリフレッシュ実装: リフレッシュトークンから id_token を取得し 1 回のみ自動再試行。
  - ページネーション対応：pagination_key を用いた累積取得。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存を行う。
  - 取得時刻 (fetched_at) を UTC で記録し look-ahead bias の追跡を可能に。
  - ヘルパー関数 _to_float / _to_int を実装し、型安全に変換を行う（不正値は None）。
- ニュース収集モジュールを追加 (kabusys.data.news_collector)
  - RSS フィード取得 → 前処理 → raw_news 保存 → 銘柄紐付け の ETL を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策（_is_private_host、リダイレクト時の検証、スキーム検査）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検証。
    - URL スキーム検証（http/https のみ許可）。
  - 記事IDは正規化した URL の SHA-256（先頭32文字）で一意化し冪等性を担保（utm_* 等のトラッキングパラメータ除去）。
  - テキスト前処理: URL 除去、空白正規化、先頭・末尾トリム。
  - DB 保存はチャンク化して 1 トランザクションで実行し、INSERT ... RETURNING により実際に挿入された件数を正確に取得する（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出機能（4桁数字）と既知銘柄セットによるフィルタリング（extract_stock_codes）。
  - fetch_rss は最終 URL の再検証や Content-Length チェックなど堅牢な取得処理を実装。
- DuckDB スキーマ定義モジュールを追加 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層にまたがるテーブル DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions、processed の prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等、多数のテーブルを定義。
  - features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など実行・分析用テーブルを定義。
  - インデックス（頻出クエリ向け）を作成。
  - init_schema(db_path) でディレクトリ自動作成および全テーブル/インデックスを作成する初期化処理を実装（冪等）。
  - get_connection(db_path) で既存 DB への接続を返却。
- ETL パイプラインモジュールを追加 (kabusys.data.pipeline)
  - 差分更新（差分取得・バックフィル）と保存（jquants_client の保存関数利用）を行う ETL ロジックを実装。
  - ETLResult データクラスを導入し、取得/保存件数・品質問題・エラーを集約。
  - 市場カレンダーを用いた営業日補正、テーブル最終日取得ユーティリティを提供。
  - run_prices_etl 等の個別 ETL ジョブの基礎を実装（差分計算・backfill のデフォルト値等）。
  - テスト容易性のため id_token の注入を可能にする設計。
- テスト/モックを想定した設計上の配慮
  - news_collector._urlopen をモック差し替え可能にするなど、ネットワーク依存箇所のテストフレンドリーな設計を採用。

Security
- RSS 収集・外部 URL の扱いに関して下記の防御を実装:
  - defusedxml を使用した安全な XML パース。
  - SSRF 対策: スキーム検査、プライベート IP/ループバック/リンクローカルの検出と拒否、リダイレクト先の検証。
  - レスポンスサイズ上限の導入（メモリDoSやGzip Bomb 対策）。
  - URL 正規化でトラッキングパラメータ除去（プライバシーと冪等性向上）。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で参照するため、実行前に設定が必要（未設定時は ValueError）。
- 自動 .env 読み込み:
  - プロジェクトルート (.git または pyproject.toml) を基準に .env / .env.local を自動ロードする。不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。
- DuckDB 初期化:
  - init_schema(db_path) を初回実行してスキーマを作成してください（ファイルパスの親ディレクトリは自動で作成されます）。
- 既知銘柄セット:
  - ニュースからの銘柄抽出を行う場合は known_codes を用意してください（extract_stock_codes に渡す）。

Breaking Changes
- (なし)

Fixed
- (なし)

Deprecated
- (なし)

以上

もし追加でリリースノートを英語で欲しい、あるいは各変更点に対する具体的な使用例（設定例、DB初期化サンプル、ETL 実行例）を追記したい場合は教えてください。