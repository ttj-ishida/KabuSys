# Changelog

すべての重要な変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

全体指針:
- 形式: https://keepachangelog.com/ja/1.0.0/
- バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]
（今後の変更をここに記載）

## [0.1.0] - 2026-04-23
初回リリース。プロジェクトのコア機能一式を実装。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__="0.1.0"）。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - 環境変数から各種設定を取得するプロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - env / log_level の値検証。無効値は ValueError を発生させる。
    - .env 自動ロード（プロジェクトルートの .env → .env.local、OS 環境変数優先）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーを実装（クォート、エスケープ、export 形式、コメント処理に対応）。

- 設定ウィザード CLI
  - 対話式ウィザードで .env を作成/更新するスクリプトを追加（src/kabusys/config_setup.py）。
    - 多数の設定項目定義（実行環境、API トークン、DB パス、LINE トークン、ログレベル、Kill Switch 設定など）。
    - 既存 .env 読み込み、マスク表示（シークレットキー）、入力検証、.env の書き出し機能を提供。

- 設定検証 CLI
  - 起動前に環境設定を検証する CLI を追加（src/kabusys/validate_config.py）。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml ファイルの存在・パース検証（PyYAML 未インストール時はスキップ）など。
    - --strict オプションにより警告も FAIL として扱う。

- 実行・監視用エントリポイント
  - run_execution スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine の起動フロー（プロセス優先度設定、DB 接続、Broker クライアント生成、ExecutionEngine 実行、停止フラグ検知）。
    - paper_trading 環境では paper_trading 用 SQLite を使用して本番 DB を分離。
  - run_monitoring スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループと停止フラグの監視、MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き。

- Execution サブシステム（発注エンジン）
  - ExecutionEngine を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理ウィンドウ（8:50-9:10）と push ドレインループ（9:10-15:30）をサポート。
    - kill_switch（全 active 注文のキャンセルとループ停止）を実装。
    - WebSocket push ワーカーを持ち、push を受け _push_queue に投入して処理。
    - position_entries の書き込み（DuckDB を使用）や発注遅延計測の監視DB反映を組み込み。
  - OrderRecord（状態マシン）を実装（src/kabusys/execution/order_record.py）。
    - 明確な OrderState 列挙、および許可遷移テーブルを提供。
    - 状態遷移検証と updated_at 自動更新、関連フィールド更新ロジックを実装。
    - 不正遷移時に InvalidStateTransitionError を raise。
  - OrderManager を実装（src/kabusys/execution/order_manager.py）。
    - create_order / send_order / sync_order / cancel_order の API を提供。
    - create_order は signal_id の重複検知（DuplicateOrderError）。
    - send_order はクラッシュ対策として OrderSent の永続化→ブローカー呼出→broker_order_id 永続化→OrderAccepted 更新の 2 相永続化戦略を採用。OrderRejectedError / OrderSentPendingError の扱いを実装。
    - sync_order はブローカー状態を取得して DB と同期し、部分約定時のフィールド更新を適切に処理。
    - cancel_order は取りうる終端状態でキャンセル不可を検出し、実際のブローカーキャンセル呼出と DB 更新を行う。
  - Reconciler / RiskManager などの組み合わせでリコンシリエーションや Gate チェックを行う構成に対応（ExecutionEngine から使用）。

- Broker クライアント
  - KabuStationClient 実装（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 REST クライアント。トークン取得（遅延初期化）、401 に対する再取得と 1 回リトライ、429=RateLimit の特殊扱い、タイムアウト/ネットワーク例外の BrokerAPIError 変換などを実装。
    - kabu station の注文状態コードを内部ステータスにマッピング。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を利用して SQLite の監視テーブルを確実に初期化する処理を run scripts として組み込み。

- プロセス周りのユーティリティ連携
  - process_priority セット（高優先度設定）や logging setup と統合（setup_logging, set_process_priority を使用）。

### Changed
- （初回リリースのため、該当なし）

### Fixed
- （初回リリースのため、該当なし）

### Notes / 実装上の注意
- config/*.yaml の内容検証は PyYAML の存在に依存。PyYAML がインストールされていない場合は警告を出してパース検証をスキップする。
- .env の自動読み込みはプロジェクトルートの検出に依存（.git または pyproject.toml を探索）。見つからない場合は自動ロードをスキップする。
- ExecutionEngine の時間ベースの挙動（発注ウィンドウ等）はローカル環境の時刻に依存するため、テスト時は直接メソッドを呼ぶことが可能。
- PAPER_FILL_MODE 等の一部設定は厳格な値検証を行い、不正値で例外を投げる設計になっている。
- kill.flag の取り扱い:
  - 起動時に kill.flag が存在すると基本的に起動を拒否する（KILL_FLAG_CLEAR_ON_START=1 の場合は除く）。
  - 実行中に検出された場合は kill_switch を発動して全 active 注文をキャンセルする。

## 将来の改善候補（コードから推測）
- KabuStationClient の非同期対応（httpx.AsyncClient への差し替え）を容易にするための抽象化強化。
- config/*.yaml のスキーマ検証（PyYAML + JSON Schema 等）導入。
- exec/monitor のユニットテスト用の DI 強化（設定・DB のモックを簡単に差し替えられるように）。
- 複数ブローカー対応や more robust rate-limit handling の拡張。

---

変更・追加の要点はソースコードの実装内容から推測してまとめています。必要であれば各変更点に対応するファイル/関数の参照を付けたより詳細なリリースノートを作成します。