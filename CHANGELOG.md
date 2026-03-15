Keep a Changelog
すべての注目すべき変更はこのファイルで公開します。
このプロジェクトは Semantic Versioning に従います。

[0.1.0] - 2026-03-15
Added
- 初回リリース: kabusys パッケージを追加。
  - パッケージ公開情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - 公開サブパッケージ: data, strategy, execution, monitoring
- 環境設定管理モジュールを追加 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機構:
    - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定（CWD に依存しない実装）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - OS 環境変数は保護され、.env の上書きを防止（.env.local は override=True で上書き可能）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テストでの利用を想定）。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを解釈して正しく値を抽出。
    - クォートなし値でのコメント判断は '#' の直前が空白またはタブの場合のみコメントとみなす等、実用的なルールを採用。
    - 無効行やコメント行を無視する設計。
  - 環境変数取得ヘルパー _require（未設定時に ValueError を送出）。
  - Settings が提供する主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - データベースパス: duckdb_path（デフォルト: data/kabusys.duckdb）、sqlite_path（デフォルト: data/monitoring.db）
    - システム設定: env (development/paper_trading/live の制約)、log_level（DEBUG/INFO/WARNING/ERROR/CRITICAL の制約）
    - ヘルパー: is_live, is_paper, is_dev
- DuckDB スキーマ定義・初期化モジュールを追加 (src/kabusys/data/schema.py)
  - DataLayer に基づく多層スキーマを定義（Raw / Processed / Feature / Execution）。
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions（主キー・型チェックを含む）。
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols（外部キー制約あり）。
  - Feature レイヤー: features, ai_scores（戦略・AI 用の特徴量保存テーブル）。
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance（ステータス列・CHECK 制約、外部キー制約を含む）。
  - 頻出クエリを想定したインデックスを多数定義（例: 銘柄×日付、ステータス検索、外部キー参照用等）。
  - DDL は冪等（CREATE TABLE IF NOT EXISTS）で定義。
  - 公開 API:
    - init_schema(db_path): DuckDB ファイル（または ":memory:"）を初期化・テーブル作成し接続を返す。親ディレクトリが無ければ自動作成。
    - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない、初回は init_schema を推奨）。
- 監査ログ（トレーサビリティ）モジュールを追加 (src/kabusys/data/audit.py)
  - シグナルから約定までの完全な監査チェーンを保存するテーブル群を定義。
  - トレーサビリティ設計（business_date → strategy_id → signal_id → order_request_id → broker_order_id）。
  - 主なテーブル:
    - signal_events: 戦略が生成した全シグナル（リスク棄却等も含め永続化）。
    - order_requests: 発注要求（order_request_id を冪等キーとして採用、注文種別ごとの CHECK 制約、updated_at を保持）。
    - executions: 証券会社から返される約定ログ（broker_execution_id は一意／冪等）。
  - 外部キーと ON DELETE 制約は監査要件に合わせて設定（削除は原則許容しない設計）。
  - インデックス群を定義（シグナル検索、ステータス検索、broker_order_id/約定検索など）。
  - タイムゾーン: init_audit_schema は "SET TimeZone='UTC'" を実行し、すべての TIMESTAMP を UTC で保存することを明示。
  - 公開 API:
    - init_audit_schema(conn): 既存の DuckDB 接続に監査テーブルを追加（冪等）。
    - init_audit_db(db_path): 監査ログ専用の DB を初期化して接続を返す（親ディレクトリ自動作成、UTC 時刻設定）。
- パッケージ構造の土台を追加
  - 空のパッケージ初期化ファイルを配置（src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py、src/kabusys/monitoring/__init__.py）し、今後の実装の土台を用意。
- 型ヒントと pathlib/duckdb の利用により、ファイルパスや DB 接続の扱いを明確化。

Notes
- スキーマの多くに厳密な CHECK 制約や外部キーを付与しており、データ整合性を重視した設計になっています。
- init_schema / init_audit_db は親ディレクトリを自動作成するため、初回実行時にディレクトリを事前作成する必要はありません。
- audit 周りは監査・トレーサビリティ重視のため、レコードの削除を許容しない（ON DELETE RESTRICT 等）方針を明記しています。

Unreleased
- 今後の予定（例）
  - execution/strategy/monitoring モジュールの具体的な実装（発注送信、ポジション管理、監視・通知ロジック）
  - マイグレーション機能（スキーマ変更の履歴管理）
  - テストスイートと CI の追加

配布元・貢献
- 初期リリースのため、API や DDL に関するフィードバック歓迎。