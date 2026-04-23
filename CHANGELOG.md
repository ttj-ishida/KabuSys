# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-23

初回リリース。自動売買システム KabuSys の基本設定管理、実行エンジン、監視、発注ロジック、および kabuステーション API クライアントを導入します。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 設定管理
  - Settings クラスを実装（kabusys.config）。
    - 環境変数 / .env ファイルから設定を読み込み、型変換や妥当性チェックを提供。
    - J-Quants / kabu API / LINE / DB パス / PID/Kill flag 関連など主要設定をプロパティとして公開。
    - paper_trading に関連する専用設定（paper_sqlite_path / paper_fill_mode）を追加。
    - env/log level の検証で不正値は ValueError を送出する仕様。
  - 自動 .env ロード機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

- .env パース/ロード機能
  - 複数形式の .env 行パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - .env/.env.local の読み込み順序と override/protected の挙動を明示。

- 設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで .env を生成・更新する CLI を追加。
  - 主要設定項目一覧、デフォルト値、シークレット表示マスク、選択肢サポートを実装。
  - .env ファイルテンプレートを書き出す `_write_env` を実装。出力時に注意書きを含む。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前に .env と config/*.yaml の不備を検出する CLI を追加。
  - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DBパスの親ディレクトリ存在チェックを実装。
  - PyYAML があれば config/*.yaml をパースして内容検証を実行。未インストール時はスキップして警告。
  - `--strict` オプションで警告を FAIL として exit(1) を返すモードをサポート。

- 実行スクリプト
  - `run_execution.py`：ExecutionEngine の起動スクリプトを追加。
    - paper_trading 時は専用 SQLite（paper_sqlite_path）を使用し、本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出を実装。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境にかかわらず本番 sqlite_path を使用する設計。
    - ポーリング間隔を `MONITOR_POLL_INTERVAL` で上書き可能。

- 実行エンジン / 発注ロジック
  - ExecutionEngine を実装（kabusys.execution.execution_engine）。
    - シグナル処理ウィンドウ（デフォルト 8:50-9:10）と push ドレイン（9:10-15:30）を含むセッションモデル。
    - kill.flag の検査、PID ファイル管理、WebSocket push の受信とキュー処理、position_entries への記録ロジックを実装。
    - Gate1/2/3 のリスクゲートを統合（RiskManager インタフェースと連携）。
    - 発注成功/保留/失敗時のハンドリングと監視 DB ロギング（レイテンシ計測）を実装。

  - OrderRecord（状態マシンのデータモデル）を実装（kabusys.execution.order_record）。
    - 状態列挙型 OrderState と許可遷移マップを定義。
    - transition_to による遷移検証とタイムスタンプ更新。
    - 不正遷移時に InvalidStateTransitionError を送出。

  - OrderManager を実装（kabusys.execution.order_manager）。
    - create_order: signal_id ごとの重複チェック、UUID による client_order_id 発番、DB 保存、DuplicateOrderError の定義。
    - send_order: 2相永続化を意識した安全な発注フローを実装（OrderCreated→OrderSent 永続化 → broker 呼び出し → broker_order_id 保存 → OrderAccepted へ遷移）。
      - OrderRejectedError, OrderSentPendingError の扱いを明確化。
    - sync_order: broker 側ステータス取得からの同期ロジック（部分約定の更新含む）。
    - cancel_order: 端状態チェック、broker API 呼び出し、Cancelled への遷移。
    - OrderSentPendingError のサポートにより、発注が pending のケースを DB に残してリコンサイル可能に。

  - 発注フロー上の設計
    - クラッシュ耐性を考慮した状態モデル（OrderSent の永続化タイミングや broker_order_id の先保存等）。
    - Reconciliation（リコンシリエーション）との整合性を考慮した実装（send_order と sync_order の相互補完）。

- broker クライアント（kabu station）
  - KabuStationClient を実装（kabusys.execution.kabu_client）。
    - httpx を使用した同期 REST クライアント。トークン取得・自動再取得ロジックを実装。
    - レスポンス JSON パース例外やネットワーク例外を BrokerAPIError 等に変換。
    - 401 の際は自動でトークン再取得してリトライ、429 は RateLimitError、5xx は BrokerAPIError を返す。
    - kabu station の状態コード → 内部ステータス変換マップを定義。
    - WebSocket (push/stream) 統合のための stream_push の有無をチェックし、未実装時は警告。

- Monitoring / DB 初期化 / Utilities
  - monitoring DB 初期化ヘルパーを呼び出すコードパス（init_monitoring_db）。
  - process priority 設定ユーティリティの利用（set_process_priority）。
  - logging 設定ユーティリティの利用（setup_logging）。
  - run_* スクリプトで sqlite3 / duckdb の接続管理を追加。

### 変更 (Changed)
- .env 取り扱いの挙動
  - .env のパースが堅牢になり、クォーテーションやエスケープを考慮して値を正確に読み込むようになった。
  - 自動読み込み時の上書きルール（OS 環境変数保護、.env と .env.local の優先度）を明確化。

- ExecutionEngine の設計
  - シグナル処理と push ドレインを明確に分離し、WebSocket push をキューで処理するモデルにした。
  - kill_switch の実装を Engine 内に集約し、外部停止フラグ発見時に全 active 注文をキャンセルする流れを提供。

### 修正 (Fixed)
- 発注クラッシュ耐性の向上
  - send_order の 2相永続化（OrderSent 前後の DB 更新）により、クラッシュ時に broker_order_id が残るケースを扱いやすくした（リコンシリエーションで回復可能）。
  - OrderSentPending の扱いを明確にし、pending 状態での broker_order_id 永続化→呼び出し元に例外伝播の流れを導入。

- 環境検証の強化
  - validate_config にて必須環境変数の未設定をエラー扱いに、プレースホルダ値のままの場合は警告を出力するようにした。
  - KABUSYS_ENV が live の場合の追加チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険値）を追加。

### 破壊的変更 (Breaking Changes)
- Settings のプロパティは不正な値に対して ValueError を送出します（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。既存コードがこれらをキャッチしていない場合、起動時に例外が発生する可能性があります。
- .env 自動ロードの有効化はデフォルトで ON。テストや特殊用途で自動ロードを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

### セキュリティ (Security)
- .env ファイルは機密情報を含むため、生成時のテンプレートに「.env は絶対に Git にコミットしないこと」という注意書きを追加。
- config_setup の対話でシークレット項目はマスク表示しているが、保存される .env 自体はローカルの機密ファイルとして扱う前提。

### その他 / 注意事項
- config/*.yaml の検証は PyYAML がインストールされている場合にのみ行われます。未インストール時は警告を出してスキップします。
- Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用するため、監視データの分離に注意してください。
- run_monitoring のポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能。1秒未満や不正な値はデフォルトにフォールバックします。

---

今後のリリースでは、テストカバレッジの拡充、kabu client の WebSocket 実装強化、非同期対応 (httpx.AsyncClient への移行案)、および詳細な監視・メトリクス記録の追加を検討しています。