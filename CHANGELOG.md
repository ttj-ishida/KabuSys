# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

注記:
- パッケージのバージョンは src/kabusys/__init__.py の __version__ に従います。
- 本ファイルはコード内容から推測して作成しています。

[Unreleased]

## [0.1.0] - 2026-04-22
初回リリース — 基本的な実行基盤、設定管理、発注エンジン、監視周りを実装。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
- 環境/設定管理
  - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）。
    - J-Quants / kabu API / LINE / DB パス /各種閾値 / PID/KILL フラグなどをプロパティとして提供。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE に対する値検証を実行し、不正値の場合は ValueError を送出。
  - .env ファイルの自動読み込み機能を追加
    - プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を読み込む。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装（クォート処理、エスケープ、インラインコメント処理対応）。
- 対話式設定ウィザード
  - python -m kabusys.config_setup で .env の初期作成・更新を支援するウィザードを追加（src/kabusys/config_setup.py）。
  - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）とテンプレート書き出し機能を提供。
- 設定検証 CLI
  - python -m kabusys.validate_config により .env と config/*.yaml の存在/基本的妥当性をチェック（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL 検証、DB パス親ディレクトリ存在チェック、PyYAML があれば YAML パース検証を実行。
  - --strict モードで警告も FAIL 扱い（exit(1)）。
  - 本番向け追加チェック（KABUSYS_ENV=live のときの LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）。
- 実行スクリプト
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
    - ExecutionEngine を構成し、セッション（シグナル処理 + push ドレイン）を実行（src/kabusys/run_execution.py）。
    - paper_trading 環境では paper_trading 用 SQLite を使用して本番 DB と分離。
    - PID ファイル、stop flag（data/stop_requested.flag）を用いた起動/終了制御。
    - プロセス優先度設定、Logging セットアップ呼び出しに対応。
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
    - SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL 環境変数で間隔上書き、デフォルト 60 秒）（src/kabusys/run_monitoring.py）。
    - 監視は環境に関わらず本番 sqlite_path を使用する仕様。
- 発注関連コア
  - OrderRecord: 注文状態マシンと遷移ロジックを実装（src/kabusys/execution/order_record.py）。
    - 明示的な OrderState 列挙、許可遷移テーブル、InvalidStateTransitionError を用意。
    - transition_to() による状態遷移とオプションフィールド更新を提供。
  - OrderManager: 外向き API（作成・送信・同期・キャンセル）を実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id の重複防止ロジック（部分ユニーク制約と DuplicateOrderError）。
    - send_order: クラッシュ安全性を考慮した 2 相永続化戦略（OrderSent を DB に書いてから broker 呼び出し、broker_order_id を先に保存してから状態遷移）。
    - OrderSentPendingError を特別扱い（order_id を保存して OrderSent のまま残す）。
    - sync_order: broker 側状態同期、部分約定の進行はフィールド差分のみ更新。
    - cancel_order: 終端状態のキャンセル禁止チェック（InvalidStateTransitionError）と broker cancel 呼び出し。
  - ExecutionEngine: シグナルループ、push ドレイン、Gate (1/2/3) によるリスクチェック、kill_switch を実装（src/kabusys/execution/execution_engine.py）。
    - kill_switch: 全 active 注文のキャンセル処理（API エラーは警告で継続）。
    - push のハンドリングで broker_order_id→client_order_id 照合、Gate3（ドローダウン）判定、監視 DB へのイベント記録フックを実装。
    - position_entries への書き込み（約定日の次営業日を fill_date に使用）。
  - Broker クライアント類
    - KabuStationClient を追加（src/kabusys/execution/kabu_client.py）
      - httpx を使用した同期 REST クライアント、トークン自動取得・再取得、401 リトライ、429（RateLimit）/5xx ハンドリング。
      - WebSocket push を受け取る stream_push（存在すれば）との統合を想定。
- DB / 監視
  - duckdb と sqlite を併用する設計を導入（分析用に DuckDB、監視/発注履歴に SQLite）。
  - init_monitoring_db による監視テーブル初期化を起動時に保障（both run_execution/run_monitoring）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- .env は Git にコミットしないよう注意喚起を .env テンプレートに記載（config_setup の出力）。

### Notes / 実装上の重要ポイント（運用向け）
- 設定検証 (validate_config)
  - 必須環境変数: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD を確認。
  - KABUSYS_ENV は development/paper_trading/live のいずれかでなければエラー。
  - LOG_LEVEL は WARNING 等の有効値チェック。PyYAML がない場合は YAML の内容検証をスキップする。
  - --strict を使うと警告もエラー扱いになり exit(1) で終了する。
- DB パス
  - DUCKDB_PATH / SQLITE_PATH（監視 DB） の親ディレクトリが存在しない場合は警告。起動時に作成される場合がある。
- Paper trading
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番 DB と分離。
  - PAPER_FILL_MODE は instant/partial/never/reject のいずれか。誤設定は例外。
- Kill switch / PID
  - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START が 1 でなければ起動を拒否（SystemExit）。
  - KILL_FLAG_CLEAR_ON_START=1 のときは起動時に kill.flag を自動で削除する（警告表示）。
- クラッシュ耐性
  - send_order の設計によりクラッシュ中でも Reconciliation により状態復元を試みられるよう broker_order_id を早期永続化している。
- 監視ループ
  - MONITOR_POLL_INTERVAL により監視ポーリング間隔を調整可能。1 未満や不正な値はデフォルト（60 秒）にフォールバック。

もしリリース／変更履歴の粒度をさらに細かく分けたい、あるいは日付や既知の issue/PR 番号を付与したい場合は指示してください。