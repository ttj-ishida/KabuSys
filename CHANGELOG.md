Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

v0.1.0 - 2026-04-23
-------------------

初回リリース。KabuSys 自動売買基盤のコアユーティリティ・実行スクリプト・ポートフォリオ構築ロジック・運用ツール群を含みます。

Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト data/stop_requested.flag によるフラグで制御。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する挙動。
    - DB 初期化（init_monitoring_db）と duckdb 接続を行う。例外はログ出力して継続。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて実行。
    - エンジンはスレッドで起動され、stop flag（data/stop_requested.flag）で停止可能。PID ファイル管理あり。
    - RiskManager に初期設定（max_position_pct、max_utilization、rate_limit_per_sec 等）のデフォルトを設定。

- 環境設定管理
  - config.py
    - .env 自動読み込みロジック（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env / .env.local の読み込み順序と保護（OS 環境変数の保護機能）。
    - .env 行パーサーがクォート、エスケープ、export KEY=val 形式、インラインコメントをサポート。
    - 各種設定プロパティ（DB パス、PID/kill flag パス、閾値等）を Settings クラスとして提供。
    - PAPER_FILL_MODE（instant/partial/never/reject）など Paper Trading 向け設定をバリデーション。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加（項目の定義と保存ロジックを含む）。
    - 秘匿項目はマスク表示、選択肢・デフォルト提示、既存 .env の読み込みに対応。
    - 保存前に確認プロンプトを表示。

  - validate_config.py
    - 起動前に .env や config/*.yaml の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パス親ディレクトリチェック、YAML ファイル存在・パース検証（PyYAML があれば実施）、本番環境向け追加警告等を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 一貫したログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - LOG_LEVEL / LOG_DIR / 引数経由で設定を解決。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラをクリーンに置き換える処理を実装。

  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収したプロセス優先度設定と CPU affinity 設定を追加（psutil 使用）。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。
    - 権限不足や未対応 OS に対するフォールバックと警告を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）と重み計算（calc_equal_weights、calc_score_weights）実装。
    - calc_score_weights は全スコアがゼロの場合に等金額配分にフォールバックして警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）を実装。既存保有のセクター別時価をもとに新規候補を除外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピングとフォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジックを実装。allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元株丸め（lot_size）、単銘柄上限、aggregate cap、コストバッファ（手数料・スリッページ見積り）を考慮したスケーリングを実装。
    - 利用可能現金を超える場合のスケールダウンと残差配分ロジックを実装。

  - portfolio/__init__.py
    - 上記関数群をパッケージ API として公開。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 各種閾値（稼働率、注文成功率、送信率、P95 レイテンシ）を定め、SQLite の paper_trading DB から統計を集計して PASS/FAIL を判定。
    - CLI による期間指定（--from/--to）と DB 指定（--db、または環境変数 PAPER_TRADING_SQLITE_PATH）対応。
    - P95 計算、NULL / テーブル未存在時のフォールバックを実装。

- 研究用モジュール（部分実装）
  - research/factor_research.py
    - Momentum/Value/Volatility/Liquidity の計算仕様と計算用ユーティリティを追加（DuckDB 接続を受け取る設計）。
    - モメンタム計算（calc_momentum）等の関数骨格を含むが、一部実装が継続中（本スナップショットでは未完の箇所あり）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数の取り扱いに注意:
  - .env は絶対に Git にコミットしないことを README に明記するよう意図（config_setup のヘッダコメント）。
  - 秘匿値は対話ウィザードでマスク表示するが、保存される .env は平文であることに注意。

Notes / Known limitations
- research/factor_research.py は本スナップショットで途中まで（未完）です。ファクター計算の完全実装は今後の作業予定。
- apply_sector_cap の価格欠損（price が 0.0 の場合）によりエクスポージャーが過小推定される旨の TODO コメントあり。将来的にフォールバック価格の導入が想定されている。
- process_priority の優先度設定は OS 権限に依存し、権限不足時は警告を出してスキップする実装です。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化して続行します（運用環境のディレクトリ権限を事前に確認してください）。

参考: 環境変数・設定キー（主要）
- KABUSYS_ENV (development | paper_trading | live)
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔）
- PAPER_FILL_MODE（instant|partial|never|reject）
- LOG_LEVEL, LOG_DIR
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険）

------------------------------------
今後の予定（短期）
- factor_research の完全実装とテスト追加
- 単体テスト・統合テストの整備（特に position_sizing や risk_adjustment）
- ドキュメント（README / 運用手順）およびデプロイ/サービスユニット化のサンプル追加

（以上）