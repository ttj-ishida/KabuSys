CHANGELOG.md

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

Unreleased
- なし

0.1.0 - 2026-04-23
Added
- パッケージ初期リリース（KabuSys v0.1.0）。
- 環境・設定管理
  - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数が優先されます）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 高度な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理）。_parse_env_line により無効行を無視。
  - _load_env_file による読み込みは override/protected パラメータで既存 OS 環境の上書き制御が可能。
  - Settings クラスを追加し、環境変数からアプリ設定を取得する API を提供（様々なプロパティ: jquants_refresh_token、kabu_api_password、duckdb_path、sqlite_path、paper_sqlite_path、pid_file_path、kill_flag_path、しきい値等）。
  - PAPER_FILL_MODE の妥当性チェック（"instant" | "partial" | "never" | "reject"）を実装。

- 設定支援ツール / 検証ツール
  - 対話式ウィザード (kabusys.config_setup) を追加。python -m kabusys.config_setup で .env の生成・更新を支援。項目の選択肢・デフォルト・シークレット表示（マスク）に対応。保存前に内容確認を行う。
  - 設定検証 CLI (kabusys.validate_config) を追加。python -m kabusys.validate_config により .env や config/*.yaml の不足・不整合を起動前に検出。--strict オプションで警告を失敗扱いにできる。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - プレースホルダ値（*_here / your_value）の検出と警告。
    - KABUSYS_ENV / LOG_LEVEL の値チェック（有効値の検証、live の場合の注意喚起）。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在確認。
    - config/*.yaml の存在確認と PyYAML が存在する場合の YAML パース検証（PyYAML 未インストール時はスキップして警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定の未設定や KILL_FLAG_CLEAR_ON_START の警告）。

- 実行スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、PID ファイル管理、stop flag 検出、DB 接続（paper_trading 時は paper 用 SQLite を使用）を行う。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定（デフォルト 60 秒）。監視は本番 sqlite_path を使用。

- 発注・実行エンジン
  - ExecutionEngine を追加（セッション実行の中核）。
    - シグナル処理（default: 8:50-9:10）→ push ドレイン（9:10-15:30）というセッション制御を実装。
    - WebSocket スレッド（broker の stream_push がある場合に有効）で受信 payload をキュー処理。
    - kill.flag の扱い（起動時チェック、設定により自動クリア、kill_switch の発動）と PID ファイルの書き込み/削除。
    - _process_signals によるシグナル読取、Gate1（シグナルレベル）、Gate2（エグゼキューションレベル、レート制限・リトライ・サーキットブレーカー考慮）、Gate3（ドローダウン監視）を実装。
    - 発注後の position_entries 登録（buy は entry 登録、sell は sell_date 更新）。duckdb を使った実装。
    - 発注メトリクスの監視DBへの記録（監視 DB が提供されている場合）。

- 注文管理（Order）
  - OrderRecord: 注文状態列挙（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）と状態遷移ルールを持つ純粋データモデルを実装。InvalidStateTransitionError を定義。
  - OrderManager: 外向き API を提供（create_order, send_order, sync_order, cancel_order）。
    - create_order は signal_id の重複（アクティブ注文の存在）チェックを行い、DuplicateOrderError を投げる。
    - send_order はクラッシュ耐性を考慮した 2 相永続化フロー（OrderSent を DB に commit → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted へ遷移）を実装。OrderRejectedError, OrderSentPendingError の取り扱いを実装。
    - sync_order は broker 側の状態取得により状態を同期。部分約定の進行は差分更新で反映。OrderSent->Filled/PartialFill のケースは OrderAccepted を経由して遷移させることで整合性を確保。
    - cancel_order は終端状態のキャンセル不可チェックを行い、broker API 呼び出し後に Cancelled に遷移。

- ブローカークライアント
  - KabuStationClient を実装（httpx を使用した同期クライアント）。
    - トークン取得を内部管理（遅延初期化、401 時の再取得とリトライ）。
    - レスポンス JSON パース失敗やタイムアウト／ネットワークエラーを BrokerAPIError としてラップ。
    - 401（認証失敗）・429（レート制限）・5xx（サーバエラー）を適切に扱う。
    - kabu ステーションの状態コードを内部ステータス（open/partial/filled/cancelled/rejected 等）へマッピング。
    - 将来の非同期対応のための設計を考慮（httpx.AsyncClient へ置換可能）。
    - websocket 経由の push 受信（stream_push）をサポートするフックを想定。

- リスク管理 / リコンシリエーション / 監視連携
  - ExecutionEngine と OrderManager が RiskManager / Reconciler / MonitoringDB と連携する設計を導入（Gate チェックや Reconciliation 実行、監視イベント書き込みなどをサポート）。

Changed
- n/a（初回リリース）

Fixed
- n/a（初回リリース）

Security
- 環境変数ファイル (.env) を絶対に Git にコミットしない旨の注記を config_setup の出力に追加。

Notes / Implementation details
- プロジェクトルート検出は .git または pyproject.toml の存在で判定するため、CWD に依存せずパッケージ配布後も安定して動作します。
- run_monitoring/run_execution は stop フラグ（data/stop_requested.flag）を監視し、外部による停止要求に応答します。
- __version__ は "0.1.0" に設定されています。

今後の予定（短期）
- broker API のテストダブル・Mock の充実化とユニットテストの追加。
- 非同期（async）対応の検討（httpx.AsyncClient 等）。
- より詳細な監視／メトリクス収集の拡充。