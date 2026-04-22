# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-22

初期リリース。KabuSys の設定管理、検証、監視・実行ランナー、および発注周りのコア実装を含みます。

### Added
- パッケージ初期バージョンを追加（__version__ = 0.1.0）。
- 環境設定 / 管理
  - Settings クラスを実装し、環境変数から各種設定値（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、KABUSYS_ENV 等）を取得・検証する機能を提供。
  - .env 自動読み込み機能を実装（優先順: OS 環境 > .env.local > .env）。プロジェクトルートは .git / pyproject.toml を探索して特定するため、CWD に依存しない読み込みを実現。
  - .env パースロジックを実装（export 句、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応）。
  - PAPER_FILL_MODE 等一部設定の値検証を実装（不正値は ValueError を発生）。

- 設定ウィザード CLI
  - config_setup.py に対話式ウィザードを実装。対話により .env を初期作成／更新できる。
  - 保存前の確認、シークレット項目のマスク表示、--env-file による出力パス指定に対応。
  - .env の読み書き（既存値の読み込み、ヘッダコメントを付与して書き込み）。

- 設定検証 CLI
  - validate_config.py を実装し、起動前に .env と config/*.yaml の不備を検出可能。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認および PyYAML を使ったパース検証（PyYAML 未インストール時は警告でスキップ）を行う。
  - 出力は INFO/WARNING/ERROR を分けて表示。--strict フラグで警告を FAIL として exit(1) で終了可能。

- 実行・監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。paper_trading モード時は paper_trading 用 SQLite を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。
  - 両スクリプトとも起動時にプロセス優先度を設定し、PID ファイル / 停止フラグを扱う処理を実装。

- 発注系コア
  - OrderRecord: 注文状態を表す State Machine を実装。状態列挙、許可される遷移定義、遷移検証（不正遷移時に InvalidStateTransitionError を発生）およびメタ情報（broker_order_id、約定数量、平均約定価格など）を保持。
  - OrderRepository（参照のみ）と組み合わせる OrderManager を実装。create/send/sync/cancel の外向き API を提供。
    - create_order: signal_id 重複の検出（DB 制約違反やアクティブ注文の検査により DuplicateOrderError を発生）。
    - send_order: 2相永続化戦略を採用（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を保存 → OrderAccepted に遷移）。OrderRejected/OrderSentPending のハンドリングを実装し、クラッシュ時の再生性を考慮。
    - sync_order: broker 側の注文状態を照合してローカル状態を同期。部分約定の進行ではフィールドだけ更新する最適化あり。
    - cancel_order: 取消不可状態の保護（終端状態では InvalidStateTransitionError を発生）と、broker API 呼び出しを経たキャンセル処理を実装。
  - ExecutionEngine: シグナルプル型の発注エンジンを実装。
    - シグナル読み込み（DuckDB）、Gate1（シグナル単位のリスクチェック）、Gate2（実行レベルのレート制御・サーキットブレーカ）、発注、および push ドレインループ（sync + Gate3 ドローダウン監視）を実装。
    - kill_switch 機能により全 active 注文のキャンセルを行う（外部 stop/kill.flag に対応）。KILL_FLAG_CLEAR_ON_START の挙動を尊重。
    - WebSocket push の受信を別スレッドで行い、push をキュー化して同期処理。

- ブローカークライアント
  - KabuStationClient を実装（httpx を使用する同期クライアント）。トークン管理（遅延初期化・401 時の再取得と再試行）、HTTP エラー→独自例外変換、429 による RateLimitError の扱い等を実装。
  - WebSocket push 用に websocket（同期）を利用するインターフェースを想定（stream_push を持つ broker の有無をチェック）。

- DB / 監視連携
  - duckdb と sqlite を組み合わせたデータアクセスを想定。ExecutionEngine / Monitoring で duckdb_conn, sqlite_conn を使用。
  - 監視用 DB 初期化（init_monitoring_db）呼び出しを実装し、監視イベントの記録フックを配置。

- リスク管理連携
  - RiskManager / Reconciler などの外部コンポーネントと統合する設計（実装ファイルは参照）。Gate チェック結果に基づく挙動（サーキットブレーカ、レート制限、ドローダウン検出）を導入。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Removed
- 新規リリースのため該当なし。

### Security
- 現時点で特記事項なし。シークレット（トークン/パスワード）は .env に保持する設計であり、config_setup にも「.env を絶対に Git にコミットしない」旨の注意文を追加。

注意:
- 本 CHANGELOG は提供されたコードベースからの推測を元に作成しています。実際の変更履歴やコミットメッセージがある場合はそれに合わせて更新してください。