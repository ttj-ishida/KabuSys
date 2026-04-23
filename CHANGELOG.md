# Changelog

すべての注目すべき変更点をここに記録します。
このファイルは "Keep a Changelog" の形式に準拠します。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-23

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - パッケージ公開用の主要モジュール群を導入（data, strategy, execution, monitoring を __all__ に公開）。

- 設定関連
  - 環境変数/設定管理モジュールを追加（src/kabusys/config.py）。
    - .env ファイルの自動読込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env / .env.local の優先順位（OS 環境 > .env.local > .env）を実装。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD オプションを追加。
    - .env のパースロジックを実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント処理）。
    - 必須環境変数取得用の _require()、Settings クラス（各種プロパティ）を実装。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を行う。
  - 対話式設定ウィザードを実装（src/kabusys/config_setup.py）。
    - .env の初期生成・更新を支援する CLI ウィザード。項目定義、既存 .env の読み込み、対話的プロンプト、.env 書き出し処理を提供。
    - 機密値は表示をマスクして確認できる（保存前に要確認）。

- 設定検証ツール
  - validate_config CLI を追加（src/kabusys/validate_config.py）。
    - .env と config/*.yaml の起動前検証ツール。
    - 必須環境変数の存在チェック、プレースホルダ判定、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML がインストールされている場合）、本番環境向けガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START など）。
    - --strict オプションで警告を FAIL として exit(1) にする機能。
    - 情報 / 警告 / エラーの集約表示。

- 実行スクリプト
  - Execution 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine を起動するエントリポイント。プロセス優先度設定、PID/stop フラグ管理、DB 接続、paper_trading 用 DB 分離を実装。
  - Monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能。Monitoring は環境に関係なく本番 sqlite_path を使用する仕様。

- Execution コンポーネント
  - ExecutionEngine を追加（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（8:50–9:10）と push/drain ループ（9:10–15:30）を実装。
    - kill.flag 検出、KILL_FLAG_CLEAR_ON_START による起動時自動クリア、PID ファイル管理。
    - WebSocket push の受信スレッド（broker が stream_push を提供する場合）と push キューのドレイン処理を実装。
    - シグナル処理フローにおける Gate 1/2（シグナル・エグゼキューション検査）、Gate 3（ドローダウン検査 / kill_switch 発動）を統合。
    - position_entries への約定記録、モニタリング DB へのトレードイベント記録処理を追加（失敗時は警告に留めてフロー継続）。
    - Reconciler の起動フックを追加（起動時リコンシリエーション）。
  - OrderManager を追加（src/kabusys/execution/order_manager.py）。
    - OrderRecord と OrderRepository を組み合わせた外向き API（create_order, send_order, sync_order, cancel_order）を実装。
    - create_order: client_order_id に uuid4 を採番、同一 signal_id の重複チェック（DB 制約違反は DuplicateOrderError に変換）。
    - send_order: クラッシュ時の整合性を考慮した 2 相永続化戦略（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移）を実装。OrderRejectedError / OrderSentPendingError の取り扱いを実装。
    - sync_order: broker からの状態取得に基づく同期ロジック。部分約定進捗のフィールド更新を含む。
    - cancel_order: 終端状態のキャンセル制御、broker 呼び出し、状態遷移処理。
  - OrderRecord と状態遷移モデルを追加（src/kabusys/execution/order_record.py）。
    - OrderState 列挙、許容遷移テーブル、transition_to による遷移検証（InvalidStateTransitionError を投げる）、updated_at 自動更新等を実装。
  - execution 内で使用する各種ユーティリティを導入（broker_factory, order_repository, reconciler, risk_manager などの呼び出しポイントを実装／統合）。

- Broker (kabu) クライアント
  - KabuStationClient を追加（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期的 REST クライアント。トークン取得（/token）とトークンキャッシュ、401 発生時の自動再取得およびリトライ、タイムアウト／ネットワーク例外のエラーハンドリングを実装。
    - kabu station の状態コードを内部状態 ("open", "partial", "filled", "cancelled", "rejected") へマップする処理を実装。
    - RateLimitError / BrokerAPIError 等の HTTP レスポンスに基づく例外種別を導入。
    - WebSocket push の受信（websocket 経由）をサポートするためのストリーミングフック（stream_push）に対応する設計。

- モニタリング
  - Monitoring DB 初期化ユーティリティを参照するコードを追加（init_monitoring_db の呼び出しポイントを run_monitoring/run_execution に実装）。
  - SystemMonitor / MonitoringDB と連携することで監視イベントの記録・ループ処理を実現。

- ユーティリティ
  - プロセス優先度設定ユーティリティ呼び出しを追加（set_process_priority を起動時に High に設定）。
  - ロギングセッティングユーティリティを導入して各スクリプトで初期化（setup_logging）。

### 変更 (Changed)
- 初回リリースのため特段の変更はなし（初期実装）。

### 修正 (Fixed)
- 初期リリースのため特段の修正はなし。

### 既知の制限 / 注意事項
- config/*.yaml の中身検証は PyYAML がインストールされている場合のみ実施される。未インストール時は YAML 検証がスキップされ、警告が出力される。
- KabuStationClient の実装は同期 httpx.Client ベース。将来的に非同期化が必要な場合は httpx.AsyncClient への移行が想定されている。
- .env の自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布環境等で該当ファイルが存在しない場合は自動ロードがスキップされる。
- 一部の外部モジュール（監視/実行の内部実装や Broker API の詳細）は別モジュールに依存しており、本リリースではインタフェース設計と統合ポイントが実装されている。

---

今後のリリースでは、テストの追加、エラーケースの更なる網羅、非同期対応、より詳細なモニタリング指標の追加等を予定しています。