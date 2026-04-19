# CHANGELOG

すべての変更は「Keep a Changelog」形式に従います。  
このファイルはコードベースから推測できる機能追加・設計方針・既知の制約を基に作成しています。

## [Unreleased]
- ドキュメント化されていない内部改善やマイナー修正を収集中。
- 将来的に以下が想定されます：
  - research/factor_research モジュールの実装完了（現在ファイル末尾で未完部分あり）
  - 銘柄ごとの lot_size を stocks マスタから参照する拡張
  - price が欠損している場合のフォールバック価格導入（position_sizing 内 TODO）

---

## [0.1.0] - 2026-04-19
初期リリース — KabuSys: 日本株自動売買システム（コードベースから推定）

### Added
- コア実行スクリプト
  - run_execution.py: ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード専用 DB（data/paper_trading.db）を使用し、MockBrokerClient を利用する設計（BrokerClientFactory 経由）。
    - プロセス優先度を起動時に "high" に設定。
    - 停止制御: data/stop_requested.flag と data/execution.pid を使用して安全に停止/復帰。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了。

- 環境設定・検証関連 CLI
  - config_setup.py: 対話式 .env 作成/更新ウィザード（必須値の入力、既存 .env の再利用、保護注意喚起など）。
  - validate_config.py: 起動前の設定検証ツール（必須環境変数や config/*.yaml、パス等の検査、--strict オプションで警告を失敗扱いに）。
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL 判定を行う。

- 設定管理
  - config.py:
    - Settings クラスによる環境変数ラッパーを提供（各種既定値・検証ロジックを含む）。
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE などの設定をサポート。
    - 環境（KABUSYS_ENV）/ログレベル 等の検証を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates, calc_equal_weights, calc_score_weights を実装（スコア正規化・同点のタイブレーク等）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存保有を考慮して新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた新規発注株数の算出、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積り。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログ出力先を指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py:
    - set_process_priority: Windows と POSIX を吸収してプロセス優先度を設定（psutil を使用）。失敗時は警告でスキップ。
    - set_cpu_affinity: カレントプロセスを最初の N コアに固定するユーティリティ（権限不足等で失敗しても警告でスキップ）。

- データベース関連
  - 監視用 DB 初期化ユーティリティ呼び出し（monitoring_db.init_monitoring_db）を run_execution/run_monitoring で実行し、監視テーブルの存在を保証（冪等）。
  - DuckDB 接続を各所で利用（データ分析/ファクター計算用）。

- 研究・ファクター計算（下地）
  - research/factor_research.py:
    - Momentum/Value/Volatility/Liquidity 指標計算の設計と定数を含む実装下地。DuckDB の prices_daily / raw_financials テーブルを参照する前提。
    - ただしファイル末尾に未完の実装箇所があるため継続実装が必要。

- パッケージ情報
  - kabusys.__version__ = "0.1.0"

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Known issues / Notes
- position_sizing.calc_position_sizes 内:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメント。将来的に前日終値や取得原価等でのフォールバックを検討。
- research/factor_research.py は現状で一部実装が途中（ファイル末尾に start_da で切れている箇所あり）。ファクター計算の完成が必要。
- ロギングディレクトリの作成失敗時にはファイル出力が無効化されるが、警告は stdout/stderr に出力されるのみ。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で失敗する可能性あり（失敗時は警告でスキップする仕様）。
- Paper Trading と本番 DB は意図的に分離（paper_trading 用 DB: data/paper_trading.db）。環境変数または引数でパスを変更可能。

### Environment variables (主なもの・デフォルト)
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db（paper_trading 時に使用）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL: デフォルト INFO
- LOG_DIR: デフォルト logs/
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒） — デフォルト 60
- KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリアするか（0/1、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

---

（注）この CHANGELOG はリポジトリ内のソースコードを解析して推測した内容に基づいて作成しています。実際のリリースノートや変更履歴はコミットログやプロジェクト管理情報を参照して確定してください。