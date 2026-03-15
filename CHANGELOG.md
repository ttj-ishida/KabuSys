# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠し、Semantic Versioning を想定しています。  
日付はこのコードスナップショットの作成日（2026-03-15）を使用しています。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-03-15

### Added
- 初期公開リリース。パッケージメタ情報と主要コンポーネントを追加。
  - パッケージバージョン: 0.1.0
  - パッケージ説明: KabuSys - 日本株自動売買システム
  - パッケージの公開 API: data, strategy, execution, monitoring

- 環境設定管理モジュールを追加（kabusys.config）。
  - .env / .env.local の自動読み込み機能を実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を検索（CWD 非依存）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - OS 環境変数は保護され、.env による上書きを防止。
  - 独自の .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
  - 環境設定の取得用 Settings クラスを追加。プロパティ経由で設定を取得。
    - J-Quants / kabuステーション / Slack / データベース / システム設定をカバー。
    - 必須キーは未設定時に ValueError を送出する _require() を利用して検出。
    - サポートされる環境: development, paper_trading, live（不正値は ValueError）。
    - サポートされるログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL（不正値は ValueError）。
    - データベースパスのデフォルト:
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db

  - 主に期待される環境変数（抜粋）:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
    - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN
    - SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV, LOG_LEVEL

- データレイヤー（DuckDB）スキーマ定義を追加（kabusys.data.schema）。
  - 3層＋実行層のスキーマ定義（Raw / Processed / Feature / Execution）。
  - 主なテーブル（抜粋）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・チェック制約（非負制約、CHECK、PRIMARY KEY、FOREIGN KEY 等）を付与。
  - クエリパフォーマンスを考慮したインデックス定義を追加（銘柄×日付スキャン、ステータス検索等）。
  - スキーマ初期化 API:
    - init_schema(db_path) — DB ファイルを作成（親ディレクトリ自動生成）し、全テーブル／インデックスを作成して接続を返す（冪等）。
    - get_connection(db_path) — 既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュールを追加（kabusys.data.audit）。
  - DataPlatform 設計に基づく監査テーブル群を追加し、シグナル→発注→約定までの UUID 連鎖によるトレーサビリティを実現。
  - 監査用テーブル（抜粋）:
    - signal_events（戦略が生成したシグナルと決定、棄却理由等）
    - order_requests（発注要求、冪等キー order_request_id を持つ）
    - executions（証券会社からの約定ログ、broker_execution_id は冪等キー）
  - テーブル制約と状態遷移の設計原則を明文化（削除禁止、created_at/updated_at、UTC 保存等）。
  - 監査用インデックスを追加（処理待ち検索、signal_id 結合、broker_order_id 紐付け等）。
  - 監査用スキーマ初期化 API:
    - init_audit_schema(conn) — 既存の DuckDB 接続に監査テーブルを追加（UTC タイムゾーン設定を実行）。
    - init_audit_db(db_path) — 監査専用 DB を作成して接続を返す。

- パッケージ雛形ファイルを追加（空の __init__ でモジュールを露出）
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/data/__init__.py
  - src/kabusys/monitoring/__init__.py

### Changed
- （初版のため変更なし）

### Fixed
- （初版のため修正なし）

### Security
- （初版のため特記事項なし）

---

補足（利用開始メモ）
- DB 初期化例（Python）:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
- 監査ログ追加例:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn)  # conn は init_schema などで得た接続
- 自動 .env ロードを一時的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

（以上）