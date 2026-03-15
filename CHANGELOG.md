CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトではセマンティックバージョニングを採用しています（https://semver.org/）。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-15
--------------------

Added
- 初回リリース: KabuSys v0.1.0
  - パッケージ構成:
    - kabusys (トップレベル)
    - kabusys.data
    - kabusys.strategy (プレースホルダ)
    - kabusys.execution (プレースホルダ)
    - kabusys.monitoring (プレースホルダ)

- config モジュールを追加（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない探索実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - OS 環境変数は保護（protected）され、意図せず上書きされない。
  - .env パーサーは以下に対応:
    - コメント・空行・export プレフィックス
    - シングル/ダブルクォート内のエスケープ処理
    - クォート無し値内のコメント扱い（直前が空白/タブの場合）
  - Settings クラスを提供（settings インスタンス経由で利用）
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを定義
    - デフォルト値の提供（例: KABUSYS_API_BASE_URL のデフォルトなど）と必須チェック（_require）
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値は列挙）
    - ユーティリティ: is_live / is_paper / is_dev

- J-Quants API クライアントを追加（kabusys.data.jquants_client）
  - 取得対象:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー（祝日・半日・SQ）
  - 設計上の主要機能:
    - レート制限厳守（120 req/min）: 固定間隔スロットリングを行う RateLimiter 実装
    - リトライロジック: 指数バックオフ、最大試行回数 3 回、対象ステータス (408, 429, 5xx) とネットワークエラーに対応
    - 401 応答時のトークン自動リフレッシュ（1 回のみ）と再試行
    - ページネーション対応（pagination_key を用いた繰り返し取得）
    - トークンはモジュールレベルでキャッシュし、ページネーション間で共有
    - Look-ahead bias 対策: 取得時刻（fetched_at）を UTC で記録
    - DuckDB への保存は冪等（INSERT ... ON CONFLICT DO UPDATE）を採用
  - 公開関数:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
    - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)
  - 入出力/変換ヘルパー:
    - _to_float / _to_int: 型変換の安全実装（空値や不正値は None）
  - ロギング: 取得件数・保存件数・スキップ件数等を INFO/WARNING ログに出力

- DuckDB スキーマ定義を追加（kabusys.data.schema）
  - 3 層（Raw / Processed / Feature）＋ Execution レイヤーのテーブル定義を含む
  - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
  - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature 層: features, ai_scores
  - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して制約（PRIMARY KEY / CHECK / FOREIGN KEY）を設定し、データ整合性を強化
  - 頻出クエリを想定したインデックス群を定義
  - 公開 API:
    - init_schema(db_path) -> DuckDB 接続（テーブル作成は冪等）
    - get_connection(db_path) -> 既存 DB への接続（初期化は行わない）
  - init_schema は db_path の親ディレクトリを自動作成

- 監査ログ（Audit）モジュールを追加（kabusys.data.audit）
  - トレーサビリティを目的とした監査テーブルを定義
    - signal_events (戦略層のシグナルログ)
    - order_requests (発注要求ログ、order_request_id を冪等キーとして利用)
    - executions (証券会社からの約定ログ)
  - 設計原則:
    - 監査ログは削除しない（ON DELETE RESTRICT を使用）
    - すべての TIMESTAMP は UTC に固定（init_audit_schema で SET TimeZone='UTC' を実行）
    - status 列や詳細な CHECK 制約で状態遷移と整合性を担保
    - インデックスを整備し検索や JOIN を高速化
  - 公開 API:
    - init_audit_schema(conn) -> 既存接続に監査テーブルを追加（冪等）
    - init_audit_db(db_path) -> 監査専用 DB を初期化して接続を返す

Changed
- 該当なし（初回リリースのため）

Fixed
- 該当なし（初回リリースのため）

Security
- 該当なし（初回リリースのため）

Notes / Known limitations
- kabusys.strategy, kabusys.execution, kabusys.monitoring パッケージはプレースホルダ（__init__.py のみ）として用意。戦略ロジック、発注実行ロジック、モニタリングの実装は今後追加予定。
- J-Quants クライアントは urllib を用いて実装されており、将来的に requests 等への切り替えを検討する余地がある。
- DuckDB スキーマは初期設計に基づく。運用で要件変更が生じた場合はマイグレーション戦略を別途用意する必要がある。

References
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として定義しています。