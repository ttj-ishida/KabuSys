Keep a Changelog
-----------------

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

未リリース
---------

- （現在なし）

0.1.0 - 2026-04-23
-----------------

Added
- 基本アーキテクチャの初期実装を追加（初期リリース）。
  - パッケージ情報
    - kabusys パッケージのバージョンを 0.1.0 に設定。
  - 設定管理
    - 環境変数/.env の自動読み込み機能を実装。
      - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込む。
      - OS 環境変数を保護する protected ロジックを導入し、.env.local で上書きできる仕組みを提供。
    - .env パース機能を強化。
      - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行内コメントの扱いを実装。
    - Settings クラスを実装し、各種設定（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、ログレベル、各種閾値など）を環境変数から取得するプロパティを提供。
      - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の値検証ロジックを実装（不正値で ValueError を送出）。
      - Paper Trading 用の専用 SQLite パス（PAPER_TRADING_SQLITE_PATH）や paper_fill_mode をサポート。
  - 環境設定ウィザード CLI（config_setup）
    - 対話式で .env を作成・更新するウィザードを実装。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を用意。
    - 既存 .env 読み込み、値のマスク表示、選択肢サポート、保存確認、--env-file オプション対応。
    - .env のテンプレート書き出しを実装（書き込み時に注意文を挿入）。
  - 設定検証 CLI（validate_config）
    - .env および config/*.yaml の設定不備を起動前に検出する CLI を実装。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）とプレースホルダ検出。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックと live 環境時の注意喚起。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）の親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml の存在確認と、PyYAML がインストールされている場合は YAML のパース検証（インストールがない場合は警告してスキップ）。
    - --strict モードで警告を FAIL として扱い非ゼロ終了コードを返すオプション。
  - 実行系スクリプト
    - run_execution: ExecutionEngine を起動するスクリプトを実装。
      - KABUSYS_ENV=paper_trading 時に paper_trading 用 DB を使用し、本番 DB と分離。
      - プロセス優先度設定、高優先度で実行するユーティリティ呼び出しを行う。
      - PID ファイル管理、停止フラグ（data/stop_requested.flag）検知、スレッド管理を実装。
    - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを実装。
      - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）と不正値フォールバック処理を実装。
      - 監視用 DB に接続して DuckDB / SQLite を扱う。
  - 実行エンジン（ExecutionEngine）
    - Signal Queue Pull 型発注エンジンを実装。
      - シグナル処理窓（8:50–9:10）と WebSocket push ドレインループ（9:10–15:30）を想定したセッション実行。
      - kill.flag 検査、起動時のリコンシリエーション呼び出し、PID 書き出し、WebSocket スレッド管理を実装。
      - Gate1: シグナルレベル検査、Gate2: エグゼキューションレベル（レート制限 / サーキットブレーカー）検査、Gate3: ドローダウン監視を組み合わせた安全制御。
      - 発注後に position_entries テーブルに約定予定日を書き込む処理（DuckDB 経由）を実装。
      - 発注 latency を監視 DB に記録するフックを提供（MonitoringDB 経由）。
  - 注文管理
    - OrderRecord: 注文状態機械（State Machine）と状態遷移ロジックを純粋ロジックとして実装。
      - 許可される状態遷移のマップを明示。InvalidStateTransitionError を導入。
    - OrderManager: 外向き API を実装。
      - create_order: client_order_id に UUID4 を採番、signal_id ごとの重複検出（DuplicateOrderError）。
      - send_order: クラッシュ耐性を考慮した 2 相永続化戦略を採用（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）。
        - OrderRejectedError / OrderSentPendingError（注文番号は得られたが約定しない/保留）をハンドリング。
      - sync_order: broker 側の注文状態を照会してローカル状態を同期。部分約定の進捗更新を考慮。
      - cancel_order: 終端状態のキャンセル不可能判定、broker cancel 呼び出し、Cancelled への遷移。
  - ブローカークライアント
    - KabuStationClient: kabu-station REST API クライアントを実装（httpx 同期クライアント）。
      - トークン取得と自動再取得ロジック（401 時に再取得してリトライ）。
      - httpx のタイムアウト/ネットワークエラーを BrokerAPIError にラップ。
      - 429 を RateLimitError として扱う。
      - WebSocket push 受信用の stream_push のハンドリング（存在しない broker の場合はスキップする保護）。
  - リスク管理 / リコンシリエーション / モニタリング（骨格）
    - RiskManager, Reconciler, MonitoringDB 等と連携するインターフェースを利用する設計を反映（詳細実装は各モジュールに依存）。
  - ユーティリティ
    - ロギングセットアップ / プロセス優先度設定ユーティリティを利用する起動フローに統合。

Changed
- 初版のため履歴なし。

Fixed
- 初版のため履歴なし。

Removed
- 初版のため履歴なし。

Notes / 補足
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
- run_execution/run_monitoring はデフォルトで data ディレクトリの PID/stop フラグ/DB を参照するため、data ディレクトリの権限や配置に注意。
- YAML の検証は PyYAML がインストールされていない環境でスキップされるが、存在チェックは行われる（config/*.yaml が必要な場合は generate_config スクリプト等で生成する旨の警告が表示される）。

参考
- 実行例:
  - 環境検証: python -m kabusys.validate_config [--strict]
  - 環境作成: python -m kabusys.config_setup
  - 実行: python -m kabusys.run_execution / python -m kabusys.run_monitoring

（必要に応じてこの CHANGELOG はリポジトリの実際のコミット履歴に合わせて追記・分割してください。）