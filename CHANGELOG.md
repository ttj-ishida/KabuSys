# CHANGELOG

すべての注目すべき変更をここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-22

### 追加
- 初期リリース: KabuSys 日本株自動売買システムの基本コンポーネントを実装。
- 設定関連
  - 環境変数 / 設定管理モジュールを追加（kabusys.config）
    - .env ファイルの自動読み込み（プロジェクトルート検出: .git または pyproject.toml）
    - 読み込み優先順: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
    - .env のパースはシングル/ダブルクォート、エスケープ、インラインコメントに対応
    - _load_env_file による上書き制御（protected により OS 環境変数を保護）
  - Settings クラスを提供（settings インスタンス）
    - 必須/オプション設定の getters を提供（例: jquants_refresh_token、kabu_api_password、duckdb_path 等）
    - 環境値の妥当性検査（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などで不正値は ValueError）
    - paper_trading 用の専用 DB パス（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）
    - kill flag / PID /閾値（CPU/MEM/DISK）に関する設定を追加
- CLI ツール
  - 環境設定ウィザード（kabusys.config_setup）
    - 対話形式で .env の初期作成・更新を支援
    - シークレット項目は表示時にマスク（****）
    - デフォルト値・選択肢・説明を備えたウィザード項目群を実装
    - .env の書き込みを行う _write_env を実装
  - 設定検証ツール（kabusys.validate_config）
    - .env と config/*.yaml の存在・基本整合性チェックを事前実行
    - 必須環境変数未設定はエラー、プレースホルダは警告
    - KABUSYS_ENV / LOG_LEVEL / DB パス等のチェック、--strict オプションで警告を FAIL 扱いに可能
    - PyYAML がない場合は YAML 検証をスキップし警告を出力
- 実行 / 監視エントリポイント
  - run_execution（ExecutionEngine 起動スクリプト）
    - paper_trading 時は MockBroker を使用し、paper_trading 用 SQLite を利用して本番 DB から分離
    - プロセス優先度設定、停止フラグ検知、PID ファイル管理を実装
  - run_monitoring（SystemMonitor ポーリングループ）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視用 SQLite / DuckDB 接続、停止フラグによる優雅終了
- 発注周り（execution パッケージ）
  - OrderRecord（状態マシン）を追加
    - OrderState 列挙型と許可遷移テーブルを定義
    - transition_to による遷移検証・自動 updated_at 更新
    - InvalidStateTransitionError を定義
  - OrderRepository / OrderManager を組み合わせた外向き API（OrderManager）
    - create_order / send_order / sync_order / cancel_order を実装
    - send_order は「OrderCreated → OrderSent」（永続化）→ broker 呼出 → broker_order_id 永続化 → OrderAccepted という二相永続化でクラッシュ耐性を確保
    - OrderSentPendingError（ブローカーが注文番号を発行したが約定しないケース）への対応
    - DuplicateOrderError を導入して同一 signal_id の多重発注を禁止
    - sync_order はブローカー状態に基づき部分約定の進展や状態同期を実施
    - cancel_order は終端状態に対するチェック・ブローカー呼出・状態遷移を実装
  - ExecutionEngine（Signal Queue Pull 型発注エンジン）
    - シグナル処理ループ（8:50-9:10）と WebSocket push ドレインループ（9:10-15:30）を実装
    - Gate 1/2/3 による複数段階のリスク管理（シグナル単位・エグゼキューション単位・ポートフォリオ絵評価）
    - kill_flag の検査と kill_switch による全 active 注文キャンセル
    - position_entries への約定記録（BUY は entry を、SELL は sell_date を更新）
    - push notification をキューに入れて処理する仕組みを実装
    - 監視データベース（MonitoringDB）への発注イベントログ出力に対応
- ブローカークライアント
  - KabuStationClient（kabu station REST API 実装）
    - httpx を用いた同期的な API 呼び出しとトークン管理（遅延取得と 401 リトライ）
    - レスポンス JSON パース失敗等は BrokerAPIError に変換
    - HTTP 429 を RateLimitError に変換する等のエラー処理
    - WebSocket push の受信（stream_push）を前提とした設計（存在しない場合は WebSocket スレッドをスキップ）
    - kabu ステータスコード → 内部ステータスのマッピングを実装

### 変更
- なし（初回リリースのため "変更" セクションはありません）。

### 修正
- なし（初回リリース）。

### 破壊的変更
- Settings の env/log_level/paper_fill_mode 等で不正値が与えられると ValueError を送出します。既存運用で環境値が不正な場合、起動時に例外が発生します。validate_config を使って事前検証することを推奨します。

### セキュリティ
- config_setup の対話表示でシークレット項目（トークン・パスワード）はマスク表示（****）するようにした。
- .env は「絶対に Git にコミットしないこと」とヘッダに明記して出力。

### 注意 / マイグレーションノート
- 自動的に .env を読み込む挙動はプロジェクトルートの検出に依存します（.git または pyproject.toml を基準）。配布後や特殊なディレクトリ構成では自動ロードが無効になる可能性があります。テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading モードは本番 DB（SQLITE_PATH）と完全に分離するため、PAPER_TRADING_SQLITE_PATH（environment: PAPER_TRADING_SQLITE_PATH）を使用できます（Settings.paper_sqlite_path）。
- config/*.yaml の内容検証には PyYAML が必要です。インストールされていない場合は validate_config が YAML パース検証をスキップして警告を出します。
- 本番稼働時は KABUSYS_ENV=live のときに LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を必ず確認してください。validate_config が警告を出します。

---

今後の予定（未実装・改善案）
- 非同期 httpx.AsyncClient による非同期化対応
- 追加の BrokerClient 実装（モック以外）
- 詳細な監視/メトリクスの拡充
- 単体テストの整備と CI での validate_config 実行

（以上）