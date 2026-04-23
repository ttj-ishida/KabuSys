CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

リンクや追加メタデータはこのサンプルには含まれていません。

0.1.0 — 2026-04-23
------------------

Added
- 初回公開リリース。KabuSys 日本株自動売買システムの基本機能を実装。
- 環境設定・読み込み
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどのパターンに対応。
  - Settings クラスを提供し、環境変数経由でアプリケーション設定を一元管理。各プロパティは値の妥当性チェックを行い、不正値は ValueError を送出する。
  - paper_trading 用の分離された DB パス（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）や PAPER_FILL_MODE 指定のサポート。

- 対話式セットアップ
  - config_setup.py による .env 作成・更新ウィザードを実装。選択肢、デフォルト、シークレットマスク表示、既存値の再利用に対応。
  - .env 出力フォーマットには注意書き（.env をコミットしない等）を含む。

- 設定検証 CLI
  - validate_config CLI を実装。必須環境変数の存在、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL 等の値検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パース検証を行う。
  - PyYAML が未インストールの場合は YAML 内容検証をスキップして警告を出す。
  - --strict モードを指定すると警告も FAIL として exit(1) を返す。

- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - プロセス優先度設定（High）機能を呼び出す。
    - paper_trading 環境では専用 SQLite DB を使用して本番 DB と分離。
    - PID ファイル書き出し、停止フラグ（data/stop_requested.flag / kill.flag）検出、KILL_FLAG_CLEAR_ON_START の挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計。

- 発注・実行エンジン（core）
  - execution_engine.py: Signal Queue Pull 型の ExecutionEngine 実装。
    - 発注時間帯（signal_send_start / signal_send_end / market_close）に基づくフロー。
    - シグナル読み込み、Gate1/Gate2/Gate3 によるリスクチェック、WebSocket push ドレインループ、kill_switch の導入。
    - position_entries への書き込みや監視DBへのトレードイベント記録に対応。
  - order_record.py: 注文状態（OrderState）列挙と OrderRecord データモデル、状態遷移ロジック（transition_to）を実装。許可されない遷移は InvalidStateTransitionError を送出。
  - order_manager.py: OrderRecord と OrderRepository を組み合わせる外向き API を実装。
    - create_order: signal_id の重複チェック（DB 制約含む）と UUID による client_order_id 採番。
    - send_order: クラッシュ耐性を考慮した 2 相永続化ロジック（OrderSent 永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移 等）。
    - OrderRejectedError / OrderSentPendingError のハンドリングおよび伝播の実装。
    - sync_order: broker の状態照合・同期ロジック（部分約定の進行に応じた更新を含む）。
    - cancel_order: キャンセル不可能な状態の判定および broker cancel 呼び出し。

- ブローカークライアント
  - kabu_client.py: KabuStation 用同期 REST クライアント実装（httpx を使用）。
    - トークン取得の遅延初期化と 401 に対する再取得リトライ処理。
    - レスポンス JSON パース失敗やタイムアウト/ネットワークエラーを BrokerAPIError 等に変換。
    - HTTP 429 を RateLimitError として扱う。
    - kabu ステータスコード→内部状態マッピングを定義。

- 監視・DB 初期化
  - monitoring/run 用の DB 初期化（init_monitoring_db）や SystemMonitor との接続を行うフローを追加（run_monitoring/run_execution から利用）。

- ユーティリティ
  - プロセス優先度設定、ログセットアップなど外部ユーティリティを組み合わせて使用（高優先度の設定やログ初期化を起動時に行う）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- .env ファイルには機密情報が含まれるため .env を絶対に Git にコミットしない旨を出力ファイルのヘッダに明記。

Notes / 注意事項
- validate_config は PyYAML がない環境でも動作しますが、config/*.yaml のパースチェックはスキップされ YAML の誤りは検出されません。検査を有効にするには PyYAML をインストールしてください。
- ExecutionEngine の動作には broker 実装（BrokerAPIProtocol）と適切な DB（DuckDB/SQLite）が必要です。paper_trading モードでは専用の SQLite を使用するため本番データと分離されます。
- kill.flag（および KILL_FLAG_CLEAR_ON_START）の扱いは起動時と実行中で異なります。設定を誤ると本番で自動的に Kill Switch が解除されてしまうため、特に本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- .env の読み込み順や自動読み込みを無効化するフラグはテスト実行等で利用可能です。

ライセンスや互換性、今後の予定については別途ドキュメントで追記予定です。