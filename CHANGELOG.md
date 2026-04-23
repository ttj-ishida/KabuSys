# CHANGELOG

このプロジェクトは Keep a Changelog の形式に準拠しており、逆順（最新が先）で変更履歴を記載します。

全般的な注意
- 本リポジトリは日本株自動売買システム「KabuSys」のコードベースです。本ログはコード内容から推測して作成しています。

Unreleased
- なし

0.1.0 - 初回リリース
----------------------------------------

Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 環境設定 / 設定管理
  - Settings クラス（kabusys.config）を追加。環境変数から各種設定値を取得するプロパティを提供：
    - J-Quants / kabuステーション API トークン・パスワード取得（必須チェックを内部で行う）
    - DUCKDB / SQLite のパス、paper_trading 用 SQLite パス
    - PID ファイル / kill flag / kill フラグ自動クリア設定
    - 各種閾値（CPU / Memory / Disk）やログレベル、環境（development/paper_trading/live）判定ヘルパー
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）
  - 環境変数自動ロード機能を実装（.env と .env.local、OS 環境変数を保護する挙動、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプション）。
  - .env ファイルのパーサ実装（クォートやエスケープ、コメント処理に対応）。

- 環境設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを追加：
    - .env ファイルの生成・更新を対話形式で支援
    - デフォルト値、選択肢、シークレットマスク表示、既存 .env 読み込みの再利用
    - .env 書き出しテンプレート（コメント付き、Git へコミットしない旨の注意）を提供
    - 使い方: python -m kabusys.config_setup（--env-file オプションでパス指定可）

- 設定検証 CLI
  - `kabusys.validate_config` を追加。起動前に .env と config/*.yaml の不備を検出：
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
    - プレースホルダ（"_here" や "your_value"）の警告
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、KABUSYS_ENV=live の注意喚起
    - DUCKDB/SQLite パスの親ディレクトリ存在チェック（自動作成の可能性を注記）
    - config/*.yaml の存在確認と（PyYAML がインストールされている場合の）パース検証
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）
    - --strict オプション（警告を FAIL 扱いし exit(1) で終了）
    - CLI 使い方: python -m kabusys.validate_config

- 実行スクリプト（監視 / 実行）
  - run_monitoring（kabusys.run_monitoring）を追加：
    - SystemMonitor のポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒、1 秒以上の整数のみ採用）
    - monitoring 用 SQLite / DuckDB 接続（monitoring は環境にかかわらず本番 sqlite_path を使用）
    - stop フラグ検出で安全に終了
    - プロセス優先度設定・ログセットアップを呼び出し

  - run_execution（kabusys.run_execution）を追加：
    - ExecutionEngine の起動スクリプト
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用し本番 DB と分離
    - PID / stop フラグハンドリング（起動前に停止フラグがあれば起動せず終了）
    - プロセス優先度設定、ログセットアップ、DB 初期化処理実行
    - エンジンを別スレッドで実行し停止フラグを監視

- Execution エンジンと発注フロー
  - ExecutionEngine（kabusys.execution.execution_engine）を実装：
    - セッション制御（signal_send_start/End、market_close）に基づいたフロー
    - 起動時の Reconciliation 実行（reconciler が設定されている場合）
    - PID ファイル書き込み・削除の管理
    - シグナル処理ループ（シグナル読み込み、Gate1/Gate2 リスクチェック、発注、position_entries への記録）
    - push（kabu push）ドレインループ、push による同期、Gate3 ドローダウンチェックと kill_switch 発動ロジック
    - WebSocket スレッドを起動する機能（broker が stream_push を持たない場合はスキップ）
    - kill_switch による全 active 注文キャンセル処理と停止フラグ設定
    - 発注時の監視 DB へのイベントロギング（監視 DB が渡された場合）
    - 発注/キャンセルフローの堅牢性を高める設計（PID / stop flag の扱い、クリティカルなチェック）

- 注文管理・永続化（DBは OrderRepository 経由）
  - OrderRecord（kabusys.execution.order_record）を追加：
    - 注文状態を Enum で定義（created, sent, accepted, partial, filled, closed, cancelled, rejected）
    - 許可遷移テーブルと transition_to メソッド（不正遷移時は InvalidStateTransitionError を送出）
    - メタデータ（broker_order_id, filled_qty, avg_fill_price, error_message）を扱う

  - OrderManager（kabusys.execution.order_manager）を追加：
    - create_order / send_order / sync_order / cancel_order の実装
    - create_order: 同一 signal_id の active 注文重複検査（DuplicateOrderError）
    - send_order: 2 段階永続化戦略
      - Step1: OrderSent に遷移して DB に保存（クラッシュ安全性）
      - broker API 呼び出し → broker_order_id を先にコミット（state は Sent のまま）→ OrderAccepted に遷移してコミット
      - OrderRejectedError / OrderSentPendingError 等のケースをハンドリング（pending は OrderSent のまま broker_order_id を保存してリスロー）
      - その他例外はキャッチしない（list_uncertain で検出するため）
    - sync_order: broker 側の最新状態を取得してローカル状態に同期。部分約定の進行では差分更新のみ行う。OrderSent→Filled のような飛び越しは OrderAccepted を経由して復元。
    - cancel_order: 終端状態はキャンセル不可（InvalidStateTransitionError）。broker_order_id がある場合は broker 側のキャンセル API を呼ぶ。

  - 状態マッピング / キャンセル不許可状態等の取り決めを明示化（_STATUS_TO_STATE, _CANCEL_INELIGIBLE_STATES）

- Broker / KabuStation クライアント
  - KabuStationClient（kabusys.execution.kabu_client）を追加：
    - httpx を使った同期 REST クライアント実装
    - トークン取得（遅延初期化・自動再取得）、認証付きリクエスト（401 時に再取得してリトライ）
    - レスポンス JSON パースのエラーハンドリング、タイムアウトやネットワークエラーの変換
    - HTTP ステータスに応じた例外分類（401 / 429 / >=500 の扱い）
    - websocket / push を受けるための stream_push（存在する場合）と WebSocket スレッド連携に対応（payload の OrderID を用いた同期処理を前提）

- 監視機能
  - monitoring 用初期化と SystemMonitor のポーリング開始スクリプトを提供（run_monitoring）
  - 監視 DB 初期化ユーティリティ呼び出し（init_monitoring_db）

- リスク管理 / Rate limit / Circuit Breaker の統合（ExecutionEngine 側）
  - RiskManager を利用した Gate1（シグナルレベル）、Gate2（実行レベル / rate limit）、Gate3（ドローダウン）チェックを組み込み
  - Gate2 の rate limit は最大リトライ 3 回、Circuit Breaker 発動時はシグナルループを停止してドレインループは継続する挙動
  - API 成功/失敗の記録により rate limit 管理を行うフックを用意

- その他ユーティリティ参照
  - setup_logging（ログ設定）や set_process_priority（プロセス優先度設定）を呼び出す設計

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Deprecated / Removed / Security
- 初回リリースのため該当なし

補足 / 注意事項（実装からの推測）
- .env の読み込み順は OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。見つからない場合はスキップされるため、配布後も安全に動作する。
- PyYAML が未インストールの場合、config/*.yaml の内容検証はスキップされるが存在チェックは行われる。
- 実際の BrokerAPIProtocol / RiskManager / MonitoringDB 等の実体は別モジュール（コードベース内）に依存しており、ここに挙げたのは呼び出し側の契約や期待動作の説明です。

利用方法（抜粋）
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution

以上。必要があればリリース日付の追記や、各機能をより細かく分類した変更ログ（例: Bugfix / Minor）を追加します。