# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
このファイルは、ソースコードの内容から実装された機能・修正点を推測して作成しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（互換性のある場合）
- Fixed: バグ修正（互換性のある場合）
- Security / Removed / Deprecated: 必要に応じて記載

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - yyyy-mm-dd
初回公開リリース。主要な機能と実装の概要を記載します。

### Added
- 設定管理
  - Settings クラスを実装。環境変数ベースで設定を提供（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン等）。
  - .env ファイルの自動ロード機能を実装。読み込み順序は OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロード無効化可能。
  - .env パースの堅牢化: export 構文対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなど。

- セットアップ / 検証用 CLI
  - 対話式の環境設定ウィザード（kabusys.config_setup）を追加。`.env` の初期作成・更新を支援。
  - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス・親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検証（PyYAML がある場合）等を実施。
  - validate_config に `--strict` オプションを追加し、警告も失敗（exit 1）として扱うモードを提供。
  - validate_config はプレースホルダ値（`_here`, `your_value` など）や live 環境向けの追加警告を出す。

- 実行スクリプト
  - run_execution スクリプトを追加。ExecutionEngine を起動するためのプロセスエントリポイント。
    - paper_trading モード用に専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - PID ファイル書き出し、停止フラグ（data/stop_requested.flag）検知、プロセス優先度設定（高）をサポート。
  - run_monitoring スクリプトを追加。SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - Monitoring は実行環境にかかわらず本番用 sqlite_path を使用する設計。

- 発注・注文管理
  - OrderRecord データモデルと状態遷移（OrderState）を実装。許可される遷移のみ受け入れ、無効な遷移は InvalidStateTransitionError を送出。
  - OrderManager を実装:
    - create_order: signal_id に対する重複検出（部分ユニークインデックス / DB 競合を含む）と OrderCreated レコード生成。
    - send_order: クラッシュ耐性を考慮した 2 相永続化戦略を実装（OrderSent に遷移して commit → broker 呼び出し → broker_order_id を先に永続化 → OrderAccepted に遷移）。OrderRejectedError / OrderSentPendingError の扱いを実装。
    - sync_order: broker 側の状態取得によりローカル状態を同期。部分約定の進行時は filled_qty / avg_fill_price の更新を行う。OrderSent→Filled/PartialFill の場合は OrderAccepted を中継して遷移。
    - cancel_order: 終端状態の判定とキャンセル処理。必要に応じて broker の cancel_order を呼ぶ。
  - DuplicateOrderError 定義（同一 signal_id の active 注文重複の検出）。

- ExecutionEngine（発注エンジン）
  - Signal Queue Pull 型の発注エンジンを追加。シグナル処理ウィンドウ（デフォルト 8:50-9:10）と push ドレインループ（9:10-15:30）を実装。
  - Gate ベースのリスクチェック（Gate1: シグナルレベル、Gate2: エグゼキューションレベル（レート制御／サーキットブレーカー）、Gate3: ドローダウン監視）を組み込み、NG 時の挙動（スキップ/kill_switch 発動）を実装。
  - size_multiplier の処理（買いのみ適用、100株単位切り捨て）や発注遅延計測（latency_ms）の監視 DB ログ登録（MonitoringDB が渡された場合）をサポート。
  - WebSocket push の受信（broker が stream_push を提供する場合）を別スレッドで行い、push を受け取って sync_order と Gate3 評価を行う。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（httpx 同期クライアント）。トークンの遅延取得、401 発生時のトークン再取得と 1 回リトライ、429（Rate Limit）や 5xx のエラーを専用例外に変換する。
  - WebSocket（push）受信用の stream_push 対応を想定した設計（stream_push を持たない場合は警告を出してスキップ）。

- 監視・DB 初期化
  - monitoring_db の初期化用 init_monitoring_db の呼び出しを実装（監視テーブルが存在することを保証）。
  - DuckDB と SQLite 両方の接続管理を実装（分析用と監視用の使い分け）。

- ロギング・プロセス周辺ユーティリティ
  - ログ設定セットアップ（setup_logging）とプロセス優先度設定（set_process_priority）を利用する起動フローを採用。
  - kill.flag による起動拒否や起動時自動クリア（KILL_FLAG_CLEAR_ON_START=1）をサポート。

### Changed
- プロジェクトルート検出
  - config モジュール内で .git または pyproject.toml を探索してプロジェクトルートを特定する方式を採用。これによりカレントワーキングディレクトリに依存せずに .env 自動ロードが動作。

### Fixed
- 例外/障害耐性の強化
  - send_order フローで中途クラッシュしても再同期（Reconciliation）で回復可能な状態を残すように永続化の順序を工夫。
  - validate_config で PyYAML 未インストール時に YAML 内容検証をスキップして警告を出すようにし、環境に依らず検証が進むようにした。
  - MONITOR_POLL_INTERVAL の値が不正（0 以下や非数）の場合にデフォルトへフォールバックする保護処理を追加。

### Security
- 機密情報取り扱いの留意点
  - .env の README コメントに「.env を Git にコミットしないこと」を明示。
  - config_setup のシークレット項目は表示時にマスクするなどの配慮を実装。

---

既存のコードから推測してまとめています。日付（yyyy-mm-dd）は実際のリリース日に合わせて更新してください。追加機能・実装の詳細や API の仕様変更がある場合は、対応する項目を追記してください。