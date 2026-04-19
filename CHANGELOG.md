# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従って記載しています。  
バージョン番号はパッケージルートの __version__ を基にしています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 起動スクリプト / 実行系
  - run_execution.py
    - ExecutionEngine を起動するエントリスクリプトを追加。
    - プロセス優先度を起動時に "high" に設定。
    - 環境変数 KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - PID ファイルの扱い（data/execution.pid）をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。不正値はデフォルトへフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を用いる（監視データの一元化）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - SQLite / DuckDB 接続の初期化（init_monitoring_db）を実行。

- 設定管理・CLI
  - config.py
    - .env ファイルの自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env / .env.local の読み込み順と上書きルールを実装（OS 環境変数はプロテクト）。
    - 複雑な .env 行パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
    - Settings クラスを実装。J-Quants / kabuAPI / LINE / DB パス / 監視しきい値 / システム設定（KABUSYS_ENV / LOG_LEVEL 等）をプロパティで提供。
    - Paper Trading 関連: PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH のプロパティを提供。
    - 環境自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - デフォルト値・選択肢・シークレット入力・保存確認を実装。
  - validate_config.py
    - .env と config/*.yaml の設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML ファイルの存在およびパースチェック（PyYAML があれば実行）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) を実装。既存保有のセクター別時価比率が max_sector_pct を超える場合は同セクターの新規候補を除外（unknown セクターは適用除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未定義レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - lot_size（単元株）で丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケールダウン、残差を考慮した追加配分のアルゴリズムを実装。
    - cost_buffer による保守的コスト見積りをサポート。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - コンソール出力は stdout を使用、ファイル出力は TimedRotatingFileHandler（日次ローテーション、30 日分保持）を使用。
    - 既存ハンドラの二重設定防止のため再初期化ロジックを実装。
    - LOG_DIR / LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップして警告を出す。
  - utils/process_priority.py
    - psutil を利用してプラットフォーム差（Windows / POSIX）を吸収するプロセス優先度設定を追加（set_process_priority）。
    - CPU affinity 設定ユーティリティ set_cpu_affinity を実装（最初の N コアに固定）。
    - 権限不足や未対応 OS 時に安全にフォールバックし警告を出力。

- モニタリング DB 初期化インターフェース
  - monitoring/monitoring_db.py（呼び出し箇所あり）
    - 監視用テーブルの初期化を行う init_monitoring_db を使用（冪等）。

- 実行検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数など。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ (--from / --to)、DB パス指定 (--db)、環境変数 PAPER_TRADING_SQLITE_PATH をサポート。
    - レポートは標準出力に整形して出力。

- 研究用モジュール（骨格）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity の設計方針と定数を定義）。
    - calc_momentum をはじめとするファクター計算関数の設計を開始（DuckDB の prices_daily / raw_financials を参照する方針）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Implementation details
- DB・ファイルパスのデフォルト値:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH（監視 DB）: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID / stop flag 等は data/ ディレクトリ下に配置する想定。
- .env の読み込み順:
  - OS 環境変数（保護） > .env (.env の既存キーは上書きしない) > .env.local（override=True: .env を上書き）
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可。
- ロギング:
  - stdout とファイルの両方を基本出力先とし、ログレベルや出力先は環境変数で制御可能。
- プロセス優先度:
  - Windows / Linux (POSIX) をサポートし、権限不足時は警告してスキップ。

### Known issues / TODOs
- research/factor_research.calc_momentum がファイル末尾で途中（実装未完 / 切断の痕跡あり）。完全実装が必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合にエクスポージャーが過少見積りされる注記あり。前日終値や取得原価を用いるフォールバック処理が TODO。
- position_sizing:
  - 将来的に銘柄毎の lot_size をサポートする旨の TODO（現状は全銘柄共通の lot_size を想定）。
- テスト：ユニットテストや統合テストは本変更セットに含まれていない（追加推奨）。
- ドキュメント：API ドキュメント・運用手順の整備が必要（README、運用 Playbook 等）。

---

（補足）この CHANGELOG はリポジトリ内ソースコードの内容および docstring・コメントから推測して作成しています。実際のリリースノートとして使用する場合は、実装担当者による確認・加筆を推奨します。