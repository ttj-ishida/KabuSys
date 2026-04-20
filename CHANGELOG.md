CHANGELOG
=========

このファイルは「Keep a Changelog」形式に準拠して作成されています。  
コードベースの内容から推測できる追加・仕様・挙動を記載しています（自動生成・推測に基づくため実際の差分履歴と若干異なる可能性があります）。

Unreleased
----------

- なし

0.1.0 - 2026-04-20
------------------

Added
- 初回公開（0.1.0）。
- 設定・環境読み込み
  - .env 自動ロード実装（プロジェクトルート = .git または pyproject.toml を探索）。
  - .env / .env.local を OS 環境変数を保護しつつ読み込む仕組みを搭載（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env の行パーサは export 形式、クォート、バックスラッシュエスケープ、行内コメントなどに対応。
  - Settings クラスにより環境変数を型付きプロパティで取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH など）。
  - PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject"）、PAPER_TRADING_SQLITE_PATH 等のペーパートレード用設定をサポート。
  - KABUSYS_ENV（development/paper_trading/live）の検証とログレベル（LOG_LEVEL）検証を実装。

- 設定支援 CLI
  - config_setup ウィザードを追加（python -m kabusys.config_setup）。
  - 対話式に .env を作成・更新する機能を提供。シークレットはマスク表示、選択肢・デフォルト対応。
  - .env の書式テンプレートを生成。

- 設定検証 CLI
  - validate_config により .env および config/*.yaml 周りの基本的な検証を実行（python -m kabusys.validate_config）。
  - 必須環境変数チェック、パス存在チェック、YAML パースチェック（PyYAML がある場合）、本番向け警告等を実装。
  - --strict オプションで警告も失敗扱いにできる。

- ロギング
  - utils.logging_setup: StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに統一的に設定。
  - LOG_DIR/LOG_LEVEL によるカスタマイズに対応。ログディレクトリ作成失敗時はコンソールのみで継続。

- プロセス優先度・CPU 制御ユーティリティ
  - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度 (high/normal/low) を設定。
  - CPU アフィニティ指定（最初 N コアに固定）を行う set_cpu_affinity を提供。
  - 権限不足や未対応 OS の場合は警告を出し処理をスキップ。

- 実行エントリ・監視エントリ
  - run_execution.py
    - ExecutionEngine 起動スクリプト。プロセス優先度設定、SQLite / DuckDB 接続、BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行う。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離。
    - 停止フラグ（data/stop_requested.flag）と実行 pid ファイル（data/execution.pid）の取り扱い。停止フラグ検知で安全にシャットダウン。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番の sqlite_path を使用する点に注意（設計上の明示）。
    - stop フラグ検知でループ終了。例外時はログを残して次のポーリングに回す。

- データベース・分析
  - DuckDB のサポート（duckdb_conn を各種コンポーネントに渡す）。
  - monitoring_db 初期化ユーティリティを使用して監視テーブルの冪等な作成を保証。

- Portfolio 構築モジュール（純関数）
  - portfolio.portfolio_builder
    - select_candidates: score 降順・タイブレークに signal_rank を使用し上位 N 件を選択。
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター比率が max_sector_pct を超える場合に候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をマップ、未知はフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based/equal/score）に基づく株数計算、単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守的評価、端数配分ロジックを実装。

- Paper Trading 検証ツール
  - tools.paper_verification_report
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み検証レポートを標準出力に生成（期間指定 --from/--to 対応）。
    - システム稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - P95 計算、閾値はソース内定数で定義（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms）。
    - データ欠損に対しては N/A 表示や保守的な FAIL 判定を行う。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注意・マイグレーション
- run_monitoring は「監視用 DB」を常に Settings.sqlite_path（デフォルト data/monitoring.db）を使うため、開発環境であってもモニタデータは本番 sqlite_path を参照する点に注意してください（設計上の挙動）。
- .env 自動ロードはプロジェクトルートが検出できない場合スキップされます。テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE に不正な値を与えると例外を送出します。利用可能値は "instant", "partial", "never", "reject"。
- process_priority の適用は OS 権限に依存します。権限不足時は警告が出て処理は継続されます。

参考コマンド
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring

（以上）