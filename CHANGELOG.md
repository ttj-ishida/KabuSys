CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このCHANGELOGは、提供されたコードベースの内容から推測して作成しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-22
------------------

Added
- パッケージ初回リリース。
- 環境設定/読み込み
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env/.env.local の読み込みロジックを提供。OS 環境変数を保護する protected オプション、override オプションをサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート（テスト用）。
  - .env パーサを実装：
    - export プレフィックス対応（export KEY=val）。
    - シングル/ダブルクォート文字列のエスケープ処理対応。
    - クォートなし行のインラインコメント処理（# の直前が空白/タブの場合にコメント扱い）。
- Settings（設定）クラス
  - 環境変数から各種設定値を取得する Settings クラスを提供（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、各種閾値など）。
  - env/log_level/paper_fill_mode 等の値検証を実装（不正値は ValueError を送出）。
  - paper_trading 向けの paper_sqlite_path、kill_flag 関連、閾値（CPU/MEM/DISK）等のプロパティを提供。
  - settings インスタンスをモジュールレベルで公開。
- 対話式設定ウィザード
  - python -m kabusys.config_setup で .env を対話式に作成・更新する CLI を実装。
  - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を含む。
  - 既存 .env を読み込み、既存値の再利用・マスク表示（シークレット項目）に対応。
  - .env を安全に書き出すヘルパーを実装（書き出しテンプレートに注意書きあり: Git にコミットしないこと）。
- 設定検証ツール
  - python -m kabusys.validate_config による CLI を実装。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）。
  - KABUSYS_ENV 値チェック、有効値（development, paper_trading, live）。
  - LOG_LEVEL の妥当性チェック。
  - DUCKDB/SQLITE の親ディレクトリ存在チェック（存在しない場合は警告）。
  - config/*.yaml の存在確認および PyYAML がある場合はパース検証（PyYAML 未インストール時は警告して検証をスキップ）。
  - KABUSYS_ENV=live の際の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定等）を追加。
  - --strict フラグにより警告もエラー扱い（exit(1)）にできる。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。
    - paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（stop_requested.flag / kill.flag）対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
- 実行エンジン（ExecutionEngine）
  - Signal Queue Pull 型の発注エンジンを実装。
  - EngineConfig により対象日・発注時間帯（デフォルト 8:50–9:10）・市場クローズ（15:30）を管理。
  - run_session によりリコンシリエーション実行、kill.flag チェック、PID 書き出し、WebSocket スレッド起動、シグナル処理ループ、push ドレインループを実行。
  - _process_signals() は多段の Gate（Gate1: シグナルレベル、Gate2: エグゼキューションレベル（レート制限・サーキットブレーカー））を通して発注。
  - 発注成功時に position_entries テーブルへ約定予定日を記録する処理を実装（DuckDB を使用）。
  - push 通知ハンドリング（_drain_push_queue/_handle_push）で sync_order を実行し、Gate3（ドローダウン監視）で必要なら kill_switch を発動。
  - kill_switch() は全 active 注文をキャンセルし停止フラグをセットする。
- 注文管理
  - OrderRecord（状態遷移ロジックを持つ純粋モデル）を実装：
    - OrderState 列挙と許可遷移テーブルを定義。
    - transition_to() により遷移検証、updated_at 自動更新、付随フィールド（broker_order_id, filled_qty, avg_fill_price, error_message）の更新をサポート。
    - 不正遷移時に InvalidStateTransitionError を送出。
  - OrderManager（外向き API）を実装：
    - create_order(): signal_id 重複チェック（DB の部分ユニークインデックス/アプリ側チェック）を行い DuplicateOrderError を送出。
    - send_order(): クラッシュ時の回復設計を考慮した 2 段階永続化戦略を実装（OrderSent を先に永続化 → ブローカー呼び出し → broker_order_id の永続化 → OrderAccepted に遷移）。
      - OrderRejectedError を捕捉して Rejected に遷移。
      - OrderSentPendingError（注文番号は得られたが確定しないケース）を特殊扱いして broker_order_id を保存した上で再送出。
    - sync_order(): broker からの状態を照会して状態を同期（部分約定の進行はフィールド更新のみで対応）。
    - cancel_order(): 終端状態確認後にキャンセル（終端状態では InvalidStateTransitionError を送出）。
- ブローカークライアント（kabu station）
  - KabuStationClient 実装（httpx を使用する同期クライアント）。
  - トークン取得処理（_get_token）と認証付きリクエスト(_request)を実装。401 発生時はトークン再取得して 1 回リトライ。
  - レスポンス JSON パース失敗やタイムアウト/ネットワークエラーを BrokerAPIError に変換。
  - 429 を RateLimitError として扱う。
  - kabu ステーションのステータスコードを内部ステータス ("open", "partial", "filled", "cancelled", "rejected") にマッピング。
  - WebSocket push の受信（stream_push が存在する broker に依存）を想定したストリーミングハンドリング設計。
- 監視・DB
  - monitoring_db 初期化のための init_monitoring_db 呼び出しを run_monitoring/run_execution 内で行い、監視用テーブルの存在を保証。
  - 発注イベントを監視 DB にログするフック（monitoring_db.log_trade_event）を ExecutionEngine 内で使用（監視 DB が設定されている場合）。
- ログ/プロセスユーティリティ
  - setup_logging / set_process_priority といったユーティリティを利用してログ設定・プロセス優先度変更を行う場所を用意。

Changed
- 初期リリースのため、既存との互換性に関する変更点はなし。

Fixed
- 初回リリースの状態のため、特定のバグフィックス履歴はなし（ただし設計上の注意点をドキュメントに反映）。

Removed
- 初回リリースのため、削除履歴はなし。

Security
- 環境変数や .env ファイルの取り扱いに注意する旨を明示（.env を絶対に Git にコミットしないこと）。
- kill_switch / 本番環境フラグに関するガードを追加（KABUSYS_ENV=live の際の注意喚起など）。

注意／マイグレーション
- PyYAML は必須ではない（validate_config は PyYAML 未インストール時は YAML パース検証をスキップして警告を出す）。YAML 内容の厳密検証が必要な場合は PyYAML をインストールしてください。
- validate_config の --strict モードは警告をエラーとして扱い exit(1) を返すため、CI 等で厳密チェックする場合は --strict を利用してください。
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path を使用します。監視 DB を環境に応じて切り替えたい場合は挙動を確認してください。
- run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。paper_trading 動作時の DB の分離に注意してください。
- ExecutionEngine は起動時に kill.flag の存在を確認します。KILL_FLAG_CLEAR_ON_START=1 を設定すると存在する kill.flag をクリアして起動しますが、本番では 0 を推奨します。

既知の制限
- kabu_client の一部実装はエラーメッセージやステータスハンドリングに依存しており、kabu ステーションの挙動（API レスポンス形式／WebSocket ペイロード）に合わせた追加調整が必要な場合があります。
- 一部のモジュール（Reconciler、MonitoringDB など）はここで参照され利用されますが、詳細な実装や外部依存の動作により微調整が必要になる可能性があります。

Contributors
- 単一リポジトリからの推測（作者情報はソースに明記なし）。