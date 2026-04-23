CHANGELOG
=========

すべての注目すべき変更点を記載します。セマンティックバージョニングに従います。

[Unreleased]
-------------

- （現状なし）

[0.1.0] - 2026-04-23
-------------------

Added
- 初回リリース。KabuSys の基盤機能を実装。
- 環境設定 / ユーティリティ
  - .env ファイル自動読み込み機構を実装。プロジェクトルート（.git / pyproject.toml）を基準に探索し、.env / .env.local を読み込む（OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを強化：export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、無効行スキップに対応。
  - config_setup CLI（python -m kabusys.config_setup）を追加：対話式ウィザードで .env を初期作成・更新可能。シークレット項目のマスク表示、選択肢・デフォルト表示、保存確認を実装。
  - validate_config CLI（python -m kabusys.validate_config）を追加：起動前に .env と config/*.yaml の設定不備を検出。--strict オプションで警告を FAIL 扱いにできる。
  - validate_config は PyYAML が存在する場合に config/*.yaml をパースして内容検証を行い、存在しない場合やパース失敗は適切に警告/エラーを出力。
- 設定管理（Settings）
  - Settings クラスを実装し、環境変数から型安全に設定値を取得するプロパティ群を提供（トークン・API パスワード / DB パス / LINE トークン / PID / kill flag 等）。
  - 各プロパティで妥当性チェックを実施（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などは不正値で例外を送出）。
  - paper_trading 向けの paper_sqlite_path を分離して提供。
- 実行スクリプト
  - run_execution（python -m kabusys.run_execution）を追加：ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時は専用 SQLite（paper_trading.db）を使用し、本番 DB と分離。
  - run_monitoring（python -m kabusys.run_monitoring）を追加：SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
  - 両スクリプトでプロセス優先度設定、ログ設定、DB 初期化、PID / stop flag の扱い等を統一。
- 発注系コア
  - OrderRecord：注文状態を表す状態マシンモデルと遷移ロジックを実装（OrderState 列挙、許容遷移表、transition_to による検証）。
  - OrderManager：OrderRecord（ロジック）と OrderRepository（SQLite）を組み合わせた外向き API を実装。create_order（重複検出）、send_order（永続化の2相手続き、OrderSentPending/Rejected の扱い）、sync_order（broker 照合による同期）、cancel_order を提供。
  - DuplicateOrderError / InvalidStateTransitionError 等の専用例外を定義。
  - send_order の実装はクラッシュ耐性を考慮：OrderSent を先に永続化し、broker_order_id を先にコミットすることでリコンシリエーションでの回復を容易に。
- ExecutionEngine（発注エンジン）
  - Signal Queue Pull 型の発注エンジンを実装。8:50-9:10 をシグナル処理、9:10-15:30 を push ドレインループとして運用。
  - Gate ベースのリスク制御:
    - Gate 1: シグナル単位の検査（サイズ・注文金額等）
    - Gate 2: エグゼキューションレベル（レート制限 / サーキットブレーカー）。リトライロジック（最大3回）を実装。
    - Gate 3: ポートフォリオ指標によるドローダウン監視。NG の場合に kill_switch 発動。
  - size_multiplier の適用（BUY のみ、100 株単位丸め）や pending 注文の扱い（BUY pending は position_entries に記録）を実装。
  - WebSocket push 処理（broker の stream_push を使う場合）を別スレッドで受信し、_push_queue 経由で同期処理を行う。
  - リコンシリエーションフロー呼び出し（起動時）に対応し、結果をログ出力。
  - kill.flag の存在に応じた起動拒否 / 自動クリア（KILL_FLAG_CLEAR_ON_START）を実装。
  - PID ファイルの書き出し / 削除を実装。
  - 監視用の MonitoringDB ログ（発注イベントの記録）を optional にサポート。
- Broker / KabuStation クライアント
  - KabuStationClient を実装（httpx を同期クライアントとして使用）。トークン取得・再取得ロジック、401 の場合のリトライ、429（RateLimit）の例外化、タイムアウト/ネットワークエラーの BrokerAPIError 変換等を実装。
  - WebSocket(push) を受け取る stream_push を持つ broker 実装に対応。
  - kabu ステータス → 内部ステータスへのマッピングを提供。
- 監視 / DB
  - run_monitoring と ExecutionEngine で monitoring DB の初期化を行う init_monitoring_db 呼び出しを統一して実行。
  - DuckDB と SQLite の接続管理（close）を適切に行う。
- その他ユーティリティ
  - .env 書き込みロジック（config_setup の _write_env）によりテンプレート付きの .env を生成。
  - ログメッセージや警告を日本語で出力してユーザーに分かりやすくした。

Changed
- （初版のため無し）

Fixed
- （初版のため無し）

Removed
- （初版のため無し）

Notes
- 設定/運用上の注意点や挙動は CLI のヘルプとログメッセージを参照してください（例: validate_config の --strict、KILL_FLAG_CLEAR_ON_START の影響、paper_trading 用 DB 分離など）。