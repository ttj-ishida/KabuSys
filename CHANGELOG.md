CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-22
-----------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- 設定/CLI:
  - kabusys.config: 環境変数 / .env の自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml で検出して .env / .env.local を読み込む。
    - OS 環境変数を保護する仕組み（.env の上書きを制御）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ: export プレフィックス、クォート文字（' "）内のバックスラッシュエスケープ、インラインコメントの扱い等に対応した堅牢な行パーサを実装。
  - kabusys.config_setup: 対話式ウィザードで .env の初期作成/更新を支援。機密項目は表示をマスクし、テンプレート形式で .env を書き出す。
  - kabusys.validate_config: .env と config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数チェック、環境値の妥当性確認（KABUSYS_ENV/LOG_LEVEL 等）、DB パスや config YAML の存在およびパース検証を行う。
    - --strict オプションで警告を FAIL（exit(1)）扱いにできる。
- 設定モデル:
  - Settings クラスを追加。各種設定値（トークン、DB パス、PID/kill フラグパス、閾値や PAPER_FILL_MODE 等）の取得とバリデーションを提供。
  - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL の値検証を実装（不正値は ValueError を raise）。
- 実行スクリプト:
  - run_execution: ExecutionEngine 起動スクリプトを追加。paper_trading 環境時は paper_trading 用 SQLite を使用して本番 DB と分離。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
  - 両スクリプトでプロセス優先度を設定するユーティリティを呼び出し、起動ログを出力。
- 発注関連コンポーネント:
  - execution.execution_engine: Signal Queue ベースの発注エンジンを実装。シグナル処理時間窓（8:50–9:10）、WebSocket push ドレイン（9:10–15:30）、kill flag / PID ファイルの扱い、リコンシリエーション実行フローを実装。
  - execution.order_record: OrderState の状態機械と OrderRecord データモデルを実装。許容遷移を定義し、不正遷移時は InvalidStateTransitionError を送出。
  - execution.order_manager: OrderRecord と OrderRepository を組み合わせた外向き API を提供。
    - create_order: client_order_id に uuid4 を採番し、重複（同一 signal_id の active 注文）を検出して DuplicateOrderError を投げる。
    - send_order: 2相永続化の戦略を採用（OrderSent の永続化→broker 呼び出し→broker_order_id を先に保存→OrderAccepted への遷移）、OrderSentPendingError の伝播、Rejected の扱いを実装。
    - sync_order: broker の状態取得に基づく同期ロジック（状態遷移、部分約定の差分更新）を実装。
    - cancel_order: 終端状態をチェックし、必要に応じて broker cancel を呼び出して Cancelled へ遷移。
  - execution.reconciler / risk_manager との連携点を用意（ExecutionEngine から利用）。
- ブローカークライアント:
  - execution.kabu_client: kabu-station REST API クライアントを追加（httpx 同期クライアントを使用）。
    - トークン取得の遅延初期化および 401 時の自動再取得・リトライを実装。
    - HTTP エラーを BrokerAPIError / RateLimitError 等へマッピング。
    - kabu の状態コードを内部ステータスにマッピング。
    - WebSocket push 受信を stream_push の存在で判別。
- DB / 監視:
  - DuckDB（分析用）と SQLite（監視/注文履歴）を併用する設計を導入。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）呼び出しを run_* スクリプトで実行。
  - ExecutionEngine から監視 DB へ発注イベント（log_trade_event）の記録を行うフックを追加（MonitoringDB が渡された場合）。
- その他:
  - パスの親ディレクトリ存在チェック（起動時に自動作成される可能性を警告）やログレベルの検証・デフォルト化など、堅牢性向上のための各種チェックを追加。
  - パッケージの __version__ を 0.1.0 に設定。

Changed
- 初版リリースにあたって、設計上の注意点やデフォルト挙動を明確化（kill.flag の自動クリア設定や起動拒否ロジック、paper_trading の DB 分離など）。

Fixed
- （初回公開時点での既知のクラッシュ安全性対策）
  - send_order におけるクラッシュ時の状態不整合を最小化するため、broker_order_id の先行コミットや状態遷移の分離を採用。
  - sync_order にて同一状態でも部分約定の進行を差分更新する実装を追加。

Known issues / Notes
- YAML のパース検証は PyYAML がインストールされている場合のみ実行される（未インストール時は警告してスキップ）。
- run_execution / run_monitoring は外部の BrokerAPI 実装や MonitoringDB 実装に依存する。テスト用に MockBrokerClient 等の差替えが想定される。
- 一部の値（PAPER_FILL_MODE や LOG_LEVEL 等）は Settings 側で厳格に検証するため、不正値を設定すると起動時に例外が発生する。

License
- このリリースでのライセンス情報はリポジトリのトップレベルの記載に従ってください。