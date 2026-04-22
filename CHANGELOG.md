# CHANGELOG

すべての注記は Keep a Changelog の形式に従い、セマンティックバージョニングを採用します。  

既知のバージョン:
- 0.1.0 — 初回リリース

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-22
初回リリース。自動売買システム KabuSys のコア機能や運用ユーティリティをまとめて追加しました。

### Added
- 実行エントリ / 実行エンジン
  - run_execution.py を追加。ExecutionEngine を起動する CLI スクリプト。
  - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、紙トレード用 DB（デフォルト: data/paper_trading.db）に完全分離して記録。
  - エンジンは PID ファイル（data/execution.pid）を扱い、データベース接続（SQLite / DuckDB）を初期化して依存コンポーネント（OrderManager, OrderRepository, RiskManager, Reconciler 等）を組み立てる。
  - 停止フラグ（data/stop_requested.flag）による優雅な停止をサポート。

- 監視エントリ / System Monitor
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプト。
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を指定可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
  - 監視用 DB は環境に関わらず本番の sqlite_path を利用して初期化（init_monitoring_db）。
  - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定管理
  - config.py を追加。Settings クラスでアプリケーション設定（環境変数）を一元管理。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、各種閾値（CPU/MEM/DISK）などのプロパティを提供。
  - Settings に is_live / is_paper / is_dev 判定ユーティリティを追加。

- 設定支援 CLI
  - config_setup.py を追加。対話式ウィザードで .env を生成・更新するツール。
  - J-Quants トークンや kabu API パスワード等、秘密項目のマスク表示、デフォルト・選択肢のサポート、保存前の確認を実装。
  - 書き出しテンプレートは .env に安全に保存するよう注記あり（Git へコミットしない旨）。

- 設定検証 CLI
  - validate_config.py を追加。起動前に環境変数や config/*.yaml の有無・基本整合性を検証する。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、PyYAML がない場合の YAML 検証スキップ、KABUSYS_ENV=live 時の追加ガード等を実装。
  - --strict モードで警告を失敗扱いにできる。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。ペーパートレードの SQLite ログから各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計・レポート出力する CLI。
  - 日付範囲フィルタ（--from/--to）および DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
  - PASS/FAIL の閾値を定義（稼働率、成功率、送信率、P95 レイテンシ等）し、基準を満たさない場合に FAIL 理由を列挙。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコア総和が 0 の場合は警告して等配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジームは 1.0 でフォールバックし警告。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）。risk_based / equal / score の配分方式をサポート、単元株（lot_size）での丸め、コストバッファ・aggregate cap のスケーリングと残差配分ロジックを実装。

- ログ・ユーティリティ
  - utils.logging_setup.setup_logging を追加。ルートロガーを統一的に設定：
    - StreamHandler を stdout に出力（stdout を採用することで外部の stdout/stderr リダイレクトと整合）。
    - 日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log に出力、30日保持。
    - LOG_LEVEL / LOG_DIR / 引数による上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
    - 既存ハンドラを安全に flush/close してクリアすることにより重複出力を防止。

- プロセス優先度 / CPU affinity
  - utils.process_priority: set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。Windows（psutil の優先度定数を使用）と POSIX（nice 値）を吸収し、権限不足や未対応 OS に対しては警告でスキップする堅牢実装。

- 研究用ファクター計算（骨組み）
  - research.factor_research を追加（モメンタム / MA200, ATR 等の計算方針を実装）。DuckDB 接続を受け、prices_daily / raw_financials を参照してファクター算出を行う設計。※ファイル末尾は一部未完（続きを追加予定）。

- パッケージ情報
  - kabusys.__init__.py にて __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （現時点で特記事項なし）

----

補足（運用上の注目点）
- MONITOR_POLL_INTERVAL：監視ループの間隔を秒単位で設定可能（不正値はデフォルト 60 秒にフォールバック）。
- PAPER_FILL_MODE：paper_trading のモック約定モード（instant/partial/never/reject）を検証して不正値は例外とする。
- .env 自動ロードの挙動：OS 環境変数を優先し、.env は上書きされない（.env.local は上書き）。テスト等で自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
- ログはデフォルトで logs/ 以下に保存。ログディレクトリ作成に失敗した環境（権限等）でも stdout への出力にフォールバックして動作継続。

今後の予定（非包括的）
- research.factor_research の完全実装（関数継続・テスト追加）。
- ExecutionEngine / SystemMonitor 周りの更なる堅牢化・単体テスト追加。
- strategy モジュールやデータ取得パイプラインの追加実装。