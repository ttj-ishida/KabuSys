CHANGELOG
=========

このファイルは Keep a Changelog の形式に従って作成されています。  
主な変更点・追加機能を日本語でまとめています。

## [0.1.0] - 2026-04-23

### Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。

- 環境/設定管理
  - 環境変数/設定読み込みモジュール (kabusys.config) を追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサは export 形式・クォートされた値（バックスラッシュエスケープ対応）・インラインコメント処理に対応。
    - _require() による必須環境変数チェックとエラーメッセージ整備。
    - Settings クラスで各種設定値を型安全に取得（J-Quants トークン、kabu API パスワード、DB パス、paper trading の分離設定、PID/KILL フラグ、閾値など）。
    - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。

  - 対話式設定ウィザード CLI (kabusys.config_setup) を追加。
    - .env の初期作成・更新を対話形式で支援。選択肢・デフォルト・シークレット入力に対応。
    - 生成される .env のテンプレートは .env を絶対に Git にコミットしない旨の注記付き。
    - 生成後に validate_config を案内。

  - 起動前設定検証ツール CLI (kabusys.validate_config) を追加。
    - 必須/任意環境変数の存在、プレースホルダ値の検出、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス親ディレクトリ存在確認。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。PyYAML 未インストール時はスキップして警告。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START のリスク指摘）。
    - --strict オプションで警告を FAIL（exit code 1） として扱う。

- 実行スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - paper_trading モード時は paper_trading 用の SQLite DB に分離して接続。
    - プロセス優先度設定、PID ファイル書き込み、停止フラグ検出（data/stop_requested.flag）に対応。
    - DuckDB / SQLite 接続、監視 DB 初期化を実施。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用。

- 発注/注文管理コンポーネント
  - OrderRecord (kabusys.execution.order_record)
    - 注文状態列挙 OrderState と許容遷移を明示。
    - transition_to による状態遷移検証（不正遷移は InvalidStateTransitionError 発生）。
    - 時刻は UTC で管理、オプションフィールドの安全な更新を提供。

  - OrderManager (kabusys.execution.order_manager)
    - signal_id 単位での重複発注検出 (DuplicateOrderError)。
    - create_order / send_order / sync_order / cancel_order の安全な実装。
      - send_order はクラッシュ耐性を考慮した二相的永続化（OrderSent を先にコミットし、broker_order_id を保存してから OrderAccepted に遷移）。
      - OrderRejectedError / OrderSentPendingError の扱いを明確化。
      - sync_order は broker の状態を照合し、部分約定や状態遷移を反映（必要に応じて中間状態 OrderAccepted を経由）。
      - cancel_order はキャンセル不可状態を弾くロジックを実装。

  - ExecutionEngine (kabusys.execution.execution_engine)
    - Signal Queue Pull 型発注エンジンを実装。
    - 発注ウィンドウ（デフォルト 8:50-9:10）やセッション終了時刻（15:30）に従った実行フロー。
    - Gate 1 (シグナルレベル)、Gate 2 (エグゼキューション・レート制御、リトライ/サーキットブレーカー対応)、Gate 3 (ポートフォリオドローダウン監視) のリスク検査を導入。Gate 3 NG 時は kill_switch 発動。
    - ブローカーへの発注フローにおけるレイテンシ計測・監視DBへのログ記録（MonitoringDB が提供されている場合）。
    - websocket push（kabu push）処理用のスレッドと内部キュー（_push_queue）を実装。push 受信時に sync_order を呼び出す。
    - kill_switch 実装により全 active 注文のキャンセルとループ停止を実現。
    - 発注成功時は次回取引日の position_entries の登録処理を行い、BUY と SELL の扱いを分離。

- ブローカークライアント
  - KabuStationClient (kabusys.execution.kabu_client)
    - httpx を用いた同期 REST クライアント実装。将来的に httpx.AsyncClient に差し替え可能な設計。
    - トークン取得の遅延初期化と 401 に対する自動再取得・1回リトライを実装。
    - レスポンス JSON パースエラー・タイムアウト・ネットワークエラーを BrokerAPIError 等にマッピング。
    - 429 に対して RateLimitError を返すなど HTTP ステータスに基づくエラー分類。
    - websocket（stream_push）を通じた push 受信用インターフェースを想定。

- リスク管理・監視関連（実装の統合）
  - RiskManager, Reconciler, OrderRepository 等と ExecutionEngine の連携を実装（ExecutionEngine 側で利用）。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を run_* スクリプトで利用。

### Changed
- （初版のため該当なし）

### Fixed
- .env パーサを強化：クォート内部のバックスラッシュエスケープ対応、インラインコメントの扱い改善により現実的な .env の記述を正しく解釈可能に。

### Security
- config_setup にて生成される .env のヘッダに「.env を絶対に Git にコミットしないこと」を明記。機密情報（トークン/パスワード）はシークレット入力として扱う仕組みを用意。

### Migration notes
- なし（初回リリース）。既存環境からの導入時は .env（.env.local）をプロジェクトルートに配置し、python -m kabusys.validate_config で事前検証してください。

---

今後の予定（参考）
- BrokerAPI の追加実装（モックや他ブローカー対応）、詳細な監視/アラート強化、より細かなテストカバレッジの追加。