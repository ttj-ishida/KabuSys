# Changelog

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています（意味的にはカテゴリ分け: Added / Changed / Fixed 等を使用）。  
このファイルはコード内容から推測して作成しています。実際のコミット履歴ではない点にご注意ください。

## [Unreleased]

### Added
- 実行・監視系の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 DB（data/paper_trading.db, 環境変数で上書き可）と MockBrokerClient を使用する振る舞いをサポート。
    - PID ファイル / stop flag を用いた外部停止制御に対応（data/execution.pid、data/stop_requested.flag）。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動用スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視処理は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを初期化する設計。

- 環境・設定管理ユーティリティを追加
  - config.py: 環境変数の自動読み込みロジック（.env, .env.local）と Settings クラスを提供。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export プレフィックス、クォート、エスケープ、インラインコメントを考慮した実装。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / PID・Kill flag / モニタ閾値 / env/log レベル等）。
    - PAPER_FILL_MODE のバリデーション（"instant","partial","never","reject" のみ許可）。
    - KABUSYS_ENV の検証（"development","paper_trading","live"）。
  - config_setup.py: 対話式 .env 作成ウィザード。
    - 複数項目の入力プロンプト、既存 .env の読み込み、確認後の保存機能を提供。
  - validate_config.py: 起動前設定検証 CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パース検証、live 時の安全確認等を行う。
    - --strict オプションで警告を FAIL 扱いにできる（exit(1)）。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを提供。
    - stdout へ StreamHandler、ファイルへ TimedRotatingFileHandler（日次・30世代）を設定。
    - LOG_DIR 環境変数／引数で出力先を変更可。ディレクトリ作成失敗時はファイルハンドラを自動で無効化しコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度・CPU affinity 設定。
    - Windows / POSIX（Linux, Darwin, FreeBSD）向けに優先度を設定、psutil が利用可能な環境で動作。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。

- ポートフォリオ構築・リスク調整・ポジションサイジングの純関数群を追加（DB 参照なし）
  - portfolio/portfolio_builder.py
    - 選定ロジック（select_candidates）、等重み（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - calc_score_weights は全スコアがゼロの場合に等重みへフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーに基づく候補除外ロジック。unknown セクターは制限対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知のレジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）や cost_buffer を考慮したアルゴリズム実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標を算出してレポートを出力。
    - 指標: システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）。
    - デフォルト閾値（例: uptime >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）を用いた PASS/FAIL 判定。
    - コマンドラインで --from / --to / --db を指定可能。

- 研究用ファクタ計算（初期実装）
  - research/factor_research.py: DuckDB 接続を受け取りモメンタム等のファクターを計算する設計。
    - Momentum（1M/3M/6M, MA200乖離）、Volatility(ATR)、Liquidity 等を想定。DuckDB の prices_daily / raw_financials を利用する方針。

### Changed
- パッケージ初期化
  - __init__.py にバージョン文字列 __version__="0.1.0" を追加。公開 API の __all__ を定義。

### Fixed
- .env パーサの堅牢化
  - export プレフィックスやクォート内のエスケープ、インラインコメントの取り扱いを明確化し、不正な行を無視するよう改善（想定挙動）。

## [0.1.0] - 2026-04-18

Note: 初回リリース。上記の機能群をまとめて公開。

### Added
- 初期リリースとして以下の主要機能を実装・公開:
  - 実行エンジン起動スクリプト（run_execution.py）
  - 監視ポーリング起動スクリプト（run_monitoring.py）
  - 環境設定 / ウィザード / 検証ツール（config.py, config_setup.py, validate_config.py）
  - ロギング／プロセス制御ユーティリティ（utils/logging_setup.py, utils/process_priority.py）
  - ポートフォリオ構築・リスク・ポジション決定関数群（portfolio/*）
  - Paper Trading 検証レポートツール（tools/paper_verification_report.py）
  - 研究用ファクタ計算モジュール（research/factor_research.py、初期部分）
  - パッケージメタ情報（__version__）

### Security
- 環境変数には機密値（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / LINE_CHANNEL_ACCESS_TOKEN 等）を使用するため、config_setup において .env を絶対に Git にコミットしない旨の注意文を明記。

---

追加・修正・バグ修正は今後のリリースで逐次反映していきます。  
この CHANGELOG はコードからの推測に基づくため、実際のコミットログやリリースノートと差異がある可能性があります。必要であれば、特定ファイルや機能について詳細な変更点の追記を作成します。