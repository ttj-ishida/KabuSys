# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」準拠です。  
リリース日付はソース内の __version__ と現在の日付に基づきます。

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージ初期実装（KabuSys 自動売買システムの最初の公開版）。
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境設定管理
  - .env の自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（src/kabusys/config.py）。
  - .env と .env.local の読み込み優先度をサポート（OS 環境変数を保護する仕組みを導入）。
  - .env のパースを堅牢化:
    - export KEY=val 形式対応、クォート（シングル/ダブル）の内部エスケープ処理、行内コメントの取扱いなど（src/kabusys/config.py::_parse_env_line）。
  - Settings クラスを提供し、環境変数からアプリケーション設定を取得するプロパティ群を実装（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、しきい値等）（src/kabusys/config.py）。
  - PAPER_FILL_MODE の有効値検証（instant/partial/never/reject）等、各種値検証を実装。

- 環境設定ウィザード CLI
  - 対話式ウィザードで .env を作成・更新するツールを追加（python -m kabusys.config_setup）。既存 .env 読み込み、シークレットマスク表示、選択肢/デフォルト対応、保存確認を含む（src/kabusys/config_setup.py）。
  - .env への書き込みテンプレートを実装（機密情報はマスク表示し、.env を Git にコミットしない注意を記載）。

- 設定検証 CLI
  - .env と config/*.yaml の起動前検証ツールを追加（python -m kabusys.validate_config）。
  - 必須環境変数チェック、環境（KABUSYS_ENV）/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml ファイル存在チェックおよび PyYAML があればパース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知・KILL_FLAG_CLEAR_ON_START チェック）を実装。
  - 警告を失敗扱いにする --strict オプションをサポート。終了コードで FAIL/OK を返す（src/kabusys/validate_config.py）。

- 実行スクリプト
  - 実行エンジン起動スクリプト run_execution を実装（python -m kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出（data/stop_requested.flag）、監視 DB 初期化を行う（src/kabusys/run_execution.py）。
  - 監視ループ起動スクリプト run_monitoring を実装（python -m kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）、停止フラグで正常終了、監視用 DB 接続を行う（src/kabusys/run_monitoring.py）。

- Execution / Order 関連コア実装
  - OrderRecord（状態機械）を実装。状態列挙 OrderState と許容遷移を定義し、transition_to による遷移および入力検証を提供（src/kabusys/execution/order_record.py）。
  - OrderManager を実装。signal_id に対する重複注文回避（部分ユニーク制約の扱い）、create/send/sync/cancel のフローと例外ハンドリング（DuplicateOrderError / OrderRejectedError / OrderSentPendingError 等）を実装（src/kabusys/execution/order_manager.py）。
    - send_order はクラッシュ耐性を考慮した2相的永続化手順を実装（OrderSent を先に永続化 → API 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）。
    - sync_order は broker からの状態取得を反映。部分約定の進行は差分更新で扱う。
    - cancel_order は終端状態チェック後に broker cancel を呼び、Cancelled に遷移。
  - ExecutionEngine を実装。シグナル処理（8:50–9:10）と WebSocket push ドレインループ（9:10–15:30）、kill.flag チェック、PID ファイル管理、リコンシリエーション開始時の実行、WebSocket push の受信と処理、Gate1/2/3 によるリスク制御、position_entries への約定記録などを実装（src/kabusys/execution/execution_engine.py）。
    - Gate2 のレート制限リトライ（最大 3 回）や CIRCUIT_BREAKER 発生時のシグナルループ停止ロジックを含む。
    - kill_switch は全 active 注文をキャンセルし、ループを停止する仕組みを提供。

- Broker / KabuStation クライアント
  - KabuStation REST API クライアントを実装（httpx ベース）。トークン取得／自動再取得、401 リトライ、429 レート制限、500 系エラーの扱いを実装。JSON パース失敗は BrokerAPIError に変換（src/kabusys/execution/kabu_client.py）。
  - WebSocket 受信（push）を想定した stream_push 用コールバック受入れに対応。

- データベース・監視
  - DuckDB と SQLite を併用する設計を採用。監視用テーブル初期化ヘルパーを使用（init_monitoring_db を呼び出す箇所を追加）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 機密情報の取り扱いに関する注意:
  - .env は絶対に Git にコミットしないことを .env テンプレートに明記（src/kabusys/config_setup.py）。

---

注: 各モジュール内にはさらに細かなログ記録、例外変換、クラッシュ回復を意識した実装（OrderSentPendingError の伝播、Reconciliation での復旧設計など）が含まれます。詳細は各ファイルの docstring/coments を参照してください。