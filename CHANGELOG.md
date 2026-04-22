# CHANGELOG

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 初回リリース
リリース日: 未設定

### 追加
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装。
  - package バージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。

- 設定関連
  - Settings クラス（src/kabusys/config.py）を導入し、環境変数から型変換・検証された設定値を提供。
    - J-Quants / kabu API / LINE / DB /監視 /システム関連のプロパティを提供（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, pid_file_path, kill_flag_path, cpu_threshold_pct など）。
    - env（KABUSYS_ENV）と log_level の妥当性チェックを行い、不正値では ValueError を送出。
    - PAPER_FILL_MODE の許容値検証（"instant","partial","never","reject"）を実装。
    - paper_trading 環境用に paper_sqlite_path を分離。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - OS 側の環境変数を保護するための挙動を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの扱い等を考慮して堅牢にパース。

- 設定ウィザード CLI
  - python -m kabusys.config_setup による対話式ウィザード（src/kabusys/config_setup.py）を追加。
    - 必須 / 任意 / secret / 選択肢付き項目を定義して対話的に .env を生成・更新。
    - 既存 .env の読み込みと Enter による既存値再利用に対応。
    - シークレット項目は表示時にマスク。
    - 作成される .env のテンプレートに説明コメントを付与（Git にコミットしない旨の注意を含む）。
    - プロンプト中断時の安全な挙動（中断で保存しない）を実装。

- 設定検証 CLI
  - python -m kabusys.validate_config による設定検証ツール（src/kabusys/validate_config.py）を追加。
    - 必須環境変数の存在確認、プレースホルダ値チェック（*_here / your_value などで警告）。
    - KABUSYS_ENV, LOG_LEVEL の妥当性チェック（許容値一覧で検証）。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認および（PyYAML がインストールされていれば）YAML パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE トークン/ユーザーID / KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにして exit(1) を返す。

- 実行スクリプト
  - run_execution（src/kabusys/run_execution.py）:
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - プロセス優先度を上げる処理を最初に実行（set_process_priority）。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。
  - run_monitoring（src/kabusys/run_monitoring.py）:
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視 DB は環境無関係）。

- 注文・約定処理（Execution / Broker）
  - OrderRecord（src/kabusys/execution/order_record.py）:
    - 注文状態列挙 OrderState と許可遷移の定義。
    - transition_to による遷移検証と updated_at 自動更新。
    - 不正遷移時は InvalidStateTransitionError を発生。
  - OrderManager（src/kabusys/execution/order_manager.py）:
    - create_order: signal_id に対する重複注文検出（部分ユニーク索引 / DB 制約を踏まえた DuplicateOrderError）。
    - send_order: クラッシュ安全性を考慮した 2 相永続化フローを実装。
      - OrderCreated → OrderSent を永続化してから broker API 呼び出し。
      - broker_order_id を先にコミット（state は Sent のまま）、その後 OrderAccepted に遷移してコミット。
      - OrderRejectedError / OrderSentPendingError を適切に扱う（pending は broker_order_id を保存した上で OrderSent のまま残す）。
      - その他の例外は捕捉せず OrderSent のまま残すことで不確定注文の検出を可能に。
    - sync_order: broker 側のステータスを取得してローカル状態を同期（status → OrderState マップを適用）。部分約定の進捗はフィールド更新で対応。
    - cancel_order: 終端状態ではキャンセル不可として InvalidStateTransitionError を送出。broker_order_id がある場合は broker 側で cancel_order を呼ぶ。
    - Cancel 不可の状態セット（Filled を含む）を明確化。

  - ExecutionEngine（src/kabusys/execution/execution_engine.py）:
    - Signal Queue Pull 型の発注エンジンを実装。
    - セッションの時間区切り: シグナル処理（8:50-9:10）→ push ドレイン（9:10-15:30）。
    - kill.flag の検査・KILL_FLAG_CLEAR_ON_START 動作（設定に応じて起動時にクリア or 起動拒否）。
    - PID ファイル管理（書き込み・削除）。
    - WebSocket スレッドによる push 受信と _push_queue への投入、ドレイン時に sync_order を実行。
    - 発注フローにおける 3 つの Gate（Gate1: signal-level、Gate2: execution-level (rate limit/circuit breaker)、Gate3: ドローダウン監視）を導入。Gate2 はリトライロジック（最大 3 回）を持つ。
    - 発注成功/保留/失敗時のログ・リスク管理（risk_manager.record_api_success / record_api_error）。
    - 発注時の約定日（fill_date）記録処理（duckdb に position_entries を挿入/更新）。
    - 発注イベントを MonitoringDB にログとして残す（monitoring_db が渡されている場合）。
    - kill_switch(): 全 active 注文をキャンセルしてループ停止する処理を公開（stop() はエイリアス）。

  - Broker クライアント（kabu station 実装、src/kabusys/execution/kabu_client.py）
    - KabuStationClient を実装（同期 httpx クライアント + token 管理）。
    - token の遅延取得と 401 時の自動再取得ロジックを実装。
    - HTTP レスポンスの JSON パース失敗やタイムアウト/ネットワークエラーを BrokerAPIError に変換。
    - 429 (rate limit) を RateLimitError に変換。
    - websocket push 受信機構へのフック（stream_push）を想定した設計。
    - kabu ステータスコード → 内部ステータス ("open","partial","filled","cancelled","rejected") マッピングを実装。

- 監視関連
  - monitoring 側に対する初期化処理（init_monitoring_db）や SystemMonitor の起動ロジック（run_monitoring）を実装。
  - 監視起動時にプロセス優先度を上げる、停止フラグ検知で安全終了。

### 変更
- なし（初回リリースのため、既存機能の変更履歴はなし）。

### 修正
- なし（初回リリース）。

### 注意事項 / 運用上のガイド
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダにも記載）。
- 本番運用時は KABUSYS_ENV=live を設定すると追加の警告が出る（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認推奨）。
- send_order の設計はクラッシュ耐性を考慮しているが、運用中の不確定状態（OrderSent のまま等）は Reconciliation によって回復する必要がある。
- run_monitoring は常に本番 sqlite_path を参照するため、監視 DB の切り分けを必要とする場合は設定を確認すること。

（今後のリリースでは各モジュールのテストカバレッジ、async 対応の検討、YAML 設定のスキーマ検証、より詳細な監視メトリクスなどを追加予定）