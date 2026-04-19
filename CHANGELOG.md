# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のリリース履歴は以下の通りです。

## [0.1.0] - 2026-04-19
初回リリース。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として追加。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト直下の data/stop_requested.flag をチェック。
    - 起動時にプロセス優先度を "high" に設定し、logging を初期化。
    - monitoring 用の SQLite DB（Settings.sqlite_path）へ接続して初期化（監視は環境にかかわらず本番 sqlite_path を使用）。
    - DuckDB 接続を並行利用。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / Reconciler / RiskManager 等の組み立てと ExecutionEngine の起動をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知時の安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定し、logging を初期化。
    - デフォルトの RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。

- 設定管理
  - config.py
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
    - プロジェクトルートの自動検出ロジック（.git または pyproject.toml）を導入し、CWD に依存せずに .env を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 複数の設定プロパティ（J-Quants、kabu API、LINE、DuckDB/SQLite パス、paper trading の挙動、監視閾値、ログ設定、環境種別検証など）を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。

  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。
    - KABUSYS_ENV など主要設定のプロンプト、既存 .env の読み込み、秘密値のマスク表示、保存機能を実装。
    - .env 書き込みテンプレートを提供（Git に .env をコミットしない旨のヘッダ含む）。

  - validate_config.py
    - 起動前検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数の有無、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ有無、config/*.yaml の存在チェック（PyYAML があればパース検証）等を行う。
    - --strict モードで警告をエラー扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（select_candidates）。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。全スコア 0 の場合は等配分にフォールバックして警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（当日売却予定銘柄をエクスポージャー計算から除外可能）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（'bull'/'neutral'/'bear' のマップ、未知レジーム時は 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes を実装。
    - allocation_method に応じた算出（"risk_based" / "equal" / "score"）に対応。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap のスケールダウン、cost_buffer を考慮した保守的見積り、残余現金での端数配分ロジックを実装。

  - portfolio/__init__.py にて関数をまとめてエクスポート。

- ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用できるログ設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を定義し、ディレクトリ作成失敗時のフォールバック処理を実装。

  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice）と CPU affinity 設定ユーティリティを実装。
    - psutil を利用。権限不足などで失敗した場合は警告ログを出してスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）から SQLite を読み、システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）等を算出して判定（PASS/FAIL）を出力。
    - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）を設定。

- リサーチ（作業中）
  - research/factor_research.py
    - ファクター計算モジュール（モメンタム等）の実装を開始。モメンタム計算のための定数・インタフェース（calc_momentum）を記述（ファイル途中までの実装）。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- なし（初回リリースのため該当なし）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- なし。

注記:
- run_monitoring/run_execution はそれぞれ logging_setup と process_priority を利用しており、ログ出力先や優先度は環境変数（LOG_LEVEL, LOG_DIR）およびプラットフォームに依存します。
- Settings は自動で .env をプロジェクトルートから読み込みます（OS 環境変数が優先）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 提供される CLI（config_setup / validate_config / paper_verification_report）は、運用前の設定確認や Paper Trading 検証に有用です。

今後の予定（例）
- research/factor_research の完全実装（Momentum / Value / Volatility / Liquidity 等の計算ロジックを完成）。
- monitoring と execution の統合テストおよび監視データベース周りの追加ユーティリティ。
- 銘柄別 lot_size 対応や手数料モデルの拡張。

--- 
この CHANGELOG はリリース内の主要な追加点と注意点をまとめたものです。細かな実装の参照は各ソースファイルの docstring を参照してください。