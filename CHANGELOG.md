CHANGELOG
=========
すべての注目すべき変更を時系列で記録します。  
フォーマットは「Keep a Changelog」準拠です。

[Unreleased]
------------

- （現時点の未リリース変更はありません）

[0.1.0] - 2026-04-22
-------------------

Added
- 初回リリース。KabuSys 日本株自動売買システムの基盤機能を追加。
  - CLI / ユーティリティ
    - config_setup: 対話式ウィザードで .env を作成／更新する CLI（python -m kabusys.config_setup）。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、ログレベル、Kill Switch 設定 等）をサポート。保存前に確認プロンプトを表示。
    - validate_config: 起動前に .env と config/*.yaml の不備を検出する検証ツール（python -m kabusys.validate_config）。--strict オプションで警告も失敗扱いにできる。PyYAML 未インストール時は YAML 内容検証をスキップする旨を警告。
    - run_execution: ExecutionEngine を起動するスクリプト（本番／ペーパートレードに対応）。停止フラグ、PID ファイル管理、プロセス優先度設定を実装。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用。
  - 設定管理
    - config モジュール: .env/.env.local の自動読み込み（プロジェクトルートを .git や pyproject.toml で検出）。読み込み優先度は OS 環境 > .env.local > .env。export 句、引用符、エスケープ、インラインコメントのパースに対応。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - Settings クラス: 環境変数をラップしたプロパティ群を提供（トークン、kabu API パスワード、DB パス、PID/KILL フラグ、閾値、env/log_level 等）。PAPER_FILL_MODE の値検証や KABUSYS_ENV / LOG_LEVEL の検証を行い、不正な値は ValueError を送出。
  - 発注フロー（Execution）
    - ExecutionEngine: シグナル処理（デイリーループ: 既定では 8:50–9:10 でシグナル送出、9:10–15:30 で push ドレイン）を実装。kill.flag による起動拒否あるいは自動クリア（KILL_FLAG_CLEAR_ON_START=1）に対応。PID ファイル書き込み、WebSocket push の受信と処理をサポート。
    - OrderRecord: 状態遷移を厳密に管理する状態マシン（OrderCreated → OrderSent → OrderAccepted → PartialFill → Filled → Closed、Rejected/Cancelled 等）。不正遷移は InvalidStateTransitionError を送出。
    - OrderManager: create/send/sync/cancel の外向き API。二相永続化を意識した send_order 実装（OrderSent を先にコミット → broker へ送信 → broker_order_id を保存 → OrderAccepted に遷移等）。OrderSentPendingError（注文番号は得られたが約定しない／保留）を伝播して取り扱い可能。DuplicateOrderError による同一 signal_id の重複防止。
    - ExecutionEngine 内のリスク管理ゲート（Gate1: シグナルレベル、Gate2: 実行レート制限／サーキットブレーカー、Gate3: ポートフォリオドローダウン）を呼び出し、Gate3 NG 時は kill_switch を発動して全 active 注文をキャンセル。
    - Reconciliation を起動時に実行可能（Reconciler が渡された場合）。sync_order により broker 側状態を照合して DB を更新。
    - position_entries への約定予定日の記録（BUY は entry、SELL は sell_date 更新等）、DuckDB を利用したシグナル取得ロジックを実装。
    - Paper trading モード: KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
  - Broker / API クライアント
    - KabuStationClient: kabuステーション REST API クライアント（httpx 同期版）。トークン取得の遅延初期化、401 時のトークン再取得＋リトライ、429（Rate Limit）に対する RateLimitError 判別、各種 HTTP/ネットワークエラーを BrokerAPIError に変換。WebSocket push（stream_push）をサポートする broker 実装と連携可能。
  - 監視（Monitoring）
    - run_monitoring と init_monitoring_db を使った監視 DB 初期化・ポーリングループを実装。監視ログの記録機能を ExecutionEngine から呼び出し可能（監視 DB 書き込み失敗時は通知してフローを継続）。
  - その他
    - process_priority（ユーティリティ参照）を起動時に High に設定するフックを実装（run_execution/run_monitoring で使用）。
    - ロギング設定ユーティリティ（setup_logging）を呼び出してログ整形を行う。

Changed
- 初回リリースのため変更履歴はなし。

Fixed
- 初回リリースのため修正履歴はなし。

Security
- 秘匿情報は .env に保存し Git にコミットしない旨を config_setup に明示。対話ウィザードではシークレット項目をマスク表示。

Notes / Usage
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- .env ウィザード:
  - python -m kabusys.config_setup
- 実行:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

開発者向け補足
- プロジェクトルートの検出は .git または pyproject.toml の存在で行うため、配布後も CWD に依存せず動作することを想定。
- .env の自動ロードはテスト等で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
- YAML ファイル（config/*.yaml）検証は PyYAML の有無に依存し、未インストール時は検証をスキップして警告を出します。

-- End of changelog --