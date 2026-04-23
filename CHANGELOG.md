# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。
意味のあるリリースごとにセクションを作成してください。

## [Unreleased]

## [0.1.0] - 2026-04-23

### Added
- 初回リリース。KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- 環境・設定管理
  - Settings クラス（kabusys.config）を追加。環境変数から設定を読み込み、型変換や妥当性検証を行う（KABUSYS_ENV / LOG_LEVEL 等の検証、PAPER_FILL_MODE の検証など）。
  - 自動 .env ロード機能を追加（プロジェクトルートを .git / pyproject.toml から検出）。優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサを実装。export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いに対応。
- 設定ウィザード CLI
  - kabusys.config_setup に対話式ウィザードを追加。`.env` の初期作成・更新を支援（項目定義、シークレット入力、デフォルト、選択肢表示、保存確認など）。
  - `.env` 書き出しフォーマットを確立（各種セクション、注意書き、Git コミットしない旨を明示）。
- 設定検証 CLI
  - kabusys.validate_config を追加。.env および config/*.yaml の問題を起動前に検出する CLI を提供。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）・プレースホルダ検出・KABUSYS_ENV / LOG_LEVEL の妥当性検証・DB パスの親ディレクトリ存在チェック・YAML パース検証（PyYAML 未インストール時はスキップ）・本番環境向けの追加ガードを実装。
  - --strict オプションで警告も失敗扱い（exit 1）にできる。
- 実行・監視起動スクリプト
  - run_execution（ExecutionEngine 起動）と run_monitoring（SystemMonitor ポーリング）を追加。いずれも Settings を利用して設定を取得する。
  - プロセス優先度設定ユーティリティ呼び出し、PID ファイル・停止フラグ管理、DB 接続（SQLite / DuckDB）および監視 DB 初期化を実装。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明記。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
- Execution エンジン・発注ワークフロー
  - ExecutionEngine を追加。シグナル処理（指定時間帯）・WebSocket push ドレインループ・セッションライフサイクルを実装。
  - ExecutionEngine 内に以下機能を実装:
    - kill.flag 検査と KILL_FLAG_CLEAR_ON_START による起動時自動クリアオプション。
    - PID ファイル書き込み・削除処理。
    - WebSocket push の背景スレッド（broker が stream_push を提供する場合）と push キュー処理。
    - シグナル読み取り（DuckDB クエリ）・Gate1/2/3 によるリスクチェック・レートリミット再試行ロジック・position_entries への記録。
    - Reconciler による起動時リコンシリエーション呼び出し（存在する場合）。
- 注文関連ロジック
  - OrderRecord（状態機械）を追加。状態遷移の許可表（allowed transitions）と transition_to による検証を実装。不正遷移時に InvalidStateTransitionError を発生。
  - OrderManager を追加。DB（OrderRepository）と OrderRecord を組み合わせ、create/send/sync/cancel の安全なフローを実装。
    - create_order: signal_id の重複検出（DuplicateOrderError）、UUID による client_order_id 発番、SQLite のユニーク制約考慮。
    - send_order: 2フェーズ永続化戦略（OrderSent を先に DB に保存 → broker へ送信 → broker_order_id を保存 → OrderAccepted に遷移）を実装。OrderRejectedError / OrderSentPendingError の取り扱いを行う。
    - sync_order: broker 側ステータス照合と部分約定情報の更新。OrderSent→(Partial/Fill) の場合に OrderAccepted を経由して遷移可能にする実装（リコンシリエーションを考慮）。
    - cancel_order: 終端状態のキャンセル拒否チェックと broker への cancel 呼び出し、Cancelled への遷移。
  - OrderManager は監視 DB（MonitoringDB）が提供されれば発注イベントのログを書き込む仕組みを持つ。
- Broker / kabu API クライアント
  - KabuStationClient を実装（kabu station REST API）。httpx を使用した同期クライアント。
  - トークン管理（遅延初期化・401 時の再取得）と 1 回リトライロジック、HTTP ステータスに応じた例外変換（401 / 429 / >=500 の扱い）を追加。
  - kabu ステータスコード → 内部ステータスマッピングを追加。
- 監視関連
  - run_monitoring スクリプトを追加。SystemMonitor を使ったポーリングループ、停止フラグ検知、例外キャッチでの継続処理を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env を Git にコミットしない旨を README/生成ファイルに明記（config_setup のヘッダに注意書き）。
- .env の読み込みは既存の OS 環境変数を保護する仕組みを導入（protected set）。.env.local は上書き可能だが OS 環境変数は上書かない。

### Notes / Implementation details
- 環境変数の妥当性検査は Settings 側でも行われ、プログラム実行時に即座に ValueError を投げることで早期検出する設計。
- Execution・Monitoring は DB コネクション（sqlite3 / duckdb）を明示的に作成・クローズする責務を持つ。
- Order の永続化・状態管理はクラッシュ耐性を考慮した設計（2 相永続化、Reconciliation を前提とした broker_order_id 保存など）。
- YAML のパース検証は PyYAML が利用可能な場合のみ実行され、未インストール時は警告を出してスキップする。

今後のリリースでは、テストカバレッジの追加、async 化対応（httpx.AsyncClient など）、監視・アラート強化、UI/運用スクリプトの整備を予定しています。