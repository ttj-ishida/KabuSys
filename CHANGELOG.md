# Changelog

すべての重要な変更はこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠します。  

※ この CHANGELOG はコードベースの内容から推測して生成しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-22
初回リリース。日本株自動売買フレームワーク「KabuSys」の基盤機能を実装。

### Added
- 全体
  - パッケージ初期バージョンを定義（__version__ = "0.1.0"）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - 環境変数の自動読み込み機能を実装（.env / .env.local、OS 環境変数を保護）。
  - 自動読み込みを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

- 設定・CLI
  - Settings クラスを実装し、環境変数から各種設定値を取得するプロパティを提供。
    - 必須の取得メソッド（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）は未設定時に ValueError を送出。
    - パス設定（DUCKDB_PATH, SQLITE_PATH など）は Path に変換して expanduser() を実行。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE などの値検証を実装（無効値は例外）。
    - kill flag, PID ファイルパス、閾値（CPU/MEM/DISK/MEMORY）等の監視関連設定を実装。
  - .env の対話式作成・更新ウィザード（kabusys.config_setup）を実装。
    - 項目一覧、デフォルト値、選択肢、シークレットマスク表示機能を提供。
    - 既存 .env の読み込みと Enter による既存値継承。
    - 書き込みテンプレート（.env）を生成。`.env を絶対に Git にコミットしない`旨のヘッダを付与。
    - 実行例: python -m kabusys.config_setup

  - 設定検証 CLI（kabusys.validate_config）を実装。
    - .env と config/*.yaml の設定不備を起動前に検出。
    - 必須/任意環境変数チェック、プレースホルダ検出（"_here" / "your_value"）を実装。
    - KABUSYS_ENV/LOG_LEVEL の妥当性チェック。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック。
    - config/*.yaml の存在チェックおよび PyYAML があれば YAML のパース検証（PyYAML 未導入時はスキップして警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告など）。
    - --strict オプションで警告も FAIL 扱い（exit(1)）。
    - 実行例: python -m kabusys.validate_config

- 実行スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - ExecutionEngine の起動フロー（DB 接続、Broker クライアント生成、コンポーネント組立、セッションスレッド起動）を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（設定で上書き可）を使用して本番 DB と分離。
    - stop_requested.flag による停止検知、PID ファイル管理、プロセス優先度設定、リソースクリーンアップを実装。
    - 実行例: python -m kabusys.run_execution

  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。
    - SystemMonitor のポーリングループを実行（デフォルト 60 秒、MONITOR_POLL_INTERVAL 環境変数で上書き可能）。
    - 監視は環境に関わらず本番 sqlite_path を使用する旨を明記。
    - 停止フラグ検知、例外時のログ記録、DB クローズ処理を実装。
    - 実行例: python -m kabusys.run_monitoring

- 実行コア: 発注・状態管理
  - OrderRecord（状態マシン）のデータモデルを実装（order_record.py）。
    - 状態遷移（OrderCreated → OrderSent → OrderAccepted → PartialFill/Filled → Closed 等）と遷移許可テーブルを実装。
    - transition_to() で遷移検証、updated_at の自動更新、オプションフィールド更新を行う。
    - 不正遷移時は InvalidStateTransitionError を送出。
  - OrderManager を実装（order_manager.py）。
    - create_order: signal_id に対する重複（アクティブ注文）チェックと DB 保存。UUID の client_order_id 付与。
    - send_order: 二相永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted を永続化）によりクラッシュ耐性を確保。
      - OrderRejectedError、OrderSentPendingError の扱い（pending は broker_order_id を保存して OrderSent のまま残す）を実装。
    - sync_order: broker 側のステータス照合 → 状態更新（差分更新も考慮）を実装。OrderSent→Filled/PartialFill のケースで OrderAccepted を経由する補正ロジックあり。
    - cancel_order: 終端状態はキャンセル不可とし、broker API 呼び出し後に Cancelled に遷移。
    - DuplicateOrderError を定義して signal_id 単位の重複を表現。
    - DB 側の UNIQUE 制約違反を DuplicateOrderError に変換する扱いを実装（orders.signal_id に関する例外変換）。

  - ExecutionEngine を実装（execution_engine.py）。
    - シグナル処理ループ（_process_signals）:
      - size_multiplier 適用（買いのみ）、量を100株単位に丸める等のロジック。
      - Gate 1（シグナルレベル）/ Gate 2（エグゼキューションレベル: レート制限, Circuit Breaker）/ Gate 3（ドローダウン監視）の仕組みを想定した呼び出し点を実装。
      - RiskManager との連携（check_signal / check_execution / check_metrics）、API 成功／失敗の記録。
      - 発注送信時のレイテンシ計測と監視DBへの記録（監視DB提供時）。
      - 発注成功時に position_entries テーブルへエントリを記録（BUY/SELL の取り扱いを明記）。
      - DuplicateOrderError のハンドリングで重複スキップ。
    - push ドレイン処理（_drain_push_queue / _handle_push）:
      - broker 側の push (OrderID) を受け取り、broker_order_id から client_order_id を照合して sync_order を呼ぶ。
      - push を受けた際にも Gate 3（ドローダウン）チェックを行い NG なら kill_switch を発動。
    - kill_switch(): 全 active 注文のキャンセル、全ループ停止処理を実装（外部呼び出し stop()）。
    - WebSocket ワーカースレッドの起動（broker が stream_push を持たない場合はスキップ）。
    - セッション開始時のリコンシリエーション呼び出し（reconciler が与えられた場合）と kill.flag の扱い（KILL_FLAG_CLEAR_ON_START に応じて自動クリア可能）。

- ブローカー API クライアント
  - KabuStationClient を実装（kabu_client.py）。
    - httpx を用いた同期 REST クライアント。
    - トークンの遅延取得・再取得を実装（_get_token、401 時は再取得してリトライ）。
    - レスポンス JSON パース失敗やネットワーク例外を BrokerAPIError に変換。
    - 429 は RateLimitError として扱う。
    - websocket / stream_push を使った push ハンドリングとの統合を想定。
    - トークン更新/再試行や各種 HTTP エラー処理を実装しているため、信頼性を高める。

- 監視・DB 初期化
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を run_monitoring/run_execution で使用（実装は別ファイル）。
  - run_monitoring と run_execution の両方で duckdb と sqlite の接続を確立してクリーンにクローズする処理を実装。

### Changed
- （初版のため変更履歴なし）

### Fixed
- （初版のため修正履歴なし）

### Security
- .env を Git にコミットしない旨を明記したテンプレートを生成するようにした（config_setup）。

### Notes / Migration
- .env は絶対にリポジトリにコミットしないでください。config_setup により安全にローカルで作成できます。
- 本番運用時は KABUSYS_ENV=live に設定することで追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認等）が有効になります。KILL_FLAG_CLEAR_ON_START はデフォルト 0（自動クリアしない）を推奨します。
- validate_config により起動前チェックが可能です。可能であれば CI やデプロイ前に --strict モードでチェックすることを推奨します。
- YAML ファイルのパース検証は PyYAML の導入が必要です（未インストール時は警告してスキップします）。
- KabuStationClient は httpx、websocket 等の依存が必要です。実運用前に依存パッケージを揃えてください。

--- 

今後の予定（例）
- Reconciler / RiskManager / OrderRepository の更なる堅牢化テストとドキュメント整備
- 非同期化（async/await）サポート（httpx.AsyncClient など）
- より詳細な監視イベント・メトリクスの充実
- テストカバレッジの追加および CI ワークフローでの validate_config の自動実行

（以上）