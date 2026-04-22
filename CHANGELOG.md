# Changelog

すべての重要な変更を本ファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-22

初期リリース。KabuSys のコア設定管理、実行エンジン、発注フロー、監視、及び関連 CLI を追加しました。

### Added
- 基本パッケージ定義
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）
    - 環境変数から設定を取得するプロパティ群（J-Quants トークン、kabu API パスワード、DB パス、PID/Kill flag、しきい値等）
    - 値検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の妥当性チェック）
    - paper_trading 用 DB パスの分離（PAPER_TRADING_SQLITE_PATH）
    - 自動 .env 読み込み機能
      - プロジェクトルートを .git または pyproject.toml を基準に探索
      - 読み込み順: OS 環境変数 > .env.local > .env
      - OS 環境変数を保護するための上書き制御
      - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
    - .env ファイルパーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理に対応）

- 設定ウィザード CLI
  - config_setup（src/kabusys/config_setup.py）
    - 対話式で .env を初期作成 / 更新
    - シークレット値は表示をマスク
    - デフォルト値・選択肢・説明を提供
    - 生成される .env ファイルには注意書きを付加（.env を Git コミットしない旨）
    - 保存前に設定確認とキャンセル可能

- 設定検証 CLI
  - validate_config（src/kabusys/validate_config.py）
    - .env および config/*.yaml の設定不備を起動前に検出
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック
    - DB パス（DUCKDB_PATH, SQLITE_PATH）の親ディレクトリ存在チェック
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証
    - KABUSYS_ENV=live の際の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意）
    - --strict オプションで警告を失敗扱いにする機能

- 実行スクリプト
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine 起動用スクリプト
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離
    - プロセス優先度設定、PID 管理、停止フラグ検出を実装
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず本番 sqlite_path を使用

- 発注 / 実行コア
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態列挙（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）
    - 状態遷移ルールと検証、InvalidStateTransitionError
    - 不変のビジネスロジックとして DB には触れない実装
  - OrderManager（src/kabusys/execution/order_manager.py）
    - create_order / send_order / sync_order / cancel_order の外向き API 実装
    - DuplicateOrderError を導入（同一 signal_id の active 注文重複検出）
    - send_order における二相的な永続化設計
      - OrderSent に遷移して commit → broker 呼び出し → broker_order_id を先に永続化 → OrderAccepted に遷移
      - OrderSentPendingError（broker が注文番号を返すが確定しないケース）を扱い、OrderSent のまま永続化して呼び出し元へ伝搬
      - OrderRejectedError をハンドリングして Rejected に遷移
    - sync_order による broker 照合（状態同期）と部分約定のフィールド更新
    - cancel_order は終端状態では拒否し、それ以外は broker API を呼んで Cancelled へ遷移
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - Signal Queue 型の発注エンジン実装（シグナル処理窓: 8:50-9:10、push ドレイン: 9:10-15:30）
    - リコンシリエーション呼び出し（起動時、Reconciler がある場合）
    - kill.flag の起動時チェック（KILL_FLAG_CLEAR_ON_START の挙動サポート）
    - PID ファイル書き出し / 削除
    - WebSocket スレッド（broker が stream_push を持つ場合のみ）
    - Gate 1/2/3 によるリスクチェックフロー
      - Gate1: シグナル単位チェック（size_multiplier の処理、BUY のみ適用）
      - Gate2: 実行レベル検査（レート制限、Circuit Breaker の検知と停止）
      - Gate3: ドローダウン監視（push ハンドリング後に現在ポートフォリオ評価で kill_switch 発動可能）
    - position_entries の DuckDB への記録ロジック（約定日を翌営業日で記録）
    - 監視DB（MonitoringDB）がある場合のトレードイベント記録
    - 外部からの stop() を kill_switch() の公開エイリアスとして提供
  - Broker 関連
    - KabuStationClient（src/kabusys/execution/kabu_client.py）
      - httpx を用いた同期 REST クライアント実装
      - トークン取得の遅延初期化と 401 時の再取得 + リトライ処理
      - レスポンス JSON のパースエラー・タイムアウト・ネットワークエラーを BrokerAPIError に変換
      - 429 レスポンスは RateLimitError として扱う
      - kabu ステータスコード → 内部ステータス文字列マッピングを実装
    - BrokerAPIProtocol, OrderRequest/Response, OrderStatus 等のインターフェースを利用（実装の分離）

- 監視関連
  - monitoring_db / SystemMonitor の初期化を行う呼び出しを run_* スクリプトに追加
  - 監視ループは stop_requested.flag の検知で終了

- ユーティリティ
  - PID / 停止フラグ / プロセス優先度設定、ログセットアップ（setup_logging）を使用するよう構成

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Security
- .env ファイルは Git にコミットしないよう注意書きを出力（config_setup が生成する .env に明記）
- config_setup の表示ではシークレット値をマスク表示

### Notes / Implementation details
- YAML のパース検証は PyYAML がインストールされている場合のみ実行され、未インストール時は警告を出してスキップする設計
- validate_config は --strict を指定すると警告も failure として exit code 1 を返す
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（run_monitoring の設計方針）
- ExecutionEngine は paper_trading モード時に paper 用 SQLite を使用して本番 DB と分離
- Order の永続化戦略はクラッシュ耐性（OrderSent の中間状態や broker_order_id の先出し保存）を考慮している
- .env パースは export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント等に対応している

---

将来的な変更は本ファイルの上部に追記してください。