# CHANGELOG

すべての変更は「Keep a Changelog」形式に従い、重要な変更のみを列挙しています。

全般方針:
- バージョン番号はパッケージ内の __version__ に合わせて記載しています。
- 日付は本リリース作成日です。

## [Unreleased]
（今後の変更を記載）

## [0.1.0] - 2026-04-30
初回リリース

### Added
- 基本パッケージメタ情報
  - パッケージバージョンを __version__ = "0.1.0" として追加。
- 実行用エントリポイント（CLI）
  - run_execution: ExecutionEngine 起動スクリプトを追加。実行エンジンの起動、起動時リコンシリエーション、Execution Startup Summary の生成、スレッドによる実行管理、停止フラグ対応を実装。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時の総資産計算（現金 + ポジション評価額）を追加。
    - 注文管理、リスク管理、リコンシリエーション、レポート保存の組立を行う。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - プロセス優先度設定、PID ファイル生成、停止フラグ検出を実装。
  - run_intraday_monitor: ザラ場中監視の対話型 CLI を追加（ワッチモード/間隔指定対応）。
    - 状態評価（OK / WARNING / CRITICAL）と CLI 向けサマリ表示を提供。
  - run_position_reconciliation_report: 日次ポジション照合レポート生成 CLI を追加（watch モード、JSON/保存オプション対応）。
  - run_signal_queue_report: Signal Queue 確認ビュー生成 CLI を追加（日付 / JSON / 保存オプション対応）。
  - run_pre_market_report: Pre-Market レポート生成 CLI を追加（stop flag を考慮、JSON/保存対応）。
  - run_market_close_report: Market Close Summary レポート生成 CLI を追加（JSON/保存対応）。
  - run_performance_report: 運用成績サマリーレポート生成 CLI を追加（daily/weekly/monthly、環境切替、日付範囲、保存オプション）。
- 設定管理・ウィザード・検証
  - config.py: Settings クラスを実装。
    - 環境変数読み込み（.env, .env.local の自動ロード）、プロジェクトルートの自動検出（.git または pyproject.toml を起点）。
    - 必須環境変数取得ヘルパ、各種パス（duckdb, sqlite, paper_sqlite）と論理フラグ（is_live / is_paper / is_dev）を提供。
    - paper_fill_mode の妥当性チェックを実装（instant / partial / never / reject）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を使った自動ロード無効化に対応。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 秘匿項目は表示マスク、既存 .env の読み込み・再利用、出力テンプレートを実装。
  - validate_config.py: 起動前に設定を検証する CLI を追加。
    - 必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、データベースパスの親ディレクトリ存在確認、config/*.yaml 存在および YAML パース検証（PyYAML の有無で動作分岐）を実装。
    - KABUSYS_ENV=live 用の追加警告（LINE 未設定や KILL_FLAG_CLEAR_ON_START の危険値など）。
    - --strict オプションで警告も失敗として扱う機能。
- 監視・プロセス管理
  - stop/kill フラグ、PID ファイルの取り扱いを統一（data/*.pid, stop_requested.flag 等）。
  - プロセス優先度を設定するユーティリティを利用（set_process_priority）。
- モニタリング関連
  - monitoring_db の初期化呼び出しを実装（init_monitoring_db）。
  - Intraday、Pre-Market、Market-Close、Signal-Queue、Position Reconciliation、Performance の各種 collector/report 機能を呼び出す CLI を追加。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。ペーパートレード履歴（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し、閾値判定（稼働率 99%、成功率 90% など）を行う。
- DB 接続
  - DuckDB と SQLite の組み合わせで読み取り専用接続を行うCLIが複数追加（read_only オプション利用）。
- レポート出力形式
  - CLI は JSON / CLI サマリ / Markdown など複数形式での出力をサポートし、保存オプションで artifacts 配下に保存可能。

### Changed
（初回リリースのため過去変更はなし。将来の変更はここに記載）

### Fixed
（初回リリースのためなし）

### Security
（なし）

---

注記（実装上の重要ポイント、利用時の注意）
- 環境変数自動ロードはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視用 DB（settings.sqlite_path）を KABUSYS_ENV に関係なく使用します。Execution は is_paper 判定で paper_sqlite_path に切替え、paper_trading と本番 DB を分離しています。
- MONITOR_POLL_INTERVAL は整数で 1 以上を要求します。不正な値を指定した場合は警告を出しデフォルト 60 秒にフォールバックします。
- config/*.yaml の検証は PyYAML がインストール済みであることを前提とします（未インストール時は YAML 内容チェックをスキップして警告を出します）。
- 各 CLI は停止フラグ（data/stop_requested.flag 等）や PID 管理、タイムアウト/Join の扱いを行います。運用環境での監視/再起動方法はドキュメントに従ってください。