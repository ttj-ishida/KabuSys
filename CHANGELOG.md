# Changelog

すべての重要な変更をここに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-22

### Added
- 初回リリース。KabuSys の基礎機能を実装。
- パッケージメタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 環境変数 / 設定管理
  - Settings クラスを実装し、環境変数経由で各種設定（J-Quants / kabuAPI / LINE / DB パス /監視閾値 / PID/Kill flag など）を取得可能に。
  - .env ファイルの自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。自動ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をサポート。
  - .env のパース機能を強化（export 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応）。
  - `_load_env_file` にて既存 OS 環境を保護する protected 引数を用意し、上書き挙動を制御。
- 対話式設定ウィザード
  - `kabusys.config_setup` モジュールで `.env` の初期生成・更新ウィザードを実装。項目定義（選択肢・デフォルト・シークレット表示等）を内蔵。
  - 生成される `.env` のテンプレートとヘッダコメント（コミット禁止の注意）を出力。
  - 使用例: `python -m kabusys.config_setup`
- 設定検証 CLI
  - `kabusys.validate_config` モジュールで起動前に `.env` と `config/*.yaml` の設定不備を検出する CLI を実装。
  - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML があれば実行）を含む。
  - `--strict` オプションで警告も失敗扱いにできる。
  - 使用例: `python -m kabusys.validate_config`、`--strict` オプション対応。
- 実行用エントリスクリプト
  - `run_execution.py`: ExecutionEngine 起動スクリプトを実装。paper_trading モード時は専用 SQLite（`PAPER_TRADING_SQLITE_PATH`/`data/paper_trading.db`）を使用して本番 DB と分離。
  - `run_monitoring.py`: SystemMonitor ポーリングループ起動スクリプトを実装。`MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は常に本番 sqlite_path を使用。
  - 両スクリプトともプロセス優先度設定、PID/停止フラグ処理、DB 接続（sqlite3 / duckdb）の初期化処理を搭載。
- 注文関連コアロジック
  - OrderRecord: 状態遷移ロジックを持つ純粋なドメインモデルを実装。状態列挙 OrderState と許可遷移表を定義し、不正遷移時に `InvalidStateTransitionError` を送出。
  - OrderManager: データベース上の OrderRepository と BrokerClient を組み合わせ、create/send/sync/cancel の一連の外向き API を実装。
    - create_order: signal_id の重複検出（DB の部分ユニーク制約違反は DuplicateOrderError に変換）。
    - send_order: クラッシュ耐性を考慮した 2 相永続化パターンを採用（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移 等）。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order: broker 側ステータス同期ロジックを実装（部分約定の差分更新、OrderSent→Filled などの間接遷移への対応）。
    - cancel_order: キャンセル不可能状態の検査と broker への取消 API 呼び出し処理。
  - OrderState/ステートマシンに基づく堅牢な状態管理（許可遷移テーブル）。
- ExecutionEngine
  - シグナルプル型発注エンジンを実装（EngineConfig で target_date / 時間帯を管理）。
  - 主な動作:
    - 起動時 Reconciliation 実行（reconciler が提供されていれば）。
    - kill.flag の検査と KILL_FLAG_CLEAR_ON_START に基づく自動クリア挙動。
    - PID ファイル書き出し（ディレクトリ作成含む）。
    - WebSocket push を受け取るバックグラウンドスレッド（broker が stream_push を持つ場合）。
    - シグナル処理（8:50-9:10）と push drain ループ（9:10-15:30）を実装。
    - シグナル処理における Gate 1（シグナルレベル）/ Gate 2（エグゼキューションレベル : レート制限と回避）/ Gate 3（ドローダウン監視）の統合。Gate2 のレート制限でのリトライ・サーキットブレーカー挙動を実装。
    - 発注後の position_entries への書き込み（fill_date を翌営業日に設定）や監視DBへのイベントロギングを組み込み（監視DBが提供されている場合）。
    - kill_switch により全 active 注文をキャンセルする機能。
- ブローカークライアント（kabu）
  - KabuStationClient を実装（同期 httpx を使用）。トークン取得・再取得、自動リトライ（401 の場合）、HTTP 時のエラー種別を BrokerAPIError / RateLimitError 等で扱う。
  - kabu ステータスコード -> 内部ステータス（open/partial/filled/cancelled/rejected）のマッピングを実装。
  - WebSocket (push) 受信経路を想定（別途 stream_push を持つ broker 実装と連携）。
- 監視関連
  - monitoring 用 DB 初期化ヘルパーの呼び出し（init_monitoring_db）を run スクリプトに組み込み。
  - 監視ループでの停止フラグ検出・例外ハンドリングの実装。
- ログ・プロセスユーティリティ
  - setup_logging、set_process_priority などのユーティリティ呼び出しを各 run スクリプトで利用。
- DB ハンドリング
  - sqlite3 と duckdb の接続管理を標準化（起動時に接続 → 終了時にクローズ）。
- ドキュメント的なコード内コメント
  - 多くのモジュールで設計意図・安全性（クラッシュ耐性）・使用例などの説明を詳細に注釈。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

注:
- 実行には依存ライブラリ（httpx、duckdb、PyYAML など）が必要。PyYAML 未インストール時は validate_config の YAML 内容検証をスキップして警告を出す。
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダにも注意書きあり）。