CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
--------------------

初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。
主な追加点・設計方針は以下の通りです。

Added
- パッケージ基盤
  - kabusys パッケージ初期化とバージョン定義 (src/kabusys/__init__.py)。
  - パッケージ公開モジュール一覧: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定管理
  - 環境変数/ .env の読み込みと管理を行う settings (src/kabusys/config.py) を実装。
    - プロジェクトルート判定ロジック（.git または pyproject.toml を探索）により、カレントワークディレクトリに依存しない自動 .env ロードを実装。
    - .env と .env.local を優先順位付きで読み込み（OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
    - export KEY=val 形式やシングル/ダブルクォート、行末コメントの扱いを含む堅牢な1行パーサ実装。
    - 必須項目に対する _require() （例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
    - 設定値バリデーション: KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- データ取得（J-Quants）
  - J-Quants API クライアントを実装 (src/kabusys/data/jquants_client.py)。
    - daily_quotes（株価日足）、financial_statements（四半期財務）、market_calendar（JPXカレンダー）取得に対応。
    - API レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
    - 再試行（指数バックオフ、最大3回）と HTTP ステータスに応じたハンドリング（408/429/5xx をリトライ候補に）。
    - 401 受信時はリフレッシュトークンを使った id_token 自動リフレッシュを1回行って再試行。
    - ページネーション対応（pagination_key の追跡）。
    - 取得時刻（fetched_at）を UTC ISO8601 形式で保存し、Look-ahead Bias の追跡を可能にする。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で実装。
    - 型変換ユーティリティ（_to_float, _to_int）により不正値を安全に扱う。

- ニュース収集
  - RSS ベースのニュース収集モジュールを実装 (src/kabusys/data/news_collector.py)。
    - デフォルトソース（Yahoo Finance のビジネス RSS）を指定。
    - URL 正規化（utm_* 等のトラッキングパラメータ削除、クエリソート、フラグメント削除）と SHA-256 による記事ID生成（先頭32文字）で冪等性を確保。
    - defusedxml を使用した安全な XML パース（XML Bomb 対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - 事前にホストがプライベート/ループバック/リンクローカルでないことをチェックし、リダイレクト先も検査。
      - リダイレクト時にスキーム・プライベートアドレスを検証するカスタム HTTPRedirectHandler を導入。
    - レスポンスサイズの上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェックでメモリDoS / Gzip bomb を防止。
    - テキスト前処理（URL除去、空白正規化）と pubDate パース（RFC 2822 → UTC ナイーブ datetime）。
    - raw_news へのバルク挿入はチャンク化とトランザクションで実装し、INSERT ... RETURNING で実際に挿入された記事IDを返却。
    - 記事と銘柄コードの紐付け（news_symbols）を一括で保存するユーティリティを提供。既知銘柄の抽出は 4 桁数字パターンを利用。

- DuckDB スキーマ
  - DuckDB 用のスキーマ定義と初期化機能を実装 (src/kabusys/data/schema.py)。
    - Raw / Processed / Feature / Execution のレイヤーに対応したテーブル定義を用意。
    - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル。
    - features, ai_scores などの Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution テーブル。
    - 各種チェック制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を定義。
    - 典型クエリに合わせたインデックス定義を用意。
    - init_schema(db_path) により親ディレクトリ自動作成→DDL 実行→接続を返却。get_connection() も提供。

- ETL パイプライン
  - ETL 管理モジュールを実装（src/kabusys/data/pipeline.py）。
    - 差分更新のためのヘルパー（最終取得日の取得 get_last_price_date / get_last_financial_date / get_last_calendar_date、テーブル存在チェック）。
    - 市場カレンダーに基づく営業日の調整関数 (_adjust_to_trading_day)。
    - run_prices_etl: 差分取得ロジック（最終取得日から backfill して再取得）、jquants_client を使った取得と保存、および ETLResult データクラスにより実行結果（取得数／保存数／品質問題／エラー）を集約。
    - ETL 設計方針として「差分更新」「backfill による後出し修正吸収」「品質チェックは収集を続行し呼び出し元で判断」を採用。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- ニュース収集における複数のセキュリティ対策を導入:
  - defusedxml による XML パースの安全化。
  - SSRF 対策（スキーム検証、ホストがプライベートかのチェック、リダイレクト時の検査）。
  - レスポンスサイズ上限と gzip 解凍後の検査（メモリ DoS / Gzip bomb 対策）。

Notes / Implementation details
- 冪等性: raw データ保存は基本的に ON CONFLICT を利用（更新またはスキップ）しており、再実行可能な ETL を目指しています。
- ログ: 各主要処理で logging を使用して取得件数・挙動を記録します。
- 設計上の決定: J-Quants のレートリミット（120 req/min）をモジュールレベルで守る実装。トークンの自動リフレッシュは 401 に対して1回のみ行うことで無限ループを防止。
- DB: DuckDB を採用。ファイルパスのデフォルトは data/kabusys.duckdb。:memory: でのインメモリ利用にも対応。

Known issues / TODO
- strategy / execution / monitoring の各パッケージは初期エクスポートのみで、実際の戦略ロジック・発注実装・監視機能は今後の実装予定。
- quality モジュール（pipeline で参照）は参照されているが、品質チェックルールと具体的なチェック実装は継続実装が想定されます。
- 単体テスト・統合テスト、運用時のメトリクス収集／監視やエラーレポーティングの追加が推奨されます。

ライセンス
- （ライセンス情報はリポジトリの LICENSE 等を参照してください）