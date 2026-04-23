# CHANGELOG

すべての重要な変更は Keep a Changelog 準拠で記載します。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

全般的な注意
- 文面はソースコード（src/kabusys 以下）から推測してまとめています。実際のコミット履歴ではありません。
- バージョンはパッケージ定義（__version__ = "0.1.0"）に合わせています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-23
初回リリース — 基本的な実行基盤、設定管理、発注エンジン、監視、ブローカークライアントを実装。

### Added
- 環境・設定管理
  - 自動 .env ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export 形式、引用符付き値、エスケープ、インラインコメントの一部に対応（_parse_env_line）。
  - Settings クラスを実装して環境変数を型付きで提供（jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_fill_mode 等）。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の値検証を行い、無効な場合は ValueError を送出。

- 設定支援 CLI
  - 対話式 .env ウィザードを実装（src/kabusys/config_setup.py）。
    - 入力のマスキング（シークレット項目）、選択肢サポート、既存 .env の読み込み・再利用、.env ファイル書き出し機能を提供。
    - 書き出し時のテンプレートと注意文を付与。

- 設定検証 CLI
  - 起動前に環境変数と config/*.yaml を検証するツールを追加（src/kabusys/validate_config.py）。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、PyYAML 有無に基づく YAML パースチェックを実装。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL として扱う挙動をサポート。

- 実行および監視スクリプト
  - 実行 Engine の起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite を使い、本番 DB と分離。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）検出、プロセス優先度設定機能を実装。
  - 監視ループの起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、負値はデフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知によりループ終了、例外時はログ出力して次ポーリングへ復帰。

- 発注ロジック
  - OrderRecord: 状態遷移モデルと検証を実装（src/kabusys/execution/order_record.py）。
    - 明示的な状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可遷移テーブルおよび不正遷移時の InvalidStateTransitionError。
    - transition_to による updated_at 自動更新と関連フィールド更新。
  - OrderManager: 外向け発注 API（create_order / send_order / sync_order / cancel_order）を実装（src/kabusys/execution/order_manager.py）。
    - create_order は signal_id のアクティブ重複を検出して DuplicateOrderError を送出。DB の部分ユニーク制約違反を DuplicateOrderError に変換。
    - send_order はクラッシュ耐性を考えた 2 相永続化戦略を採用（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted）。
    - OrderSentPendingError の扱い（注文番号は得られたが約定しないケース）は保持して呼び出し元へ伝播。
    - sync_order は broker 側の状態を照合してローカル状態を更新。部分約定の進行は差分更新。
    - cancel_order は終端状態のキャンセル不可チェックを行い、broker_order_id があれば API 呼び出しを行って Cancelled に遷移。
    - broker 側状態文字列 -> 内部 OrderState マッピングを定義。

- ExecutionEngine
  - シグナルプル型エンジンを実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理ウィンドウ（デフォルト 8:50–9:10）と push ドレインループ（9:10–15:30）を実装。
    - Gate1（シグナル単位検査）、Gate2（実行レベル検査、レート制限、サーキットブレーカー対応）、Gate3（ドローダウン監視による kill switch）を実装。
    - size_multiplier の適用（BUY のみ）、100株単位での切り捨て。
    - 発注成功/失敗でのリスクマネージャ通知、監視 DB へのトレードイベント記録（monitoring DB が指定された場合）。
    - push 通知の取り込み（_push_queue）、同期処理、ポジション評価に基づく Gate3 チェック。
    - kill_switch は全アクティブ注文のキャンセルを試み、ループ停止を行う。
    - 起動時に kill.flag の存在をチェックし、KILL_FLAG_CLEAR_ON_START に応じて挙動を制御（存在で起動拒否または自動クリア）。
    - PID ファイルの作成・削除を実装（デフォルト path は設定から取得）。

- Broker クライアント（kabu station）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx.Client を用いた同期 REST 実装。
    - トークン取得の遅延初期化と 401 発生時の自動再取得・1 回リトライ。
    - レスポンス JSON パース失敗、タイムアウト、ネットワークエラーを BrokerAPIError 等に変換。
    - HTTP 429 を RateLimitError にマッピング。
    - kabu station の状態コード（1..7）を内部の 'open' / 'partial' / 'filled' / 'cancelled' / 'rejected' 等にマッピング。
    - websocket（push）受信のためのストリーム push のサポート（存在しない場合はスキップする安全化）。

- モニタリング関連
  - 監視 DB 初期化ヘルパー（init_monitoring_db）や SystemMonitor（参照される）を使用して監視データを取る実装（run_monitoring/run_execution から利用）。

- ユーティリティ
  - ログ設定セットアップ、プロセス優先度設定などのユーティリティ関数を利用（setup_logging / set_process_priority）。

### Changed
- 初回リリースのため該当なし（新規実装群）。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- なし。

### Removed
- なし。

### Security
- 機密情報（トークン・パスワード）は対話ウィザードでマスクして扱うよう配慮。
- .env ファイルは絶対にリポジトリにコミットしない旨の注意文を生成。

---

補足（実装上の注意・既知の挙動）
- validate_config は PyYAML が未インストールの場合、YAML 内容検証をスキップして警告を出す（導入時に PyYAML の有無により挙動が変わります）。
- ExecutionEngine の発注フローはクラッシュ耐性を考慮して複数段階で DB を更新しますが、異常系の再同期（Reconciler）を別途動かす想定です。
- Settings の自動 .env 読み込みは OS 環境変数を保護するため .env.local の上書きも OS 環境変数を上書きしない設計になっています。
- KabuStationClient は同期 httpx を使用しており、将来的に非同期化する場合は httpx.AsyncClient に置き換え可能。

もし詳細なコミット単位の CHANGELOG や追加のリリースノートが必要であれば、実際の VCS ログ（git）やリリース方針に基づいてさらに細かく分割して作成します。