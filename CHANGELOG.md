CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在なし）

0.1.0 - 2026-03-18
------------------

Added
- 初回公開リリース。
- パッケージ概要:
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - モジュール構成（主要モジュール）: data, strategy, execution, monitoring（strategy, execution, monitoring は初期プレースホルダ）。
- 環境設定 / 管理:
  - 環境変数を .env/.env.local または OS 環境変数から読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml によって検出）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env の行パーサは `export KEY=val`、クォート（シングル/ダブル）、エスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、必須環境変数の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）や各種既定値（KABU_API_BASE_URL, DB パス等）を管理。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション実装。
- J-Quants API クライアント（kabusys.data.jquants_client）:
  - API 呼び出しのための汎用 _request 実装。JSON デコードエラーハンドリング、タイムアウト設定。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を導入。
  - リトライ/バックオフ: 指数バックオフ、最大 3 回リトライ。対象ステータス (408, 429, >=500) に対応。429 の場合は Retry-After ヘッダを優先。
  - トークン管理: リフレッシュトークンから id_token を取得する get_id_token、モジュールレベルのトークンキャッシュ、自動リフレッシュ（401 受信時に1回のみリフレッシュして再試行）。
  - データ取得関数: 日足（fetch_daily_quotes）、財務（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）をページネーション対応で実装。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - fetched_at を UTC で記録して「いつデータを取得したか」を保持（Look-ahead Bias 対策）。
    - 冪等性確保のため INSERT ... ON CONFLICT ... DO UPDATE（アップサート）を採用。
    - PK 欠損行のスキップとログ出力。
- ニュース収集モジュール（kabusys.data.news_collector）:
  - RSS フィードからニュース記事を収集する fetch_rss、記事保存用の save_raw_news、記事と銘柄の紐付け save_news_symbols、複数ソースの統合 run_news_collection を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト時のスキーム/ホスト検査用ハンドラ、ホストのプライベートアドレス/ループバック判定、最終 URL の再検証。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止、gzip 解凍後もサイズ検査。
  - 機能:
    - URL 正規化とトラッキングパラメータ（utm_*, fbclid, gclid など）削除。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - DuckDB への一括挿入はチャンク化してトランザクション内で実行。INSERT ... ON CONFLICT DO NOTHING RETURNING を活用して新規挿入 ID を正確に返却。
    - 記事本文から4桁銘柄コード抽出（既知銘柄リストに基づく）と一括紐付け保存。
- スキーマ定義と初期化（kabusys.data.schema）:
  - DuckDB 用のテーブル定義を包括的に実装（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層。
  - features, ai_scores 等の Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層。
  - 適切な制約（PRIMARY KEY、CHECK）、外部キー、およびインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成（必要時）・DDL 実行して接続を返す。get_connection() で既存 DB に接続可能。
- ETL パイプライン（kabusys.data.pipeline）:
  - ETLResult データクラスを提供し、取得数・保存数・品質問題一覧・エラー一覧を集約。
  - 差分更新ヘルパー: テーブルの最終取得日取得、営業日調整（market_calendar に基づく _adjust_to_trading_day）。
  - run_prices_etl の骨組み（差分更新ロジック、バックフィル期間 _DEFAULT_BACKFILL_DAYS=3、最小データ日 _MIN_DATA_DATE、保存は jquants_client の save_* を使用）を実装。
  - 品質チェック（quality モジュール）との連携を想定した設計（品質チェックは致命的なエラーがあっても ETL を継続する方針）。
- ユーティリティ関数:
  - 型変換ユーティリティ (_to_float/_to_int)、URL 正規化、RSS 日時パース、銘柄コード抽出などの堅牢なユーティリティを実装。

Security
- RSS 経由の XML パースに defusedxml を使用（XML 脆弱性対策）。
- SSRF 対策（リダイレクト検証、プライベートIP拒否、スキーム制限）。
- 外部入力（.env、RSS 等）の堅牢なパースで予期せぬ挙動の低減。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / 未完事項
- strategy, execution, monitoring の実装はプレースホルダであり、今後のリリースで戦略ロジック・発注モジュール・監視機能の追加を予定。
- pipeline.run_prices_etl の実装はファイル内で続きがあることが想定される（コードの途中で終端しているため、実装の続きやその他 ETL ジョブ（financials/calendar）の統合は今後追加予定）。
- quality モジュール（品質チェック）の具体的な実装は別モジュールに委ねられているため、ルール拡張や重大度設定は今後の改善点。

作者
- kabusys 開発チーム

（この CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノートはプロジェクトの公式履歴に従ってください。）