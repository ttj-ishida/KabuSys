# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトはセマンティックバージョニングに従います。  

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 初期リリースを公開。
- 設定管理:
  - Settings クラスを導入し、環境変数からアプリケーション設定を取得可能に。
  - .env/.env.local の自動読み込み機能を実装（OS 環境変数を保護する保護キー機能付き）。
  - .env のパース機能を強化：`export KEY=val`、シングル/ダブルクォート値、バックスラッシュエスケープ、インラインコメント処理に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
  - 設定プロパティ（duckdb/sqlite パス、PID/Kill flag パス、閾値、paper trading 関連、ログレベル等）を定義。
  - PAPER_FILL_MODE の検証（有効値チェック）を実装。

- 設定ウィザード:
  - `kabusys.config_setup` に対話式 CLI ウィザードを追加し、.env の初期作成・更新を支援。
  - 保存テンプレート（.env 生成フォーマット）を実装。機密値は表示をマスク。

- 設定検証 CLI:
  - `kabusys.validate_config` に設定検証ツールを追加。
  - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パス親ディレクトリ存在チェック、config/*.yaml 存在と YAML パース（PyYAML インストール時）を実施。
  - プレースホルダ値検出（例: 値が "your_value" や "_here" 終端）と警告表示。
  - `--strict` フラグで警告を FAIL（exit 1）として扱うオプションを追加。

- 実行スクリプト:
  - `run_execution.py` を追加。ExecutionEngine を起動するエントリポイントを提供。
    - paper_trading モードでは paper_trading 用 SQLite を使用し、本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、stop フラグ検知、kill_flag 起動時挙動（KILL_FLAG_CLEAR_ON_START による自動クリア）を実装。
  - `run_monitoring.py` を追加。SystemMonitor のポーリングループを起動するスクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、無効値時はデフォルトにフォールバック）。
    - 監視用 SQLite は環境にかかわらず本番 sqlite_path を使用。

- 発注エンジンと関連コンポーネント:
  - ExecutionEngine を実装。シグナル読み込み、Gate1/2/3 によるリスクチェック、WebSocket push ドレイン、セッションスケジュール（8:50-9:10/9:10-15:30）をサポート。
  - EngineConfig を定義し、ターゲット日付や時間帯を設定可能に。
  - OrderRecord（状態遷移を管理する純粋ビジネスロジック）を実装。OrderState 列挙型と許容遷移テーブル、InvalidStateTransitionError を定義。
  - OrderManager を実装。DB（OrderRepository）との連携、create/send/sync/cancel 操作を提供。
    - create_order は signal_id の重複を検出して DuplicateOrderError を返す。
    - send_order はクラッシュ耐性を考慮した 2 段階永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）を実装。
    - OrderSentPendingError（注文番号が発行されたが約定しないケース）を適切に扱う。
    - sync_order は broker 側の状態照合を行い、部分約定の進行等を反映する。
    - cancel_order はキャンセル不可能状態のチェックと broker へのキャンセル呼び出しを行う。

- ブローカークライアント:
  - KabuStationClient を実装（httpx を利用する同期クライアント）。
    - トークン取得の遅延初期化と 401 時のトークン再取得リトライを実装。
    - send_order / cancel_order / get_order_status 等の API 呼び出しを実装。
    - レスポンス JSON パース失敗や HTTP エラーは適切に BrokerAPIError / RateLimitError / OrderRejectedError に変換。
    - 発注時に成行注文なら Price=0 を強制する安全策を実装。

- その他ユーティリティ:
  - process_priority 設定、ログセットアップなど運用ヘルパーを利用する設計を導入。
  - DuckDB を分析用に使用。ExecutionEngine とモジュール間での DuckDB 接続受け渡しをサポート。

### 変更 (Changed)
- なし（初版のため該当なし）。

### 修正 (Fixed)
- なし（初版のため該当なし）。

### 破壊的変更 (Removed)
- なし。

### セキュリティ (Security)
- .env を絶対に Git にコミットしないことを README/生成テンプレート等で明示（.env ファイルヘッダに注意書きを記載）。

---

注記:
- 本リリースは設計上の多くの運用上の安全策（クラッシュ時の状態回復を考慮した永続化手順、kill-switch、reconciliation への配慮等）を含みます。開発・本番での運用の際は .env の機密情報管理と KABUSYS_ENV の設定に十分ご注意ください。