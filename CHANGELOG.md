Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  

0.1.0 - 2026-03-18
------------------

Added
- 初期リリース (v0.1.0)
  - パッケージ基本情報
    - パッケージ名: KabuSys
    - バージョン: 0.1.0
    - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に定義
  - 環境変数/設定管理 (kabusys.config)
    - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装
      - プロジェクトルートはこのファイルの位置から .git または pyproject.toml を探索して検出
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）
      - OS 環境変数は protected として .env による上書きを防止
    - .env パーサーの実装
      - export KEY=val 形式対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
      - インラインコメントやクォートなしの # 処理に対応
    - Settings クラスを提供（プロパティ経由で必須/任意設定を取得）
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須チェック
      - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の値検証
      - DB パス（DUCKDB_PATH, SQLITE_PATH）の Path 変換とデフォルト
      - is_live/is_paper/is_dev プロパティ

  - J-Quants API クライアント (kabusys.data.jquants_client)
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装
    - get_id_token によるリフレッシュトークン→IDトークン取得 (POST)
    - HTTP リクエストユーティリティ _request を実装
      - レート制御: 固定間隔スロットリングによる 120 req/min の制限（_RateLimiter）
      - 再試行 (最大 3 回) と指数バックオフ
      - HTTP 429 の場合は Retry-After ヘッダを優先
      - 401 が返った場合は自動で id_token をリフレッシュして 1 回だけリトライ（無限再帰を防止）
      - JSON デコードエラー・ネットワークエラーのハンドリング
    - DuckDB への保存関数 save_daily_quotes/save_financial_statements/save_market_calendar を実装
      - 挿入は冪等（ON CONFLICT DO UPDATE）で重複を排除
      - fetched_at を UTC ISO8601 で記録し、いつデータを取得したかをトレース可能に

  - ニュース収集 (kabusys.data.news_collector)
    - RSS フィードの取得と raw_news への保存機能を実装
      - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを定義
      - fetch_rss: RSS 取得、XML 解析、記事抽出を実装
      - save_raw_news: INSERT ... RETURNING を使い、新規挿入された記事IDを返す（チャンク分割）
      - 銘柄紐付け (save_news_symbols / _save_news_symbols_bulk) を実装（ON CONFLICT DO NOTHING）
    - 安全性・堅牢性向上機能
      - defusedxml を使い XML ベースの攻撃を緩和
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、読み込みオーバー時はスキップ（Gzip 解凍後も検査）
      - リダイレクト検査付きハンドラで SSRF を防止（スキーム検証、プライベート IP アドレスの検出）
      - URL 正規化とトラッキングパラメータ削除（_normalize_url/_make_article_id）
      - 記事IDは正規化 URL の SHA-256（先頭32 文字）で生成し冪等性を担保
      - URL スキーム検証 (http/https のみ許可)
    - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字、known_codes によるフィルタ）

  - DuckDB スキーマ定義と初期化 (kabusys.data.schema)
    - Raw / Processed / Feature / Execution 層のテーブル群を定義
      - raw_prices, raw_financials, raw_news, raw_executions など Raw 層
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed 層
      - features, ai_scores など Feature 層
      - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution 層
    - 制約（PRIMARY KEY、CHECK、FOREIGN KEY）やインデックスを多数定義
    - init_schema(db_path) でディレクトリを自動作成し、全 DDL を冪等に実行して接続を返す
    - get_connection(db_path) で既存 DB へ接続（初期化は行わない旨を明記）

  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult dataclass による ETL 結果の集約（品質問題とエラーリストを含む）
    - 差分更新ロジック（最終取得日を確認し、backfill_days を使って数日前から再取得）
    - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS）と最小データ日付の設定
    - get_last_* ヘルパー、_adjust_to_trading_day、run_prices_etl 等の基盤的な ETL 関数群を実装
    - jquants_client の fetch/save 関数を利用して idempotent に保存

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集モジュールで SSRF 対策を実装
  - リダイレクト先のスキーム・ホスト検証、プライベート IP チェックにより内部ネットワークへのアクセスを防止
  - defusedxml を使用して XML パース時の攻撃を緩和
  - 外部入力（URL）に対するスキーム制限（http/https のみ）を徹底
- .env パーサーはエスケープ処理を考慮し、コメントやクォート処理での不正解釈を緩和

Performance
- J-Quants クライアントで固定間隔スロットリングを導入し API レート制限を厳守（120 req/min）
- ニュース保存時はチャンク（デフォルト 1000 件）でバルク INSERT を行いトランザクションをまとめてオーバーヘッドを削減

内部（Internal）
- 型注釈や TypedDict を活用して内部 API の可読性・テスト性を向上
- ユーティリティ関数（_to_float/_to_int/URL 正規化/日付パースなど）を分離

Notes / Migration
- 初期リリースのため移行作業は不要
- 設定
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）を設定しないと Settings のプロパティアクセスで ValueError が発生します
  - 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- DuckDB スキーマは init_schema() を一度実行してから ETL/収集処理を実行してください

既知の制限 / 今後の課題
- pipeline.run_prices_etl の戻り値タプルの末尾が途中で切れているように見える（現コードスニペットの最後にコンマがあり、完全な戻り値定義が欠落している可能性がある）。この点は次リリースで確認・修正を推奨。
- strategy、execution、monitoring パッケージは __init__.py が空で公開のみされており、各層の具象実装は今後追加予定。

Contributing
- バグ報告、機能提案は Issue を作成してください。プルリクエストはテストと型チェックを含めて送ってください。

ライセンス
- ソースコード内に明示的なライセンスヘッダはありません。配布前に適切なライセンスを追加してください。