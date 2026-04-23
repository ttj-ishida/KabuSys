# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース。

### Added
- パッケージのバージョンを `__version__ = "0.1.0"` として追加。
- 環境設定 / 起動補助 CLI を追加:
  - python -m kabusys.config_setup
    - 対話式ウィザードで .env の初期作成・更新を支援するツールを追加。
    - 設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を含む。
    - シークレット項目はマスク表示、選択肢・デフォルト値のサポート、保存確認を実装。
  - python -m kabusys.validate_config
    - .env と config/*.yaml の起動前検証ツールを追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）、KABUSYS_ENV/LOG_LEVEL 値検証、DBパスの親ディレクトリ存在確認、YAML パース（PyYAML が無ければスキップ）を実施。
    - `--strict` フラグにより警告も失敗（exit 1）扱いにできる。
- 設定読み込み/管理:
  - `kabusys.config.Settings` クラスを追加。環境変数から設定を取得する一元化された API を提供。
  - .env の自動ロード機構を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理等に対応）。
  - .env 読み込みは OS 環境変数を保護（読み込み時の protected set）し、`.env.local` を .env より優先して上書きできる。
  - Paper Trading 向け設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。
- 実行スクリプト:
  - `run_execution.py`
    - ExecutionEngine を起動するエントリポイント。paper_trading 環境では専用 SQLite DB を使用し、本番 DB と分離。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- Execution エンジン / 発注ロジック:
  - `ExecutionEngine` を追加:
    - シグナル処理（8:50-9:10） → push ドレインループ（9:10-15:30）のセッション実行フロー。
    - WebSocket push を受けるワーカー（broker が `stream_push` を持たない場合はスキップ）。
    - PID ファイル書き出し、kill.flag による起動拒否/クリアの挙動を実装。
    - Gate1/2/3 によるリスクチェックと kill_switch 発動ロジックを搭載。
    - position_entries の DuckDB 書き込みを実装（entry/sell の記録）。
  - `OrderRecord`（状態遷移ロジック）を追加:
    - OrderState enum と許可される遷移テーブルを定義。無効遷移時は `InvalidStateTransitionError` を送出。
    - 状態遷移時に更新フィールド（broker_order_id / filled_qty / avg_fill_price / error_message）を反映。
  - `OrderManager` を追加:
    - create_order, send_order, sync_order, cancel_order を実装。
    - send_order はクラッシュ耐性を高めるための 2 段階永続化（OrderSent を先にコミット → broker 呼び出し → broker_order_id をコミット → OrderAccepted へ遷移）を採用。
    - OrderSentPendingError（注文番号は発行されたが約定しないケース）を適切に扱う。
    - 同一 signal_id の重複注文防止（DuplicateOrderError）を実装。
    - sync_order で broker の状態を取得し DB と同期。部分約定の進展はフィールド更新で反映。
    - cancel_order はキャンセル不可能な状態を拒否し、broker に対してキャンセル API を呼ぶ。
- ブローカークライアント:
  - `KabuStationClient` を実装（httpx 同期クライアント、将来の async 対応が容易）。
    - Token の遅延取得・自動再取得（401 リトライ）を実装。
    - レスポンス JSON パースエラーやタイムアウト、ネットワークエラーを BrokerAPIError 等に変換。
    - HTTP 429 に対して RateLimitError を返す。
    - kabu station の状態コードを内部ステータスにマッピング。
- 監視 / DB:
  - Monitoring 用 DB 初期化（init_monitoring_db）を実行スクリプトで利用（監視テーブルの冪等初期化）。
  - 発注時の監視 DB への書き込み（latency, 状態等）を ExecutionEngine に組み込み、書き込み失敗時は警告で続行する実装。
- その他ユーティリティ:
  - プロセス優先度設定（set_process_priority）およびログ設定（setup_logging）を run スクリプトで使用。
  - 環境変数の必須/任意一覧や有効値集合（KABUSYS_ENV, LOG_LEVEL 等）を明示的に定義。

### Changed / Improved
- .env パーサの堅牢化:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、インラインコメントの扱いを正しく実装。
- 自動ロード時の安全性強化:
  - OS 環境変数は protected として上書きされないように実装。
  - プロジェクトルート検出ロジックにより CWD に依存せずに .env を自動読み込み。
- 実行時安全性の向上:
  - send_order における 2 段階永続化でクラッシュ時のリカバリ可能性を高め、Reconciliation 処理との整合性を確保。
  - ExecutionEngine の起動/終了フローにおいて kill.flag の扱いと KILL_FLAG_CLEAR_ON_START の挙動を明確化。
  - run_monitoring の MONITOR_POLL_INTERVAL の不正値耐性を追加（不正ならデフォルトにフォールバック）。
- エラーメッセージ・ログを充実化:
  - validate_config における情報/警告/エラー出力を整備し、--strict モードを追加。
  - 各所で例外発生時にログを残し、可能な限り処理を継続する設計（監視 DB / position_entries 書き込み失敗など）。

### Fixed
- DB/ファイルパス関連の注意点を明示:
  - DUCKDB_PATH / SQLITE_PATH の親ディレクトリが存在しない場合に警告を出すようにした（起動時に自動作成される場合がある旨を記載）。
- YAML 検証の可搬性:
  - PyYAML 未インストール時は YAML パース検証をスキップし、警告を出すようにして起動環境に依存しない動作を確保。

### Removed
- なし

### Deprecated
- なし

### Security
- なし（ただしシークレット項目は対話ウィザードでマスク表示し、.env は Git にコミットしないよう注意喚起を追加）。

---

注記:
- 本リリースはコードベースから推測して作成した CHANGELOG です。実際の変更履歴やリリース日付は開発時の履歴に従って調整してください。