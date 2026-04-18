CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に従い、セマンティックバージョニングを使用しています。
リリース日: 2026-04-18

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリースを追加。
- コアライブラリ:
  - kabusys.config
    - .env ファイル自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env ファイルのパース実装（クォート、エスケープ、インラインコメントに対応）。
    - Settings クラスを導入し、アプリケーション全体で利用する設定プロパティを提供（J-Quants / kabuステーション / LINE / DB / 監視閾値 / システム設定等）。
    - 環境値検証を実装（KABUSYS_ENV, LOG_LEVEL の有効値チェック、PAPER_FILL_MODE の有効値チェックなど）。
    - settings = Settings() をモジュールスコープで公開。

  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを提供。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
      - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用して起動（監視データは本番 DB に保存）。
      - 起動時にプロセス優先度を "high" に設定。
      - 停止はプロジェクトの data/stop_requested.flag により検出。
      - SQLite / DuckDB の接続管理を含む。

    - run_execution.py
      - ExecutionEngine 起動スクリプトを提供。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と完全に分離して動作。
      - Paper 環境では MockBrokerClient を使用（BrokerClientFactory を通じて生成）。
      - 起動時にプロセス優先度を "high" に設定。
      - 停止フラグ（data/stop_requested.flag）を検出すると安全にエンジンを停止。
      - PID 管理（data/execution.pid）に対応。

  - 設定関連 CLI
    - config_setup.py
      - 対話式ウィザードで .env の初期作成・更新を支援。
      - J-Quants / kabu API / DB / LINE / ログレベル / Kill Switch 設定等の主要項目を対話で設定可能。
      - シークレット項目はマスク表示。
      - .env の読み書き機能を実装（既存値の読み込みと Enter での再利用に対応）。
    - validate_config.py
      - 起動前チェック用 CLI を提供（.env と config/*.yaml の基本的整合性検査）。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML ファイルのパース検証（PyYAML インストール時）等を実施。
      - --strict オプションにより警告も失敗として扱うモードをサポート。
      - 本番 (live) 向けの追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

  - portfolio モジュール（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: BUY シグナルのスコア降順で上位 N を選出（同スコアは signal_rank でブレーク）。
      - calc_equal_weights: 等金額配分を計算。
      - calc_score_weights: スコア比率による配分。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中度上限を適用して候補を除外するロジック。既存保有（当日売却予定を除外）を基にセクター別エクスポージャを算出。
      - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
    - portfolio.position_sizing
      - calc_position_sizes: 重み／候補と各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer など）から発注株数を計算。
      - risk_based / equal / score の割当方法をサポート。
      - aggregate cap により利用可能現金を超えた場合はスケーリングし、lot_size 単位で再配分するロジックを実装。

  - ユーティリティ
    - utils/logging_setup.py
      - 統一ログ設定ユーティリティを提供。
      - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）のファイル出力（logs/<app_name>.log、30 日保持）をルートロガーに設定。
      - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
      - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト ("INFO")。
      - stdout を使用（stderr ではない）点を明確化。
    - utils/process_priority.py
      - プロセス優先度設定（"high"/"normal"/"low"）を Windows / POSIX に対応して抽象化。
      - CPU affinity を最初 N コアに固定する機能（set_cpu_affinity）を提供。
      - 権限不足等で設定できない場合は警告を出力してスキップ。

  - monitoring
    - run_monitoring 起動時に使用する DB 初期化ヘルパー（init_monitoring_db）や SystemMonitor（run_monitoring が利用）を組み込み（監視 DB テーブルの初期化を行う）。
    - 監視ループは例外ハンドリングを行い、check_once() 内での例外発生時にもポーリングを継続する。

  - tools
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI を追加。
      - system_status / trade_logs / risk_logs テーブルを参照し、稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を計算して PASS/FAIL 判定を出力。
      - しきい値: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 latency <= 200 ms（デフォルト）。
      - --from/--to/--db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数が優先設定として利用可能。
      - DB が存在しない場合のエラーメッセージと回避策を明示。

  - research
    - research/factor_research.py
      - DuckDB 上の prices_daily / raw_financials を用いたファクター計算を行うための骨組みを追加（モメンタム / Value / Volatility / Liquidity 記載）。
      - モメンタム計算の定数などを定義。calc_momentum の実装を開始（注: ファイル末尾で実装途中で途切れた箇所あり）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数ファイル (.env) の注意喚起を config_setup の生成ヘッダに明記（.env を Git にコミットしないこと）。

Notes / 運用上の注意
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。監視データは本番 DB と同一の場所に保存される点に注意してください。
- ExecutionEngine は paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用するため、本番 DB とデータを分離できます。
- PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject" であり、不正値は起動時に例外を発生させます。
- KILL_FLAG_CLEAR_ON_START を本番で "1" にすることは危険であり、validate_config はその設定に対して警告を出します。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（デフォルト保持 30 日）。ログディレクトリが作成できない環境ではコンソール出力のみになります。
- process_priority の設定は OS 権限に依存します。権限不足時は警告を出力して処理を継続します。

References
- プロジェクト内のスクリプトやドキュメント（例: PortfolioConstruction.md, StrategyModel.md）に準拠した実装設計を意図しています。config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）についてはコード中で参照されていますが、本パッケージに含めていない場合は別途用意してください。