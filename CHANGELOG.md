CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。
このプロジェクトは "Keep a Changelog" の構成に準拠しています。

フォーマット:
- 既存のリリースは日付付きで記載
- セクション: Added, Changed, Fixed, Security, 注意事項（移行メモ等）

Unreleased
----------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-15
--------------------

Added
- 初回リリース。パッケージメタ情報:
  - kabusys.__version__ = "0.1.0"
  - パッケージ公開モジュール: data, strategy, execution, monitoring
- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装
    - 読み込み順序: OS環境変数 > .env.local > .env
    - プロジェクトルートの自動検出: .git または pyproject.toml を起点として探索（CWD に依存しない）
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - OS の既存環境変数は保護され、.env による上書きを防止（.env.local は override）
  - 高度な .env パーサを実装
    - export KEY=val 形式対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート有無で挙動を区別）
  - Settings クラス（settings インスタンス）を提供し、主要設定をプロパティ経由で取得
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトを含む）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV 検証（有効値: development, paper_trading, live）
    - LOG_LEVEL 検証（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - ヘルパー: is_live, is_paper, is_dev
  - 必須環境変数未設定時は ValueError を送出

- データスキーマ（kabusys.data.schema）
  - DuckDB 用スキーマ定義を導入（Raw / Processed / Feature / Execution の 3+1 層設計）
  - Raw Layer のテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer のテーブル:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer のテーブル:
    - features, ai_scores
  - Execution Layer のテーブル:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリを考慮したインデックス定義を追加
  - DB 初期化 API:
    - init_schema(db_path) — 指定した DuckDB ファイル（または ":memory:"）を初期化して接続を返す。親ディレクトリを自動作成。DDL は冪等。
    - get_connection(db_path) — 既存 DB への接続（スキーマ初期化は行わない）

- 監査ログ（kabusys.data.audit）
  - シグナルから約定に至るトレーサビリティを完全に残す監査ログを実装
  - トレーサビリティ階層の設計（business_date → strategy_id → signal_id → order_request_id → broker_order_id）
  - テーブル:
    - signal_events（シグナル生成ログ。拒否・エラーも記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ。各種チェック制約を追加）
    - executions（証券会社からの約定情報。broker_execution_id はユニーク）
  - インデックスを多数追加（ステータス検索、signal_id 参照、broker_order_id 参照など）
  - 全 TIMESTAMP は UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）
  - DB 初期化 API:
    - init_audit_schema(conn) — 既存の DuckDB 接続に監査テーブルを追加（冪等）
    - init_audit_db(db_path) — 監査ログ専用の DuckDB を初期化して接続を返す

- パッケージ構成
  - 空のパッケージ初期化ファイルを配置: execution, strategy, monitoring, data（各 __init__）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

注意事項 / 移行メモ
- 環境変数の自動ロード動作:
  - OS 環境変数が優先されます。テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env.local は .env の上書き用に読み込まれます（override=True）。
- .env パーサの仕様:
  - クォートありの値はエスケープ処理をサポートし、インラインコメントは無視されます。
  - クォートなしの値では、直前がスペース/タブの '#' 以降をコメントとして扱います（一般的な .env 慣習に合わせた挙動）。
- Settings の検証:
  - KABUSYS_ENV と LOG_LEVEL に対して不正な値が設定されると ValueError を送出します。事前に .env.example を参照してください。
- DB 初期化:
  - init_schema / init_audit_db は親ディレクトリが存在しない場合に自動作成します。既存テーブルがある場合はスキップされるので冪等です。
  - 監査スキーマは UTC タイムゾーンでタイムスタンプを記録します。
- 監査ログの運用:
  - order_request_id を冪等キーとして扱い、二重発注防止に利用する設計です。
  - 監査テーブルは削除しない運用を想定しているため、外部キーは ON DELETE RESTRICT を利用しています。
- 今後の実装予定（未実装）
  - strategy、execution、monitoring 各モジュールのビジネスロジック（現在はパッケージのみ用意）

著作権 / ライセンス
- 本リリースのソースコード中にライセンス表記が含まれていないため、利用前にライセンス方針を確認してください。

（注）この CHANGELOG は提供されたコードベースから推測して作成しています。実際のコミット履歴や意図した設計方針に基づく正式な変更履歴は、開発履歴（コミットログなど）を参照してください。