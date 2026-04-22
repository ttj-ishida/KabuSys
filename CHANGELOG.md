CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、SemVer を想定します。

## [Unreleased]
- 今後の変更予定。

## [0.1.0] - 2026-04-22
最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装。

### Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 設定・環境変数管理
  - Settings クラスを実装し、環境変数経由でアプリケーション設定を取得可能に。
  - 多数のプロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE 関連、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ、監視しきい値など）。
  - 環境値の検証を実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の検証で不正値は ValueError を発生）。
  - 自動 .env 読み込み機構を実装（検出ルール: プロジェクトルート = .git または pyproject.toml）。優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env ファイル読み込みの保護機能: OS 環境変数は protected として上書きされない。

- .env パーサー / ローダ
  - export KEY=val 形式をサポート。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、空行・コメント行の無視など、堅牢な行単位パースを実装。

- 設定ウィザード CLI
  - kabusys.config_setup モジュールで対話式ウィザードを実装。
  - 各項目の説明、デフォルト、選択肢、機密値のマスク表示、既存 .env の読み込みおよび上書き動作をサポート。
  - .env ファイル書き出し機能（書式化されたヘッダコメントを含む）を提供。
  - ユーザーによる確認プロンプトとキャンセル処理を実装。

- 設定検証 CLI
  - kabusys.validate_config モジュールで起動前設定検証 CLI を実装。
  - 必須/任意の環境変数チェック、プレースホルダ値検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml ファイルの存在・パース検証（PyYAML があれば安全にパース）。
  - --strict フラグで警告を失敗扱いにするオプション。
  - 検証結果を INFO/WARNING/ERROR に分類して出力し、終了コードを適切に設定。

- 実行用スクリプト
  - run_execution.py: ExecutionEngine を用いた発注エンジンの起動スクリプトを追加。
    - paper_trading 時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出（stop_requested.flag）を実装。
  - run_monitoring.py: SystemMonitor ポーリングループの起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔変更（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は常に本番 sqlite_path を使用（環境に依らず）。

- Execution エンジンと関連コンポーネント
  - ExecutionEngine を実装（シグナル読み込み、発注ループ、push ドレインループ、セッション管理）。
    - 発注ウィンドウ（既定: 8:50-9:10）と市場クローズ（既定: 15:30）に基づく実行フロー。
    - WebSocket push 処理のための別スレッド（broker が stream_push を提供する場合）。
    - PID 書き込み / kill.flag の検査（KILL_FLAG_CLEAR_ON_START による起動時クリアオプション）。
    - セッション中のリコンシリエーション起動フック（Reconciler 統合）。
  - _process_signals()
    - シグナル読み取り（DuckDB）→ Gate 1（シグナルレベル検査）→ Gate 2（実行レベルの検査, レート制限, リトライ）→ 発注の流れを実装。
    - size_multiplier 適用（BUY のみ、最小単位 100）と 0 の場合スキップ。
    - 発注成功・保留・失敗に応じたログ・リスクメトリクス更新。
    - 発注時に position_entries テーブルへの記録（fill_date は翌営業日）/ ON CONFLICT 処理。
    - 発注レイテンシを監視 DB に記録（MonitoringDB 統合）。
  - Push 処理
    - push payload から OrderID を抽出し、broker_order_id に基づく注文同期（sync_order）を行う。
    - push 発生時にも Gate 3（ドローダウン監視）を評価して必要なら kill_switch を発動。

- 注文周りのロジック
  - OrderRecord: 注文状態（OrderState enum）と状態遷移ロジックを実装。
    - 許可される状態遷移表を定義。
    - transition_to() による遷移検証と更新・タイムスタンプ自動更新。
    - InvalidStateTransitionError を導入。
  - OrderManager: 外向き API（create_order, send_order, sync_order, cancel_order）を実装。
    - DuplicateOrderError を導入（同一 signal_id の active 注文重複を防止）。
    - create_order は UUID を client_order_id として採番し、DB 整合性（部分ユニークインデックス違反）を DuplicateOrderError に変換。
    - send_order はクラッシュ耐性を意識した 2 相永続化パターンを採用（OrderSent に更新 → broker 呼び出し → broker_order_id を先に DB に保存 → OrderAccepted へ遷移）。
      - OrderRejectedError、OrderSentPendingError を適切に処理（pending は broker_order_id を保存して OrderSent のまま残す）。
    - sync_order は broker の状態取得により部分約定や状態遷移を反映する。OrderSent→Filled/Partial の場合は一時的に OrderAccepted を経由して遷移。
    - cancel_order は終端状態のキャンセル不可チェックと broker cancel 呼び出しを行う。

- ブローカークライアント（kabuステーション用）
  - KabuStationClient を実装（httpx 同期クライアント利用）。
    - トークン管理（遅延初期化・401 時の再取得と一回再試行）を実装。
    - レスポンスの JSON パース失敗を BrokerAPIError に変換。
    - HTTP 429 を RateLimitError として扱う、5xx をサーバーエラーとして BrokerAPIError を送出。
    - 内部で kabu ステーションの状態コードを "open"/"partial"/"filled"/"cancelled"/"rejected" にマップするルールを実装。
    - タイムアウト / ネットワークエラーを明確な例外に変換。

- 監視関連
  - monitoring_db.init_monitoring_db の初期化呼び出しを run_monitoring/run_execution に追加して監視テーブルの存在を保証。
  - ExecutionEngine 等から MonitoringDB を使用して発注イベント（Sent 等）をログ可能。

- ユーティリティ
  - logging_setup と process_priority の利用箇所を追加し、起動時のロギング初期化とプロセス優先度設定を行う。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- .env の注意喚起: .env は絶対に Git にコミットしないことを .env 生成ヘッダで明記。

### Notes / Implementation details
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動化を抑制可能。
- Monitoring は KABUSYS_ENV に関係なく常に本番用の sqlite_path を使用する設計（監視は常に本番 DB を見ることが意図）。
- ExecutionEngine のセッションはテスト用に _process_signals() と _drain_push_queue() を直接呼び出すことで短絡できる。
- PAPER_TRADING モードでは発注は MockBrokerClient を用いる想定（BrokerClientFactory を使用して切替）。
- 一部モジュールは外部ライブラリ（PyYAML, httpx, websocket, duckdb, sqlite3 等）に依存。PyYAML 未導入時は validate_config で YAML 検証がスキップされる旨を警告。

---

著者注: この CHANGELOG は与えられたコードベースの実装内容から推測して作成しています。実際のリリース履歴やコミット単位の変更点はリポジトリのコミット履歴を参照してください。