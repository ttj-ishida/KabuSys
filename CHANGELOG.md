CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。

[Unreleased]
------------

（なし）

0.1.0 - 2026-04-19
-----------------

Added
- 初回リリース: KabuSys v0.1.0 を追加。
- 起動スクリプト
  - run_execution.py: 実行エンジン (ExecutionEngine) 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、Mock ブローカ（BrokerClientFactory を経由）で発注を分離。
    - エンジンの PID ファイル作成・停止フラグ（data/stop_requested.flag）検知をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視 DB は共有される想定）。
    - 停止フラグ存在時にループを終了し、例外時はログを残して次サイクルに継続。
- 環境設定 / 管理
  - config.py: 環境変数読み込み・Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を行い、.env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサは export 構文やシングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）と入力値検証を提供。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 必須/任意項目の提示、既存 .env の読み込み、保存機能を提供。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス、config/*.yaml の存在および YAML パース（PyYAML がインストールされている場合）を検証。
    - --strict オプションで警告を FAIL 扱いにできる。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ヘルパーを追加。
    - コンソール出力は stdout を使用、ファイルは日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log に出力（30 日分保持）。
    - LOG_LEVEL / LOG_DIR の環境変数や引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows（psutil の優先度定数）と POSIX（nice 値）を吸収し、呼び出し側は OS を意識せず set_process_priority()/set_cpu_affinity() を使用可能。
    - 権限不足等の例外は安全にログ警告してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で上位 N を選択（signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等比重およびスコア加重（スコア合計 0 の場合は等分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタ。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3, 未知は 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・現金等を元に発注株数を計算（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限・全体利用上限、cost_buffer を考慮したスケーリングや残差配分ロジックを実装。
  - portfolio/__init__.py にて上記関数をエクスポート。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status, trade_logs, risk_logs などから稼働率・注文成功率・送信率・P95 レイテンシ等を集計。
    - 合格基準（デフォルト）: 稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms。FAIL/ PASS の判定を表示。
    - 引数 --from / --to / --db で期間・DB 指定可能。PAPER_TRADING_SQLITE_PATH 環境変数を尊重。
- research/factor_research.py: ファクター計算モジュール（モメンタム、MA200乖離、ATR、出来高系など）の骨子を追加。DuckDB 経由で prices_daily / raw_financials を参照する設計。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- ルートログ設定の統一化:
  - 全起動スクリプトは setup_logging() を呼び出して共通のログ出力形式・ファイル管理を行うように変更。
- SQLite / DuckDB の扱い:
  - monitoring 用 DB 初期化（init_monitoring_db）を起動時に保障する処理を追加（冪等）。

Fixed
- なし（初回リリース）

Security
- なし

Notes / Migration
- .env の初期設定は config_setup.py のウィザードを利用してください。生成した .env は決して Git にコミットしないでください（README/ファイルヘッダでも警告済み）。
- 本番稼働時は KABUSYS_ENV を "live" に設定してください。validate_config による事前チェックを推奨します（--strict オプションで厳密チェック可能）。
- monitoring は KABUSYS_ENV に関わらず sqlite_path を使用します。監視データを分離したい場合は SQLITE_PATH を適切に設定してください。
- paper_trading の DB は PAPER_TRADING_SQLITE_PATH 環境変数で分離可能（デフォルト: data/paper_trading.db）。
- process_priority の設定は権限に依存します。設定に失敗した場合は警告ログが出力されますが起動は継続します。
- research/factor_research.py は実装途中（ファイル末尾が途中で切れている可能性あり）。ファクター計算の利用時は要確認。

References
- 起動用 CLI:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

--- End of CHANGELOG ---