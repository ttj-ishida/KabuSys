# Changelog

すべての注目すべき変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

現在のリリース方針: 初回公開リリースを記録しています。

## [0.1.0] - 2026-04-22

### Added
- パッケージ初回リリース。
- 環境 / 設定管理
  - Settings クラスによる環境変数ベースの設定取得を実装。
  - .env 自動読み込み機構を追加（優先順位: OS 環境 > .env.local > .env）。自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーを独自実装:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォートとバックスラッシュエスケープに対応した値のパース。
    - インラインコメント処理（クォートなしの '#' は直前が空白/タブの場合のみコメントとして扱う）。
    - ファイル読み込み時の上書き制御（override フラグ）とプロテクト（protected, OS 環境変数保護）。
  - 環境変数必須チェック用 helper (_require) を追加（未設定時に ValueError を送出）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。

- CLI / ユーティリティ
  - 環境設定ウィザード: python -m kabusys.config_setup
    - 対話形式で .env を生成/更新する run_wizard。
    - .env テンプレート書き込み機能（.env を決して Git にコミットしない旨の警告を含む）。
  - 設定検証 CLI: python -m kabusys.validate_config
    - .env と config/*.yaml の設定不備（未設定の必須環境変数、プレースホルダ値、KABUSYS_ENV の不正値、ログレベル不正、DB パス親ディレクトリ未存在など）を起動前に検出。
    - PyYAML 未インストール時は YAML 内容検証をスキップして警告。
    - --strict モードで警告も FAIL として exit(1)。
  - 実行用エントリスクリプト:
    - run_execution: ExecutionEngine の起動スクリプト（KABUSYS_ENV に応じて paper_trading では専用 DB を使用）。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能）。

- 実行・監視基盤
  - PID / stop フラグ / kill.flag による起動制御を実装。
  - 起動時にプロセス優先度を設定するユーティリティ（set_process_priority を使用）。
  - 監視（monitoring）は常に本番 sqlite_path を使用して独立して稼働。
  - run_monitoring は監視ループ、例外ハンドリング、停止フラグ検出を実装。

- 注文実行フレームワーク
  - OrderRecord: 注文状態（State Machine）データモデルを実装。
    - OrderState 列挙、許可される状態遷移マップ、InvalidStateTransitionError。
    - transition_to による遷移検証と updated_at 自動更新。
  - OrderManager: 外向け API（create/send/sync/cancel）を実装。
    - create_order: signal_id 単位で重複チェック（部分ユニークインデックス + DB 制約考慮）。DuplicateOrderError を定義。
    - send_order: クラッシュ耐性を考慮した 2 相永続化設計（OrderSent を先に永続化 → ブローカー呼び出し → broker_order_id 永続化 → OrderAccepted に更新）。OrderRejectedError / OrderSentPendingError の取り扱い。
    - sync_order: broker のステータス照会に基づく同期ロジック（部分約定の差分更新を含む）。
    - cancel_order: キャンセル不可状態の判定と broker 取消呼び出しを行う。
  - ExecutionEngine: シグナルプル型発注エンジンを実装。
    - EngineConfig により発注窓（signal_send_start/end）や market_close を制御。
    - シグナル処理フロー（8:50-9:10）と push ドレイン（9:10-15:30）を実装。
    - Gate 1/2/3 によるリスクチェックを導入（Gate2 はレート制限 / サーキットブレーカ対応、Gate3 はポートフォリオ検査で kill_switch 発動）。
    - size_multiplier の適用（BUY のみ）、発注レート計測と監視 DB へのログ（MonitoringDB が提供される場合）。
    - WebSocket push を受けて _push_queue に投入するワーカ（stream_push を持たない broker はスキップ）。
    - kill_switch 実装: 全 active 注文のキャンセル、ループ停止、ログ出力。外部 stop() は kill_switch の公開エイリアス。
    - 起動時にリコンシリエーションを実行（Reconciler が注入されている場合）。
    - PID ファイル書き込み / 起動時の kill.flag 処理（KILL_FLAG_CLEAR_ON_START を尊重）。

- ブローカークライアント
  - KabuStationClient （kabu station 向け REST 実装）を追加。
    - API トークンの遅延取得と自動再取得（_get_token）。
    - 認証付きリクエスト処理（_request）で 401 を検知したらトークン再取得して 1 回リトライ。
    - HTTP エラー（タイムアウト / ネットワーク / 429 レート制限 / >=500）を BrokerAPIError / RateLimitError に適切に変換。
    - kabu station の注文状態コード → 内部ステータス（open/partial/filled/cancelled/rejected）マッピングを実装。
    - 将来的な非同期化を見据え httpx.Client を使用（同期実装）。

- データベース
  - duckdb と sqlite を使用したデータアクセスの雛形と接続確立（Execution / Monitoring 用）。
  - run_execution は paper_trading 環境時に paper_sqlite_path（分離された SQLite DB）を利用するよう実装。
  - 監視用 DB 初期化ヘルパー init_monitoring_db を呼び出して監視テーブルの存在を保証。

- ロギング・ユーティリティ
  - setup_logging を利用したログ初期化フローを導入（各スクリプトで利用）。
  - ログレベルと設定の検証は Settings により行い、想定外の値は例外を発生させる（実行時 fail-fast）。

注: 上記の機能はコードベースから推測して記載しています。実際の挙動・ドキュメントと差異がある場合があります。

### Security
- .env の取り扱いに関する注意: .env は絶対にリポジトリにコミットしない旨の注記を .env テンプレートに含めています。

<!--
将来のリリース:
- [Unreleased] セクションを使用して今後の変更を追跡してください。
-->