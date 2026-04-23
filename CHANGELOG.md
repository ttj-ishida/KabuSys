# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-23

### Added
- 初回リリース: KabuSys 基本コンポーネントを追加。
- 環境変数 / 設定管理
  - 自動 .env 読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を探索して特定）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルの堅牢なパーサを実装（export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
  - _load_env_file による上書き動作（override/protected による OS 環境保護）。
  - Settings クラスを実装し、環境変数を型付きプロパティとして提供（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、env 判定、しきい値等）。
  - 設定値検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）は Settings のプロパティで ValueError を投げて明示的に検出。

- .env 設定ウィザード CLI
  - 対話式ウィザード（kabusys.config_setup）を追加。.env の初期作成・更新を支援。
  - 秘密値のマスク表示、選択肢・デフォルト表示、既存 .env 読み込み、--env-file オプション、保存時の注意書き（.env をコミットしないよう警告）を実装。

- 設定検証 CLI
  - kabusys.validate_config を追加。.env と config/*.yaml の起動前検証を実行。
  - 必須 / 任意の環境変数チェック、プレースホルダ検出、KABUSYS_ENV の妥当性チェック（development/paper_trading/live）、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェックを実装。
  - PyYAML が存在する場合は config/*.yaml をパースして内容検証（存在しないファイルは警告）。--strict オプションで警告を FAIL 扱いにする。

- 実行スクリプト
  - run_execution.py を追加。ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - PID ファイル管理、stop フラグ検出による安全な起動/停止ロジックを実装。
    - プロセス優先度を設定（utils.process_priority）。
  - run_monitoring.py を追加。SystemMonitor をポーリング実行するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を使用。

- 発注 / 実行基盤
  - ExecutionEngine を実装（signal の読み込み → Gate1/Gate2 を通じて発注 → WebSocket push のドレイン）。
    - シグナル処理時間帯管理（デフォルト 8:50–9:10）、マーケット終了時刻（デフォルト 15:30）をサポート。
    - kill.flag 検査・KILL_FLAG_CLEAR_ON_START の挙動、PID 書き込みと削除を実装。
    - WebSocket スレッド（broker が stream_push を持つ場合）による push 処理をサポート。
    - position_entries への書き込み（約定日に基づく保有日数管理）を実装。
    - 発注に関する監視 DB へのログ出力フックを追加（MonitoringDB が渡された場合）。
  - run loop 内の例外処理やクラッシュ安全性を考慮した設計（OrderSent の2相永続化など）。

- 注文管理（Order）
  - OrderRecord: 注文状態を表す state machine を実装（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）。
    - 許可される状態遷移を定義し、InvalidStateTransitionError を導入。
    - transition_to によりオプションフィールド（broker_order_id / filled_qty / avg_fill_price / error_message）を安全に更新。
  - OrderManager: DB（OrderRepository）と Broker API を結合する外向き API を実装。
    - create_order: signal_id 単位の重複防止（DuplicateOrderError）、UUID で client_order_id を付与、SQLite のユニーク制約違反を DuplicateOrderError に変換。
    - send_order: 安全な順序で OrderSent を永続化 → broker 送信 → broker_order_id 永続化 → OrderAccepted へ遷移。OrderRejectedError, OrderSentPendingError の扱いを明確化。
    - sync_order: broker からのステータス取得によりローカル状態を同期。部分約定の進展はフィールド更新で対応。
    - cancel_order: キャンセル不可状態の判定、broker への cancel 呼び出しと Cancelled への遷移。

- ブローカークライアント
  - KabuStationClient を実装（httpx 同期クライアント）。
    - トークン管理（遅延取得、401 を受けたら再取得して1回リトライ）。
    - HTTP レスポンスの JSON パースエラーやタイムアウト・ネットワークエラーを BrokerAPIError にマッピング。
    - 429 を RateLimitError に変換、5xx をサーバーエラー扱いでエラー化。
    - kabu station の内部状態コードマップ（数値→open/partial/filled/...）を定義。
    - 将来の async 化を見据えた実装コメント。

- リスク管理 / リコンサイル / 監視連携（骨格）
  - ExecutionEngine から RiskManager、Reconciler、MonitoringDB との連携ポイントを実装（Gate1/2/3、Reconciliation の呼び出し・結果ログ出力）。

- パッケージ情報
  - パッケージ初期バージョン __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Breaking changes
- Settings のプロパティは環境変数の妥当性チェック時に ValueError を投げます。既存の外部コードが直接環境変数の未設定・不正値を許容していた場合は影響があります。
- .env は絶対に VCS にコミットしないでください（config_setup のヘッダにも注意書きを記載）。
- run_monitoring と run_execution はそれぞれ別プロセスで実行する想定です。paper_trading モードでは実取引を行わないよう DB を分離しています。

----

旧バージョン履歴はこの初回リリース時点ではありません。今後のリリースでは Unreleased セクションを用いて変更を追記します。