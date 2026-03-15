Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

フォーマット
-----------

各リリースは日付付きで記載し、セクションは以下を含みます: Added, Changed, Fixed, Removed, Security（該当するもののみ記載）。

Unreleased
----------

- なし（初回リリースのみ）

[0.1.0] - 2026-03-15
--------------------

Added
- 初期リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ構成:
    - src/kabusys/__init__.py: パッケージメタ（__version__ = "0.1.0"）と公開サブパッケージ指定 (data, strategy, execution, monitoring)。
    - strategy/, execution/, monitoring/: プレースホルダの __init__.py（将来の拡張用）。

- 環境設定管理モジュール (src/kabusys/config.py)
  - .env ファイルまたは環境変数からの設定読み込みを実装。
  - プロジェクトルートの自動検出機能を追加（.git または pyproject.toml を基準）。
  - .env のパースロジック:
    - 空行・コメント行（#）の無視、export KEY=val 形式への対応。
    - シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い。
    - クォート無し値に対する「# はスペース直前でコメント扱い」の処理。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供（settings インスタンス）:
    - J-Quants / kabuステーション / Slack / データベース / システム設定用プロパティ。
    - デフォルト値と必須チェック（未設定時は ValueError）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値を限定）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API ベースの実装: トークン取得、データ取得、DuckDB への保存ユーティリティ。
  - レート制限: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
  - リトライ戦略:
    - 最大 3 回、指数バックオフ（ベース 2 秒）。
    - 再試行対象: 408, 429, 5xx およびネットワークエラー。
    - 429 の場合は Retry-After ヘッダを優先。
  - 認証トークン管理:
    - get_id_token() でリフレッシュトークンから ID トークンを取得。
    - モジュールレベルのトークンキャッシュを保持し、401 受信時に自動リフレッシュして 1 回リトライ。
    - 無限再帰防止フラグ（allow_refresh）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes(), fetch_financial_statements(): pagination_key を追跡して全件取得。
    - fetch_market_calendar(): JPX カレンダー取得。
  - DuckDB 保存関数（冪等）:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar() は ON CONFLICT DO UPDATE を使用して重複を排除。
    - fetched_at は UTC の ISO 形式で記録（look-ahead bias 対策）。
    - PK 欠損行のスキップと警告ログ出力。
  - 型変換ユーティリティ: _to_float(), _to_int()（空値・不正値の扱いを明確化）。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層 + Execution 層のテーブル定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な CHECK 制約、PRIMARY KEY、FOREIGN KEY を設定。
  - パフォーマンスを考慮したインデックス定義（銘柄×日付検索、ステータス検索等）。
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成→全テーブル／インデックス作成（冪等）。
  - get_connection(db_path) を提供（既存 DB への接続）。":memory:" サポートあり。

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - signal_events, order_requests, executions の監査向けテーブル定義を追加。
  - 設計上の特徴:
    - order_request_id を冪等キーとして扱い二重発注を防止。
    - すべての TIMESTAMP は UTC（init_audit_schema() は SET TimeZone='UTC' を実行）。
    - order_requests に対する詳細な CHECK（limit/stop/market の価格ルール）とステータス列。
    - executions は broker_execution_id をユニーク（証券会社側の冪等キー）。
    - 監査ログは削除しない前提（FK は ON DELETE RESTRICT）。
  - 指定された索引用のインデックスを作成（status スキャンや signal_id/日付での検索を最適化）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（冪等・UTC 設定）。

- ロギングと警告
  - ファイル読み込み失敗や PK 欠損行は warnings / logger.warning を使って通知。
  - fetch/save の取得件数ログ出力を実装。

Fixed
- なし（初回リリース）

Changed
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- 認証トークンの自動リフレッシュとキャッシュにより、401 発生時に安全に再取得して再試行する挙動を実装（無限ループ防止のため 1 回のみ自動リフレッシュ）。

Notes / Known limitations
- execution/strategy/monitoring パッケージは現時点では実装の骨子（__init__.py）に留まり、具体的な発注ロジック／戦略／監視機能は今後の実装対象。
- ネットワークIOは urllib を直接利用しており、ユニットテストでは外部 API のモックが必要。
- DuckDB に依存（duckdb パッケージが必要）。init_schema() を初回実行する際は書き込み権限のあるディレクトリが必要。

References
- セマンティックバージョニング: https://semver.org/
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/