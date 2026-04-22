CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

- （現在未リリースの変更はありません）

0.1.0 - 2026-04-22
-----------------

Added
- 初回リリース。以下の主要機能を実装。
  - 設定読み込み/管理（src/kabusys/config.py）
    - プロジェクトルートを .git / pyproject.toml から自動検出し、.env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
    - .env ファイルの堅牢なパース実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理をサポート）。
    - 環境変数取得ヘルパー _require と Settings クラスを提供。J-Quants / kabu API / DB /監視/システム設定等のプロパティを定義し、値の検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）を実施。
    - settings = Settings() の単一インスタンスを提供。

  - 環境設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式ウィザードで .env を作成/更新。シークレット項目のマスク表示、選択肢／デフォルト対応、既存値の再利用。
    - 書き込み時にテンプレートヘッダ付きで .env を生成。--env-file オプションに対応。
    - 初期に用意された設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。

  - 設定検証 CLI（src/kabusys/validate_config.py）
    - .env と config/*.yaml の起動前検証ツール。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLite パスの親ディレクトリ存在チェック、config/*.yaml の存在確認および PyYAML があればパース検証。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定など）。
    - --strict オプションで警告を FAIL 扱いにできる。

  - 実行スクリプト（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）
    - 共通: ログ設定・プロセス優先度設定、SQLite / DuckDB コネクション初期化、監視 DB 初期化を実装。
    - run_execution:
      - ExecutionEngine の起動フロー。paper_trading 環境では paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
      - 停止フラグ / PID ファイル管理、デーモンスレッドによるエンジン実行、停止時の安全クリーンアップ。
    - run_monitoring:
      - SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。

  - Execution エンジン本体（src/kabusys/execution/execution_engine.py）
    - Signal Queue 型発注エンジンを実装。セッション制御（signal_send_start / signal_send_end / market_close）と WebSocket push ドレイン。
    - 発注フローにおける 3 段階の Gate:
      - Gate 1: シグナルレベル検査（risk_manager.check_signal）
      - Gate 2: 実行レベル検査（レート制限、リトライ、サーキットブレーカー）
      - Gate 3: ドローダウン（ポートフォリオ評価に基づく kill switch 発動）
    - シグナルの size_multiplier 適用、BUY のみ数量切り捨て（100株単位）などの振る舞い。
    - 発注後に position_entries を DuckDB に書き込み（保有日数／再エントリー制御用）。
    - WebSocket スレッド経由で受けた push を処理し、該当注文の同期(sync_order) をトリガー。push がない場合でもポートフォリオ評価を行う設計。

  - 注文関連ロジック（src/kabusys/execution/order_record.py, order_manager.py, order_repository 連携）
    - OrderRecord: 状態遷移を厳密に管理する状態機械を実装（OrderCreated → OrderSent → OrderAccepted → PartialFill → Filled → Closed / Cancelled / Rejected）。不正遷移は InvalidStateTransitionError を送出。
    - OrderManager:
      - create_order: signal_id の重複防止（DB とプログラム内チェック）および UUID による client_order_id 採番。
      - send_order: クラッシュ耐性を考慮した 2 相永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移）。OrderRejectedError / OrderSentPendingError の取り扱いを実装。
      - sync_order: broker 側ステータスの取得とローカル状態の同期。部分約定の進行は差分更新により対応。
      - cancel_order: 終端状態ではキャンセル不可エラーを投げ、そうでなければ broker cancel を実行して Cancelled に遷移。
    - DuplicateOrderError, 状態マッピング定義などを提供。

  - broker クライアント: KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx を用いた同期 REST クライアント実装。トークン取得・キャッシュ・401 再取得リトライを実装。
    - レスポンス JSON パース失敗やネットワーク/タイムアウトを BrokerAPIError にラップ。
    - ステータスコード 429 を RateLimitError にマッピング。kabu ステータスコード → 内部ステータスのマッピングを提供。
    - WebSocket push（stream_push）をサポートする broker に対して WebSocket ワーカを統合する設計。

  - リコンシリエーション / 監視連携
    - ExecutionEngine 起動時に Reconciler を実行可能（存在する場合）。
    - MonitoringDB（インターフェース）へのトレードイベントログ記録ポイントを実装（発注レイテンシなど）。

  - ユーティリティ
    - robust な PID / stop flag 処理、プロセス優先度調整フック、ログセットアップフック（setup_logging）を利用。

Changed
- 初期実装のため該当なし。

Fixed
- 初期実装のため該当なし。

Notes
- .env はセキュアに扱うべきであり、config_setup で生成した .env を Git にコミットしないようヘッダに明記しています。
- YAML 検証は PyYAML がインストールされている場合にのみ行われ、未インストール時は警告を出してスキップされます。
- 一部の API 呼び出し（broker API など）は外部依存のため実行環境での動作確認が必要です。

開発上の補足（コードからの推測）
- セッション／発注フローは日本株寄り（100株単位など）を念頭に設計されています。
- データ層に DuckDB を分析用、SQLite を監視/履歴用として使い分ける設計です。
- paper_trading 用に本番 DB と分離する仕組みが用意されています（PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE）。

--- 
（本 CHANGELOG は提示されたソースコードの内容から推測して作成したもので、実際のリリースノートはプロジェクトの正式な履歴に基づいて更新してください。）