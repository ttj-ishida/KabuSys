# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このファイルはコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-04-23
初回公開リリース（推測）。主な機能と実装の概要を記載します。

### 追加（Added）
- パッケージの基本構成
  - パッケージ名: kabusys、バージョン __version__ = 0.1.0
  - モジュール群: data, strategy, execution, monitoring（__all__ に宣言）

- 設定 / 環境変数管理
  - Settings クラスを実装（kabusys.config）
    - 環境変数から各種設定値を取得するプロパティ群（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、PID/kill flag パス、閾値など）
    - env/log_level のバリデーション（有効な値チェック）
    - paper_trading 向けの paper_sqlite_path / paper_fill_mode の取り扱いと検証
    - kill_flag_clear_on_start を bool として読み取る
  - .env 自動ロード機能
    - プロジェクトルート（.git または pyproject.toml）を探索して .env を自動読み込み
    - 読み込み優先順位: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env パーサーの実装（引用符、エスケープ、# コメント処理、export プレフィックス対応）

- 対話式設定ウィザード
  - kabusys.config_setup: .env の初期作成 / 更新を支援する CLI（run_wizard/ main）
  - 設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）
  - シークレットのマスク表示、選択肢サポート、既存値の読み込みと Enter で継承
  - .env 書き出しテンプレート（コメント付き、Git へコミットしない旨の注意）

- 設定検証ツール
  - kabusys.validate_config: .env と config/*.yaml を起動前に検証する CLI
    - 必須/任意環境変数チェック
    - プレースホルダ値検出（"_here"/"your_value"）
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、live 環境での注意喚起
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック
    - config/*.yaml の存在確認と PyYAML を用いたパース検証（PyYAML 未インストール時は警告スキップ）
    - --strict オプションで警告も失敗扱いにして exit(1)
    - 結果を INFO/WARNING/ERROR で出力

- 実行/監視スクリプト
  - run_execution: ExecutionEngine 起動スクリプト（スレッドでエンジン実行、PID 書き込み、kill flag 処理）
    - paper_trading の場合は専用 SQLite（paper_trading.db）を使用して本番 DB と分離
    - DuckDB と SQLite の接続確立、監視テーブル初期化呼び出し
    - プロセス優先度設定（utils.process_priority）
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
    - Monitoring は環境にかかわらず本番 sqlite_path を使用
    - stop_requested.flag による終了検知

- Execution（発注）サブシステム
  - ExecutionEngine（kabusys.execution.execution_engine）
    - セッションライフサイクル管理（signal_send_start / signal_send_end / market_close）
    - WebSocket push の受信用スレッド実装（_websocket_worker、stream_push を持たない broker の場合はスキップ）
    - シグナル処理ループ（_process_signals）
      - size_multiplier の適用（BUY のみ）
      - Gate 1（シグナルレベル）／Gate 2（エグゼキューションレベル、レート制限）／Gate 3（ドローダウン監視）の導入
      - 発注前のリスクチェック（RiskManager と連携）
      - 発注時の latency 計測、監視DB へのログ送信（MonitoringDB を使用可能な場合）
      - position_entries への約定予定日の登録（DuckDB を使用）
    - kill_switch による全 active 注文のキャンセル処理（OrderManager 経由）
    - PID ファイルの管理、kill.flag の扱い（KILL_FLAG_CLEAR_ON_START による自動クリアのオプション）

  - OrderRecord（状態マシン、kabusys.execution.order_record）
    - 注文状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）
    - 許可遷移テーブルと transition_to 実装（不正遷移で InvalidStateTransitionError を raise）
    - 追加情報の更新（broker_order_id, filled_qty, avg_fill_price, error_message）

  - OrderManager（kabusys.execution.order_manager）
    - create_order: signal_id の重複チェック（DB とトランザクション整合を考慮）
      - DuplicateOrderError の導入（signal_id の部分ユニーク検査）
    - send_order: 2 相永続化パターン
      - Step1: OrderSent に遷移して永続化（クラッシュ耐性のため broker 呼び出し前に commit）
      - broker 呼び出し後、broker_order_id を先に保存し、次に OrderAccepted に遷移して保存
      - OrderRejectedError による Rejected 遷移
      - OrderSentPendingError（order_id 発行されたが約定しない）を特別扱いして broker_order_id を保存した上で例外を再スロー（Reconciliation 対象）
    - sync_order: broker 側ステータス取得 -> 内部状態へ同期（部分約定の進行では直接フィールド更新）
    - cancel_order: 取消可能かチェックし、broker に cancel を投げた後に Cancelled に遷移
    - ステータスマッピング（"open"/"partial"/"filled"/"cancelled"/"rejected" -> OrderState）

  - Broker クライアント
    - KabuStationClient（kabusys.execution.kabu_client）
      - httpx を用いた同期 REST クライアント実装
      - トークン取得の遅延初期化と 401 リトライロジック（トークン再取得 -> 1 回リトライ）
      - HTTP ステータスに応じた例外振り分け（401/429/5xx -> BrokerAPIError / RateLimitError）
      - kabu station の注文状態コード -> 内部ステータスへのマッピング

- 監視関連
  - Monitoring の初期化処理（init_monitoring_db の呼び出し）
  - ExecutionEngine / Monitoring スクリプトでの監視DB書き込み箇所（log_trade_event 等を通じて監視情報を残す設計）

### 変更（Changed）
- （初回リリースのため該当なしと推測）

### 修正（Fixed）
- （初回リリースのため該当なしと推測）

### 廃止（Deprecated）
- （初回リリースのため該当なしと推測）

### 削除（Removed）
- （初回リリースのため該当なしと推測）

### セキュリティ（Security）
- .env ファイルは「絶対に Git にコミットしないこと」と明示している点を含め、秘密情報は .env に保存する設計。ただし実運用では更なるシークレット管理（Vault 等）を推奨。

---

注: 本 CHANGELOG は提供されたソースコードの内容から実装意図・仕様を推測して作成しています。実際のリリースノートや変更履歴とは異なる場合があります。必要であれば、リポジトリのコミット履歴やリリースタグに基づいてより正確な CHANGELOG を作成します。