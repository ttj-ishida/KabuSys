# Changelog

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。  
（注: 以下はリポジトリ内コードの内容から推測してまとめた変更点です）

## [0.1.0] - 2026-04-23

### Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎機能を追加。
- CLI / ユーティリティ
  - config_setup: 対話式ウィザードで .env を生成 / 更新するコマンドラインツールを追加。
    - 各設定項目の説明、デフォルト値、選択肢、シークレット表示（マスク）に対応。
    - 既存の .env を読み込み、Enter で再利用可能。
    - 最終的に .env をテンプレート形式で出力する機能を実装。
  - validate_config: .env と config/*.yaml の起動前チェックを行う CLI を追加。
    - --strict オプションで警告を失敗（exit(1)）として扱う。
    - 必須 / 任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェックなどを実施。
    - PyYAML が未インストールの場合は YAML 中身の検証をスキップし警告を出す。
  - run_execution: ExecutionEngine を起動するスクリプトを追加（本番 / ペーパートレードに対応）。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加（MONITOR_POLL_INTERVAL に対応）。
- 設定管理
  - Settings クラスを追加し、.env ファイル（.env/.env.local）や環境変数から設定を読み込む仕組みを実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う（配布後でも CWD に依存しない）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート（テスト用途）。
  - .env 読み込みロジック:
    - export プレフィックス対応（export KEY=val）。
    - シングル/ダブルクォート文字列のバックスラッシュエスケープ処理に対応。
    - クォートなしの値のインラインコメント処理の改善（'#' の直前がスペース/タブの場合のみコメントと判定）。
- Execution / Monitoring / DB
  - ExecutionEngine 実装：
    - シグナル読み込み（DuckDB）→ Gate1/Gate2 によるリスクチェック → 発注→ push ドレイン のフローを実装。
    - kill_switch 機構（全 active 注文のキャンセル、ループ停止）。
    - WebSocket push を受ける worker（broker が stream_push を提供する場合）。
    - PID / kill.flag の取り扱い（起動時クリアオプション、PID ファイル書き込み）。
    - 発注時の position_entries への書き込み（BUY/SELL の処理差異、fill_dateは翌営業日）。
  - Order 管理:
    - OrderRecord: 状態遷移を検証する状態遷移テーブルと transition_to() を実装（不正遷移は例外）。
    - OrderManager: create/send/sync/cancel の外向け API を提供。以下の主要設計を実装:
      - create_order: signal_id の重複チェック（部分ユニーク制約違反は DuplicateOrderError に変換）。
      - send_order: 2相永続化の設計（OrderSent を先に DB に残す → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）によりクラッシュ耐性を向上。
      - OrderSentPendingError の扱い（broker_order_id を保存したまま OrderSent に留め、呼び出し元へ例外伝播）。
      - sync_order: broker の get_order_status と同期し、filled/partial の更新を反映。状態遷移上の補助（OrderSent→直接Filled などのケースで OrderAccepted を経由）。
      - cancel_order: 終端状態はキャンセル不可とし、broker API 呼び出し後に Cancelled に遷移。
  - Broker 抽象 / 実装
    - KabuStationClient: kabu-station REST API クライアントを追加。
      - トークン取得の遅延初期化と 401 に対する自動再取得＋リトライを実装。
      - httpx の例外（Timeout / RequestError）を BrokerAPIError に変換。
      - 429 を RateLimitError として扱う。
      - JSON パース失敗を明示的な BrokerAPIError に変換。
- Risk / Reconciliation / Monitoring
  - RiskManager / Reconciler / Monitoring 用のインターフェースと呼び出しポイントを ExecutionEngine に組み込み（リスクゲート、レート制限、CB、API 成功/失敗の記録、Reconciliation 起動）。
  - Monitoring 起動時は KABUSYS_ENV に関わらず「本番 sqlite_path」を使用するように設計。
- プロセス運用
  - set_process_priority の呼び出しを起動直後に行い、優先度を "high" に設定するフローを run_execution/run_monitoring に追加。
- その他
  - __version__ を "0.1.0" としてパッケージに含める。

### Changed
- データベースパスのデフォルトや各種環境変数名を整理（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH など）。
- Paper trading 用 DB を本番 DB と分離（paper_trading モードでは paper_sqlite_path を使用）。
- Settings の各プロパティで値検証を強化（PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の妥当性チェック）。
- config_setup により .env のテンプレート生成とドキュメント的コメントを追加（.env を誤ってコミットしない注意文を含む）。

### Fixed
- .env パーシング処理の改善により、クォート内のエスケープや export プレフィックス、インラインコメント処理の不具合を解消。
- Order の状態遷移ロジックの不整合防止（Allowed transitions を明確化し、InvalidStateTransitionError を導入）。
- send_order のクラッシュシナリオを考慮した永続化順序を設計し、Reconciliation で状態回復できるようにした。
- YAML パーサ（PyYAML）が存在しない環境で起動時にクラッシュしないよう検出してスキップする挙動を実装（警告出力）。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して安全にデフォルトにフォールバックする処理を追加。

### Security
- .env の取り扱いについて config_setup の出力に「.env を Git にコミットしないこと」を明示。

### Known issues / Notes
- validate_config は PyYAML 未導入時に YAML の中身検証をスキップする。YAML 構文検証を必須にする場合は PyYAML を導入すること。
- run_execution / run_monitoring はローカルファイル（data/）への書き込みを行うため、実行環境のファイルパーミッションやディレクトリ構成に注意すること。
- KabuStationClient は httpx を使用した同期実装。将来的に非同期対応する場合は httpx.AsyncClient へ差し替え可能な設計。

---

今後のバージョンでは、テストカバレッジの拡充、より詳細な監視イベントの追加、broker クライアントのエラーハンドリングの強化（リトライ戦略の調整等）を予定しています。