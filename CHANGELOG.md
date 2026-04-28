# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
重要な変更のみをコードベースから推測してまとめています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-28
初回リリース。自動売買システム KabuSys のコア CLI・ユーティリティ・レポート機能を実装。

### Added
- 基本情報
  - パッケージバージョンを定義: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。環境変数から各種設定を取得し、以下を提供:
    - J-Quants / kabuステーション / LINE API 関連の設定取得
    - DB パス（DuckDB/SQLite）、PID/kill フラグパス、監視閾値（CPU/MEM/DISK）など
    - KABUSYS_ENV / LOG_LEVEL の値検証
    - PAPER_FILL_MODE の検証（"instant"/"partial"/"never"/"reject" の有効値）
    - .env 自動ロード機能（プロジェクトルート検出、.env/.env.local の読み込み）。自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - settings インスタンスをモジュールレベルで提供。

- .env ファイルパーサ / ローダ
  - .env の堅牢なパース実装（クォート/エスケープ/コメント処理、`export KEY=val` 形式対応）。

- 環境設定ウィザード
  - 対話式に .env を作成・更新する CLI を実装（src/kabusys/config_setup.py）。
  - 大項目（KABUSYS_ENV、API トークン、DB パス、ログレベル、Kill Switch 等）の質問とファイル書き込み機能を提供。

- 設定検証 CLI
  - .env および config/*.yaml の存在・基本妥当性を検証する CLI（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML がない場合はスキップ）などを行い、errors/warnings/infos を出力。`--strict` で警告を失敗扱い可能。

- 実行エンジン起動スクリプト
  - ExecutionEngine 起動エントリ（src/kabusys/run_execution.py）。
    - 起動手順: ログ設定、プロセス優先度設定、DB 接続（paper_trading 環境では専用 SQLite を使用して本番 DB と分離）、ブローカークライアント生成、起動時総資産計算（現金 + 保有評価額）、依存コンポーネント組立（OrderRepository / OrderManager / RiskManager / Reconciler）、起動時リコンシリエーション、ExecutionEngine の起動。
    - paper_trading 環境向けに MockBroker を想定し、paper_trading 用 DB（環境変数またはデフォルト `data/paper_trading.db`）を使用。
    - PID ファイル・停止フラグ（data/stop_requested.flag）による安全停止機構を実装。
    - RiskConfig を YAML から読み込み、パラメータ検証（値域チェック、相互整合性チェック）を実装（src/kabusys/run_execution.py 内 _load_risk_config）。
    - 起動時に Execution Startup Summary（報告）を生成・保存（src/kabusys/operations/execution_startup_report.py と連携）。レポートは READY / READY_WITH_WARNINGS / BLOCKED の判定を含む。

- 監視プロセス起動スクリプト
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 常に本番 sqlite_path を監視に使用（環境に依存しない）。
    - stop フラグ検知でループ終了、例外発生時はログ出力して次ポーリングへ継続。
    - 起動時にプロセス優先度を "high" に設定する呼び出し。

- レポート / オペレーション
  - Signal Queue Confirmation View（src/kabusys/operations/signal_queue_report.py）
    - DuckDB の signals / portfolio_targets テーブルから翌営業日のシグナルを収集（collect_signals）。
    - 純粋関数でレポート構築（build_report）、CLI/JSON/Markdown フォーマッタ（format_cli_summary, format_json, format_markdown）、artifacts への保存機能（save_report）を提供。
    - save_report は artifacts/signal_queue/{date}/ に summary.json / report.md / warnings.json を出力。入力の report_date の妥当性チェックあり。
  - Execution Startup Summary（src/kabusys/operations/execution_startup_report.py）
    - Reconciler の結果から起動時サマリを作成。READY / READY_WITH_WARNINGS / BLOCKED の判定ロジックと警告生成を実装。
  - Pre-Market Report エントリポイント（src/kabusys/run_pre_market_report.py）
    - DuckDB / SQLite を読み取り、pre-market の状態（データ鮮度、signal queue、ポジション数、タスクスケジューラ等）を集約してレポートを出力。JSON 出力と artifacts 保存オプションあり。BLOCKED 状態で exit code 1。
  - Signal Queue Report CLI（src/kabusys/run_signal_queue_report.py）
    - 日付指定、JSON 出力、保存オプションを備えたエントリポイント。報告ステータスが READY なら exit code 0、それ以外は 1。
  - Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）
    - Paper trading の SQLite DB（デフォルト: data/paper_trading.db）から以下を集計:
      - システム稼働率（system_status）、注文成功率（trade_logs）、送信率、リスク却下数（risk_logs）、API レイテンシ（avg/max/P95）
    - P95 計算ロジックを含む。閾値を用いた PASS/FAIL 判定を出力。
    - CLI 引数で期間指定（--from/--to）、DB パス上書き可能。
  - operations と tools により、CLI でのヒューマンリーダブルな要約・JSON・Markdown の出力が可能。

- DB 接続・初期化
  - 監視用 DB の初期化呼び出し（init_monitoring_db）を run_monitoring/run_execution 起動時に実行してテーブル存在を保証（冪等）。

- ユーティリティ
  - プロセス優先度設定ユーティリティ利用（set_process_priority 呼び出し）。
  - ロギング設定ユーティリティ利用（setup_logging 呼び出し）。

### Changed
- n/a（初回リリースのため変更履歴なし）

### Fixed
- n/a（初回リリースのため修正履歴なし）

### Security
- 環境変数ファイル (.env) を自動的に Git にコミットしないよう注意喚起をドキュメントに記載（config_setup のヘッダー）。

---

注:
- 本 CHANGELOG はソースコードの内容から機能・挙動を推測して作成しています。実際のリリースノートへの反映時は、変更差分・コミット履歴を参照のうえ詳細を調整してください。