Keep a Changelog
=================

すべての注目すべき変更を時系列で記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

[Unreleased]

0.1.0 - 2026-03-15
------------------

Added
- 初回リリース: kabusys パッケージの基本実装を追加。
  - パッケージ情報
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - __all__ により公開サブパッケージを定義 (data, strategy, execution, monitoring)。
    - strategy/, execution/, monitoring/ のパッケージ初期化ファイルをプレースホルダとして追加。

- 環境設定モジュール (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
    - J-Quants / kabuステーション / Slack / DB パス / システム設定（環境、ログレベル）などのプロパティを提供。
    - 必須変数取得用の _require()（未設定時は ValueError を送出）。
    - KABUSYS_ENV の値検証（development / paper_trading / live のみ許可）。
    - LOG_LEVEL の値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可）。
    - is_live / is_paper / is_dev のヘルパープロパティを提供。
  - 自動 .env ロード機能を実装
    - プロジェクトルートの探索: カレントワークディレクトリに依存せず、__file__ を起点に親ディレクトリから .git または pyproject.toml を探して特定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - OS 環境変数を保護するため protected セットを使用し、override による上書き制御を実装。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップ。

  - .env パーサーの細かな仕様
    - export KEY=val 形式に対応。
    - シングル／ダブルクォートで囲まれた値をサポート（バックスラッシュエスケープを考慮）。
    - クォート無し値のコメント扱いは、'#' の直前がスペースまたはタブの場合のみコメントとして認識（インライン URL 等での誤検出を回避）。
    - 無効行（空行やコメント行、= を含まない行）は無視。

- データ層: DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - init_schema(db_path) を追加
    - 指定した DuckDB ファイルに対して全テーブル・インデックスを作成（冪等）。
    - db_path の親ディレクトリを自動作成。":memory:" のサポート。
    - スキーマは複数レイヤーで設計:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 頻出クエリを想定したインデックスを作成（例: 銘柄×日付インデックス、status 検索用インデックスなど）。
  - get_connection(db_path) を追加
    - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を推奨）。

  - テーブル定義における設計方針
    - 適切な CHECK 制約や PRIMARY KEY を付与（負値や不正値の防止）。
    - 外部キー制約を利用して整合性を確保（外部キー依存を考慮した作成順）。
    - news_symbols は news_articles と外部キーで紐付け（ON DELETE CASCADE）などのリレーションを定義。

- 監査（Audit）ログ: 監査トレーサビリティテーブル (src/kabusys/data/audit.py)
  - init_audit_schema(conn) を追加
    - 既存の DuckDB 接続に監査用テーブルを追加（冪等）。
    - すべての TIMESTAMP を UTC で保存するように SET TimeZone='UTC' を実行。
    - 監査用テーブル:
      - signal_events: 戦略が生成した全シグナル（棄却やエラーも含む）、strategy_id、decision、reason 等を保持。
      - order_requests: 発注要求ログ（order_request_id を冪等キーとする）。limit/stop/market に応じた CHECK 制約を実装。updated_at を持ちアプリ側で更新。
      - executions: 証券会社からの約定ログ（broker_execution_id をユニーク冪等キーとして扱う）。
    - インデックス類を追加（シグナル日付・銘柄、戦略別検索、status スキャン、broker_order_id/実行時系列検索等）。
    - 外部キーは ON DELETE RESTRICT を基本方針とし、監査ログを削除しない前提を明示。
  - init_audit_db(db_path) を追加
    - 監査ログ専用の DuckDB ファイルを初期化し接続を返す（parent ディレクトリ自動作成、:memory: サポート）。

Changed
- （初回リリースにつき変更履歴はなし）

Fixed
- （初回リリースにつき修正履歴はなし）

Notes / 設計メモ
- 監査系は冪等性とトレーサビリティを重視した設計。business_date → strategy_id → signal_id → order_request_id → broker_order_id の連鎖でフローを辿れるように設計されている。
- order_requests のステータス遷移や executions の broker_execution_id を利用した冪等処理を想定。
- データベース操作は基本的に冪等（CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS）なので、アプリ起動時に何度呼んでも安全。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後やテスト時に問題がある場合は KABUSYS_DISABLE_AUTO_ENV_LOAD で制御可能。

今後の予定（例）
- strategy / execution / monitoring の具象実装追加（戦略ロジック、発注エンジン、監視アラート等）。
- マイグレーション機構の導入（スキーマ変更対応）。
- 単体テスト・統合テストの追加、CI パイプラインの整備。

--- 
（この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートに反映する場合は、変更内容の確認・補足をお願いします。）