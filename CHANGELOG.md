CHANGELOG
=========

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-04-23
-------------------

初回リリース — KabuSys v0.1.0

### Added
- 全体
  - 初期バージョンを公開。パッケージメタ情報に __version__ = "0.1.0" を追加。
  - プロジェクトルートの自動検出機能を実装（.git または pyproject.toml を基準に探索）。
- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env 自動ロード機能を追加。読み込み順は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用途）。
  - .env パーサを実装：
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートを考慮した値のパース（バックスラッシュエスケープ対応）。
    - インラインコメントの扱い（クォートの有無に応じた適切な処理）。
  - 環境変数取得ユーティリティ _require と Settings クラスを追加。必須パラメータが未設定時は明示的にエラーを上げる。
  - Settings に多数のプロパティを実装（J-Quants / kabu API / LINE / DB パス / PID/Kill フラグ /閾値 / env/log_level 判定など）。
  - PAPER_FILL_MODE の値検証を実装（有効値: instant/partial/never/reject）。
  - paper_trading 用の専用 SQLite パス（PAPER_TRADING_SQLITE_PATH）をサポート。
- 環境設定ウィザード CLI (src/kabusys/config_setup.py)
  - 対話式ウィザードで .env を生成・更新する CLI を追加（python -m kabusys.config_setup）。
  - 設定項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン等）と既定値、選択肢、説明を用意。
  - シークレット項目は入力表示時にマスク。
  - 既存 .env 読み込みと Enter による既存値再利用をサポート。
  - .env のテンプレート生成（コメント付き）を実装。生成された .env を Git にコミットしない旨を明記。
  - --env-file オプションで保存先を変更可能。
- 設定検証 CLI (src/kabusys/validate_config.py)
  - .env および config/*.yaml の起動前検証ツールを追加（python -m kabusys.validate_config）。
  - 必須/任意環境変数のチェック実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）。
  - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）。live の場合は注意警告を出力。
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）チェック。
  - DUCKDB/SQLite パスの親ディレクトリ存在チェック（存在しない場合は警告）。
  - config/*.yaml ファイルの存在確認と、PyYAML があればパース検証を実行。PyYAML 未インストール時はパース検証をスキップして警告。
  - KABUSYS_ENV=live 時の追加ガードチェック（LINE通知設定、KILL_FLAG_CLEAR_ON_START の危険値検出など）。
  - --strict オプションで警告も失敗扱い（exit(1)）にする機能を実装。
  - 検証結果を INFO/WARNING/ERROR として出力し、エラー件数・警告件数に応じた終了コードを返す。
- 実行スクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine の起動スクリプトを追加。paper_trading モードでは専用 DB を使用して本番 DB と完全分離。
    - プロセス優先度設定（High）適用。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止。
    - 実行用 PID ファイル管理とクリーンアップ。
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用。
    - 停止フラグ検出、例外時のログ出力、リソースクローズ処理を実装。
- 実行コア / 注文管理
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態を列挙する OrderState を実装（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可遷移のマッピングと transition_to による遷移検証を実装。不正遷移時は InvalidStateTransitionError を送出。
    - updated_at の自動更新やオプションフィールド（broker_order_id, filled_qty, avg_fill_price, error_message）更新処理を提供。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - OrderRecord と OrderRepository を組み合わせた外向き API を実装（create/send/sync/cancel）。
    - create_order: signal_id の active 注文重複検出、UUID ベースの client_order_id 発番、DB 制約違反を DuplicateOrderError に変換。
    - send_order: 崩壊安全性を考慮した 2 段階永続化フローを実装（OrderSent を先に永続化し、その後 broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）。
    - OrderRejectedError / OrderSentPendingError のハンドリング（pending は broker_order_id を保存して例外伝播）。
    - sync_order: broker 側のステータスを内部状態へ同期し、部分約定の更新や不整合回復（OrderSent→Filled などの特別処理）に対応。
    - cancel_order: 終端状態ではキャンセル不可とし、必要に応じて broker API を呼んで Cancelled に遷移。
- ExecutionEngine（src/kabusys/execution/execution_engine.py）
  - シグナルベースの発注エンジンを実装。
  - シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を分けたセッション実行。
  - Gate 1/2/3 によるリスクチェック設計を採用：
    - Gate 1: シグナルレベル検査（信号ごとの許可）。
    - Gate 2: エグゼキューション側の検査（レート制限、回数リトライ、サーキットブレーカ対応）。
    - Gate 3: ドローダウン監視により kill_switch を発動。
  - size_multiplier による発注量調整（BUY のみ）。
  - DuplicateOrderError のスキップ、API レイテンシ計測と監視 DB へのログ（monitoring_db が提供される場合）。
  - WebSocket スレッド（broker が stream_push を持つ場合）の実装と push イベントからの同期処理。
  - 起動時のリコンシリエーション呼び出し（Reconciler がある場合）とエラー耐性。
  - kill.flag の存在時の起動拒否や KILL_FLAG_CLEAR_ON_START による自動クリア挙動（設定に従う）。
  - PID ファイル書き込みと終了時の削除。
  - DuckDB からのシグナル読み取り（_read_signals）。
  - position_entries テーブルへの約定予定日の書き込み（BUY/pending/SELL の条件差分に対応）。
- kabu station クライアント（src/kabusys/execution/kabu_client.py）
  - KabuStationClient を実装（httpx ベースの同期クライアント）。
  - トークン管理（遅延取得、自動再取得）を内部で実装し、401 時に再取得して 1 回リトライ。
  - レスポンス JSON パース失敗やネットワークエラーを BrokerAPIError に変換して明示的に報告。
  - 429 を RateLimitError として扱う。
  - websocket パッシュ受信のための stream_push 連携を想定（存在しない実装時は警告してスキップ）。
- 監視 / DB (間接)
  - monitoring_db 初期化呼び出しを各スクリプトから実行して監視テーブルの存在を保証（冪等）。
  - duckdb と sqlite の両方を使う設計を採用（分析用 DuckDB、監視/トランザクション用 SQLite）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Notes / Safety
- 多くの箇所でクラッシュ後の整合性回復（OrderSent の永続化、broker_order_id の先保存、reconciliation による復元）を考慮した設計を採用。
- .env や機密情報 (.env に含まれるトークン等) はウィザードでマスクして表示、ファイル生成時にも注意喚起コメントを挿入。
- config/*.yaml のパースには PyYAML が必要。未インストール時は検証をスキップして警告するため、起動前検証を完全に行いたい場合は PyYAML をインストールしてください。

今後の予定（例）
- KabuStationClient の async サポート（httpx.AsyncClient）への移行検討。
- 監視・メトリクス拡充、より詳細なリスク制御の設定化。
- 単体テスト・統合テストの追加と CI パイプラインの整備。