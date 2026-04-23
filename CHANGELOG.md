# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルには重要な変更点、追加機能、バグ修正、既知の注意点を日本語でまとめています。

## [0.1.0] - 2026-04-23

### Added
- 初期リリース: KabuSys 基本モジュール群を追加しました。
  - パッケージメタ情報: バージョンを __version__ = "0.1.0" に設定（src/kabusys/__init__.py）。
- 設定管理・自動読み込み
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供（src/kabusys/config.py）。
  - プロジェクトルートの自動検出ロジック（.git または pyproject.toml を基準）を実装。
  - 自動ロード順序: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パースの強化: export プレフィックス、クォート文字内のエスケープ、インラインコメント処理などに対応（詳細なパース実装あり）。
  - OS 環境変数を保護するため、上書き禁止（protected）オプションをサポート。
  - Settings による各種プロパティ（J-Quants トークン、kabu API パスワード、DB パス、PID/Kill フラグ、閾値、env/log_level 等）を提供。PAPER_FILL_MODE の検証も実装。

- 設定ウィザード CLI
  - `python -m kabusys.config_setup` による対話式ウィザードを追加。.env の初期作成・更新を支援（src/kabusys/config_setup.py）。
  - シークレット入力はマスク表示、選択肢・デフォルト指定、既存 .env の読み込み・再利用をサポート。
  - 生成される .env のテンプレート出力を実装（他者にコミットしない旨を明記）。

- 設定検証 CLI
  - `python -m kabusys.validate_config` による起動前検証ツールを追加（src/kabusys/validate_config.py）。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェックと本番（live）向け注意喚起。
  - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ確認。
  - config/*.yaml ファイルの存在確認および PyYAML があればパース検証（PyYAML 未導入時は警告でスキップ）。
  - 本番環境向け追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意）。
  - --strict オプション: 警告を FAIL として exit(1) で終了可能。
  - INFO / WARNING / ERROR の集計と適切な exit code 出力。

- 実行スクリプト
  - 監視ループ起動スクリプト: `python -m kabusys.run_monitoring`（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視は常に本番 DB を参照する設計）。
    - 停止フラグファイルの検出、例外耐性（check_once() の例外をログに出してループ継続）。
  - 発注エンジン起動スクリプト: `python -m kabusys.run_execution`（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - プロセス優先度設定（set_process_priority を呼ぶ）および PID ファイル管理、停止フラグ検出に対応。
    - DuckDB / SQLite の接続初期化と自動クリーンアップ。

- Execution エンジンと注文管理
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - Signal Queue Pull 型の発注エンジンを実装。シグナル処理時間帯（デフォルト 8:50-9:10）と push ドレイン（9:10-15:30）を持つセッションモデル。
    - WebSocket (push) スレッドの実装（broker に stream_push がない場合はスキップ）。
    - kill_switch の実装: 全 active 注文のキャンセルとループ停止。
    - Gate ベースのリスク検査（Gate 1/2/3）、rate limit retry、Gate 3 でのポートフォリオ評価による自動停止。
    - position_entries への約定予定日の書き込み（DuckDB 参照）、発注遅延計測と監視 DB へのログ記録（monitoring_db がある場合）。
    - セッション開始時に Reconciler があれば起動してリコンシリエーションを実行。
    - kill.flag の存在時の動作: KILL_FLAG_CLEAR_ON_START=1 なら自動クリアして起動、そうでなければ起動拒否。

  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態列挙 OrderState と許容遷移を定義。状態遷移検証ロジックを提供。
    - 不正遷移時は InvalidStateTransitionError を raise。

  - OrderManager（src/kabusys/execution/order_manager.py）
    - DB（OrderRepository）との組み合わせで外向き API を提供。
    - create_order: signal_id の重複チェック（DB のユニーク制約も考慮）を行い DuplicateOrderError を投げる。
    - send_order: 「OrderSent に永続化 → broker.send_order → broker_order_id 永続化（state stays Sent）→ OrderAccepted に遷移」の2相永続化フローを実装。OrderSentPendingError（注文番号はあるが約定しない）を特別扱いして broker_order_id のみ保存して伝播。
    - sync_order: broker 側の状態を取得してローカル状態に同期。状態が同一でも部分約定の進行で filled_qty/avg_fill_price のみ更新する。
    - cancel_order: キャンセル不可能な状態（Filled を含む終端状態）に対する保護。broker_order_id があれば API cancel を呼ぶ。

  - broker API インタフェースと KabuStationClient（src/kabusys/execution/kabu_client.py）
    - KabuStationClient を実装（httpx を使用、同期）。
    - トークン管理: _get_token による遅延初期化、401 時のトークン再取得とリトライを自動化。
    - レスポンス JSON パースの一貫したエラーハンドリング。
    - HTTP 429 を RateLimitError に変換、500 系を BrokerAPIError に変換。
    - kabu 注文状態コード → 内部ステータスへのマッピングを明確化。

- 監視関連
  - MonitoringDB 初期化・使用（init_monitoring_db を通じたテーブル保証）。
  - run_monitoring と run_execution の両方で duckdb と sqlite を使用して分析・監視データを扱う構成。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Security
- なし（現時点で特筆すべき脆弱性修正はありません）。

### Notes / 注意事項
- .env は絶対に Git にコミットしないでください（config_setup の生成ヘッダにも明記）。
- 本番環境（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の未設定や KILL_FLAG_CLEAR_ON_START の誤設定に注意してください。validate_config によって起動前に警告されます。
- ExecutionEngine のセッションモデルや kill.flag の扱いは運用上重要です。既存の PID / kill.flag が残っていると起動が拒否されるため、運用時には事前確認を推奨します。
- config/*.yaml の内容検証は PyYAML がインストールされている場合にのみ行われます。PyYAML 未導入時は警告が出ますが処理は継続します。
- PAPER_TRADING 用の DB（paper_trading.db）は paper_trading 環境で本番 DB と明確に分離して使用します。

もしリリースノートに追記したい点（既知の制限、次回バージョンでの予定機能など）があれば教えてください。