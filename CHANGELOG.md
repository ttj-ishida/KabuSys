CHANGELOG
=========

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初回公開リリース (バージョン 0.1.0)。
- 実行スクリプト:
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用する分離設計を導入。
    - ブローカークライアントの生成を BrokerClientFactory に委譲。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンはスレッドで実行され、 data/stop_requested.flag による外部停止をサポート。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用エントリポイントを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - data/stop_requested.flag による停止検知を実装。
- 設定管理:
  - config.py
    - .env 自動読み込み機構を導入（プロジェクトルートの .env / .env.local）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 詳細な .env パーサを実装（export プレフィックス、引用符、エスケープ、インラインコメント処理対応）。
    - Settings クラスを提供（環境変数読み取り用プロパティ群）。
    - 多数の設定プロパティを追加（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL,
      DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH,
      KILL_FLAG_CLEAR_ON_START, CPU/MEMORY/DISK 閾値, LOG_LEVEL, KABUSYS_ENV 判定ユーティリティ等）。
- 設定ツール・検証:
  - config_setup.py
    - 対話式ウィザードで .env の初期作成/更新を支援する CLI を追加。既存値の読み込みとシークレットマスク表示に対応。
    - 標準の設定項目と注記を出力して .env を生成。
  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、YAML ファイルの存在・パース検査、live 環境向けガードチェック等を実装。
    - --strict オプションで警告を失敗扱いにするモードを実装。
- ログ・プロセスユーティリティ:
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（毎日ローテーション、30日保持）を設定する共通セットアップを提供。
    - LOG_LEVEL / LOG_DIR による設定優先度、ハンドラの二重設定防止、ログディレクトリ作成失敗時のフォールバックに対応。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度（high/normal/low）設定ユーティリティを追加。
    - CPU affinity 設定関数 set_cpu_affinity を提供（利用可能なコアに固定）。
    - 権限不足や未対応プラットフォーム時は警告を出してスキップ。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py
    - 銘柄選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコア全ゼロ時は等金額にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) を実装。既存保有を基にセクター上限に達した場合は新規候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear"→1.0/0.7/0.3）。
  - portfolio/position_sizing.py
    - position sizing を実装（allocation_method="risk_based"|"equal"|"score"）。
    - 単元株（lot_size）で丸め、per-position 上限・aggregate cap のスケーリング機構、手数料/スリッページのバッファ考慮を実装。
    - 設定パラメータ: risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer など。
  - portfolio/__init__.py
    - 上記関数群をエクスポート。
- 監視/モニタリング DB:
  - monitoring_db の初期化を行う init_monitoring_db を実行時に呼び出し（冪等）。
- ツール:
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / --db）を対象に検証レポートを生成するスクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を集計。
    - デフォルト閾値を設定し、PASS/FAIL 判定を出力する。
- リサーチ:
  - research/factor_research.py（骨格実装）
    - DuckDB 接続を受けてモメンタム等のファクターを計算する関数群の設計を追加（calc_momentum 等、処理概要と定数を定義）。一部未完（ファイル末尾で途中）。
- パッケージ情報:
  - __init__.py にてバージョン __version__ = "0.1.0" を追加。

Changed
- n/a（新規リリースのため変更履歴は追加のみ）。

Fixed
- n/a（新規リリース）。

Deprecated
- なし

Security
- 環境変数ファイル (.env) の生成時に「.env を絶対に Git にコミットしないこと」を明記。

Notes / Usage highlights
- 実行:
  - 監視起動: python -m kabusys.run_monitoring
  - 実行エンジン起動: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report
- 重要な環境変数（抜粋）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development / paper_trading / live（既定: development）
  - SQLITE_PATH（監視 DB、既定: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、既定: data/paper_trading.db）
  - DUCKDB_PATH（分析 DB、既定: data/kabusys.duckdb）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒、既定: 60）
  - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、既定: instant）
  - LOG_LEVEL / LOG_DIR / KILL_FLAG_CLEAR_ON_START / KILL_FLAG_PATH 等

その他
- 本リリースは初期実装のため、将来的な API 変更や追加ユーティリティの導入により一部インタフェースが変更される可能性があります。