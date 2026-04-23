# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトはセマンティック バージョニングを採用します。

## [Unreleased]
（次回リリースに向けた未リリースの変更をここに記載します）

## [0.1.0] - 2026-04-23
初回リリース。本リリースでは自動売買システム「KabuSys」のコア設定・起動・発注・監視周りの機能を実装しています。

### Added
- 全体
  - パッケージ初期バージョン v0.1.0 を追加。
  - モジュール一覧（data, strategy, execution, monitoring）を __all__ に定義。

- 環境設定・管理
  - Settings クラス（kabusys.config）を追加。環境変数からアプリ設定を取得する統一 API を提供。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を取得するプロパティを実装（未設定時は ValueError を送出）。
    - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH）を Path 型で取得。
    - PAPER_FILL_MODE の妥当性検証（"instant"|"partial"|"never"|"reject"）。
    - env/log level 等の妥当性検証および env 判定補助プロパティ（is_live / is_paper / is_dev）。
  - .env ファイル自動読み込み機能を導入（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパース実装強化: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。

- 設定ウィザード CLI
  - kabusys.config_setup: .env の初期作成／対話式更新ウィザードを追加。
    - 対話で入力可能な項目定義（実行環境、J-Quants トークン、kabu API パスワード、DB パス、LINE 通知設定、ログレベル、Kill Flag オプション等）。
    - 既存 .env の読み込み再利用、確認プロンプト、ファイル書き出し機能を提供。
    - 秘密値は表示時にマスク。

- 設定検証 CLI
  - kabusys.validate_config: 起動前に .env および config/*.yaml を検証する CLI を追加。
    - 必須環境変数の存在チェック、プレースホルダ値検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在確認を実施。
    - config/*.yaml の存在確認および PyYAML があればパース検証を実行（未インストール時は警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict オプションで警告を FAIL（exit 1）として扱う。

- 実行スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - paper_trading モード時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - PID / stop flag の扱い、プロセス優先度設定、Logging 設定呼び出しを統合。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する。

- 発注・エンジン・ブローカークライアント
  - ExecutionEngine（kabusys.execution.execution_engine）を実装。
    - シグナル処理ウィンドウ（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）に対応。
    - kill.flag 検査、PID ファイル操作、WebSocket スレッド、push queue 処理、position_entries への書き込み。
    - Gate チェック（Gate1: signal レベル、Gate2: 実行レート制御、Gate3: ドローダウン監視）を組み込み、kill_switch により全注文キャンセルを実行。
  - OrderRecord（kabusys.execution.order_record）: 注文状態遷移のデータモデルと状態遷移ロジックを純粋ロジックとして実装。
    - OrderState 列挙と許可遷移マップを定義。
    - transition_to により遷移検証、タイムスタンプ更新、オプションフィールド更新を実施。無効遷移は専用例外を発生。
  - OrderManager（kabusys.execution.order_manager）を実装。
    - create/send/sync/cancel の外向き API を提供。
    - DuplicateOrder の検出（signal_id の部分ユニーク制約および DB 参照）。
    - send_order はクラッシュ安全性を意識した 2 相永続化（OrderSent 先に永続化→broker 呼び出し→broker_order_id 永続化→OrderAccepted へ遷移）。
    - OrderRejectedError / OrderSentPendingError の扱いを実装。
    - sync_order により broker 側ステータスと同期（部分約定の増分更新に対応）。
    - cancel_order はキャンセル不可能状態を検査し、broker cancel を実行して Cancelled に遷移。
  - Broker API 周りの型／エラー処理（BrokerAPIProtocol, OrderRequest, OrderResponse 等）とインターフェースを前提とした実装を含む。
  - KabuStationClient（kabusys.execution.kabu_client）を追加。
    - httpx を用いた同期 REST クライアント（トークン管理、自動再取得、401 リトライ、429 レートリミット判定、タイムアウト/ネットワーク例外を BrokerAPIError に変換）。
    - kabu ステーションの注文状態コード→内部状態マッピング。
    - 将来的な async 対応を見据えた設計。
    - WebSocket push 受信（stream_push）を想定した on_message ハンドリング（ExecutionEngine と連携）。

- 監視 DB 初期化
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を run_monitoring/run_execution で利用して監視テーブルを準備。

- ユーティリティ
  - process_priority 設定、logging_setup 呼び出しの導入（起動時に適切な優先度とログ設定を適用）。
  - run_* スクリプトでの例外ハンドリングとリソースクローズ（sqlite/duckdb 接続のクローズ）を実装。

### Changed
- N/A（初回リリースのため過去バージョンからの変更点はありません）

### Fixed
- N/A（現時点で既知の修正履歴はありません）

### Notes / Known behaviors
- .env のパースは多くのケース（クォート、エスケープ、コメントなど）に対応していますが、極端な形式の .env がある場合は想定外の挙動になる可能性があります。
- ExecutionEngine のセッションスケジュール（8:50 / 9:10 / 15:30）はコード内定数であり、必要に応じて EngineConfig で上書き可能です。
- run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計です（監視の一貫性確保のため）。
- config/*.yaml のパース検証は PyYAML がインストールされている場合にのみ実行されます。未インストール時は警告となります。

---

今後の予定:
- 単体テスト、結合テストの追加
- async クライアント対応やより詳細な監視イベントの拡張
- ドキュメントの追加（運用手順、デプロイ手順、設定例）