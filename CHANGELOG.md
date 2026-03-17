CHANGELOG
=========

すべての注目すべき変更点をここに記録します。  
このプロジェクトはセマンティックバージョニングに従います。詳細は Keep a Changelog の形式に準拠しています。

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ基盤
  - パッケージ初期化を追加。kabusys.__init__ に __version__ = "0.1.0" と公開モジュール一覧 (__all__) を定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを追加。読み込み順は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を探索）。パッケージ配布後も CWD に依存せず動作。
  - .env パーサーを実装:
    - コメント、空行、export 形式に対応。
    - クォート文字やバックスラッシュエスケープを考慮した値解析。
    - インラインコメントの取り扱い（クォート有無での振る舞い違い）に対応。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト時に便利）。
  - 必須環境変数取得用の _require() を実装し、未設定時は明示的な ValueError を送出。
  - Settings クラスを実装し、以下の設定プロパティを提供:
    - J-Quants / kabuステーション / Slack 用の必須トークン類（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - DB パス（DUCKDB_PATH, SQLITE_PATH）
    - 実行環境 KABUSYS_ENV（development, paper_trading, live の検証）
    - ログレベル LOG_LEVEL の検証
    - is_live/is_paper/is_dev の判定ヘルパー

- J-Quants API クライアント (kabusys.data.jquants_client)
  - ベース実装を追加：
    - API ベース URL、レートリミット（120 req/min）、最小インターバル制御（固定間隔スロットリング）を実装した RateLimiter。
    - リトライロジック（最大 3 回、指数バックオフ、HTTP 408/429/5xx をリトライ対象）。
    - 401 受信時にリフレッシュトークンから id_token を再取得して 1 回リトライする自動トークンリフレッシュ機構。
    - ページネーション対応の取得関数:
      - fetch_daily_quotes (OHLCV 日足)
      - fetch_financial_statements (四半期 BS/PL)
      - fetch_market_calendar (JPX マーケットカレンダー)
    - JSON デコード失敗時の明示的エラーとログ出力。
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes: raw_prices テーブルへ保存（PK: date, code）
      - save_financial_statements: raw_financials テーブルへ保存（PK: code, report_date, period_type）
      - save_market_calendar: market_calendar テーブルへ保存（PK: date）
    - データ変換ユーティリティ (_to_float, _to_int) を実装（不正値/空値は None。整数変換で小数部が残る場合は None を返す）
    - fetched_at を UTC ISO8601 (Z) で記録し、Look-ahead bias を防止するための取得時刻トレーシングを実装。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュースを収集・前処理・DB 保存するフルワークフローを実装:
    - デフォルトソース: Yahoo Finance のビジネスカテゴリ RSS を登録。
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb 等の対策）。
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベート/ループバック/リンクローカル/マルチキャスト IP の接続拒否（直接 IP および DNS 解決結果を検査）、リダイレクト時の事前検証ハンドラ。
      - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後サイズ検証（Gzip bomb 対策）。
    - URL 正規化: トラッキングパラメータ（utm_* 等）除去、スキーム/ホストの小文字化、フラグメント削除、クエリパラメータソート。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を保証。
    - テキスト前処理: URL 除去、空白の正規化など。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事 ID のリストを返す。チャンク処理と 1 トランザクションで実行し、例外時はロールバック。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING で保存。トランザクション制御あり。
    - 銘柄コード抽出: 正規表現による 4 桁数字候補を抽出し、known_codes によるフィルタリングで有効コードのみ返す。
    - run_news_collection: 複数 RSS ソースを独立して処理し、部分的失敗時も他ソースを継続。新規保存件数をソース毎に集計して返す。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - データレイク向けの多層スキーマを定義（Raw / Processed / Feature / Execution 層）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルのチェック制約（CHECK）や主キー、外部キーを定義。
  - 実務でのクエリ性能向上のためのインデックスを用意（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ自動作成と DDL 実行による初期化（冪等）を実装。get_connection() で既存 DB に接続するヘルパーを提供。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass を導入。ETL 実行結果、品質問題（quality モジュールの QualityIssue 想定）およびエラーリストを格納・判定するユーティリティを提供。
  - スキーマ/テーブル存在確認と最終取得日の取得ユーティリティを実装（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーを用いた営業日調整ロジック _adjust_to_trading_day を実装（未取得時はフォールバックして target_date を保持）。
  - run_prices_etl を実装（差分取得ロジック）:
    - date_from 未指定時は DB の最終取得日から backfill_days（デフォルト 3 日）前を再取得開始日とする（後出し修正を吸収）。
    - target_date より新しい date_from の場合はスキップ。
    - J-Quants から日足を取得して save_daily_quotes で保存。取得件数と保存件数を返す設計。

Security
- 外部データ取得に関するセキュリティ設計を明示:
  - SSRF 対策（スキーム検証、プライベート IP ブロック、リダイレクト検査）。
  - XMLパースに defusedxml を使用。
  - レスポンスサイズリミットと gzip 解凍後チェック。

Notes
- 設計原則として「冪等性」「Look-ahead Bias 防止」「API レート制限順守」「再試行とトークン自動更新」「トランザクションでのDB操作」を採用。
- quality モジュールや strategy / execution / monitoring の中身はこのリリースでは主要な骨組み（モジュールパッケージの存在）を残しており、詳細実装は別途拡張予定。

Deprecated
- なし（初回リリースのため該当なし）。

Fixed
- なし（初回リリースのため該当なし）。

Acknowledgements
- 本リリースは、データ取得・保存・前処理・スキーマ設計・ETL 制御の初期実装を含みます。今後、品質チェック（quality）、戦略ロジック（strategy）、実行コンポーネント（execution）、監視（monitoring）などを順次拡張していきます。