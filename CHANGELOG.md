KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットについては Keep a Changelog に準拠しています。
リリース日付はソースコードから推測した日付を使用しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
-----------------

Added
- 基本アプリケーション構成を追加
  - パッケージ初期バージョンを 0.1.0 として定義（src/kabusys/__init__.py）。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を高に設定して起動。
    - 環境が paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db など）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による制御を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（デフォルト 60 秒）を上書き可能。無効値はデフォルトにフォールバックして警告を出力。
    - Monitoring は実行環境にかかわらず本番用 sqlite_path を使用する（運用上の分離方針）。
    - 停止フラグ検知で安全にループを終了し、例外時はログを出して次のポーリングへ継続。
- 設定・環境管理
  - config.py: 環境変数読み込み・Settings クラスを追加。
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - .env パーサは export プレフィックス、クォート、インラインコメント等に対応する堅牢な実装。
    - Settings による各種プロパティ（DB パス、PID ファイル、しきい値、env/log level 判定、paper_trading 用設定等）と入力検証を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- 設定補助 CLI
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連など）。
    - 既存 .env 読み込み、入力プロンプト、確認後に安全に書き込み。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・config YAML ファイル存在確認、KABUSYS_ENV=live 時の追加ガードなど。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート/上位選定。
    - calc_equal_weights, calc_score_weights: 重み計算（score が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用（既存保有を考慮し上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 対応、未知値はフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数計算（risk_based / equal / score の allocation_method をサポート）。
    - 単元（lot_size）丸め、per-position/aggregate 上限、cost_buffer による保守的見積り、スケーリングと残差処理を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加（setup_logging）。
    - stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順を定義。
  - utils/process_priority.py
    - set_process_priority, set_cpu_affinity を追加。psutil を使い Windows / POSIX の差分を吸収。権限不足や未対応 OS の場合は警告を出してスキップ。
- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を起動スクリプトから利用（監視テーブルの冪等な初期化）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からレポートを生成。
    - システム稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシを算出。
    - P95 計算、期間指定オプション（--from/--to）をサポート。基準値（稼働率/成功率/送信率/P95 レイテンシ）による PASS/FAIL 判定を出力。
- 研究用モジュール（下位関数群を追加）
  - research/factor_research.py
    - DuckDB を用いたファクター計算の枠組みを追加（モメンタム、MA200 乖離、ATR、流動性等を想定した設計）。注: ファイル末尾が途中の実装を含む（今後実装継続予定）。

Changed
- なし（新規初期実装のため変更履歴なし）。

Fixed
- なし（初期リリース）。

Security
- なし。

Notes / 実装上の注意
- run_monitoring は「監視は本番 sqlite_path を使用する」設計になっており、環境（KABUSYS_ENV）が paper_trading であっても監視 DB は分離されません。運用時は意図した DB パスを設定してください。
- .env 読み込みは OS 環境変数を優先し、.env.local を使って上書き可能。ただし OS 環境変数は保護されます（override と protected の仕組み）。
- process_priority や CPU affinity の設定は権限やプラットフォームに依存するため、失敗時は警告を出してスキップします。
- paper_trading 用 DB はデフォルトで data/paper_trading.db を想定。必要に応じて PAPER_TRADING_SQLITE_PATH 環境変数または run-time オプションで変更してください。

参考
- 主な環境変数:
  - KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, KILL_FLAG_CLEAR_ON_START

---- 
（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートや公開日付はプロジェクトの運用ルールに従って調整してください。）