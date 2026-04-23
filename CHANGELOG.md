# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-23

### Added
- 全体
  - 初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを追加。
- 設定関連
  - 環境変数/設定管理モジュールを追加（kabusys.config）。
    - .env の自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を基準）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - _load_env_file による読み込み時の「protected（OS 環境変数）」保持処理を実装。
    - Settings クラスを追加。環境変数から各種設定を安全に取得するプロパティを提供（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, pid_file_path 等）。
    - PAPER_FILL_MODE の検証ロジックを追加（有効値: instant, partial, never, reject）。
    - 環境値に対する検証（KABUSYS_ENV, LOG_LEVEL 等）を実装し、不正値時は ValueError を発生させる。
- CLI / ユーティリティ
  - 環境設定ウィザード CLI を追加（kabusys.config_setup）。
    - 対話的に .env を生成/更新する run_wizard を実装。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 通知設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）をサポート。
    - 既存 .env の読み込み、シークレットマスク表示、保存確認、テンプレートでの書き出しを実装。
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - .env と config/*.yaml の起動前検証を実施。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定検出、プレースホルダ検出を実装。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認および PyYAML が利用可能な場合は YAML パースチェック（PyYAML 未インストール時は警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の危険設定確認）。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。
- 実行用スクリプト
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
    - ExecutionEngine の起動フロー（プロセス優先度設定、DB 接続、ブローカークライアント生成、各コンポーネント組立、スレッド制御、停止フラグ監視）を実装。
    - paper_trading 環境では専用の paper SQLite を使用して本番 DB と分離。
  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
- 発注/状態管理
  - OrderRecord（状態遷移の純粋ロジック）を追加（kabusys.execution.order_record）。
    - 注文状態を列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可される状態遷移を明示化し、不正遷移で InvalidStateTransitionError を発生。
    - 状態遷移時に関連フィールド（broker_order_id, filled_qty, avg_fill_price, error_message, updated_at）を更新。
  - OrderManager を追加（kabusys.execution.order_manager）。
    - signal_id 重複チェック（DB の部分ユニーク制約と整合）を含む create/send/sync/cancel の外向け API を実装。
    - send_order において「OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted に遷移」の二相的耐障害設計を実装（クラッシュ耐性向上）。
    - OrderRejectedError, OrderSentPendingError の取り扱いを実装（pending の場合は broker_order_id を永続化して例外を再送出）。
    - sync_order による broker 状態同期と部分約定数/平均約定価格の更新実装。
    - cancel_order によるキャンセル処理とキャンセル不可状態の検出。
  - ExecutionEngine（kabusys.execution.execution_engine）を追加。
    - シグナルの読み込み（DuckDB）→ Gate1/2 のリスクチェック → 発注 → position_entries の記録 → push ドレイン のフローを実装。
    - Gate2 のレート制限リトライ（最大 3 回）や Circuit Breaker の検出、Gate3（ドローダウン）での kill_switch 発動を実装。
    - WebSocket push の受信を別スレッドで処理し、_push_queue を経由して sync と Gate3 評価を実行。
    - セッションライフサイクル（8:50 発注開始、9:10 発注締切、15:30 セッション終了）に沿った run_session を実装。
    - kill.flag 処理と KILL_FLAG_CLEAR_ON_START による起動時の自動クリア挙動を実装。
- ブローカークライアント
  - KabuStationClient を追加（kabusys.execution.kabu_client）。
    - httpx を使った同期 REST クライアントを実装。トークン取得・自動再取得（401 時リトライ）を実装。
    - レスポンス JSON パース失敗やネットワーク例外を BrokerAPIError に変換。
    - 429 は RateLimitError を送出。
    - 将来の async への切替を見越した実装。
    - WebSocket を使った push (stream_push) を想定した stream/handler のフックをサポート（push 受信は ExecutionEngine 側で利用）。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- なし（初回リリースのため該当なし）。

### Security
- 環境変数取り扱いにおいてシークレットの表示をマスク化（config_setup の対話表示）。
- .env のテンプレートに「.env を絶対に Git にコミットしない」注意書きを追加。

### Notes / Implementation details（重要な設計上の注意）
- .env パース（kabusys.config._parse_env_line）は複数のケースに対応:
  - export KEY=val 形式の対応
  - シングル/ダブルクォート内のバックスラッシュエスケープ対応
  - クォートなしの場合のインラインコメント認識（# の直前が空白/タブのとき）
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップして警告を出す設計。PyYAML があれば YAML の safe_load によるパースチェックを行う。
- OrderManager の send_order はクラッシュ時のリカバリ（Reconciliation）を容易にするため、broker_order_id を先に DB に保持する二相的な永続化を行う。
- ExecutionEngine はテスト容易性を考慮し、実際の run_session を使わず _process_signals / _drain_push_queue を直接呼べる設計。
- Monitoring / 監視周りは duckdb と sqlite を併用。monitoring は環境に関わらず本番 sqlite_path を使用する点に注意。

---

今後のリリースでは、既知の改良点（例: async 対応の KabuStationClient、Reconciler の拡張、より細かな監視メトリクス、ユニットテスト・統合テストの追加等）を予定しています。