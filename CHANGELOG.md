# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 初回リリース
リリース日: 2026-04-23（推定）

### 追加
- 基本ランタイム / サービス起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 停止制御: プロジェクトルート配下の data/stop_requested.flag を検知してループを終了。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する実装。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB の接続・初期化（init_monitoring_db 呼び出し）を行い、例外時もログ出力して次のポーリングへフォールバック。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（デフォルト: data/paper_trading.db）で本番 DB と完全分離する。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag の検出でエンジン停止。実行時 PID は data/execution.pid に保存する想定（pid_file 引数を受け取る）。
    - 依存コンポーネント組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）と ExecutionEngine の run_session を別スレッドで実行する制御ループを実装。
    - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors 等）を設定し、initial_portfolio_value は broker.get_available_cash() を使用。

- 設定・環境変数関連
  - config.py
    - .env ファイルの自動読み込み機能を追加（プロジェクトルートの .env / .env.local をロード。OS 環境変数は保護）。
    - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を探索）。
    - .env パースの強化: export プレフィックス対応、クォート/エスケープの取り扱い、インラインコメントの扱い（クォート有無での挙動差異）。
    - Settings クラスを追加し、各種設定プロパティを提供（J-Quants, kabu API, LINE, DuckDB/SQLite パス、Paper Trading 設定、監視閾値、PID/Kill flag パス、KABUSYS_ENV/LOG_LEVEL の検証など）。
    - PAPER_FILL_MODE の検証（有効値: "instant", "partial", "never", "reject"）を実装。
    - 環境判定プロパティ: is_live / is_paper / is_dev。

  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。
    - 項目定義と既存値の読み込み・保存ロジック（.env の読み書き）を実装。
    - シークレット項目（トークンやパスワード）はマスク表示して扱う。生成された .env のフォーマットは README 的コメント付きで出力。

  - validate_config.py
    - 起動前チェック CLI を追加（必須環境変数の有無、KABUSYS_ENV 値、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検証、live 環境の追加ガードなど）。
    - --strict オプションで警告もエラー扱いにする機能を提供。
    - 出力は INFO / WARNING / ERROR をまとめて表示し、終了コードで FAIL/OK を示す。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成するコマンドラインスクリプトを追加。
    - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
    - 期間フィルタ (--from / --to) に対応。
    - レポート項目:
      - システム稼働率（system_status テーブル）
      - 注文成功率 / 送信率（trade_logs）
      - リスク却下数（risk_logs）
      - API レイテンシ（avg / max / P95）
    - 判定基準（デフォルト閾値）を導入:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - DB 内に該当テーブルがない場合は適切に N/A を出力する耐性を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 重み計算: calc_equal_weights（等金額）と calc_score_weights（スコア正規化、全スコアが 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を実装。既存保有のセクター別時価を計算し、上限超過セクターの新規候補を除外。unknown セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各配分方式（"risk_based", "equal", "score"）に対応した発注株数計算を実装。
    - リスクベース: ポジションごとのリスク許容量（risk_pct）とストップロス比率（stop_loss_pct）に基づいた株数算出。
    - 等配分/スコア配分: 重みと portfolio_value, max_utilization の制約を考慮。
    - 単元株（lot_size）で丸め、1株単位での誤差を残差分配（fractional remainder）により埋めるロジックを実装。
    - aggregate cap（available_cash 超過時）でスケールダウンして lot 単位で再配分する処理を実装。
    - price が無効な銘柄はスキップ。max_position_pct により 1 銘柄の上限を強制。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテーションでファイル出力する TimedRotatingFileHandler をルートロガーに設定。
    - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > "INFO"。ログディレクトリ解決順: 引数 > LOG_DIR > "logs/"。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみ継続。
    - 既存ハンドラはクリアして重複出力を防止。
  - utils/process_priority.py
    - プラットフォーム横断でプロセス優先度設定を行う set_process_priority を実装（"high"/"normal"/"low"）。
    - Windows と POSIX（Linux/Mac/FreeBSD）向けの実装分岐と失敗時のフォールバック処理（権限不足などで警告を出す）。
    - set_cpu_affinity: 指定コア数にプロセスをピン止めする補助関数を追加（利用可能なコア数チェック、権限不足で警告）。
  - utils/__init__.py を追加。

- 研究用ファクター計算（骨格）
  - research/factor_research.py
    - DuckDB を使ったファクター計算モジュールの骨格（Momentum, Value, Volatility, Liquidity の設計方針と定数）を追加。calc_momentum の冒頭実装を含む（続きは実装途上）。

- パッケージ情報
  - kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。
  - パッケージ公開用 __all__ に主要サブパッケージを列挙。

### 変更
- なし（初回リリースのため）

### 修正
- なし（初回リリースのため）

### 注意事項 / 既知の制限
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後にプロジェクトルートが特定できない環境では自動読み込みはスキップされる。
- position_sizing の lot_size は現状全銘柄共通の固定値（デフォルト 100）。将来的に銘柄別単元対応を想定する注記あり。
- risk_adjustment.apply_sector_cap は price が欠損（0.0）の場合にエクスポージャーを過小評価する可能性があり、将来的に前日終値等でフォールバックする改善が示唆されている。
- research/factor_research.py は一部実装途上（calc_momentum の先頭まで含む）。

---

将来的な変更・修正はこの CHANGELOG に追記します。必要であれば各項目をより詳細に分割して記載します。