# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [0.1.0] - 2026-04-23

### 追加 (Added)
- パッケージ初期リリース。
- 基本情報
  - パッケージ名: KabuSys
  - バージョン: 0.1.0

- 設定管理
  - Settings クラス（kabusys.config）を導入し、環境変数から設定を取得する一貫した API を提供。
  - .env 自動読み込み機能:
    - OS 環境変数 > .env.local > .env の優先順で読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーの実装:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱い。
    - 読み込み時に既存の OS 環境変数の保護（protected）をサポート。

- 設定ウィザード CLI
  - kabusys.config_setup モジュールで対話式ウィザードを実装。
  - .env ファイルの作成・更新を支援。複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 系設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を扱う。
  - シークレット項目はマスク表示、デフォルト値・選択肢をサポート。
  - 生成される .env のテンプレートに注意書きを追加（.env を Git にコミットしない旨）。

- 設定検証 CLI
  - kabusys.validate_config により起動前に設定の妥当性をチェックする CLI を提供。
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の存在チェック、プレースホルダ検出（*_here / your_value）を実装。
  - KABUSYS_ENV、LOG_LEVEL の値検証（有効候補: development / paper_trading / live、LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL）。
  - DB パス（DUCKDB_PATH, SQLITE_PATH）の親ディレクトリ存在確認。
  - config/*.yaml（system_config.yaml 等）の存在確認と、PyYAML インストール有無に応じたパース検証（インストールされていない場合はスキップ）。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険値確認）。
  - --strict オプションで警告を FAIL として exit(1) にする挙動を追加。

- 実行スクリプト
  - run_execution: ExecutionEngine を起動するためのスクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite DB（paper_sqlite_path）を使用して本番 DB と分離。
    - プロセス優先度設定、PID/停止フラグ管理、DB 接続の確立とクリーンアップを実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。
    - Monitoring は実行環境に関係なく本番 sqlite_path を使用する方針。

- 実行エンジン（コア）
  - ExecutionEngine（kabusys.execution.execution_engine）
    - シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を想定したセッション実行。
    - run_session によりリコンシリエーション、kill.flag の検査、PID 書き込み、WebSocket スレッド管理を行う。
    - シグナル読み込みは DuckDB を通じて portfolio_targets と JOIN して取得。
    - 発注フロー:
      - Gate 1: シグナルレベル検査（RiskManager）
      - Gate 2: エグゼキューションレベル検査（レート制限、リトライ）
      - 実際の発注後、position_entries への記録処理
      - 発注時のレイテンシや監視 DB（MonitoringDB）へのログ書き込みを試行（失敗しても発注フロー継続）
    - WebSocket push 受信は broker.stream_push（存在する場合）を利用して payload をキューに投入。
    - push 処理時に sync_order を呼び、Gate 3（ドローダウン監視）でポートフォリオ評価を行い、条件不良時は kill_switch を発動。

- 注文管理関連
  - OrderRecord（kabusys.execution.order_record）
    - 注文状態を列挙した OrderState（created, sent, accepted, partial, filled, closed, cancelled, rejected）と状態遷移ルールを定義。
    - transition_to による遷移検証とタイムスタンプ更新を実装。無効遷移時は InvalidStateTransitionError を raise。
  - OrderManager（kabusys.execution.order_manager）
    - Signal に基づく注文の生成(create_order)、送信(send_order)、同期(sync_order)、取消(cancel_order) の外向け API を実装。
    - DuplicateOrderError を導入して同一 signal_id の重複発注を防止。
    - send_order はクラッシュ安全性を考慮した 2 段階永続化（OrderSent の記録→broker 呼び出し→broker_order_id を先に保存→OrderAccepted へ遷移）を実装。
    - OrderRejectedError, OrderSentPendingError 等の broker 側エラー取り扱いに対応。
    - sync_order は broker のステータスを取得して部分約定/全約定を反映。状態遷移ポリシーに従い適切に更新。

- リスク管理 / 再整合
  - RiskManager（参照実装を参照する形で利用される）を組み込み、Gate1/2/3 の評価により発注制御・kill_switch 発動を行う設計。
  - Reconciler による起動時リコンシリエーション (reconciler.run()) を実行し、現地注文と DB を突合する仕組みを組み込める設計。

- ブローカークライアント
  - KabuStationClient（kabusys.execution.kabu_client）
    - httpx を用いた同期 REST クライアント実装。
    - トークン取得の遅延初期化および 401 時の自動再取得/リトライを実装。
    - レスポンス JSON パース失敗やタイムアウト・ネットワークエラーを BrokerAPIError 等に変換して扱う。
    - HTTP ステータス 429 は RateLimitError として扱うマッピング。
    - kabu station の内部状態コードを内部状態文字列（open/partial/filled/cancelled/rejected）へマッピング。

- 監視（Monitoring）
  - monitoring_db 初期化関数を使用して SQLite 監視 DB の存在を保証。
  - run_monitoring にて SystemMonitor を定期実行するポーリングループを提供（停止フラグ・例外ハンドリングを実装）。

### 変更 (Changed)
- 初回公開のため該当なし。

### 修正 (Fixed)
- 初回公開のため該当なし。

### 既知の注意点 (Notes)
- .env ファイルはセキュリティ上 Git にコミットしないことを強く推奨。
- PyYAML がインストールされていない環境では config/*.yaml の中身検証はスキップされる（validate_config で警告を出します）。
- KabuStationClient は同期クライアント実装。将来の async 対応は httpx.AsyncClient への置換で対応可能。
- PAPER_FILL_MODE や LOG_LEVEL、KABUSYS_ENV 等は Settings 経由で厳格に検証され、不正値だと例外を送出する箇所があるため注意。

---

今後の変更履歴は本ファイルに追記してください。