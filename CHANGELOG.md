# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。  
このファイルはコードベースから推測して作成した初期の変更履歴です。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-23
初回リリース。システムの主要コンポーネントと運用用 CLI を実装。

### 追加
- 全体
  - パッケージ初期版を追加。パッケージ名: KabuSys、バージョン 0.1.0。
  - メイン機能: 日本株自動売買の Execution エンジン、監視（Monitoring）、設定管理、実行スクリプト、ブローカー API クライアントなど。

- 設定 / 環境
  - 環境変数/設定管理モジュール (src/kabusys/config.py)
    - .env 自動読み込み機能（プロジェクトルートの検出ロジック: .git または pyproject.toml を基準）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。既存 OS 環境変数を保護する仕組みを実装。
    - .env のパースはシングル/ダブルクォート・エスケープ・コメント処理に対応。
    - Settings クラスを提供し、各種環境設定値をプロパティとして取得可能（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値など）。
    - バリデーション: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の有効値チェック。無効な場合は ValueError を送出。

  - 環境設定ウィザード CLI (src/kabusys/config_setup.py)
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 必須項目（J-Quants トークン、kabu API パスワード等）や任意項目（LINE トークン等）を定義。
    - 既存 .env の読み込み・再利用、シークレットマスク表示、選択肢の検証、保存確認を実装。
    - .env を書き出す際に注意書き（Git にコミットしないこと）を明記。

  - 設定検証 CLI (src/kabusys/validate_config.py)
    - .env と config/*.yaml の基本チェックを行う CLI を追加。
    - 必須環境変数 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD) の未設定検出、プレースホルダ値検出。
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）。
    - LOG_LEVEL の妥当性チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - DUCKDB/SQLITE パスの親ディレクトリ存在確認。
    - config/*.yaml の存在確認と PyYAML によるパース確認（PyYAML 未インストール時は警告でスキップ）。
    - KABUSYS_ENV=live の場合は本番用追加チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定など）。
    - CLI オプション --strict を追加（警告も FAIL として exit(1)）。

- 実行スクリプト
  - 実行エンジンスクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine を起動するスクリプトを追加。
    - paper_trading 環境では paper_trading 用の SQLite を使用して本番 DB と分離。
    - 起動時にプロセス優先度を高く設定。
    - stop フラグ（data/stop_requested.flag）による停止検出、PID ファイル管理を実装。

  - 監視ループスクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 未満はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- Execution エンジン本体
  - ExecutionEngine (src/kabusys/execution/execution_engine.py)
    - Signal Queue Pull 型の発注エンジンを実装。
    - シグナル処理ウィンドウ（デフォルト 8:50–9:10）と push ドレインループ（9:10–15:30）を実装。
    - kill.flag による起動拒否/起動時クリアの設定 (KILL_FLAG_CLEAR_ON_START) を考慮。
    - PID ファイル書き出し・削除処理。
    - WebSocket スレッド（broker が stream_push を提供する場合）と push キュー処理。
    - Gate1 (signal-level)、Gate2 (execution-level レート制限・サーキットブレーカー)、Gate3 (ドローダウン監視) のリスクチェック統合。
    - 発注後に position_entries へ約定日（翌営業日）を書き込むロジック（DuckDB を使用）。
    - 発注に関する監視イベントのログ (monitoring_db) を呼び出す仕組み。

- 注文管理 / ブローカー API
  - OrderRecord / 状態遷移モデル (src/kabusys/execution/order_record.py)
    - 注文状態列挙 OrderState と許可遷移テーブルを実装。
    - 不正遷移時に InvalidStateTransitionError を送出。
    - transition_to メソッドで updated_at を自動更新、オプションフィールドの更新に対応。

  - OrderManager (src/kabusys/execution/order_manager.py)
    - DB に依存する OrderRepository と組み合わせて外向き API を提供（create_order, send_order, sync_order, cancel_order）。
    - create_order: 同一 signal_id の active 注文重複チェック（DuplicateOrderError）。
    - send_order: 2 相永続化パターンでクラッシュ安全性を確保（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted へ遷移）。
    - OrderSentPendingError（注文は送信されたが約定しない / pending）を呼び出し元へ伝播する動作。
    - sync_order: broker 側状態を取得して DB と同期（部分約定の増分更新を含む）。
    - cancel_order: キャンセル不可能状態の判定、broker cancel 呼び出し後に Cancelled へ遷移。

  - KabuStationClient（kabuステーション API 実装） (src/kabusys/execution/kabu_client.py)
    - httpx ベースの同期クライアントを実装。将来的な async 対応を見据えた設計。
    - トークン取得の遅延初期化と 401 時の再取得・1回リトライ機構。
    - レスポンス JSON パース失敗、タイムアウト、ネットワークエラーは BrokerAPIError に変換。
    - 429 レスポンスは RateLimitError として扱う。
    - WebSocket / push 受信用に websocket 経由の stream_push を想定（stream_push を持たない broker はスキップ）。

- リスク管理 / リコンシリエーション / 監視
  - RiskManager、Reconciler、MonitoringDB などの呼び出し箇所を実装（インターフェースと統合点）。  
    （詳細実装ファイルは本リリース内に含まれるが、CHANGELOG では主要設計点を列挙）

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリースだが、クラッシュシナリオを考慮した堅牢化を実装）
  - send_order の 2 相永続化により、クラッシュ後の状態復旧（Reconciliation）を考慮。
  - ExecutionEngine の起動時 reonciliation 呼び出しを保護（例外時はログを残してセッション継続）。

### セキュリティ
- .env ファイルは Git にコミットしない旨を README/生成ファイルに明記（config_setup のヘッダに注意書き）。
- .env 読み込み時に OS 環境変数を保護する仕組みを実装（override/ protected パラメータ）。
- KABUSYS_ENV=live の場合に注意喚起や危険な設定（KILL_FLAG_CLEAR_ON_START=1）の警告を出す検証を追加。

### 注意事項 / 運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（validate_config で検出）
- 有効値:
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - PAPER_FILL_MODE: instant | partial | never | reject
- Paper trading:
  - KABUSYS_ENV=paper_trading の場合、Execution は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用し、本番監視 DB と分離される。
- 監視ループは常に本番 sqlite_path を使用する仕様。
- 停止制御:
  - data/stop_requested.flag の存在で run_* スクリプトは優雅に停止する。
  - kill.flag（settings.kill_flag_path）により ExecutionEngine の起動拒否または即時 kill_switch 発動。KILL_FLAG_CLEAR_ON_START=1 なら起動時に自動クリアする。
- ログ・プロセス優先度:
  - 起動時にプロセス優先度を高（"high"）へ設定するユーティリティを呼び出す。
  - setup_logging でアプリ名別ログ設定を行う（monitoring/execution）。

### 既知の制限
- YAML 検証は PyYAML がインストールされている場合のみ行われる（未インストール時は警告でスキップ）。
- KabuStationClient は同期 httpx.Client 実装。将来的な非同期対応は別途。
- 一部のコンポーネント（RiskManager, Reconciler, MonitoringDB 等）はインターフェース中心の組み立てを行っており、外部依存や環境により動作が異なる可能性がある。

---

この CHANGELOG は現行コードベースから推測して作成しています。実際のコミット履歴や注釈がある場合は、それに合わせて更新してください。