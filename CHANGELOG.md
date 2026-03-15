CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。バージョニングは semver に従います。

0.1.0 - 2026-03-15
------------------

初回リリース。日本株自動売買システムの基本的なモジュール群と永続化スキーマ、環境設定管理機能を追加しました。

Added
- パッケージ初期化
  - pkg: kabusys
  - __version__ = "0.1.0"
  - サブパッケージのエクスポート: data, strategy, execution, monitoring

- 環境変数・設定管理モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装
    - プロジェクトルート判定: .git または pyproject.toml を探索して決定（CWD 非依存）
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - 環境変数名 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）
    - OS 環境変数は保護（.env の上書きを防止）し、.env.local は上書き可能
  - .env パーサーを実装（kabusys.config._parse_env_line）
    - コメント行・空行の無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしの場合のインラインコメント判定（直前が空白/タブのみ）
  - Settings クラスを追加（settings インスタンスを提供）
    - 必須設定を取得する _require() を実装（未設定時は ValueError）
    - 必須環境変数（プロパティ）
      - JQUANTS_REFRESH_TOKEN
      - KABU_API_PASSWORD
      - SLACK_BOT_TOKEN
      - SLACK_CHANNEL_ID
    - オプション・デフォルト値
      - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
      - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
      - SQLITE_PATH: デフォルト "data/monitoring.db"
      - KABUSYS_ENV: デフォルト "development"
      - LOG_LEVEL: デフォルト "INFO"
    - 値検証
      - KABUSYS_ENV は {development, paper_trading, live} のいずれか
      - LOG_LEVEL は {DEBUG, INFO, WARNING, ERROR, CRITICAL} のいずれか
    - is_live / is_paper / is_dev ヘルパーを提供

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - 3 層アーキテクチャに基づくテーブル定義を実装
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer:
      - features, ai_scores
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種 CHECK 制約、PRIMARY KEY、FOREIGN KEY を定義（データ整合性向上）
  - 頻出クエリ向けのインデックスを作成（例: code, date に関する複合インデックス、status 検索用など）
  - init_schema(db_path) を提供
    - 指定した DuckDB ファイルを初期化してすべてのテーブルとインデックスを作成（冪等）
    - db_path の親ディレクトリが存在しない場合は自動作成
    - ":memory:" を指定してインメモリ DB を使用可能
    - 初回以外は既存テーブルをスキップ（安全な再実行）
  - get_connection(db_path) を提供
    - 既存 DB への単純接続（スキーマ初期化は行わない）

- 監査ログ・トレーサビリティ (kabusys.data.audit)
  - 戦略から約定までのトレースを行う監査テーブル群を追加
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして扱う）
    - executions（約定ログ、broker_execution_id を冪等キーとして扱う）
  - 監査用インデックスを作成（例: signal_events の日付/銘柄検索、order_requests.status スキャン、broker_order_id での紐付けなど）
  - init_audit_schema(conn) を提供
    - 既存の DuckDB 接続に監査テーブルを追加（冪等）
    - すべての TIMESTAMP を UTC で保存するために SET TimeZone='UTC' を実行
  - init_audit_db(db_path) を提供
    - 監査ログ専用 DuckDB を初期化して接続を返す（親ディレクトリ自動作成、UTC 時間設定）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 設計上の重要点
- .env パーサーの挙動
  - クォートありの値はエスケープを解釈し、閉じクォート以降のインラインコメントは無視
  - クォートなしの値では '#' が現れた場合、その直前が空白/タブであれば以降をコメントと判断
- 環境変数の自動ロードはプロジェクトルートの発見に依存する（.git または pyproject.toml が必要）
- DuckDB のスキーマ初期化は冪等（繰り返し実行しても既存テーブルは上書きされない）
- 監査ログは削除しない運用を想定（外部キーは ON DELETE RESTRICT）
- order_requests の制約により order_type に応じた limit_price / stop_price の必須・排他チェックを実施
- 監査系ではすべての TIMESTAMP を UTC で保持（外部システムとの時刻ずれを防止）

Migration / Upgrade notes
- 0.1.0 は初回リリースのため移行事項はありません。将来のバージョンでスキーマ変更や列追加を行う際は、DuckDB の互換性・既存データの取り扱いに注意してください。

開発者向け補足
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境依存の自動ロードを抑制できます。
- init_schema / init_audit_db は ":memory:" を受け付けるため、ユニットテストでインメモリ DB を簡単に利用可能です。

---