CHANGELOG
=========

すべての重要な変更は Keep a Changelog 準拠で記録しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-22
--------------------

Added
- 初期リリース。
- 設定・起動支援ツール
  - 対話式 .env ウィザードを追加（kabusys.config_setup）
    - python -m kabusys.config_setup で実行。
    - KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等、主要な環境変数の入力を補助。
    - 秘匿値のマスク表示、選択肢・デフォルトのサポート、既存 .env の読み込み・更新。
    - .env の書き出しフォーマットを定義（Git にコミットしない旨のヘッダを含む）。
  - 設定検証 CLI を追加（kabusys.validate_config）
    - python -m kabusys.validate_config（--strict オプションで警告を FAIL 扱い）
    - 必須環境変数未設定やプレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在と YAML パース（PyYAML が存在する場合）をチェック。
    - live 環境向けの追加ガード（LINE通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
- 実行用スクリプト
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検知、デーモンスレッドでのエンジン実行。
  - Monitoring 起動スクリプト（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
- 設定管理（kabusys.config）
  - .env 自動ロード機能を搭載（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み優先順: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env パーサを実装（export プレフィックス対応、クォート文字列のエスケープ対応、インラインコメントの処理）。
  - Settings クラスを導入し、環境変数を型付けされたプロパティで提供。値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE など）で不正値は ValueError を送出。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や PID/KILL フラグパス等を提供。
- 発注/実行系コア
  - OrderRecord（kabusys.execution.order_record）
    - 注文状態列挙 OrderState と許容遷移を定義。
    - transition_to() による状態遷移検証と updated_at 自動更新を実装。不正遷移時は InvalidStateTransitionError を raise。
  - OrderManager（kabusys.execution.order_manager）
    - signal_id 重複防止（部分ユニークインデックスとアプリレベルチェック）で DuplicateOrderError を導入。
    - send_order における耐障害性向上（OrderSent を事前に永続化 → broker 呼び出し → broker_order_id の永続化 → OrderAccepted 更新 の 2 相永続化を採用）。
    - OrderRejectedError / OrderSentPendingError の扱いを実装。OrderSentPendingError は broker_order_id を保存したまま伝播。
    - sync_order による broker 側状態同期と部分約定更新の処理。
    - cancel_order 実装（キャンセル不可状態判定、API 呼び出し、Cancelled への遷移）。
  - ExecutionEngine（kabusys.execution.execution_engine）
    - シグナル取得（DuckDB）、Gate 1/2/3 による多段リスクチェック（シグナルレベル、実行レベル、ドローダウン監視）。
    - size_multiplier の適用（BUY のみ）、100株単位での切り捨て処理。
    - レート制限リトライ（Gate2）とサーキットブレーカー検出時のシグナルループ停止。
    - 発注時のレイテンシ計測、発注成功/保留/失敗のハンドリング、position_entries への書き込み（発注結果に応じてエントリ/クローズを記録）。
    - push（WebSocket）からの通知処理（_push_queue を介して sync と Gate3 チェックを実行）。
    - kill_switch 実装（全 active 注文のキャンセル試行、停止イベント設定）。
    - セッションライフサイクル制御（8:50 発注開始 → 9:10 発注締切 → 15:30 セッション終了）。
- Broker クライアント
  - KabuStationClient（kabusys.execution.kabu_client）
    - httpx を使った同期 REST クライアントを実装（認証トークン取得・自動再取得、リクエスト時の 401 リトライ処理）。
    - ステータスコードマッピング（kabu station の状態コード → 内部状態: open/partial/filled/cancelled/rejected）。
    - ネットワークエラー/タイムアウトを BrokerAPIError 等に変換。429 に対して RateLimitError を導入。
    - WebSocket push 受信（stream_push がある実装向け）。
- 監視連携
  - monitoring_db 初期化ロジック（init_monitoring_db）呼び出しにより、監視用テーブルの冪等初期化を保証。
  - 発注イベントを監視 DB にログ記録するフックを ExecutionEngine に追加（監視 DB が設定されている場合）。
- その他ユーティリティ
  - .env 読み込みの失敗を warnings.warn で通知（権限等でファイルが読めない場合の安全処理）。
  - Process 優先度設定ユーティリティ（set_process_priority）の採用（起動直後に CPU 優先度を上げる）。
  - ロギング初期化ユーティリティ（setup_logging）を利用。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （該当なし）

Notes / 考慮点
- validate_config は PyYAML が未導入の場合 YAML 内容の検証をスキップして警告するため、CI 等で厳密に YAML 構文を検査したい場合は PyYAML のインストールを推奨します。
- .env の自動ロードはデフォルトで有効。テストやプロセス間の環境隔離目的で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による無効化が可能です。
- ExecutionEngine のセッション制御や kill_flag の挙動はデフォルトで厳格に設定されています（残存する kill.flag があると起動を拒否）。テスト目的で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動でクリアしますが、本番では推奨されません。