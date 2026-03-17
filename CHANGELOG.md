CHANGELOG
=========

すべての重要な変更はこのファイルに記録されています。
フォーマットは「Keep a Changelog」に準拠しています。

フォーマットの概要:
- 変更はセクションごとに分類（Added, Changed, Fixed, Security, など）
- バージョンごとに日付を付与

[Unreleased]
------------

- 現在未リリースの作業はありません。

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
- パッケージ公開エントリポイント
  - src/kabusys/__init__.py に __version__ と主要サブモジュールを定義（data, strategy, execution, monitoring）。
- 環境変数・設定管理モジュール
  - src/kabusys/config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）による .env 自動読み込み。
    - .env / .env.local の読み込み順序および上書きルール（OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
    - .env の行パーサーは export プレフィックス、クォート、エスケープ、インラインコメント（#）等に対応。
    - Settings クラスで主要設定をプロパティとして公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等）。
    - KABUSYS_ENV / LOG_LEVEL の値検証と便利な bool プロパティ（is_live / is_paper / is_dev）。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API レート制限管理（_RateLimiter、デフォルト 120 req/min 固定間隔スロットリング）。
    - 汎用リクエストラッパー (_request) にリトライ（指数バックオフ）、429 の Retry-After 優先、408/429/5xx の再試行、最大試行回数、タイムアウト等を実装。
    - 401 Unauthorized 受信時はリフレッシュ処理を一度実行して再試行するトークン自動更新ロジック。
    - id_token キャッシュをページネーション間で共有する実装。
    - データ取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）はページネーション対応とフェッチログを出力。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等性を担保する ON CONFLICT / DO UPDATE を使用し、fetched_at（UTC）記録を付与。
    - 型安全な数値変換ユーティリティ (_to_float, _to_int) を実装。
- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード取得と記事保存ワークフロー（フェッチ → 前処理 → raw_news 保存 → 銘柄紐付け）。
    - 記事IDは URL 正規化後の SHA-256 の先頭32文字で生成し冪等性を保証（utm_* 等のトラッキングパラメータを除去）。
    - defusedxml による XML パース、安全な gzip ハンドリング、レスポンスサイズ上限（デフォルト 10MB）検査（Gzip bomb 防止含む）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - 事前のホストプライベート判定による拒否。
      - リダイレクト時にスキームとリダイレクト先のプライベートアドレスを検査するカスタムリダイレクトハンドラ。
    - RSS の前処理（URL 除去、空白正規化）、pubDate の安全なパース（UTC 変換、失敗時は代替時刻）を実装。
    - DuckDB への保存はチャンク化してトランザクションで実行、INSERT ... RETURNING による挿入件数算出（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
    - 銘柄コード抽出ロジック（4桁数字の抽出、既知銘柄セットでフィルタ）を提供（extract_stock_codes）。
    - デフォルト RSS ソースに Yahoo Finance（business カテゴリ）を追加。
    - 全ソースを対象にした実行関数 run_news_collection を実装（ソース毎に独立したエラーハンドリング、銘柄紐付けは新規挿入記事のみ）。
- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py
    - DataPlatform 設計に基づく 3 層＋実行層（Raw / Processed / Feature / Execution）のテーブル群を定義。
    - raw_prices, raw_financials, raw_news, raw_executions、processed テーブル（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）、
      feature テーブル（features, ai_scores）、および execution テーブル（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を含む DDL を提供。
    - 頻出クエリに対応するインデックスを定義。
    - init_schema(db_path) で親ディレクトリ自動作成、全テーブル／インデックスを冪等に作成し接続を返す。":memory:" によるインメモリ DB サポート。
    - get_connection(db_path) による既存 DB への接続取得。
- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass により ETL 実行結果、品質問題、エラー等を構造化して返却・ログ用辞書化(to_dict)。
    - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）実装。
    - market_calendar を用いた営業日調整ヘルパー (_adjust_to_trading_day)。
    - 差分更新ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - run_prices_etl 実装（差分取得ロジック、バックフィル日数の扱い、J-Quants からの取得と保存の呼び出し）。品質チェックフレームワーク（quality モジュール）と連携する設計。

Security
- ニュース収集での SSRF 対策、XML パースの安全化（defusedxml 使用）、受信サイズ制限、リダイレクト検査を実装。
- API クライアントでのリトライ制御やトークン自動更新により認証失敗やレート制限に耐性を持たせる。
- .env 読み込みで OS 環境変数を「protected」として扱い、意図しない上書きを防止。

Notes / Developer guidance
- 環境変数:
  - 自動読み込みはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 必須環境変数には Settings のプロパティからアクセスすると ValueError が投げられるため、起動前に .env を用意するか環境変数をセットしてください。
- DB 初期化:
  - 初回は init_schema(settings.duckdb_path) を呼んでスキーマを作成してください。既存 DB には get_connection を使用。
- J-Quants トークン:
  - get_id_token は settings.jquants_refresh_token を用いる設計。API コールは自動的にトークンをキャッシュ・リフレッシュします。
- ニュース記事の ID は URL 正規化に依存します。トラッキングパラメータの削除やクエリパラメータのソートルールが適用されます。

Breaking Changes
- 初期リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

---

脚注:
- 本 CHANGELOG はコードベースから実装内容を推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、そちらを優先して差分を反映してください。