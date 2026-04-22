# Changelog

すべての注目すべき変更を記載します。This project adheres to "Keep a Changelog" の方針に準拠します。

フォーマット:
- 変更はセマンティックに分類（Added / Changed / Fixed / Deprecated / Removed / Security）
- 各リリースはバージョンと日付を記載

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-22
初回リリース。KabuSys の基盤となる設定管理、実行エンジン、監視、発注関連のコア機能を実装しました。

### Added
- 基本パッケージ情報
  - パッケージのバージョン情報を `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として追加。

- 環境変数・設定管理
  - Settings クラスを実装（`src/kabusys/config.py`）。
    - 環境変数読み取り API（J-Quants / kabu API / LINE / DB パス等）。
    - env 値の自動読み込み: プロジェクトルート（.git や pyproject.toml を基準）から `.env` / `.env.local` を読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - 必須変数未設定時に明示的に例外を投げる `_require()`。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH や監視用の閾値など多数のプロパティを提供。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - .env 解析ロジックを実装（クォート・エスケープ・コメント処理に対応）。

- 設定ウィザード CLI
  - 対話式ウィザードで `.env` を作成/更新する `config_setup` CLI を追加（`src/kabusys/config_setup.py`）。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン 等）。
    - 既存 `.env` の読み込み、入力プロンプト（シークレットマスク、選択肢、デフォルト）、ファイル書き出しロジック。
    - 保存確認の流れと注意書きを出力。

- 設定検証ツール
  - 起動前に環境設定を検証する CLI `validate_config` を追加（`src/kabusys/validate_config.py`）。
    - 必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性検証。
    - DUCKDB/SQLite の親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml の存在確認と PyYAML があればパース検証（PyYAML 未インストール時はスキップして警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の注意）。
    - --strict フラグで警告も失敗扱いにできる。

- 実行用スクリプト（プロセス立ち上げ）
  - ExecutionEngine 起動スクリプト `run_execution.py` を追加。
    - プロセス優先度設定、PID/停止フラグ管理、DB 接続（paper_trading 時は専用 SQLite を使用）、DuckDB 接続、モニタリング DB 初期化を行う。
    - エンジンをスレッドで実行し、停止フラグ検知で安全に停止する仕組み。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化、DuckDB 接続、停止フラグ検知、例外時のログ出力保護。

- ExecutionEngine と発注ワークフロー
  - ExecutionEngine（`src/kabusys/execution/execution_engine.py`）を実装。
    - シグナル処理（8:50-9:10）と push ドレイン（9:10-15:30）のセッション制御。
    - WebSocket push を別スレッドで受け取り内部キューに格納。
    - シグナル読み出しは DuckDB（signals と portfolio_targets を JOIN）から行う。
    - ポジション記録（position_entries）の更新処理を追加（発注成功時に次取引日をエントリ／クローズとして記録）。
    - kill_switch による全注文キャンセル機能と stop エイリアス。

- 注文状態と管理
  - OrderRecord（`src/kabusys/execution/order_record.py`）: 純粋な状態モデルと遷移ロジックを実装。
    - OrderState 列挙、許可遷移テーブル、InvalidStateTransitionError、updated_at 自動更新等。
  - OrderManager（`src/kabusys/execution/order_manager.py`）: DB（OrderRepository）と OrderRecord を組み合わせた外向き API を実装。
    - create_order（重複シグナル検出、UUID 発番、DB 保存）。
    - send_order（2相永続化戦略: OrderSent を先に DB 保存→broker 呼び出し→broker_order_id を保存→OrderAccepted に遷移）。
    - send_order の失敗ハンドリング（OrderRejectedError, OrderSentPendingError の取り扱い）。
    - sync_order（broker からのステータス取得と状態同期、部分約定での filled_qty/avg_fill_price 更新）。
    - cancel_order（キャンセル不可能な状態の検出と Broker API 呼び出し）。
    - DuplicateOrderError の定義と DB 制約違反の変換。

- Broker クライアント
  - kabu station REST クライアント実装（`src/kabusys/execution/kabu_client.py`）。
    - httpx を使った同期クライアント、トークン取得・自動再取得（401 による再試行）、レスポンス JSON パース保護。
    - API レート制限（429）の判定と RateLimitError 投出。
    - WebSocket push サポート（stream_push 経由）を想定した設計。

- モニタリング関連
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）と SystemMonitor の起動呼び出し（監視スクリプトから利用）。
  - ExecutionEngine / 発注フローで発生したイベントを監視 DB にログするための呼び出しポイントを追加（監視書込失敗は警告で続行）。

- リスク管理・再調整（Reconciliation）設計
  - RiskManager / RiskConfig を用いた Gate1/Gate2/Gate3 のチェックフローを ExecutionEngine に統合。
  - Reconciler を用いた起動時リコンシリエーション機構（起動時に呼び出され、同期結果をログ出力）。

- ユーティリティ
  - PID ファイル書き込み・削除（起動時/終了時）。
  - stop_requested.flag / kill.flag を用いた外部制御フロー。
  - process_priority / logging_setup 等のユーティリティと組み合わせた起動処理。

### Changed
- 初回リリースにつき該当なし。

### Fixed
- 初回リリースにつき該当なし（実装時の安全策を多数追加: 例: OrderSent の永続化順序、pending 状態の明確化、部分約定更新の冪等性確保等）。

### Security
- 本番環境向けの注意喚起を実装（validate_config / config_setup にて KABUSYS_ENV=live の警告、.env を絶対に Git にコミットしない旨の文言）。

---

注:
- 上記はソースコードの内容から推測して記載した変更履歴です。実際の履歴（コミットやリリースノート）が存在する場合はそれに合わせて調整してください。