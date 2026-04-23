CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。
セマンティックバージョニングを採用しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-23
------------------

Added
- パッケージ初期リリース: KabuSys 自動売買基盤の基本機能を実装。
  - パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0"。
- 環境設定 / ロード
  - .env 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml から検出し、.env と .env.local を自動で読み込む（OS 環境変数 > .env.local > .env の優先順位）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 読み込み時の上書き制御と保護（protected）機能を考慮。
  - .env パーサ:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート、バックスラッシュエスケープに対応した値パース。
    - クォート無しのインラインコメントの扱い（直前が空白/タブの場合は # をコメントと認識）。
- 設定アクセス API
  - Settings クラス（src/kabusys/config.py）:
    - 各種環境変数をプロパティとして取得（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、各種閾値など）。
    - env/log_level 等の値検証（不正値は ValueError を送出）。
    - PAPER_FILL_MODE の有効値チェック。
    - paper_trading 用の別途 SQLite パス（PAPER_TRADING_SQLITE_PATH）をサポート。
- .env 設定ウィザード CLI
  - src/kabusys/config_setup.py:
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 秘匿項目は表示時マスク、選択肢/デフォルト/説明表示あり。
    - 生成される .env のテンプレートを自動書き込み。
    - 実行例: python -m kabusys.config_setup
- 設定検証 CLI
  - src/kabusys/validate_config.py:
    - .env と config/*.yaml の起動前検証ツール。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックと警告（live 時の注意喚起）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）の親ディレクトリ存在チェック。
    - PyYAML があれば config/*.yaml を safe_load によりパースして整合性検証（未インストール時はスキップして警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定チェック）。
    - --strict フラグで警告を FAIL（exit(1)）として扱うオプション。
    - 実行例: python -m kabusys.validate_config, python -m kabusys.validate_config --strict
- 実行スクリプト
  - run_execution (src/kabusys/run_execution.py):
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止をサポート。
  - run_monitoring (src/kabusys/run_monitoring.py):
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検出でループを終了。
- Execution コンポーネント
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）:
    - Signal Queue Pull 型の発注エンジンを実装。
    - セッションスケジュール: シグナル処理期間（デフォルト 8:50-9:10）、push ドレイン（9:10-15:30）、市場クローズ処理。
    - 起動時の Reconciliation（reconciler が設定されている場合）サポート。
    - PID ファイル書き込み・削除、kill.flag の存在チェックと KILL_FLAG_CLEAR_ON_START の挙動考慮。
    - WebSocket スレッドで kabu の push を受信して内部キューへ投入（broker が stream_push を提供する場合のみ）。
    - シグナル処理フロー:
      - size_multiplier 適用（買いのみ、100株単位切り捨て）。
      - Gate 1: シグナルレベル検査（RiskManager）。
      - Gate 2: エグゼキューションレベル検査（レート制限・リトライ・サーキットブレーカー対応）。
      - 発注処理: create_order → send_order（OrderManager） といった堅牢な二相永続化を意識したワークフロー。
      - 発注成功/保留/失敗の取り扱いと監視 DB へのログ記録（MonitoringDB が提供されている場合）。
      - Gate 3: ドローダウン監視により異常時は kill_switch を発動。
    - kill_switch: 全 active 注文のキャンセル処理（BrokerAPIError の継続処理考慮）。
  - OrderState / OrderRecord（src/kabusys/execution/order_record.py）:
    - 注文状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許容遷移を定義。
    - OrderRecord dataclass と状態遷移メソッド transition_to を実装。許可されない遷移は InvalidStateTransitionError を送出。
    - updated_at は UTC で自動更新。
  - OrderManager（src/kabusys/execution/order_manager.py）:
    - OrderRecord と OrderRepository を組み合わせた外向き API。
    - create_order: signal_id のアクティブ重複を検出して DuplicateOrderError を送出。UUID を client_order_id として採番。
    - send_order: クラッシュ耐性を考慮した処理手順（OrderSent の永続化を broker 呼び出し前に行う等）、OrderRejectedError と OrderSentPendingError の扱い。
    - sync_order: broker のステータスを取得してローカル DB に同期。部分約定の進行に応じて filled_qty / avg_fill_price の更新。
    - cancel_order: 終端状態ではキャンセル不可のチェックと broker API 呼び出し後に Cancelled へ遷移。
  - Broker API 抽象 / kabu クライアント
    - KabuStationClient（src/kabusys/execution/kabu_client.py）:
      - httpx を用いた同期 REST クライアント実装（将来 async 対応を想定して設計）。
      - トークン管理: 遅延初期化、401 での自動再取得とリトライ。
      - レスポンス JSON パース失敗やタイムアウト / ネットワークエラーを BrokerAPIError に変換。
      - 429 を RateLimitError として扱う。
      - kabu ステータスコード（1-7）を内部ステータス ("open", "partial", "filled", "cancelled", "rejected") にマッピング。
- 監視・DB 初期化
  - monitoring_db の初期化をサポートする init_monitoring_db の呼び出し（起動時に監視テーブルを保証）。
- ユーティリティ
  - プロセス優先度設定ユーティリティとログ設定のフックポイント（setup_logging, set_process_priority の呼び出しを実装）。

Notes / 補足
- YAML パースによる config/*.yaml の内容検証は PyYAML がインストールされている場合のみ実施。未インストール時は検証をスキップして警告を出力。
- Settings のプロパティは不正な値で ValueError を発生させることがあるため、起動前に validate_config CLI で検査することを推奨。
- 実装上の DB スキーマや OrderRepository の実装詳細（SQLite テーブル定義など）はこの変更ログに含まれていないが、Execution / Monitoring の起動時に init_monitoring_db を呼んで冪等に初期化する設計になっている。

今後の予定（推測）
- Reconciler / OrderRepository の詳細実装とテストの充実。
- 非同期クライアント（httpx.AsyncClient）への移行による高負荷時の改善。
- 監視・アラート機能の拡張（LINE 以外のチャネル、アラート閾値の UI 化等）。

---