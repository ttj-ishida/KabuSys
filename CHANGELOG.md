CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。
このファイルはコードベース（初期リリース v0.1.0）から推測して作成された変更履歴です。
日付はリポジトリ内のバージョン情報および現在時点の推定日を基に付与しています。

Unreleased
----------

- 追加予定 / 検討中
  - research/factor_research.py の未完了箇所（モメンタム計算関数の続き）を完成させ、ファクター算出パイプラインを統合。
  - テストカバレッジの追加（.env パーサ、position_sizing、risk_adjustment、ExecutionEngine/Monitoring の統合テスト）。
  - 銘柄ごとの lot_size を stocks マスタ等から取得する拡張（position_sizing の TODO に対応）。
  - DuckDB/SQLite 用のマイグレーションスクリプトやスキーマ管理の導入。

[0.1.0] - 2026-04-21
--------------------

Added
- 基本パッケージ情報
  - パッケージ初期バージョンを __version__ = "0.1.0" として追加。

- 設定管理
  - Settings クラスを追加。環境変数経由でアプリケーション設定を一元管理。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を参照）。
  - .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント（空白前の #）等に対応。

- 設定ユーティリティ / CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - J-Quants / kabuステーション / DB / LINE 等主要設定項目をサポート。
    - シークレット項目はマスク表示し、.env の雛形を書き出す機能を提供。
  - validate_config.py: 起動前に .env や config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値検証、LOG_LEVEL 検証、DB パスと config YAML の存在チェック、live 環境向けのガードを実装。
    - --strict オプションで警告をエラー扱いにする機能を追加。

- 実行エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db）を利用し、MockBrokerClient を利用する想定で本番 DB と分離。
    - プロセス優先度を高に設定するユーティリティ呼び出し、PID ファイル管理、停止フラグ（data/stop_requested.flag）に基づく安全な終了処理を実装。
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動を行う。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ資金は broker.get_available_cash() で取得。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）の検知、例外発生時のログ出力と継続動作、KeyboardInterrupt のハンドリングを実装。

- 監視 / DB 初期化
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）呼び出し箇所を run_* スクリプトに統合し、監視テーブルの存在を保証。

- ログ / プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定を追加。
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、デフォルト logs/、30 日保持）をルートロガーへ設定。
    - 既存ハンドラのクリア、ログディレクトリ作成失敗時のファイルハンドラ無効化フォールバックを実装。
  - utils/process_priority.py: Windows / POSIX の差を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア順ソートと上位 N 抽出（signal_rank によるタイブレーク）を実装。
    - calc_equal_weights / calc_score_weights: 等分配とスコア加重配分を実装。全スコアが 0 の場合は等分配にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用ロジックを追加（既存ポジションのセクター別時価を計算し、上限超過セクターの候補を除外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金乗数を追加（未知のレジームはフォールバック 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash） によるスケールダウン、cost_buffer（手数料/スリッページ見積り）対応、残差分の lot_size 単位での再配分ロジックを実装。
    - TODO: 将来的に銘柄別 lot_size をサポートするための注記を追加。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH を使用して paper_trading DB からシステム安定性、注文成功率、リスク却下数、API レイテンシ（平均/最大/P95）を集計。
    - パスが見つからない際のエラーメッセージ、日付フィルタ（--from/--to）対応、閾値による PASS/FAIL 判定ロジックを提供。
    - P95 計算、Null 安全な出力フォーマットを実装。

- research
  - research/factor_research.py（ファクター計算の骨組み）を追加。DuckDB 接続を受け、prices_daily/raw_financials から Momentum/Value/Volatility/Liquidity 等を計算する方針を文書化。モジュール内定数と関数シグネチャを用意（一部実装は未完）。

Changed
- なし（初期リリース）。

Fixed
- なし（初期リリース）。ただし、各ユーティリティで予防的なエラー処理（ファイル作成失敗時のフォールバック、例外時のログ出力など）を盛り込んでいる。

Security
- .env を絶対にコミットしない旨を config_setup の出力テンプレートに明記。
- シークレットは対話ウィザード中にマスク表示。

Notes / Migration
- 実行方法
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

- 環境変数
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 推奨/デフォルト: KABUSYS_ENV (development/paper_trading/live), DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。正の整数を指定。無効値はデフォルト 60 秒にフォールバック。
  - PAPER_FILL_MODE: paper_trading 時の約定動作 ("instant" | "partial" | "never" | "reject")
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB パス（デフォルト data/paper_trading.db）

- DB
  - 監視用 SQLite（SQLITE_PATH, default data/monitoring.db）と分析用 DuckDB（DUCKDB_PATH, default data/kabusys.duckdb）を併用。
  - paper_trading モードは paper_trading 専用 SQLite を利用し、本番 DB と分離。

- ログ
  - デフォルトは logs/<app_name>.log（日次ローテーション）。ログディレクトリ作成に失敗した場合はコンソール出力のみで動作。

開発者向け
- research/factor_research.py の未完部分を実装する際は、DuckDB のテーブルスキーマ（prices_daily, raw_financials）に合わせたクエリ設計を行ってください。
- position_sizing の lot_size 周りは将来的に銘柄別単位へ拡張することを想定しています。

Acknowledgements
- 本 CHANGELOG は提供されたソースコードの内容から機能/意図を推測して作成されています。実際のコミット履歴やリリースノートに基づくものではありません。必要に応じて修正・補完してください。