# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog 準拠です。  

- リリース日はコミット時点もしくはパッケージ公開日を記載してください。

## [Unreleased]

## [0.1.0] - 2026-04-22

Added
- 初期公開: KabuSys 自動売買フレームワークのコア機能を実装。
- 設定/環境管理
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env パーサを実装: コメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - Settings クラスを追加し、環境変数から型変換・検証済みの値を提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH など）。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装（不正値は ValueError を発生）。
- 設定ウィザード CLI
  - 対話式ウィザード（kabusys.config_setup）で .env の初期作成／更新をサポート。
  - シークレット項目は表示をマスク、選択肢・デフォルト・説明テキスト付き。
  - 生成される .env に注意書き（絶対に Git にコミットしない）を含めて書き出し。
- 設定検証 CLI
  - kabusys.validate_config を実装し、起動前に .env および config/*.yaml の設定不備を検出。
  - 必須環境変数チェック、プレースホルダ値検出（_here / your_value）、KABUSYS_ENV／LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを実装。
  - YAML パースの依存性判定（PyYAML 未導入時は内容検証をスキップして警告）。
  - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
  - --strict オプションを追加（警告を FAIL として exit(1)）。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。paper_trading モードでは専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
  - run_monitoring: SystemMonitor ポーリングループの起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）。Monitoring は環境に関係なく本番 sqlite_path を利用。
  - 両スクリプトでプロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
  - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/*.pid）への対応を実装。
- Execution エンジン
  - ExecutionEngine を実装（Signal Queue Pull 型）。セッション時間の定義（発注開始 8:50、発注締切 9:10、市場クローズ 15:30）。
  - run_session のワークフロー: 起動時リコンシリエーション、kill.flag 検査（KILL_FLAG_CLEAR_ON_START による振る舞い）、PID 書き出し、WebSocket Push スレッド、シグナル処理ループ（_process_signals）、push ドレイン（_drain_push_queue）を提供。
  - Push ハンドリング: broker の stream_push が無ければスキップ。push の OrderID から client_order_id を照合して sync_order を呼び出す。
  - position_entries の書き込み（約定日の翌営業日を使用）や監視 DB への発注イベント記録に対応（失敗しても発注フローを継続）。
  - kill_switch 実装: 全 active 注文のキャンセル／停止処理。外部 stop() は kill_switch の公開エイリアス。
- 注文管理・状態遷移
  - OrderRecord（状態機械）を実装。OrderState 列挙、許可遷移マップ、transition_to による検証・更新（UTC タイムスタンプ更新含む）。
  - InvalidStateTransitionError を導入。
  - OrderManager を実装: create_order（UUID による client_order_id 採番、signal 単位の重複検出）、send_order（2 相永続化パターンを採用）、sync_order（broker 側の状態を取得して同期）、cancel_order（キャンセル可否判定）を提供。
  - send_order の耐障害設計:
    - OrderSent を先に永続化してから broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移する安全な手順を採用。
    - OrderRejectedError を捕捉して Rejected に遷移。
    - OrderSentPendingError（注文番号は発行されたが約定しないケース）は broker_order_id を保存して OrderSent のまま再スロー（Reconciliation 対象）。
    - DB の一意制約違反（orders.signal_id）を DuplicateOrderError に変換して扱いやすくした。
  - sync_order の堅牢性: 状態が同じでも部分約定（filled_qty/avg_fill_price）の更新を行う。OrderSent→Filled 等、直接遷移できない場合は OrderAccepted を介して遷移させる。
- リスク管理フローとの連携
  - ExecutionEngine 内で Gate 1（シグナルレベル検査）、Gate 2（実行レベル検査：レート制限、Circuit Breaker の扱い）、Gate 3（ドローダウン監視）を導入し、拒否時の挙動や kill_switch 発動条件を明確化。
  - API 成功／失敗の記録（risk_manager.record_api_success / record_api_error）。
- Broker クライアント（kabu）
  - KabuStationClient を実装（同期 httpx クライアント）。トークン取得ロジック（遅延初期化、401 時の再取得とリトライ）を実装。
  - レスポンス JSON のパース失敗やネットワーク例外を BrokerAPIError にラップ。
  - 429（Rate limit）を RateLimitError に変換。
  - kabu ステーションの状態コードを内部ステータス文字列（open/partial/filled/cancelled/rejected）にマッピング。
  - 将来的な async 対応を考慮して設計（httpx.AsyncClient に切替可能な構造）。
- DB / 監視
  - monitoring_db の初期化ユーティリティを呼び出すことで監視テーブルを保証（冪等）。
  - DuckDB と SQLite の併用を前提にした設計（DuckDB は分析・シグナル取得、SQLite は監視・履歴）。
- その他ユーティリティ
  - プロセス優先度設定ユーティリティを使用して重要プロセスの優先度を上げる。
  - ロギング設定ユーティリティ（setup_logging）を参照して各プロセスでログを初期化。
  - 環境変数による挙動制御（KABUSYS_DISABLE_AUTO_ENV_LOAD、MONITOR_POLL_INTERVAL、KILL_FLAG_CLEAR_ON_START など）を提供。
- ドキュメント
  - 各 CLI / スクリプトのモジュール docstring に使い方や挙動を明記。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数の取り扱いに注意する旨を .env 出力ヘッダに明記（.env を絶対に Git にコミットしないこと）。

Notes / マイグレーション
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後に環境変数を直接設定して運用する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用時は KABUSYS_ENV=live とし、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を必ず確認してください（validate_config で警告表示）。
- PAPER_TRADING モードでは監視用 SQLite は paper_trading 用 DB を使用し、本番 DB と完全分離されます。

--- 

今後の TODO（例）
- async/await を活用した非同期 broker クライアントの導入（httpx.AsyncClient）。
- Unit tests / 統合テストの追加（OrderManager / ExecutionEngine の耐障害パスを重点的に）。
- YAML 設定ファイルのスキーマ検証（PyYAML があれば validate_config で詳細検証）。
- Reconciliation と発注フローに関する可視化・監視強化。