# Changelog

すべての変更は Keep a Changelog の仕様に準拠しています。  
安定版リリースはセマンティックバージョニングに従います。

全体概要:
KabuSys は日本株の自動売買基盤向けに設計された軽量ライブラリ群です。本リリースでは、環境変数管理、J-Quants API クライアント、RSS ニュース収集器、DuckDB スキーマ定義、および基本的な ETL パイプラインの初期実装を提供します。

## [0.1.0] - 2026-03-17

### Added
- 基本パッケージ構成を追加（src/kabusys/__init__.py）。
  - バージョン __version__ = "0.1.0" を設定。
  - 公開サブパッケージ: data, strategy, execution, monitoring を定義。

- 環境変数 / 設定管理モジュールを追加（src/kabusys/config.py）。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）を実装し、CWD に依存しない .env 自動読み込みを実現。
  - .env と .env.local の読み込み順序をサポート（OS 環境変数の保護、override の制御）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env ファイルの柔軟なパースを実装（export 形式、クォート、インラインコメント等に対応）。
  - Settings クラスを追加し、必須設定値の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）と妥当性チェック（KABUSYS_ENV, LOG_LEVEL）を提供。
  - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）を設定するプロパティを提供。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得 API を実装（ページネーション対応）。
  - API レート制御（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）を実装。
  - 401 レスポンス時はリフレッシュトークンでトークンを自動更新して 1 回リトライ。
  - id_token のモジュール内キャッシュ（ページネーション間で共有）を実装。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等性を考慮し、ON CONFLICT DO UPDATE を使用。
  - データ取得時に fetched_at を UTC ISO8601 で記録し、Look-ahead bias のトレーサビリティを確保。
  - 各種型変換ユーティリティ（_to_float, _to_int）を実装し、入力の頑健性を高める。

- RSS ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - デフォルト RSS ソース（例: Yahoo Finance）の収集をサポート。
  - XML パースに defusedxml を使用して XML BOM / XML Bomb 等の攻撃を軽減。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト時のスキーム・ホスト検証ハンドラを実装（内部アドレスへの到達を拒否）。
    - ホストのプライベート IP 判定（直接 IP / DNS 解決の両方を検査）。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後検査を実装（メモリDoS・Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、fragment 削除）と SHA-256 を用いた記事 ID 生成（先頭32文字）を実装し、冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を提供。
  - DuckDB への保存関数（save_raw_news, save_news_symbols, _save_news_symbols_bulk）を実装。
    - INSERT ... RETURNING を用いて、実際に挿入された件数/ID を正確に取得。
    - チャンク分割と単一トランザクションでのバルク挿入によりオーバーヘッドを抑制。
  - 銘柄コード抽出機能（extract_stock_codes）を実装（4桁数字パターン、known_codes によるフィルタリング、重複除去）。

- DuckDB スキーマ定義モジュールを追加（src/kabusys/data/schema.py）。
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル群を定義。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores 等の Feature テーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブルを定義。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックス（頻出クエリ向け）を用意。
  - init_schema(db_path) によりディレクトリ自動作成と全テーブルの冪等生成を実装。get_connection() で既存 DB へ接続可能。

- ETL パイプライン基礎を追加（src/kabusys/data/pipeline.py）。
  - ETLResult dataclass を実装し、ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を集約。
  - 差分更新補助関数（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）を追加。
  - 市場カレンダーに基づく日付調整ヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl() を実装（差分更新ロジック、backfill_days による再取得、jquants_client 経由での取得と保存）。  
    - 初回ロード用の最小日付 _MIN_DATA_DATE を定義。
    - カレンダー先読み・デフォルト backfill を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- defusedxml の採用、SSRF 用リダイレクトハンドラ、ホスト private 判定、レスポンス読み取り上限、URL スキーム検証など、外部入力（RSS）に対するセキュリティ対策を多数実装。
- J-Quants クライアントのリトライ/バックオフと 401 トークン更新処理により認証周りの堅牢性を強化。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Limitations
- run_prices_etl 等 ETL の実装は差分更新の基本ロジックを提供しますが、品質チェック（quality モジュール）や他の ETL ジョブ（financials / calendar / news 統合フロー）との統合は継続開発項目です。
- テストユーティリティや CI、実運用での監視/ロギング設定、Slack 通知（設定項目はあるが送信ロジックは別途実装が必要）などは今後の追加を想定しています。
- jquants_client の HTTP 実装は urllib を使用しており、高度な接続プーリングや非同期処理は未対応。大量同時並列処理が必要な場合は将来の改善を検討してください。

---

今後の作業候補（例）
- ETL の完全なワークフロー化（財務データ・カレンダー・ニュースの差分 ETL の統合）。
- 品質チェックモジュール（quality）の実装と ETL への組み込み。
- execution/strategy/monitoring サブパッケージの具体的実装（発注ラッパー、バックテスト、ポートフォリオ最適化、監視ダッシュボード等）。
- 単体テスト・統合テストの整備および CI パイプライン構築。