# Changelog

すべての変更は Keep a Changelog の形式に従っています。なお日付はこのリリース作成時点です。

## [0.1.0] - 2026-04-22

### Added
- 設定検証 CLI を追加
  - ファイル: src/kabusys/validate_config.py
  - .env と config/*.yaml の存在や基本的な値の妥当性を起動前にチェックする CLI を追加。警告を --strict モードで失敗扱いにできる。
  - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証、KABUSYS_ENV=live 時の追加ガードを実装。

- 環境設定ウィザードを追加
  - ファイル: src/kabusys/config_setup.py
  - 対話形式で .env を新規作成・更新するウィザードを追加。既存 .env の読み込み、シークレットマスク表示、選択肢提示、最終確認のうえ書き込みを行う。
  - .env のテンプレート書き出しロジックを実装（.env に保存すべきでない旨の注記を含む）。

- 環境設定管理モジュールを追加 / 強化
  - ファイル: src/kabusys/config.py
  - プロジェクトルート（.git または pyproject.toml）を基準に .env 自動読込を行う実装を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env 読み込みは優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き禁止）される。
  - .env の行パーサを強化（export KEY=val 形式対応、クォート文字のエスケープ対応、インラインコメント解析の改善）。
  - Settings クラスを導入し、環境変数をプロパティ経由で型付きに取得・検証できるようにした（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_sqlite_path, pid/kil l flag 関連、閾値等）。
  - PAPER_FILL_MODE の妥当性チェック（"instant"|"partial"|"never"|"reject"）を実装。

- 実行スクリプトを追加
  - ファイル: src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイント。paper_trading 環境時は paper 用 SQLite を使用するなど環境に応じた DB 分離を行う。
    - 停止フラグ / PID 管理、プロセス優先度設定、Logging セットアップを組み込む。
  - ファイル: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する。

- 注文処理周りのコアロジックを追加
  - ファイル: src/kabusys/execution/order_record.py
    - OrderRecord データモデルと状態遷移ロジック（OrderState 列挙、許可遷移マップ、transition_to メソッド）を追加。状態遷移の不正には専用例外 InvalidStateTransitionError を投げる。
  - ファイル: src/kabusys/execution/order_manager.py
    - OrderManager を追加。create/send/sync/cancel の外向き API を提供。
    - DuplicateOrderError、OrderRejectedError / OrderSentPendingError への対応、二相永続化 (OrderSent 前に DB 保存、broker_order_id 先保存 → 状態移行) によるクラッシュ耐性を実装。
    - sync_order で broker 側のステータスに同期（部分約定の進捗更新を含む）、cancel_order でキャンセル不可状態の検査を実装。

- 発注エンジンを追加
  - ファイル: src/kabusys/execution/execution_engine.py
    - ExecutionEngine 本体を実装。シグナル読込（DuckDB）、Gate1/2（シグナル・実行レベルのリスクチェック）、発注フロー、ドレインループ（push 処理）、Gate3（ドローダウンで kill switch 発動）を実装。
    - kill_switch により全 active 注文をキャンセルするロジックを実装。WebSocket push を受けるスレッドと _push_queue による非同期処理をサポート。
    - position_entries への約定記録（BUY / SELL の扱い分離）、監視 DB (MonitoringDB) へのイベント記録フックを用意。
    - PID ファイル管理、kill.flag の起動時チェック（KILL_FLAG_CLEAR_ON_START によるクリア）を実装。

- kabu station API クライアントを追加
  - ファイル: src/kabusys/execution/kabu_client.py
    - KabuStationClient を実装（httpx の同期 Client 使用）。トークン取得・再取得、自動リトライ（401 時）、HTTP エラー種別（429: RateLimitError 等）を取り扱う。
    - WebSocket push API（stream_push）が存在すればストリーミング受信に対応する形で設計。

- その他
  - パッケージメタ情報追加: src/kabusys/__init__.py に __version__ = "0.1.0"
  - 各コンポーネントで logging と process priority 設定フックを呼び出すように統一。

### Changed
- 設定の自動読み込みポリシーを明確化
  - プロジェクトルートを探索して .env を自動ロードする振る舞いを導入（配布後の相対パス問題に対応）。自動ロードは環境変数で無効化可能。

- DB の取り扱い
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用する仕様とした（監視は本番 DB を監視する想定）。
  - run_execution は paper_trading 時に paper_sqlite_path を使用し、本番 DB と完全に分離する仕様を追加。

### Fixed
- .env のパースと読み込みの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを改善し、より現実の .env フォーマットに耐性を持たせた。
  - .env 読込時にファイル読み込み失敗を警告に置き換えてプロセスが壊れないようにした。

- 発注フローのクラッシュ安全性向上
  - OrderManager.send_order において、OrderSent を DB に先に永続化し、その後 broker_order_id を保存 → OrderAccepted に遷移する二相永続化パターンを採用。クラッシュ時にリコンシリエーションで復旧可能になるようにした。
  - OrderSentPendingError の扱いを明確化（注文番号は発行されたが約定はないケースを DB に残して Reconciliation の対象とする）。

- sync_order の進化
  - 同一状態でも部分約定の進捗（filled_qty / avg_fill_price）が更新されている場合に DB を更新する挙動を追加。

### Security
- config_setup で生成する .env に対して「絶対に Git にコミットしないこと」を明示するヘッダを出力するようにした。

### Notes / Usage
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 実行:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- 自動環境読み込みを無効化する（テスト等）:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

### Removed
- なし

### Deprecated
- なし

もし特定の変更点について詳細（例: OrderRecord の遷移テーブル、ExecutionEngine の kill switch の振る舞い、.env のパース仕様など）が必要であれば、該当箇所のコード差分・設計意図を含めて追記します。