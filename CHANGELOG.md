# Changelog

すべての変更は「Keep a Changelog」形式に従い、重要度の高い順に記載しています。  
バージョン番号はパッケージ内の __version__ に合わせています。

## [0.1.0] - 2026-04-19

### Added
- 初期リリースとして主要モジュールと CLI/ユーティリティ群を追加。
- 起動スクリプト
  - run_execution.py: 実売買用 ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、Paper Trading 用 DB（デフォルト: data/paper_trading.db）に記録して本番 DB と分離します。  
    - 起動前にプロセス優先度を "high" に設定し、PID ファイル管理・停止フラグ（data/stop_requested.flag）に対応。スレッドベースでエンジンを実行・安全停止します。
  - run_monitoring.py: システム監視ループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。  
    - Monitoring は実行環境にかかわらず本番用 sqlite_path を使用して監視データを記録します。停止フラグ検知でループを終了します。
- 設定関連
  - config.py: 環境変数 / .env 読み込み・ラッパー Settings を実装。  
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml が基準）、優先度: OS 環境 > .env.local > .env。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。  
    - 各種プロパティを提供（J-Quants / kabu API / DB パス / PID ファイル / 監視閾値 / PAPER_FILL_MODE 等）。PAPER_FILL_MODE の検証（instant/partial/never/reject）を実装。  
  - config_setup.py: 対話式 .env 作成ウィザードを追加。秘密値はマスク表示、生成テンプレートは .env に書き出し。デフォルト値・選択肢をサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数の有無、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス・config/*.yaml の存在（および PyYAML があればパース検証）、本番向けチェック（LINE 通知設定や Kill Switch）を実行。--strict オプションで警告を失敗扱いにできます。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、デフォルト logs/<app_name>.log、30 日保持）を設定。ログディレクトリ自動作成に失敗した場合はファイル出力を無効化してコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / 引数で解決。既存ハンドラの二重登録を防止するためハンドラをクリアしてから再設定します。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。  
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収し psutil 経由で優先度を設定。アクセス不可時は警告を出してスキップ。CPU affinity 設定関数も提供。
- 監視/モニタリング基盤
  - monitoring/monitoring_db.py（起動時に初期化を呼ぶ実装を想定）と SystemMonitor を利用する実行フローを run_monitoring/run_execution に統合（監視テーブルの冪等初期化を実施）。
- Execution コンポーネント（エンジン周り）
  - execution/* の基礎コンポーネント組み立てを反映（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の利用）。  
    - RiskManager のデフォルト設定を Execution 起動時に与える（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）。 initial_portfolio_value は broker.get_available_cash() を利用。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを生成するツールを追加。  
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出。デフォルト閾値を利用して PASS/FAIL 判定を行う。日付フィルタと DB パス指定をサポート。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）を追加。スコア全 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とマーケットレジーム乗数（calc_regime_multiplier）を実装。  
    - apply_sector_cap は既存保有のセクター時価を計算して閾値超過セクターの新規候補を除外。unknown セクターは除外対象外でフォールバック。  
    - calc_regime_multiplier は 'bull'/'neutral'/'bear' マップを提供（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（risk_based / equal / score の allocation_method をサポート）。  
    - リスクベース：risk_pct, stop_loss_pct を用いた目標株数計算。  
    - 等分・スコア重み：weight に基づく投下額計算。  
    - 単元株丸め（lot_size）、1 銘柄上限・全体利用上限、cost_buffer（手数料・スリッページ想定）に対応。aggregate cap 超過時はスケーリングし、残余キャッシュを用いて lot_size 単位で再配分するロジックを実装。
  - portfolio/__init__.py: 主要 API をエクスポート。
- 研究（リサーチ）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。モメンタム計算関数（calc_momentum）を導入（実装途中の箇所あり）。
- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Notes / Usage highlights
- .env の読み込み
  - 自動ロードはプロジェクトルートを .git または pyproject.toml から検出して行うため、配布後でもカレントディレクトリに依存しません。
  - export プレフィックス・クォート・インラインコメント等の .env 文法の取り扱いを考慮したパーサを実装。
- Logging
  - ログは標準出力（stdout）に出しつつ、可能なら logs/<app_name>.log に日次ローテーションで保存します。ログディレクトリ作成に失敗しても起動は継続します。
- 実行と監視の安全停止
  - 実行/監視ともにプロジェクトルート配下の data/stop_requested.flag による停止フラグに対応しています。Execution は PID ファイルを扱い、スレッド安全に停止します。
- Paper Trading と本番の DB 分離
  - 実行エンジンは paper_trading 環境であれば paper_sqlite_path（デフォルト: data/paper_trading.db）を利用するため、本番の監視 DB とデータ分離が可能です。
- 要インストール依存
  - duckdb, psutil を利用しています。YAML 検証は PyYAML がある場合にのみ行われます。

---

今後の改善候補（未実装・TODO）
- portfolio.position_sizing の price フォールバック（前日終値や取得原価の使用）や銘柄別 lot_size のサポート。
- research.factor_research の完全実装（各ファクターの SQL 実装・テスト）。
- monitoring/monitoring_db と SystemMonitor の細部実装に応じた監視項目の拡張。
- CI 用の設定検証やユニットテストの追加（各純粋関数に対する網羅的テスト）。

（以上）