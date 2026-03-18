CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。
タグ/バージョン管理に合わせて更新してください。

Unreleased
----------

(現在なし)

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初回リリース: kabusys 0.1.0
  - パッケージ概要: 日本株自動売買システムの基礎ライブラリ（data / strategy / execution / monitoring を意図）。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を導入（読み込み順: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート判定: .git または pyproject.toml を基準に探索（__file__ 起点で探索、CWD 非依存）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
  - 環境設定ラッパ Settings を導入:
    - 必須値の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - DB パスの既定値（DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db）。
    - KABUSYS_ENV 値検証（development / paper_trading / live）。
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - ヘルパ: is_live / is_paper / is_dev。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - データ取得機能:
    - 日足（fetch_daily_quotes）
    - 財務（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - 認証: リフレッシュトークンからの ID トークン取得 (get_id_token)、モジュールレベルのトークンキャッシュ実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を厳守する RateLimiter（デフォルト間隔 60/120 秒）。
  - リトライ/耐障害:
    - 最大リトライ回数 3、指数バックオフ（base=2.0）。
    - リトライ対象: 408, 429, 5xx、およびネットワーク例外。
    - 429 の場合、Retry-After ヘッダを優先。
    - 401 受信時はトークンを自動リフレッシュして 1 回のみリトライ（allow_refresh により再帰防止）。
  - DuckDB への保存ユーティリティ（冪等性）:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存。
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE。
  - データ整形ユーティリティ: _to_float / _to_int（安全な変換、空値・不正値ハンドリング）。
  - ロギングによる取得件数・保存件数・警告の記録。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS 収集/保存ワークフロー:
    - fetch_rss: RSS フィード取得、XML パース、安全チェック、記事整形を実装。
    - save_raw_news: raw_news テーブルへチャンク INSERT + RETURNING で実際に挿入された記事 ID を取得。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への銘柄紐付け（チャンク挿入、ON CONFLICT DO NOTHING、トランザクション管理）。
    - run_news_collection: 複数ソースを順次収集し DB 保存・銘柄紐付けを実行（各ソースは独立してエラーハンドリング）。
  - セキュリティ/堅牢性:
    - defusedxml を使用して XML 関連脆弱性（XML bomb 等）に対処。
    - SSRF 対策:
      - _SSRFBlockRedirectHandler によるリダイレクト先の事前検証（スキーム/プライベートアドレス拒否）。
      - _is_private_host によるホスト/IP のプライベート判定（直接 IP 判定 + DNS 解決で A/AAAA をチェック）。
    - 許容スキームは http/https のみ。
    - レスポンス最大サイズ制限: MAX_RESPONSE_BYTES = 10 MB。超過時はスキップ。
    - gzip 解凍時のサイズ再チェック（Gzip bomb 対策）。
  - コンテンツ処理:
    - URL 正規化とトラッキングパラメータ除去（_normalize_url、utm_* 等のプレフィックス除去）。
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字で生成（_make_article_id）、冪等性確保。
    - テキスト前処理: URL 除去・空白正規化（preprocess_text）。
    - pubDate のパース（RFC 2822）と UTC 正規化（_parse_rss_datetime）。パース失敗時は警告して現在時刻で代替。
    - 銘柄コード抽出: 4桁数字パターン (\b\d{4}\b) を抽出し、known_codes フィルタで有効コードのみ返す（extract_stock_codes）。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加（DEFAULT_RSS_SOURCES）。
  - テスト容易性: _urlopen がモック可能。
- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema.md に基づくスキーマ実装（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック・PRIMARY KEY の定義（型安全・データ整合性強化）。
  - インデックスの作成（頻出クエリ向け）。
  - init_schema(db_path): DB ファイルの親ディレクトリ自動作成、全テーブルとインデックスを冪等に作成して接続を返す。
  - get_connection(db_path): 既存 DB への接続（スキーマ初期化は行わない）。
- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass による詳細な実行結果表現（取得件数/保存件数/品質問題/エラー等）。
  - 差分更新ヘルパ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date: 各 raw テーブルの最終日付取得。
    - 差分算出ロジック（最終取得日を基に backfill を考慮）。
  - 市場カレンダー関連:
    - _adjust_to_trading_day: 非営業日の場合に直近の営業日に調整（最大 30 日遡り、カレンダーがない場合はフォールバック）。
  - run_prices_etl (株価差分 ETL):
    - 差分更新・バックフィル（デフォルト backfill_days = 3）。
    - 最小データ開始日 _MIN_DATA_DATE = 2017-01-01。
    - J-Quants からの取得と jq.save_daily_quotes による冪等保存のフローを実装。
  - 設計方針:
    - 品質チェックは品質問題を検出しても ETL 自体は継続し、呼び出し元で判断可能にする（Fail-Fast ではない）。
    - id_token の注入可能性によりテスト容易性を確保。
  - 定数: 市場カレンダー先読み _CALENDAR_LOOKAHEAD_DAYS = 90。
- その他
  - パッケージルートの __init__ にバージョン (0.1.0) と __all__ を追加（"data", "strategy", "execution", "monitoring"）。
  - strategy / execution / data パッケージの初期化ファイルを追加（将来拡張用のプレースホルダ）。

Security
- ニュース収集周りに複数のセキュリティ対策を追加:
  - defusedxml による XML ハードニング。
  - SSRF 対策（スキーム検証、プライベートアドレス排除、リダイレクト検査）。
  - 外部からの巨大レスポンス・gzip 爆弾対策（最大バイト数制限と解凍後再チェック）。

Notes / Migration
- 初回利用時は init_schema(settings.duckdb_path) などで DuckDB スキーマを初期化してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  これらが未設定の場合、Settings の該当プロパティが ValueError を送出します。
- 自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector の既定 RSS は DEFAULT_RSS_SOURCES を参照します。追加ソースは run_news_collection の引数で渡せます。
- DuckDB のファイルパス既定は data/kabusys.duckdb（必要に応じて DUCKDB_PATH を設定）。

今後の予定（想定）
- pipeline における品質チェック (kabusys.data.quality) の実装統合とレポーティング強化。
- strategy / execution / monitoring 実装の追加（アルゴリズム、注文実行、監視通知等）。
- テストスイート・CI の整備、型注釈の完全化、ドキュメント整備。

References
- リポジトリ内の DataPlatform.md / DataSchema.md 等の設計ドキュメントに従って実装しています（該当ファイルが存在する場合）。